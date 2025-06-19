import pandas as pd
import numpy as np
import argparse
import random
from datetime import datetime, timedelta

parser = argparse.ArgumentParser(description='生成模拟营业厅账单Excel数据')
parser.add_argument('--rows', type=int, default=30, help='生成数据条数，默认30')
parser.add_argument('--anomaly-rate', type=float, default=0.1, help='异常数据比例，默认0.1')
parser.add_argument('--output', type=str, default='营业厅账单模板.xlsx', help='输出文件名')
args = parser.parse_args()

rows = []
base_time = datetime(2024, 1, 15, 8, 0)
business_types = [
    ("开户", [100, 200]),
    ("销户", [50, 100]),
    ("套餐变更", [100, 500]),
    ("充值", [10, 1000]),
    ("流量包", [5, 200]),
    ("国际漫游", [100, 2000])
]
operator_ids = ["OP001", "OP002", "OP003"]
branch_ids = ["BR001", "BR002", "BR003"]

for i in range(args.rows):
    btype, (amin, amax) = random.choice(business_types)
    amount = round(np.random.uniform(amin, amax), 2)
    discount = round(np.random.uniform(0, amount * 0.2), 2)
    real_amount = amount - discount
    op_id = random.choice(operator_ids)
    br_id = random.choice(branch_ids)
    date = base_time + timedelta(days=i // 15)
    time_str = (date + timedelta(hours=random.randint(8, 23), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")
    # 注入异常
    if random.random() < args.anomaly_rate:
        if btype == "国际漫游":
            amount = round(np.random.uniform(1500, 3000), 2)
        elif btype == "充值":
            amount = round(np.random.uniform(2000, 5000), 2)
        elif btype == "流量包":
            amount = round(np.random.uniform(500, 1000), 2)
        time_str = (date + timedelta(hours=random.choice([0, 1, 2, 23]), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")
    rows.append([
        f"BILL{i+1:03d}", br_id, date.strftime("%Y-%m-%d"), op_id, btype, amount, discount, real_amount, time_str
    ])

columns = ["账单编号","营业厅编号","账单日期","操作员ID","业务类型","费用金额","优惠金额","实收金额","操作时间"]
df = pd.DataFrame(rows, columns=columns)
df.to_excel(args.output, index=False)
print(f"已生成标准Excel文件：{args.output}，共{args.rows}条，异常比例{args.anomaly_rate}") 