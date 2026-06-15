# 脚本调试工作流程（2026-06-09 经验沉淀）

> 从元件模型 atomic 脚本和标签脚本调试中提炼的用户工作方式。

## 调试流程（必须遵守）

### 第一步：先分析，再修复

用户明确要求：**先分析问题根因、再修复**。不要跳过分析直接改代码。

正确顺序：
1. 读代码，理解场景逻辑和断言意图
2. 识别断言失败的类型：
   - DB 断言失败 → 查 `information_schema.columns` 确认表结构和字段类型
   - UI 文本断言失败 → 确认页面实际渲染文本（截图或 browser_snapshot）
   - check_page_errors 捕获 → 看错误信息判断是脚本问题还是平台问题
   - 按钮/元素定位失败 → 检查选择器和交互模式
3. 输出分析结论（根因 + 影响范围 + 修复建议）
4. 等用户确认后，再修复

### 第二步：DB 断言前必须查表结构

```python
# ❌ 反例：猜类型不查表
report.assertion("DB: 已逻辑删除", str(row[0]) == "1", ...)
# 当 is_delete 是 boolean 时，str(True) == "1" → "True" == "1" → 永远 False

# ✅ 正例：先查 information_schema.columns 确认类型
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'device_tags'
    ORDER BY ordinal_position
""")
```

### 第三步：UI 文本断言前必须确认页面渲染

```python
# ❌ 反例：猜页面关键词
has_release = "release" in page_text or "已发布" in page_text
# 页面上实际显示的是 "版本状态：发布" —— 两个关键词都没命中

# ✅ 正例：先 browser_snapshot 或截图确认渲染文本
# 对不确定的文本内容，只截图不做文本断言，保留现场
report.step("详情页验证", screenshot=page)
```

### 第四步：删除测试必须新建草稿

IoT 平台业务约束：已发布的数据不可删除。

```python
# ❌ 反例：试图通过删版本记录来绕过"已发布不可删除"的限制
cur.execute("DELETE FROM thing_model_version WHERE ...")  # 绕过限制

# ✅ 正例：新建一个草稿状态的实体用于删除测试
DEL_NAME = f"{DATA_PREFIX}_待删除"
page.goto(CREATE_URL)
fill_form(DEL_NAME)
save()
search(DEL_NAME)
delete()
assert UI 不显示
assert is_delete = True  # 软删除
```

### 第五步：el-autocomplete 选择器必须统一

所有脚本中 el-autocomplete 的统一交互模式：
- 选择器：`.el-autocomplete__popper li`
- 等待：`time.sleep(3)`（覆盖 debounce + 网络延迟）
- 点击：`force=True`（绕过 Popper 可见性检查）
- 收尾：`page.keyboard.press("Escape")`（关闭 popper，防止透明 overlay 拦截后续点击）
- 断言：if/else 双分支都必需有 `report.assertion()`
