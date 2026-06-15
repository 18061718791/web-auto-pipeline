# el-cascader 多选复选框交互 — 调试全记录

## 背景

2026-06-03 开发 `tag_lifecycle_test.py` 场景5（设备关联标签）时，发现设备编辑页的标签选择器并非预期的 `el-select`（带多选），而是 `el-cascader`（级联选择器，多选模式显示 `.el-checkbox`）。

## 诊断过程

| 步骤 | 操作 | 发现 |
|:---:|:---|:---|
| 1 | 查看页面 aria snapshot | 标签输入框显示 `combobox` role — 初步误判为 el-select |
| 2 | DOM 检查 dropdown 容器 | `.el-cascader__dropdown`（非 `.el-select-dropdown`）— 确认是 cascader |
| 3 | 检查选项 DOM 结构 | 每个选项含 `.el-checkbox` 和 `.el-cascader-node__label` |
| 4 | 尝试 `force=True` 点击选项文本 | 点击后展开子菜单（级联效果），不选中 — ❌ |
| 5 | 尝试 `force=True` 点击 checkbox | 通过 `page.evaluate()` 执行 `.el-checkbox.click()` — ✅ 选中 |
| 6 | DB 确认存储值 | `device.device_tags` 存的是 `tag.id`（整数，逗号分隔） |

## 对比 el-select（带多选）

| 维度 | el-select el-tag 多选 | el-cascader 复选框多选 |
|:---|:---|:---|
| 选择方式 | 点击选项文本 | 点击选项内的 **checkbox** |
| 输入框显示 | 已选项作为 el-tag 标签 | "n个项目" |
| 选中值 | 选项的 `value`（通常是 label/name） | 选项的 `value`（这里是 tag 表主键 ID） |
| 下拉容器类 | `.el-select-dropdown` | `.el-cascader__dropdown` |

## 最终交互方案

```python
def select_cascader_tag(page, tag_name):
    """在设备编辑页的 el-cascader 中选择一个标签。"""
    # 1) 打开 cascader
    page.locator('.el-cascader').click(force=True)
    time.sleep(1.5)
    
    # 2) 点 checkbox（不能点节点文本）
    page.evaluate(f"""
    () => {{
        const nodes = document.querySelectorAll('.el-cascader-node');
        for (const node of nodes) {{
            if (node.textContent.includes('{tag_name}')) {{
                const cb = node.querySelector('.el-checkbox');
                if (cb) {{ cb.click(); return true; }}
            }}
        }}
        return false;
    }}
    """)
    time.sleep(0.5)
    
    # 3) 关闭下拉
    page.keyboard.press("Escape")
    time.sleep(1)
```

## 二次确认验证

保存后，**必须重新进入编辑页**验证标签已关联（列表页标签列可能不刷新）：

```python
page.get_by_role("button", name="保存").click()
time.sleep(3)
ensure_on_page(page, LIST_URL)
page.get_by_placeholder("请输入设备名称").fill(DEVICE_NAME)
page.get_by_role("button", name="搜索").click()
time.sleep(2)
page.get_by_role("button", name="编辑").first.click()
time.sleep(3)
edit_body = page.locator("body").inner_text()
report.assertion("UI: 编辑页含已关联标签", TAG_NAME in edit_body, "")
```

## DB 断言注意事项

`device.device_tags` 存的是标签 ID（JSON 数组字符串），不是标签名称：

```python
# 正确方式：关联查询
rows = db_query("""
    SELECT t.tag_name FROM device d
    JOIN tag t ON t.id = ANY(
        SELECT unnest(string_to_array(d.device_tags, ','))::int
    )
    WHERE d.device_name = %s
""", (DEVICE_NAME,))
report.assertion("DB: 设备有标签", len(rows) > 0, f"标签={[r[0] for r in rows]}")
```
