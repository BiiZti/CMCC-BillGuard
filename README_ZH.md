# CMCC-BillGuard 资费异常检测系统

## 📋 项目简介

CMCC-BillGuard 是一个智能资费异常检测系统，专门用于识别营业厅账单中的异常消费模式。系统通过多维度分析，包括金额异常、时间异常、频率异常和特殊模式检测，为用户提供全面的风险评估。

## ✨ 主要功能

### 🔍 异常检测
- **金额异常检测**: 识别超出正常范围的费用金额
- **时间异常检测**: 检测非营业时间的操作行为
- **频率异常检测**: 识别异常的操作频率模式
- **特殊模式检测**: 
  - 夜间高流量检测
  - 国际漫游突增检测
  - 快速连续操作检测

### 📊 可视化分析
- **异常检测时间轴**: 展示费用金额趋势和风险评分
- **风险分布分析**: 统计风险评分的分布情况
- **操作员风险分析**: 分析各操作员的风险表现
- **高风险用户清单**: 列出需要重点关注的高风险记录

### 📈 报告生成
- **实时风险评分**: 为每条记录计算综合风险评分
- **风险等级分类**: 低风险(0-0.3)、中风险(0.3-0.7)、高风险(0.7-1.0)
- **Excel报告导出**: 支持将检测结果导出为Excel文件

## 🚀 快速开始

### 方式一：纯前端使用（推荐）

1. **下载项目文件**
   ```bash
   git clone https://github.com/your-repo/CMCC-BillGuard.git
   cd CMCC-BillGuard
   ```

2. **打开Web界面**
   - 直接双击 `index.html` 文件
   - 或在浏览器中打开 `index.html`

3. **上传Excel文件**
   - 支持 `.xlsx` 和 `.xls` 格式
   - 拖拽文件到上传区域或点击选择文件

4. **开始检测**
   - 点击"开始检测"按钮
   - 系统将自动分析数据并生成可视化结果

### 方式二：Python后端使用

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **运行检测**
   ```python
   from src.detector import BillingAnomalyDetector
   from src.utils.excel_parser import ExcelParser
   from src.utils.visualize import AnomalyVisualizer
   
   # 初始化检测器
   detector = BillingAnomalyDetector()
   
   # 解析Excel文件
   parser = ExcelParser("your_billing_file.xlsx")
   data = parser.load_data()
   data = parser.clean_data()
   
   # 构建基线（可选）
   detector.build_baseline(data)
   
   # 执行异常检测
   risk_scores = detector.detect_anomalies(data)
   
   # 生成可视化报告
   visualizer = AnomalyVisualizer()
   visualizer.generate_html_report(data, risk_scores, "anomaly_report.html")
   ```

## 📁 项目结构

```
CMCC-BillGuard/
├── docs/                       # 文档
│   ├── 数据字段说明.md         # 数据字段详细说明
│   └── 异常检测规则详解.md     # 检测算法和规则说明
├── src/
│   ├── main.py                 # PyQt主程序（可选）
│   ├── detector.py             # 核心检测逻辑
│   ├── utils/
│   │   ├── excel_parser.py     # Excel处理模块
│   │   └── visualize.py        # 可视化模块
│   └── config/
│       └── baseline.json       # 用户行为基线配置
├── samples/                    # 示例数据
│   └── 营业厅账单模板.xlsx     # 示例Excel文件
├── index.html                  # 纯前端Web界面
├── requirements.txt            # Python依赖清单
└── README_ZH.md               # 中文说明文档
```

## 📊 数据格式要求

Excel文件必须包含以下列：

| 列名 | 说明 | 示例 |
|------|------|------|
| 账单编号 | 唯一标识符 | BILL001 |
| 营业厅编号 | 营业厅标识 | BR001 |
| 账单日期 | 业务办理日期 | 2024-01-15 |
| 操作员ID | 处理业务的操作员 | OP001 |
| 业务类型 | 业务类型 | 开户、销户、套餐变更、充值、流量包、国际漫游 |
| 费用金额 | 业务费用 | 150.00 |
| 优惠金额 | 优惠减免金额 | 10.00 |
| 实收金额 | 实际收取金额 | 140.00 |
| 操作时间 | 具体操作时间 | 2024-01-15 09:30:00 |

## ⚙️ 配置说明

### 基线配置文件 (`src/config/baseline.json`)

- **每个业务类型可独立配置：**
  - 正常金额区间、频率、权重
  - 金额异常阈值（low/medium/high）
  - 特殊检测规则开关（如夜间高流量、快速连续、漫游突增等）

