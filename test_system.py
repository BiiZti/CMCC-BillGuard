#!/usr/bin/env python3
"""
CMCC-BillGuard 系统测试脚本
测试各个模块的功能是否正常
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_config_loading():
    """测试配置文件加载"""
    print("🔧 测试配置文件加载...")
    try:
        from detector import BillingAnomalyDetector
        detector = BillingAnomalyDetector()
        print("✅ 配置文件加载成功")
        print(f"   业务类型数量: {len(detector.config['business_types'])}")
        print(f"   风险权重配置: {detector.config['risk_weights']}")
        return True
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False

def test_excel_parser():
    """测试Excel解析器"""
    print("\n📊 测试Excel解析器...")
    try:
        from utils.excel_parser import ExcelParser
        
        # 创建测试数据
        test_data = {
            '账单编号': ['BILL001', 'BILL002', 'BILL003'],
            '营业厅编号': ['BR001', 'BR001', 'BR002'],
            '账单日期': ['2024-01-15', '2024-01-15', '2024-01-15'],
            '操作员ID': ['OP001', 'OP001', 'OP002'],
            '业务类型': ['开户', '充值', '套餐变更'],
            '费用金额': [150.0, 100.0, 200.0],
            '优惠金额': [0.0, 10.0, 20.0],
            '实收金额': [150.0, 90.0, 180.0],
            '操作时间': ['2024-01-15 09:30:00', '2024-01-15 10:15:00', '2024-01-15 11:00:00']
        }
        
        # 创建测试Excel文件
        df = pd.DataFrame(test_data)
        test_file = 'test_billing_data.xlsx'
        df.to_excel(test_file, index=False)
        
        # 测试解析器
        parser = ExcelParser(test_file)
        data = parser.load_data()
        
        if parser.validate_columns():
            print("✅ Excel解析器测试成功")
            print(f"   数据行数: {len(data)}")
            print(f"   列数: {len(data.columns)}")
            
            # 清理测试文件
            os.remove(test_file)
            return True
        else:
            print("❌ Excel列验证失败")
            return False
            
    except Exception as e:
        print(f"❌ Excel解析器测试失败: {e}")
        return False

def test_detector():
    """测试异常检测器"""
    print("\n🔍 测试异常检测器...")
    try:
        from detector import BillingAnomalyDetector
        
        # 创建测试数据
        test_data = []
        base_time = datetime(2024, 1, 15, 9, 0)
        
        # 正常数据
        for i in range(10):
            test_data.append({
                '账单编号': f'BILL{i+1:03d}',
                '营业厅编号': 'BR001',
                '账单日期': base_time.date(),
                '操作员ID': 'OP001',
                '业务类型': '开户',
                '费用金额': 150.0 + np.random.normal(0, 20),
                '优惠金额': 0.0,
                '实收金额': 150.0,
                '操作时间': base_time + timedelta(hours=i)
            })
        
        # 异常数据
        test_data.append({
            '账单编号': 'BILL011',
            '营业厅编号': 'BR001',
            '账单日期': base_time.date(),
            '操作员ID': 'OP001',
            '业务类型': '国际漫游',
            '费用金额': 2000.0,  # 异常高金额
            '优惠金额': 0.0,
            '实收金额': 2000.0,
            '操作时间': base_time + timedelta(hours=23)  # 夜间时间
        })
        
        df = pd.DataFrame(test_data)
        
        # 测试检测器
        detector = BillingAnomalyDetector()
        detector.build_baseline(df)
        risk_scores = detector.detect_anomalies(df)
        
        print("✅ 异常检测器测试成功")
        print(f"   检测记录数: {len(risk_scores)}")
        print(f"   平均风险评分: {np.mean(list(risk_scores.values())):.3f}")
        print(f"   最高风险评分: {max(risk_scores.values()):.3f}")
        
        # 检查异常检测结果
        high_risk = [score for score in risk_scores.values() if score >= 0.7]
        print(f"   高风险记录数: {len(high_risk)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 异常检测器测试失败: {e}")
        return False

def test_visualizer():
    """测试可视化模块"""
    print("\n📈 测试可视化模块...")
    try:
        from utils.visualize import AnomalyVisualizer
        
        # 创建测试数据
        test_data = []
        base_time = datetime(2024, 1, 15, 9, 0)
        
        for i in range(20):
            test_data.append({
                '账单编号': f'BILL{i+1:03d}',
                '营业厅编号': 'BR001',
                '账单日期': base_time.date(),
                '操作员ID': 'OP001',
                '业务类型': '开户',
                '费用金额': 150.0 + np.random.normal(0, 30),
                '优惠金额': 0.0,
                '实收金额': 150.0,
                '操作时间': base_time + timedelta(hours=i)
            })
        
        df = pd.DataFrame(test_data)
        
        # 创建风险评分
        risk_scores = {f'BILL{i+1:03d}': np.random.random() for i in range(20)}
        
        # 测试可视化器
        visualizer = AnomalyVisualizer()
        
        # 测试时间轴图
        timeline_fig = visualizer.create_anomaly_timeline(df, risk_scores)
        print("✅ 时间轴图生成成功")
        
        # 测试风险分布图
        risk_dist_fig = visualizer.create_risk_distribution(risk_scores)
        print("✅ 风险分布图生成成功")
        
        # 测试操作员分析图
        operator_fig = visualizer.create_operator_analysis(df, risk_scores)
        print("✅ 操作员分析图生成成功")
        
        # 测试HTML报告生成
        html_content = visualizer.generate_html_report(df, risk_scores, "test_report.html")
        print("✅ HTML报告生成成功")
        
        # 清理测试文件
        if os.path.exists("test_report.html"):
            os.remove("test_report.html")
        
        return True
        
    except Exception as e:
        print(f"❌ 可视化模块测试失败: {e}")
        return False

def test_frontend_components():
    """测试前端组件"""
    print("\n🌐 测试前端组件...")
    try:
        # 检查index.html文件是否存在
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                content = f.read()
            
            # 检查关键组件
            checks = [
                ("Plotly库", "plotly-latest.min.js" in content),
                ("XLSX库", "xlsx.full.min.js" in content),
                ("文件上传", "fileInput" in content),
                ("异常检测", "detectAnomalies" in content),
                ("可视化图表", "timelineChart" in content),
                ("风险表格", "riskTable" in content)
            ]
            
            all_passed = True
            for check_name, passed in checks:
                if passed:
                    print(f"   ✅ {check_name} - 正常")
                else:
                    print(f"   ❌ {check_name} - 缺失")
                    all_passed = False
            
            return all_passed
        else:
            print("❌ index.html文件不存在")
            return False
            
    except Exception as e:
        print(f"❌ 前端组件测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 CMCC-BillGuard 系统测试开始")
    print("=" * 50)
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("配置文件加载", test_config_loading()))
    test_results.append(("Excel解析器", test_excel_parser()))
    test_results.append(("异常检测器", test_detector()))
    test_results.append(("可视化模块", test_visualizer()))
    test_results.append(("前端组件", test_frontend_components()))
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("📋 测试结果汇总")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<15} {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常")
        print("\n📝 使用说明:")
        print("1. 直接打开 index.html 开始使用")
        print("2. 或运行 Python 脚本进行高级分析")
        print("3. 查看 README_ZH.md 了解详细文档")
    else:
        print("⚠️  部分测试失败，请检查相关模块")
    
    return passed == total

if __name__ == "__main__":
    main() 