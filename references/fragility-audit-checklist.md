# 脚本脆弱性审计指南 (2026-06-08)

## 适用场景

已有自动化测试脚本全部场景通过，但需要系统性检查是否存在隐性脆弱点时执行此审计。**场景全通过 ≠ 脚本健壮。**

## 审计方法论

从5个维度逐一检查脚本中的每个UI交互点：

```
选择器准确性 → 等待策略 → 断言特异性 → 数据依赖 → 异常恢复
```

### 维度1：选择器准确性

核对脚本中所有定位器与页面实际DOM是否一致。

**审计清单：**

- [ ] **Placeholder 文本** — 用 `browser` 工具逐一确认所有 `get_by_placeholder()` 的文本是否与页面完全一致。同一平台不同页面的 placeholder 前缀模式可能不同（如元件模型搜索= `请输入模型名称`，设备模型搜索= `请输入设备模型名称搜索`）
- [ ] **表格列索引** — 用 `browser` 工具查看 `.el-table__header th` 列顺序，确认 `locator("td").nth(N)` 的索引正确。列出所有表头：
  ```python
  # 快速验证列顺序
  headers = page.locator('.el-table__header th').all()
  for i, h in enumerate(headers):
      print(f'  Col {i}: \"{h.inner_text()[:30]}\"')
  ```
- [ ] **详情页关联组件类型** — 确认关联数据是使用 `<table>` 表格、`<div class="el-tree">` 树组件还是其他自定义组件渲染。IoT 平台设备详情页的"元件"tab 使用 `el-tree`（`.tree-node .node-actions`），用 `page.locator("tr")` 永远找不到
- [ ] **按钮文本** — 按钮文本可能有前后空格（`' 保存 '`），用 `page.locator('button').all()` 逐一检查 visible 按钮的 `inner_text().strip()`
- [ ] **DOM 结构** — 不是所有列表都用 `<tr>`。el-tree 用 `<div>` 树节点展示数据。详情页的关联 tab 可能是 `el-tree`（div）而非 `el-table`（tr）。
- [ ] **Tab 名称** — 检查 tab 实际文本（如 `元件` 而非 `关联元件`），用 `page.get_by_role('tab').all()` 确认
- [ ] **对话框按钮** — 确认按钮是否在特定的对话框作用域内（`.el-message-box__btns`、`.el-dialog`），避免匹配到页面其他位置的同名按钮

### 维度2：等待策略

检查每个 `time.sleep()` 和 `wait_for()` 的合理性。

**审计清单：**

- [ ] **固定 sleep 是否可替代** — `time.sleep(N)` 应尽量替换为显式等待：
  ```python
  # 不好的：固定等2秒
  time.sleep(2)
  
  # 好的：等元素出现后再操作
  page.locator("[role='option']").filter(has_text=option_text).first.wait_for(state="visible", timeout=3000)
  ```
- [ ] **el-select 下拉选项** — 点击 select 展开后，不能用 `time.sleep(0.5)` + `if opt.count() > 0` 检查，应使用：
  ```python
  page.locator(".el-select").filter(has_text="只读").first.click()
  option = page.locator("[role='option']").filter(has_text="读写").first
  option.wait_for(state="visible", timeout=3000)
  option.click()
  ```
- [ ] **el-autocomplete 异步搜索** — fill 后至少有 2s debounce + 后端搜索时间，用睡眠或轮询
- [ ] **保存/发布后** — 固定 sleep 3-5s 可接受（后端写入需要时间），但组合 `check_page_errors` 轮询（4次×2s）
- [ ] **页面跳转** — `page.goto(wait_until="networkidle")` 后有 1-2s 额外等渲染完成

### 维度3：断言特异性

检查每个断言是泛泛检查还是精确验证。

**审计清单：**

- [ ] **非空 vs 语义** — 只用 `assert text != ""` 会放过空内容或无关文本。应检查具体语义：
  ```python
  # 不好的：只检查单元格非空
  ok, txt = assert_ui(page, lambda: cell, "版本信息")
  
  # 好的：检查是否包含期望的语义内容
  is_published = "发布:1" in cell_text
  is_release = "发布" in status_text
  ```
- [ ] **版本信息验证** — 表头列为「版本信息」时，内容如 `草稿:0\n注销:0\n发布:1`，检查 `"发布:1" in text`
- [ ] **状态验证** — 表头列为「状态」时，检查 `"发布" in text` 或 `"草稿" in text`
- [ ] **下拉选择验证** — 选择后检查 select 显示文本是否已变，而非假设选择成功
- [ ] **关联关系验证** — 保存后额外导航到详情页检查关联实体在树/表格中可见

### 维度4：数据依赖

检查脚本中场景之间的数据依赖是否显式处理。

**审计清单：**

- [ ] **依赖链分析** — 画出完整的数据依赖有向图，标注每个实体创建需要哪些前置资源
  ```
  PV → 元件模型(创建→发布) → 元件(创建→关联PV→发布)
            ↓
      设备模型(创建→添加属性→添加元件模型→发布)
            ↓
      设备(创建→选择设备模型→关联元件→发布)
  ```
- [ ] **NON_BLOCKING 集** — `should_run()` 中的 NON_BLOCKING 场景号是否合理？如果下游场景依赖上游数据，上游不应设为 non-blocking
- [ ] **场景间页面状态** — 场景A的详情验证后会离开列表页，场景B启动时页面状态未知。场景结束时需恢复列表页搜索状态
- [ ] **清理顺序** — `DELETE` 语句需遵循外键约束顺序（先删子表，再删主表）

### 维度5：异常恢复

检查脚本在出现意外情况时是否有优雅降级路径。

**审计清单：**

- [ ] **JS evaluate 降级** — 优先用标准 Playwright 定位器（`row.locator("button").filter(has_text="查看详情")`），失败才 fallback 到 `page.evaluate()` JS 点击
- [ ] **对话框关闭** — 操作后可能弹出对话框，必须有关闭逻辑防止 overlay 拦截后续点击
- [ ] **页面报错检测** — `check_page_errors` 是否在每次保存/发布后调用
- [ ] **DB 断言容错** — `try/except AssertionError` 让 DB 断言失败不中断脚本，但通过 `report.assertion(False)` 记录到报告

## 审计工作流程

```python
# Step 1: 收集所有定位器清单
# Step 2: 用 headed browser 逐一验证
# Step 3: 修复不一致的选择器
# Step 4: 优化等待策略（sleep → wait_for）
# Step 5: 增强断言语义
# Step 6: 验证数据依赖链完整性
# Step 7: 全脚本有头模式跑一遍确认无回归
```

## 设备管理脚本审计结果示例 (2026-06-08)

| 维度 | 发现问题 | 修复 |
|:---|:---|:---|
| 选择器 | 详情页元件tab用 `el-tree` 非 `tr` | 改用 `.el-tree.inner_text()` |
| 选择器 | 发布确认按钮选择器范围过宽 | 限定到 `.el-message-box__btns` 作用域 |
| 等待 | el-select 选项用 `if count()` 检查 | 改用 `wait_for(state="visible")` |
| 断言 | 版本信息只检查非空 | 改为检查 `"发布:1" in text` |
| 断言 | 发布状态只检查非空 | 改为检查 `"发布" in text` |
| 数据依赖 | NON_BLOCKING={4,5} 不合理（下游依赖4的数据） | 改为空集 `set()` |
| 异常恢复 | 查看详情用纯JS evaluate | 优先标准定位器 + JS fallback |
