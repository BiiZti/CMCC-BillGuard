"""
Excel处理模块
用于解析和处理营业厅账单Excel文件
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)


class ExcelParser:
    """Excel文件解析器"""
    
    def __init__(self, file_path: str):
        """
        初始化Excel解析器
        
        Args:
            file_path: Excel文件路径
        """
        self.file_path = file_path
        self.data = None
        self.required_columns = [
            '账单编号', '营业厅编号', '账单日期', '操作员ID',
            '业务类型', '费用金额', '优惠金额', '实收金额', '操作时间'
        ]
    
    def load_data(self) -> pd.DataFrame:
        """
        加载Excel数据
        
        Returns:
            包含账单数据的DataFrame
        """
        try:
            self.data = pd.read_excel(self.file_path)
            logger.info(f"成功加载Excel文件: {self.file_path}")
            return self.data
        except Exception as e:
            logger.error(f"加载Excel文件失败: {e}")
            raise
    
    def validate_columns(self) -> bool:
        """
        验证必需列是否存在
        
        Returns:
            验证是否通过
        """
        if self.data is None:
            logger.error("数据未加载")
            return False
        
        missing_columns = set(self.required_columns) - set(self.data.columns)
        if missing_columns:
            logger.error(f"缺少必需列: {missing_columns}")
            return False
        
        logger.info("列验证通过")
        return True
    
    def clean_data(self) -> pd.DataFrame:
        """
        数据清洗
        
        Returns:
            清洗后的DataFrame
        """
        if self.data is None:
            raise ValueError("数据未加载")
        
        # 删除重复行
        original_count = len(self.data)
        self.data = self.data.drop_duplicates()
        logger.info(f"删除重复行: {original_count - len(self.data)} 行")
        
        # 处理缺失值
        self.data = self.data.dropna(subset=['账单编号', '营业厅编号', '操作员ID'])
        
        # 数据类型转换
        self.data['账单日期'] = pd.to_datetime(self.data['账单日期'])
        self.data['操作时间'] = pd.to_datetime(self.data['操作时间'])
        self.data['费用金额'] = pd.to_numeric(self.data['费用金额'], errors='coerce')
        self.data['优惠金额'] = pd.to_numeric(self.data['优惠金额'], errors='coerce')
        self.data['实收金额'] = pd.to_numeric(self.data['实收金额'], errors='coerce')
        
        # 填充缺失的数值为0
        numeric_columns = ['费用金额', '优惠金额', '实收金额']
        self.data[numeric_columns] = self.data[numeric_columns].fillna(0)
        
        logger.info("数据清洗完成")
        return self.data
    
    def extract_business_hours_operations(self, 
                                        start_time: time = time(9, 0),
                                        end_time: time = time(18, 0)) -> pd.DataFrame:
        """
        提取营业时间内的操作
        
        Args:
            start_time: 营业开始时间
            end_time: 营业结束时间
            
        Returns:
            营业时间内的操作数据
        """
        if self.data is None:
            raise ValueError("数据未加载")
        
        # 提取操作时间的小时部分
        operation_times = self.data['操作时间'].dt.time
        
        # 筛选营业时间内的操作
        business_hours_mask = (operation_times >= start_time) & (operation_times <= end_time)
        business_hours_data = self.data[business_hours_mask].copy()
        
        logger.info(f"营业时间内操作数量: {len(business_hours_data)}")
        return business_hours_data
    
    def get_operator_statistics(self) -> Dict:
        """
        获取操作员统计信息
        
        Returns:
            操作员统计字典
        """
        if self.data is None:
            raise ValueError("数据未加载")
        
        stats = {}
        
        # 按操作员分组统计
        operator_stats = self.data.groupby('操作员ID').agg({
            '账单编号': 'count',
            '费用金额': ['sum', 'mean', 'std'],
            '实收金额': ['sum', 'mean', 'std']
        }).round(2)
        
        # 重命名列
        operator_stats.columns = [
            '操作次数', '费用总额', '平均费用', '费用标准差',
            '实收总额', '平均实收', '实收标准差'
        ]
        
        stats['operator_stats'] = operator_stats.to_dict('index')
        
        # 按业务类型统计
        business_stats = self.data.groupby('业务类型').agg({
            '账单编号': 'count',
            '费用金额': ['sum', 'mean'],
            '实收金额': ['sum', 'mean']
        }).round(2)
        
        business_stats.columns = [
            '操作次数', '费用总额', '平均费用', '实收总额', '平均实收'
        ]
        
        stats['business_stats'] = business_stats.to_dict('index')
        
        return stats
    
    def export_cleaned_data(self, output_path: str) -> None:
        """
        导出清洗后的数据
        
        Args:
            output_path: 输出文件路径
        """
        if self.data is None:
            raise ValueError("数据未加载")
        
        try:
            self.data.to_excel(output_path, index=False)
            logger.info(f"数据已导出到: {output_path}")
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            raise


def parse_bill_excel(file_path: str, 
                    clean_data: bool = True,
                    validate_columns: bool = True) -> pd.DataFrame:
    """
    解析账单Excel文件的便捷函数
    
    Args:
        file_path: Excel文件路径
        clean_data: 是否进行数据清洗
        validate_columns: 是否验证列
        
    Returns:
        解析后的DataFrame
    """
    parser = ExcelParser(file_path)
    parser.load_data()
    
    if validate_columns:
        if not parser.validate_columns():
            raise ValueError("列验证失败")
    
    if clean_data:
        return parser.clean_data()
    
    return parser.data 