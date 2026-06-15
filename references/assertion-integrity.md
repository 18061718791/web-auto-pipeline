# 断言完整性 — 禁止静默跳过 (2026-06-08)

## 问题

场景8（创建设备+关联元件）中，关联元件的下拉选择使用 `if opt.count() > 0: opt.click()`，当元
件未出现时（因场景6未关联元件模型导致），**else 分支没有任何断言**。脚本继续执行后续的"保存设备"，
且保存成功（因为IP/MAC等校验通过），最终场景标记为"通过"。

用户指出这是**结果欺骗**：关键业务操作（关联元件）实际未执行，但测试报告显示场景通过。

## 根因

所有 if-else 分支中，只有成功分支写了代码，失败分支保持静默。`report.assertion` 只在成功时被调
用（隐式为 True），失败时不被调用 — 但 `scene_end(True)` 不检查断言是否被调用过。

## 修复方案

### 1. 下拉选择必须有双分支断言

```python
opt = page.locator("[role='option']").filter(has_text=EL_NAME).first
opt_found = opt.count() > 0
if opt_found:
    opt.click()
    time.sleep(0.5)
    log(f"    ✅ 元件已关联: {EL_NAME}")
else:
    log(f"    ❌ 元件下拉选项未出现: {EL_NAME}", "❌")
    page.evaluate("document.querySelector('.el-overlay')?.remove()")
# ★ 无论 found 与否，都必须有断言
report.assertion("关联已发布的元件", opt_found,
                 EL_NAME if opt_found else "下拉选项未出现")
```

### 2. 保存后增加关联验证

```python
# 导航到详情页 → 切换到关联 tab → 确认关联实体可见
row.locator("button").filter(has_text="查看详情").first.click()
el_tab = page.get_by_role("tab", name="元件")
el_tab.click()
el_in_detail = page.locator("tr").filter(has_text=EL_NAME)
el_associated = el_in_detail.count() > 0
report.assertion("详情验证: 设备已关联元件", el_associated, ...)
```

### 3. 断言覆盖检查清单

- [ ] 下拉选择：选项出现才点击 → else 分支有 `report.assertion(..., False, ...)`
- [ ] tab 切换：`tab.count() > 0` 的 false 分支有断言
- [ ] 保存后：check_page_errors + UI 列表 + DB + **关联关系验证**
- [ ] 发布后：UI 状态列 + DB 状态字段
- [ ] 搜索后：搜索结果行数 > 0

### 4. `scene_end(True)` 的充要条件

- 该场景内所有 `report.assertion` 均为 True（无未调用的断言）
- `check_page_errors` 无错误
- 无未捕获异常
- 关键子操作（关联、选择等）的失败必须导致场景失败，不能因后续操作成功而掩盖
