"""
可视化模块
用于生成异常检测结果的可视化图表
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AnomalyVisualizer:
    """异常检测结果可视化器"""
    
    def __init__(self):
        """初始化可视化器"""
        self.colors = {
            'normal': '#2E8B57',      # 正常 - 绿色
            'low_risk': '#FFD700',    # 低风险 - 金色
            'medium_risk': '#FF8C00', # 中风险 - 橙色
            'high_risk': '#DC143C',   # 高风险 - 红色
            'baseline': '#4169E1'     # 基线 - 蓝色
        }
    
    def create_anomaly_timeline(self, 
                               data: pd.DataFrame,
                               risk_scores: Dict[str, float],
                               baseline_data: Optional[pd.DataFrame] = None) -> go.Figure:
        """
        创建异常时间轴图
        
        Args:
            data: 账单数据
            risk_scores: 风险评分字典 {账单编号: 风险分数}
            baseline_data: 基线数据
            
        Returns:
            Plotly图表对象
        """
        # 创建子图
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('费用金额趋势', '操作频率', '风险评分'),
            vertical_spacing=0.1,
            row_heights=[0.4, 0.3, 0.3]
        )
        
        # 添加费用金额趋势
        fig.add_trace(
            go.Scatter(
                x=data['操作时间'],
                y=data['费用金额'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=[self._get_risk_color(risk_scores.get(str(bill_id), 0)) 
                           for bill_id in data['账单编号']],
                    colorscale='RdYlGn_r'
                ),
                name='费用金额',
                hovertemplate='<b>账单编号:</b> %{customdata}<br>' +
                            '<b>时间:</b> %{x}<br>' +
                            '<b>金额:</b> %{y:.2f}<br>' +
                            '<b>风险评分:</b> %{marker.color}<extra></extra>',
                customdata=data['账单编号']
            ),
            row=1, col=1
        )
        
        # 添加基线（如果有）
        if baseline_data is not None:
            fig.add_trace(
                go.Scatter(
                    x=baseline_data['操作时间'],
                    y=baseline_data['费用金额'],
                    mode='lines',
                    line=dict(color=self.colors['baseline'], width=2, dash='dash'),
                    name='历史基线',
                    hovertemplate='<b>基线金额:</b> %{y:.2f}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 添加操作频率
        hourly_counts = data.groupby(data['操作时间'].dt.hour).size()
        fig.add_trace(
            go.Bar(
                x=hourly_counts.index,
                y=hourly_counts.values,
                name='操作频率',
                marker_color=self.colors['normal'],
                hovertemplate='<b>小时:</b> %{x}:00<br>' +
                            '<b>操作次数:</b> %{y}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 添加风险评分时间轴
        risk_data = [(data.iloc[i]['操作时间'], risk_scores.get(str(data.iloc[i]['账单编号']), 0))
                    for i in range(len(data))]
        risk_times, risk_values = zip(*risk_data)
        
        fig.add_trace(
            go.Scatter(
                x=risk_times,
                y=risk_values,
                mode='markers+lines',
                marker=dict(
                    size=10,
                    color=risk_values,
                    colorscale='RdYlGn_r',
                    showscale=True,
                    colorbar=dict(title="风险评分")
                ),
                line=dict(color='gray', width=1),
                name='风险评分',
                hovertemplate='<b>时间:</b> %{x}<br>' +
                            '<b>风险评分:</b> %{y:.3f}<extra></extra>'
            ),
            row=3, col=1
        )
        
        # 更新布局
        fig.update_layout(
            title='资费异常检测时间轴分析',
            height=800,
            showlegend=True,
            hovermode='closest'
        )
        
        # 更新x轴标签
        fig.update_xaxes(title_text="时间", row=3, col=1)
        fig.update_xaxes(title_text="小时", row=2, col=1)
        fig.update_xaxes(title_text="时间", row=1, col=1)
        
        # 更新y轴标签
        fig.update_yaxes(title_text="费用金额 (元)", row=1, col=1)
        fig.update_yaxes(title_text="操作次数", row=2, col=1)
        fig.update_yaxes(title_text="风险评分", row=3, col=1)
        
        return fig
    
    def create_risk_distribution(self, risk_scores: Dict[str, float]) -> go.Figure:
        """
        创建风险分布图
        
        Args:
            risk_scores: 风险评分字典
            
        Returns:
            Plotly图表对象
        """
        risk_values = list(risk_scores.values())
        
        # 定义风险等级
        low_risk = [v for v in risk_values if v < 0.3]
        medium_risk = [v for v in risk_values if 0.3 <= v < 0.7]
        high_risk = [v for v in risk_values if v >= 0.7]
        
        fig = go.Figure()
        
        # 添加风险分布直方图
        fig.add_trace(go.Histogram(
            x=risk_values,
            nbinsx=20,
            name='风险分布',
            marker_color='lightblue',
            opacity=0.7
        ))
        
        # 添加风险等级垂直线
        fig.add_vline(x=0.3, line_dash="dash", line_color="orange", 
                     annotation_text="低风险阈值")
        fig.add_vline(x=0.7, line_dash="dash", line_color="red", 
                     annotation_text="高风险阈值")
        
        fig.update_layout(
            title='风险评分分布',
            xaxis_title='风险评分',
            yaxis_title='频次',
            showlegend=False
        )
        
        return fig
    
    def create_operator_analysis(self, data: pd.DataFrame, 
                                risk_scores: Dict[str, float]) -> go.Figure:
        """
        创建操作员分析图
        
        Args:
            data: 账单数据
            risk_scores: 风险评分字典
            
        Returns:
            Plotly图表对象
        """
        # 计算每个操作员的风险统计
        operator_risks = {}
        for _, row in data.iterrows():
            operator_id = row['操作员ID']
            bill_id = str(row['账单编号'])
            risk_score = risk_scores.get(bill_id, 0)
            
            if operator_id not in operator_risks:
                operator_risks[operator_id] = []
            operator_risks[operator_id].append(risk_score)
        
        # 计算统计指标
        operator_stats = {}
        for operator_id, risks in operator_risks.items():
            operator_stats[operator_id] = {
                'avg_risk': np.mean(risks),
                'max_risk': np.max(risks),
                'high_risk_count': sum(1 for r in risks if r >= 0.7),
                'total_operations': len(risks)
            }
        
        # 创建散点图
        operators = list(operator_stats.keys())
        avg_risks = [operator_stats[op]['avg_risk'] for op in operators]
        operation_counts = [operator_stats[op]['total_operations'] for op in operators]
        high_risk_counts = [operator_stats[op]['high_risk_count'] for op in operators]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=operation_counts,
            y=avg_risks,
            mode='markers',
            marker=dict(
                size=[max(10, count/10) for count in high_risk_counts],
                color=avg_risks,
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(title="平均风险评分")
            ),
            text=operators,
            hovertemplate='<b>操作员:</b> %{text}<br>' +
                        '<b>操作次数:</b> %{x}<br>' +
                        '<b>平均风险:</b> %{y:.3f}<br>' +
                        '<b>高风险操作:</b> %{marker.size}<extra></extra>'
        ))
        
        fig.update_layout(
            title='操作员风险分析',
            xaxis_title='操作次数',
            yaxis_title='平均风险评分',
            height=500
        )
        
        return fig
    
    def create_business_type_analysis(self, data: pd.DataFrame,
                                    risk_scores: Dict[str, float]) -> go.Figure:
        """
        创建业务类型分析图
        
        Args:
            data: 账单数据
            risk_scores: 风险评分字典
            
        Returns:
            Plotly图表对象
        """
        # 按业务类型分组分析
        business_risks = {}
        for _, row in data.iterrows():
            business_type = row['业务类型']
            bill_id = str(row['账单编号'])
            risk_score = risk_scores.get(bill_id, 0)
            
            if business_type not in business_risks:
                business_risks[business_type] = []
            business_risks[business_type].append(risk_score)
        
        # 计算统计指标
        business_stats = {}
        for business_type, risks in business_risks.items():
            business_stats[business_type] = {
                'avg_risk': np.mean(risks),
                'std_risk': np.std(risks),
                'count': len(risks)
            }
        
        # 创建箱线图数据
        fig = go.Figure()
        
        for business_type, risks in business_risks.items():
            fig.add_trace(go.Box(
                y=risks,
                name=business_type,
                boxpoints='outliers',
                jitter=0.3,
                pointpos=-1.8
            ))
        
        fig.update_layout(
            title='业务类型风险分布',
            yaxis_title='风险评分',
            height=500
        )
        
        return fig
    
    def _get_risk_color(self, risk_score: float) -> str:
        """
        根据风险评分获取颜色
        
        Args:
            risk_score: 风险评分
            
        Returns:
            颜色字符串
        """
        if risk_score < 0.3:
            return self.colors['low_risk']
        elif risk_score < 0.7:
            return self.colors['medium_risk']
        else:
            return self.colors['high_risk']
    
    def generate_html_report(self, 
                           data: pd.DataFrame,
                           risk_scores: Dict[str, float],
                           baseline_data: Optional[pd.DataFrame] = None,
                           output_path: str = "anomaly_report.html") -> str:
        """
        生成完整的HTML报告
        
        Args:
            data: 账单数据
            risk_scores: 风险评分字典
            baseline_data: 基线数据
            output_path: 输出文件路径
            
        Returns:
            HTML内容字符串
        """
        # 生成所有图表
        timeline_fig = self.create_anomaly_timeline(data, risk_scores, baseline_data)
        risk_dist_fig = self.create_risk_distribution(risk_scores)
        operator_fig = self.create_operator_analysis(data, risk_scores)
        business_fig = self.create_business_type_analysis(data, risk_scores)
        
        # 生成风险用户清单
        high_risk_bills = [(bill_id, score) for bill_id, score in risk_scores.items() 
                          if score >= 0.7]
        high_risk_bills.sort(key=lambda x: x[1], reverse=True)
        
        # 创建HTML内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>资费异常检测报告</title>
            <meta charset="utf-8">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 30px 0; }}
                .chart {{ margin: 20px 0; }}
                .risk-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .risk-table th, .risk-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .risk-table th {{ background-color: #f2f2f2; }}
                .high-risk {{ background-color: #ffebee; }}
                .medium-risk {{ background-color: #fff3e0; }}
                .low-risk {{ background-color: #f1f8e9; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>资费异常检测报告</h1>
                <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>总记录数: {len(data)} | 高风险记录: {len(high_risk_bills)}</p>
            </div>
            
            <div class="section">
                <h2>异常检测时间轴</h2>
                <div class="chart">
                    {timeline_fig.to_html(full_html=False)}
                </div>
            </div>
            
            <div class="section">
                <h2>风险分布分析</h2>
                <div class="chart">
                    {risk_dist_fig.to_html(full_html=False)}
                </div>
            </div>
            
            <div class="section">
                <h2>操作员风险分析</h2>
                <div class="chart">
                    {operator_fig.to_html(full_html=False)}
                </div>
            </div>
            
            <div class="section">
                <h2>业务类型风险分析</h2>
                <div class="chart">
                    {business_fig.to_html(full_html=False)}
                </div>
            </div>
            
            <div class="section">
                <h2>高风险用户清单</h2>
                <table class="risk-table">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>账单编号</th>
                            <th>风险评分</th>
                            <th>风险等级</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, (bill_id, score) in enumerate(high_risk_bills[:50], 1):  # 显示前50个
            risk_level = "高风险" if score >= 0.7 else "中风险" if score >= 0.3 else "低风险"
            row_class = "high-risk" if score >= 0.7 else "medium-risk" if score >= 0.3 else "low-risk"
            
            html_content += f"""
                        <tr class="{row_class}">
                            <td>{i}</td>
                            <td>{bill_id}</td>
                            <td>{score:.3f}</td>
                            <td>{risk_level}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        
        # 保存HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML报告已生成: {output_path}")
        return html_content 