```json
{
  "business_types": {
    "开户": {
      "normal_amount_range": [0, 200],
      "normal_frequency_per_day": 10,
      "risk_weight": 0.3,
      "amount_thresholds": {"low": 0.2, "medium": 0.5, "high": 0.8},
      "special_rules": {"night_high_traffic": true, "rapid_succession": false}
    },
    ...
  },
  ...
}
```

- **全局特殊检测规则**
  - `special_patterns` 节点可统一开关和调整全局特殊检测参数。

### 规则配置示例说明
- 业务类型"开户"夜间高流量检测开启，快速连续检测关闭。
- 业务类型"国际漫游"夜间高流量、快速连续、漫游突增检测均开启。
- 每个业务类型可单独调整金额异常阈值。

更多详细配置说明见 `docs/异常检测规则详解.md`。

## 🔧 检测算法

### 1. 金额异常检测
- 基于Z-score的统计异常检测
- 业务类型特定的金额范围验证
- 历史基线对比分析

### 2. 时间异常检测
- 营业时间外操作检测
- 周末操作频率分析
- 时间间隔异常检测

### 3. 频率异常检测
- 日操作频率统计
- 操作员行为基线对比
- 业务类型频率分析

### 4. 特殊模式检测
- **夜间高流量**: 检测22:00-06:00期间的高频操作
- **国际漫游突增**: 检测一周内国际漫游业务突增
- **快速连续操作**: 检测30秒内的连续操作

## 📈 风险评分机制

### 综合风险评分公式
```
风险评分 = w1 × 金额异常度 + w2 × 时间异常度 + w3 × 频率异常度 + w4 × 操作员异常度 + 特殊模式加成
```

### 风险等级分类
- **低风险 (0.0 - 0.3)**: 正常操作，无需关注
- **中风险 (0.3 - 0.7)**: 需要关注，可能存在异常
- **高风险 (0.7 - 1.0)**: 高度异常，建议立即处理

## 🎯 使用场景

### 1. 营业厅日常监控
- 实时监控营业厅操作行为
- 及时发现异常操作模式
- 预防潜在的资费纠纷

### 2. 风险用户识别
- 识别高风险用户群体
- 建立用户行为档案
- 制定个性化服务策略

### 3. 操作员行为分析
- 分析操作员工作效率
- 识别异常操作员行为
- 优化操作员培训计划

### 4. 业务模式优化
- 分析业务类型分布
- 识别业务办理高峰时段
- 优化营业厅资源配置

## 🔒 隐私保护

- 所有数据处理均在本地进行
- 不上传任何用户数据到服务器
- 支持数据加密存储
- 符合数据保护法规要求

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📞 技术支持

- **邮箱**: support@cmcc-billguard.com
- **文档**: [在线文档](https://docs.cmcc-billguard.com)
- **问题反馈**: [GitHub Issues](https://github.com/your-repo/CMCC-BillGuard/issues)

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

感谢所有为项目做出贡献的开发者和用户！

## 📜 开源协议与合规声明

- 本项目采用 [MIT License](./LICENSE) 开源协议，允许自由使用、修改、分发。
- 所有代码、文档均为团队自主原创或已获得授权，无任何公司或个人敏感/涉密信息。
- 贡献者需同意[贡献者许可协议（CLA）](./CONTRIBUTING.md)。

## 🎯 零数据演示（开箱即用）

本系统支持"零数据启动"，即使没有任何真实账单数据，也能一键生成模拟数据并体验全流程。

### 前端一键演示
- 打开 `index.html`，点击"生成模拟数据并检测"按钮，系统会自动生成并加载模拟账单数据，立即体验异常检测和可视化。

### 后端一键演示
- 运行 `samples/gen_sample_excel.py` 生成标准账单Excel文件：
  ```bash
  python samples/gen_sample_excel.py --rows 100 --anomaly-rate 0.15
  ```
- 然后用该文件作为输入，体验后端检测和报告生成。

### 自定义模拟数据
- `gen_sample_excel.py` 支持命令行参数：
  - `--rows` 生成数据条数（默认30）
  - `--anomaly-rate` 异常数据比例（默认0.1）
  - `--output` 输出文件名（默认"营业厅账单模板.xlsx"）
- 示例：
  ```bash
  python samples/gen_sample_excel.py --rows 200 --anomaly-rate 0.2 --output my_bills.xlsx
  ```

---

**CMCC-BillGuard** - 让资费异常检测更智能、更高效！ 