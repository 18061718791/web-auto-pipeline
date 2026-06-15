# Test Data Migration — 测试环境前置数据填充
> 附属于 `web-auto-pipeline` 技能

## 场景

需要为测试环境的自初始化（如业务字典）准备前置数据，而这些数据在测试环境不存在但开发环境已有完整配置时。

## 原则

1. **不通过 UI 批量创建** — 当条目多于 5 条时，UI 手动创建效率太低，易出错
2. **优先直接 SQL** — 如果环境之间 DB 表结构一致，直接 INSERT 比 UI 操作快 10 倍以上
3. **先查 DB 结构** — 用 `information_schema.columns` 确认目标表名和字段名
4. **验证一致性** — 插入后用浏览器 UI 逐条核对

## 流程

### 1. 确认 DB 表结构

目标 DB 的表名可能与开发环境不同，先查：

```python
import psycopg2
c = psycopg2.connect(host=TEST_HOST, port=5432, dbname='jwsiot_dev', user='postgres')
cur = c.cursor()

# 找字典相关表
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%dict%'")

# 确认列定义
cur.execute("""
    SELECT column_name, data_type, column_default
    FROM information_schema.columns
    WHERE table_name='system_dict'
    ORDER BY ordinal_position
""")
```

### 2. 从开发环境提取数据

通过浏览器 UI 浏览并记录数据（当开发 DB 不可直连时）：

```
1. 导航到开发环境的字典列表页
2. 点击每个字典的"查看"按钮
3. 记录所有二级条目（注意分页！共N条显示在第1-2页）
4. 数据格式：item_value, item_label, description, sort_order
```

### 3. 写入测试环境

```python
import psycopg2, datetime

TEST = dict(host='10.30.25.183', port=5432, dbname='jwsiot_dev', user='postgres')

c = psycopg2.connect(**TEST)
cur = c.cursor()
now = datetime.datetime.now()

# 插入一级字典定义
cur.execute(
    "INSERT INTO system_dict(dict_code, dict_name, description, is_delete, create_at) "
    "VALUES(%s,%s,%s,false,%s) RETURNING id",
    ('defaultSystem', '默认系统', '', now)
)
dict_id = cur.fetchone()[0]

# 批量插入二级条目
items = [
    ('ts', '调束', '', 0),
    ('bps', 'BPS', '', 0),
    # ... 更多条目
]
for val, label, desc, order in items:
    cur.execute(
        "INSERT INTO system_dict_item(dict_id, item_value, item_label, description, sort_order, is_delete, create_at) "
        "VALUES(%s,%s,%s,%s,%s,false,%s)",
        (dict_id, val, label, desc, order, now)
    )

c.commit()
c.close()
```

### 4. 验证 — 三层验证法（推荐）

不要只做「翻页看看」级别的验证。采用三层递进验证法，确保数据100%一致：

#### 第一层：总数对比

```python
# 开发环境 vs 测试环境 — 按 dict_code 分组对比记录数
cur_dev.execute("""
    SELECT d.dict_code, d.dict_name, COUNT(di.id) 
    FROM system_dict d LEFT JOIN system_dict_item di ON d.id=di.dict_id
    GROUP BY d.dict_code, d.dict_name ORDER BY d.dict_code
""")
dev_counts = cur_dev.fetchall()

cur_test.execute("""...same query...""")
test_counts = cur_test.fetchall()

# 输出对比表
print(f"{'字典代码':20s} {'字典名称':15s} {'开发':>4s} {'测试':>4s}")
print("-"*48)
for dev, test in zip(dev_counts, test_counts):
    ok = "✅" if dev[2] == test[2] else "❌"
    print(f"{dev[0]:20s} {dev[1]:15s} {str(dev[2]):>4s} {str(test[2]):>4s}  {ok}")
```

输出示例（用户评价"这个比对做的很好"的实际产出）：
```
字典代码               字典名称           开发   测试
defaultSegment       默认段                6     6  ✅
defaultSystem        默认系统             15    15  ✅
```

#### 第二层：样本条目逐项验证

总数一致后，对每个字典取 1-2 条样本，用浏览器打开查看页核对 item_value + item_label + sort_order 完全匹配：

```python
cur.execute("""
    SELECT item_value, item_label, description, sort_order
    FROM system_dict_item di JOIN system_dict d ON di.dict_id=d.id
    WHERE d.dict_code='defaultSystem' ORDER BY sort_order LIMIT 2
""")
for row in cur:
    print(f"  {row[0]:8s} {row[1]:10s} sort={row[3]}")
```

#### 第三层：截图取证

最后用 `browser_vision` 或 `browser_take_screenshot` 对测试环境的查看页截图，将截图附在报告或文档中作为最终视觉证据。

#### 简易验证（当数据量小或做快速确认时）

用浏览器导航到测试环境的字典列表页 → 点击"查看" → 逐条核对所有二级条目应完整显示（注意分页）。

## IoT 物联管理平台业务字典参考数据（2026-06-10 迁移后验证）

### 表名
- `system_dict`（一级字典定义）
- `system_dict_item`（二级字典项）

### 1. defaultSystem（默认系统）— 15 项二级值

| 序号 | 项值 | 项标签 |
|:---|:---|:---|
| 1 | ts | 调束 |
| 2 | bps | BPS |
| 3 | ls | 连锁 |
| 4 | ds | 定时 |
| 5 | bpm | BPM |
| 6 | sz | 束诊 |
| 7 | lzy | 离子源 |
| 8 | dwzk | 低温真空 |
| 9 | cdqt | 超导腔体 |
| 10 | cwqt | 常温腔体 |
| 11 | gly | 功率源 |
| 12 | ddpsp | 低电平射频 |
| 13 | scbh | 失超保护 |
| 14 | cdct | 超导磁铁 |
| 15 | cwct | 常温磁铁 |

### 2. defaultSegment（默认段）— 6 项二级值

| 序号 | 项值 | 项标签 |
|:---|:---|:---|
| 1 | HEBT | HEBT |
| 2 | HBHL | HBHL |
| 3 | LBHL | LBHL |
| 4 | RFQ | RFQ |
| 5 | MEBT | MEBT |
| 6 | LEBT | LEBT |
