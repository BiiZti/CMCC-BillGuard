#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QFileDialog,
    QTabWidget, QHeaderView
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime

class AnomalyDetector:
    """异常检测核心类"""
    def __init__(self, baseline_path="config/baseline.json"):
        self.baseline = self._load_baseline(baseline_path)
    
    def _load_baseline(self, path):
        """加载用户行为基线配置"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "max_night_traffic": 50,  # MB
                "roaming_ratio_threshold": 0.05,
                "high_cost_threshold": 500  # 元
            }
    
    def detect(self, df):
        """执行异常检测"""
        # 数据预处理
        df['日期'] = pd.to_datetime(df['日期'])
        df['是否夜间'] = df['时间段(0-24)'].between(0, 6)
        df['是否国际'] = df['国内/国际'] == '国际'
        
        anomalies = []
        for phone, group in df.groupby('手机号'):
            # 计算关键指标
            night_traffic = group[group['是否夜间']]['流量使用(MB)'].sum()
            roaming_ratio = group['是否国际'].mean()
            max_daily_cost = group['费用(元)'].max()
            avg_daily_traffic = group['流量使用(MB)'].mean()
            
            # 异常检测规则
            reasons = []
            if night_traffic > self.baseline["max_night_traffic"] * 3:
                reasons.append(f"夜间流量异常({night_traffic}MB)")
            if roaming_ratio > self.baseline["roaming_ratio_threshold"] * 5:
                reasons.append("国际漫游突增")
            if max_daily_cost > self.baseline["high_cost_threshold"]:
                reasons.append(f"单日高消费{max_daily_cost}元")
            
            if reasons:
                anomalies.append({
                    '手机号': phone,
                    '异常原因': '，'.join(reasons),
                    '起始日期': group['日期'].min().strftime('%Y-%m-%d'),
                    '结束日期': group['日期'].max().strftime('%Y-%m-%d'),
                    '记录数': len(group)
                })
        
        return pd.DataFrame(anomalies), df

class MainWindow(QMainWindow):
    """主界面"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("中国移动资费异常检测系统 v1.0")
        self.setGeometry(100, 100, 1000, 700)
        
        # 初始化组件
        self.init_ui()
        self.detector = AnomalyDetector()
        self.current_data = None
        
    def init_ui(self):
        """初始化界面布局"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        
        # 顶部控制栏
        control_layout = QHBoxLayout()
        self.btn_open = QPushButton("导入Excel文件")
        self.btn_open.clicked.connect(self.open_file)
        self.btn_export = QPushButton("导出结果")
        self.btn_export.clicked.connect(self.export_results)
        self.btn_export.setEnabled(False)
        control_layout.addWidget(self.btn_open)
        control_layout.addWidget(self.btn_export)
        control_layout.addStretch()
        
        # 结果显示区域
        self.tabs = QTabWidget()
        
        # 异常清单Tab
        self.table_tab = QWidget()
        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "手机号", "异常原因", "起始日期", "结束日期", "记录数"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.table)
        self.table_tab.setLayout(table_layout)
        
        # 可视化Tab
        self.viz_tab = QWidget()
        viz_layout = QVBoxLayout()
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        viz_layout.addWidget(self.canvas)
        self.viz_tab.setLayout(viz_layout)
        
        self.tabs.addTab(self.table_tab, "异常清单")
        self.tabs.addTab(self.viz_tab, "消费趋势")
        
        # 组装主布局
        layout.addLayout(control_layout)
        layout.addWidget(QLabel("检测结果"))
        layout.addWidget(self.tabs)
        main_widget.setLayout(layout)
    
    def open_file(self):
        """打开Excel文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择账单文件", "", 
            "Excel文件 (*.xlsx *.xls);;CSV文件 (*.csv)"
        )
        
        if path:
            try:
                df = pd.read_excel(path) if path.endswith(('.xlsx', '.xls')) else pd.read_csv(path)
                anomalies, processed_df = self.detector.detect(df)
                
                # 显示结果
                self.show_results(anomalies)
                self.plot_analysis(processed_df, anomalies)
                self.current_data = anomalies
                self.btn_export.setEnabled(True)
                
            except Exception as e:
                self.show_error(f"文件解析失败: {str(e)}")
    
    def show_results(self, df):
        """在表格中显示检测结果"""
        self.table.setRowCount(len(df))
        for row_idx, row in df.iterrows():
            for col_idx, col in enumerate(df.columns):
                item = QTableWidgetItem(str(row[col]))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)
    
    def plot_analysis(self, df, anomalies):
        """绘制消费趋势图"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 绘制所有用户流量使用基线
        df.groupby('日期')['流量使用(MB)'].mean().plot(
            ax=ax, color='gray', alpha=0.3, label='平均流量'
        )
        
        # 高亮异常用户
        for _, anomaly in anomalies.iterrows():
            user_data = df[df['手机号'] == anomaly['手机号']]
            user_data.plot(
                x='日期', y='流量使用(MB)', 
                ax=ax, marker='o', 
                label=f"{anomaly['手机号']} (异常)"
            )
        
        ax.set_title("用户流量使用趋势（异常用户高亮）")
        ax.set_ylabel("流量使用(MB)")
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        self.canvas.draw()
    
    def export_results(self):
        """导出检测结果"""
        if self.current_data is not None:
            path, _ = QFileDialog.getSaveFileName(
                self, "保存结果", "",
                "CSV文件 (*.csv);;Excel文件 (*.xlsx)"
            )
            if path:
                try:
                    if path.endswith('.csv'):
                        self.current_data.to_csv(path, index=False, encoding='utf_8_sig')
                    else:
                        self.current_data.to_excel(path, index=False)
                except Exception as e:
                    self.show_error(f"导出失败: {str(e)}")
    
    def show_error(self, message):
        """显示错误信息"""
        error_label = QLabel(message)
        error_label.setStyleSheet("color: red;")
        error_label.setAlignment(Qt.AlignCenter)
        
        # 临时替换显示内容
        self.tabs.widget(0).layout().addWidget(error_label)
        QApplication.processEvents()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    