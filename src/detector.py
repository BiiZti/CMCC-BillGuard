"""
资费异常检测核心模块
识别异常消费模式，对比用户历史行为基线
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import json
import logging
from datetime import datetime, time, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class BillingAnomalyDetector:
    """资费异常检测器"""
    
    def __init__(self, config_path: str = "src/config/baseline.json"):
        """
        初始化检测器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.baseline_data = None
        self.operator_baselines = {}
        self.business_type_baselines = {}
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"成功加载配置文件: {config_path}")
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def build_baseline(self, historical_data: pd.DataFrame) -> None:
        """
        构建用户行为基线
        
        Args:
            historical_data: 历史账单数据
        """
        logger.info("开始构建用户行为基线...")
        
        # 存储基线数据
        self.baseline_data = historical_data.copy()
        
        # 构建操作员基线
        self._build_operator_baselines(historical_data)
        
        # 构建业务类型基线
        self._build_business_type_baselines(historical_data)
        
        logger.info("用户行为基线构建完成")
    
    def _build_operator_baselines(self, data: pd.DataFrame) -> None:
        """构建操作员行为基线"""
        for operator_id in data['操作员ID'].unique():
            operator_data = data[data['操作员ID'] == operator_id]
            
            if len(operator_data) < self.config['operators']['min_operations_for_baseline']:
                continue
            
            baseline = {
                'avg_amount': operator_data['费用金额'].mean(),
                'std_amount': operator_data['费用金额'].std(),
                'avg_frequency_per_day': len(operator_data) / max(1, (operator_data['账单日期'].max() - operator_data['账单日期'].min()).days),
                'business_type_distribution': operator_data['业务类型'].value_counts().to_dict(),
                'hourly_distribution': operator_data['操作时间'].dt.hour.value_counts().to_dict()
            }
            
            self.operator_baselines[operator_id] = baseline
    
    def _build_business_type_baselines(self, data: pd.DataFrame) -> None:
        """构建业务类型基线"""
        for business_type in data['业务类型'].unique():
            business_data = data[data['业务类型'] == business_type]
            
            baseline = {
                'avg_amount': business_data['费用金额'].mean(),
                'std_amount': business_data['费用金额'].std(),
                'avg_frequency_per_day': len(business_data) / max(1, (business_data['账单日期'].max() - business_data['账单日期'].min()).days),
                'hourly_distribution': business_data['操作时间'].dt.hour.value_counts().to_dict()
            }
            
            self.business_type_baselines[business_type] = baseline
    
    def detect_anomalies(self, current_data: pd.DataFrame) -> Dict[str, float]:
        """
        检测异常
        
        Args:
            current_data: 当前账单数据
            
        Returns:
            风险评分字典 {账单编号: 风险分数}
        """
        logger.info("开始异常检测...")
        
        risk_scores = {}
        
        for _, row in current_data.iterrows():
            bill_id = str(row['账单编号'])
            
            # 计算各维度的异常度
            amount_anomaly = self._calculate_amount_anomaly(row)
            frequency_anomaly = self._calculate_frequency_anomaly(row, current_data)
            time_anomaly = self._calculate_time_anomaly(row)
            operator_anomaly = self._calculate_operator_anomaly(row)
            
            # 特殊模式检测
            special_pattern_boost = self._detect_special_patterns(row, current_data)
            
            # 计算综合风险评分
            risk_score = (
                self.config['risk_weights']['amount_anomaly'] * amount_anomaly +
                self.config['risk_weights']['frequency_anomaly'] * frequency_anomaly +
                self.config['risk_weights']['time_anomaly'] * time_anomaly +
                self.config['risk_weights']['operator_anomaly'] * operator_anomaly
            )
            
            # 应用特殊模式加成
            risk_score = min(1.0, risk_score + special_pattern_boost)
            
            risk_scores[bill_id] = risk_score
        
        logger.info(f"异常检测完成，共检测 {len(risk_scores)} 条记录")
        return risk_scores
    
    def _calculate_amount_anomaly(self, row: pd.Series) -> float:
        """计算金额异常度"""
        amount = row['费用金额']
        business_type = row['业务类型']
        bt_cfg = self._get_business_type_config(business_type)
        # 优先用业务类型独立阈值
        thresholds = bt_cfg.get('amount_thresholds', self.config['anomaly_thresholds']['amount'])
        normal_range = bt_cfg.get('normal_amount_range', [0, float('inf')])
        min_amount, max_amount = normal_range
        if amount < min_amount or amount > max_amount:
            deviation = abs(amount - (min_amount if amount < min_amount else max_amount)) / max(max_amount, 1)
            # 按阈值分级
            if deviation >= thresholds.get('high', 0.8):
                return 1.0
            elif deviation >= thresholds.get('medium', 0.5):
                return 0.7
            elif deviation >= thresholds.get('low', 0.2):
                return 0.4
            else:
                return 0.1
        
        # 如果没有基线数据，使用统计方法
        if business_type in self.business_type_baselines:
            baseline = self.business_type_baselines[business_type]
            mean_amount = baseline['avg_amount']
            std_amount = baseline['std_amount']
            
            if std_amount > 0:
                z_score = abs(amount - mean_amount) / std_amount
                return min(1.0, z_score / 3.0)  # 标准化到0-1范围
        
        return 0.0
    
    def _calculate_frequency_anomaly(self, row: pd.Series, data: pd.DataFrame) -> float:
        """计算频率异常度"""
        operator_id = row['操作员ID']
        operation_time = row['操作时间']
        
        # 计算当天该操作员的操作次数
        same_day_operations = data[
            (data['操作员ID'] == operator_id) &
            (data['操作时间'].dt.date == operation_time.date())
        ]
        
        daily_frequency = len(same_day_operations)
        
        # 与基线比较
        if operator_id in self.operator_baselines:
            baseline_frequency = self.operator_baselines[operator_id]['avg_frequency_per_day']
            
            if baseline_frequency > 0:
                frequency_ratio = daily_frequency / baseline_frequency
                if frequency_ratio > 1.5:  # 超过基线1.5倍
                    return min(1.0, (frequency_ratio - 1.5) / 2.0)
        
        # 与业务类型基线比较
        business_type = row['业务类型']
        if business_type in self.config['business_types']:
            normal_frequency = self.config['business_types'][business_type]['normal_frequency_per_day']
            
            if daily_frequency > normal_frequency * 2:
                return min(1.0, (daily_frequency - normal_frequency * 2) / normal_frequency)
        
        return 0.0
    
    def _calculate_time_anomaly(self, row: pd.Series) -> float:
        """计算时间异常度"""
        operation_time = row['操作时间']
        operation_hour = operation_time.hour
        is_weekend = operation_time.weekday() >= 5
        
        # 检查是否在营业时间外
        business_hours = self.config['time_patterns']['business_hours']
        start_hour = int(business_hours['start'].split(':')[0])
        end_hour = int(business_hours['end'].split(':')[0])
        
        if operation_hour < start_hour or operation_hour > end_hour:
            # 非营业时间操作
            if operation_hour < start_hour:
                deviation = (start_hour - operation_hour) / 24
            else:
                deviation = (operation_hour - end_hour) / 24
            
            time_anomaly = min(1.0, deviation * 2)  # 放大非营业时间的异常度
            
            # 周末加成
            if is_weekend:
                time_anomaly *= self.config['time_patterns']['weekend_multiplier']
            
            return time_anomaly
        
        return 0.0
    
    def _calculate_operator_anomaly(self, row: pd.Series) -> float:
        """计算操作员行为异常度"""
        operator_id = row['操作员ID']
        business_type = row['业务类型']
        operation_hour = row['操作时间'].hour
        
        if operator_id not in self.operator_baselines:
            return 0.0
        
        baseline = self.operator_baselines[operator_id]
        
        # 检查业务类型分布异常
        business_dist = baseline['business_type_distribution']
        total_operations = sum(business_dist.values())
        
        if total_operations > 0:
            expected_ratio = business_dist.get(business_type, 0) / total_operations
            if expected_ratio < 0.1:  # 该操作员很少办理此类业务
                return 0.3
        
        # 检查时间分布异常
        hourly_dist = baseline['hourly_distribution']
        total_hourly = sum(hourly_dist.values())
        
        if total_hourly > 0:
            expected_hourly_ratio = hourly_dist.get(operation_hour, 0) / total_hourly
            if expected_hourly_ratio < 0.05:  # 该操作员很少在这个时间操作
                return 0.2
        
        return 0.0
    
    def _detect_special_patterns(self, row: pd.Series, data: pd.DataFrame) -> float:
        """检测特殊异常模式"""
        business_type = row['业务类型']
        bt_cfg = self._get_business_type_config(business_type)
        boost = 0.0
        # 业务类型特殊规则优先
        special_rules = bt_cfg.get('special_rules', {})
        # 全局规则
        global_rules = self.config.get('special_patterns', {})
        # 夜间高流量
        if special_rules.get('night_high_traffic', global_rules.get('night_high_traffic', {}).get('enabled', False)):
            boost += self._detect_night_high_traffic(row, data)
        # 国际漫游突增
        if special_rules.get('roaming_surge', global_rules.get('international_roaming_surge', {}).get('enabled', False)):
            boost += self._detect_international_roaming_surge(row, data)
        # 快速连续操作
        if special_rules.get('rapid_succession', global_rules.get('rapid_succession', {}).get('enabled', False)):
            boost += self._detect_rapid_succession(row, data)
        return boost
    
    def _detect_night_high_traffic(self, row: pd.Series, data: pd.DataFrame) -> float:
        """检测夜间高流量模式"""
        operation_time = row['操作时间']
        night_hours = self.config['time_patterns']['night_hours']
        start_hour = int(night_hours['start'].split(':')[0])
        end_hour = int(night_hours['end'].split(':')[0])
        
        # 检查是否在夜间时段
        is_night = False
        if start_hour > end_hour:  # 跨日夜间时段
            is_night = operation_time.hour >= start_hour or operation_time.hour <= end_hour
        else:
            is_night = start_hour <= operation_time.hour <= end_hour
        
        if is_night:
            # 检查夜间操作频率
            night_operations = data[
                (data['操作时间'].dt.date == operation_time.date()) &
                ((data['操作时间'].dt.hour >= start_hour) | (data['操作时间'].dt.hour <= end_hour))
            ]
            
            if len(night_operations) > 5:  # 夜间操作超过5次
                return self.config['special_patterns']['night_high_traffic']['risk_boost']
        
        return 0.0
    
    def _detect_international_roaming_surge(self, row: pd.Series, data: pd.DataFrame) -> float:
        """检测国际漫游突增"""
        if row['业务类型'] == '国际漫游':
            operation_time = row['操作时间']
            
            # 检查最近7天的国际漫游操作
            week_ago = operation_time - timedelta(days=7)
            recent_roaming = data[
                (data['业务类型'] == '国际漫游') &
                (data['操作时间'] >= week_ago) &
                (data['操作时间'] <= operation_time)
            ]
            
            if len(recent_roaming) > 3:  # 一周内国际漫游超过3次
                return self.config['special_patterns']['international_roaming_surge']['risk_boost']
        
        return 0.0
    
    def _detect_rapid_succession(self, row: pd.Series, data: pd.DataFrame) -> float:
        """检测快速连续操作"""
        operation_time = row['操作时间']
        operator_id = row['操作员ID']
        min_interval = self.config['special_patterns']['rapid_succession']['min_interval_seconds']
        
        # 检查同一操作员在短时间内是否有其他操作
        recent_operations = data[
            (data['操作员ID'] == operator_id) &
            (data['操作时间'] < operation_time) &
            (data['操作时间'] >= operation_time - timedelta(seconds=min_interval))
        ]
        
        if len(recent_operations) > 0:
            return self.config['special_patterns']['rapid_succession']['risk_boost']
        
        return 0.0
    
    def get_high_risk_records(self, risk_scores: Dict[str, float], 
                            threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        获取高风险记录
        
        Args:
            risk_scores: 风险评分字典
            threshold: 高风险阈值
            
        Returns:
            高风险记录列表 [(账单编号, 风险评分)]
        """
        high_risk = [(bill_id, score) for bill_id, score in risk_scores.items() 
                    if score >= threshold]
        high_risk.sort(key=lambda x: x[1], reverse=True)
        return high_risk
    
    def generate_anomaly_summary(self, data: pd.DataFrame, 
                               risk_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        生成异常检测摘要
        
        Args:
            data: 账单数据
            risk_scores: 风险评分字典
            
        Returns:
            检测摘要字典
        """
        total_records = len(data)
        risk_values = list(risk_scores.values())
        
        summary = {
            'total_records': total_records,
            'high_risk_count': sum(1 for score in risk_values if score >= 0.7),
            'medium_risk_count': sum(1 for score in risk_values if 0.3 <= score < 0.7),
            'low_risk_count': sum(1 for score in risk_values if score < 0.3),
            'avg_risk_score': np.mean(risk_values),
            'max_risk_score': np.max(risk_values),
            'risk_distribution': {
                '0-0.3': sum(1 for score in risk_values if score < 0.3),
                '0.3-0.7': sum(1 for score in risk_values if 0.3 <= score < 0.7),
                '0.7-1.0': sum(1 for score in risk_values if score >= 0.7)
            }
        }
        
        return summary

    def reload_config(self, config_path: str = None):
        """
        动态重新加载配置文件（支持热更新）
        Args:
            config_path: 可选，新的配置文件路径
        """
        if config_path:
            self.config = self._load_config(config_path)
        else:
            self.config = self._load_config(self.config_path)
        logger.info(f"配置文件已热更新: {config_path or self.config_path}")

    def _get_business_type_config(self, business_type: str) -> dict:
        """
        获取业务类型的独立配置（含阈值和特殊规则）
        """
        return self.config['business_types'].get(business_type, {})