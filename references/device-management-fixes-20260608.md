# 端到端脚本修复记录 — 设备管理 (2026-06-08)

> **合并说明**：此文件已与 `2026-06-08-device-management-fixes.md` 合并（后者包含占位符验证方法等额外内容）。
> 两者都是 2026-06-08 同一调试 session 的产物，已整合为完整版本。

## 修复清单

### 1. 场景6 路由 404

**错误**：`{BASE_URL}/controller/cModelEdit?type=create`
**正确**：`{BASE_URL}/controllerType/cEdit?type=create`
**根因**：凭感觉推断路由模式，未在浏览器中验证。设备模型路由前缀是 `controllerType/`，不是 `controller/`。
**经验**：类比元件模型 → `elementType/e*`，设备模型 → `controllerType/c*`。每条路由逐一验证。

### 2. 场景6 缺失元件模型关联

设备模型创建页下方有 **"元件模型"** 区域 + **"添加元件模型"** 按钮。点击后展开表格行，含搜索元件模型的下拉框。选择已发布的元件模型后，版本列自动填充为 `v1`。

**实现步骤**：
```python
page.locator("button").filter(has_text="添加元件模型").click()
time.sleep(1.5)
el_model_inp = page.get_by_placeholder("请输入模型名称搜索")
el_model_inp.click()
el_model_inp.fill(EL_MODEL_NAME)
time.sleep(2)
el_model_opt = page.locator("[role='option']").filter(has_text=EL_MODEL_NAME).first
el_model_opt.click()
```

### 3. 场景8 表单字段缺失

设备创建表单比脚本假设多 4 个字段。浏览器验证结果：

| 字段 | 脚本中定位 | 实际 placeholder |
|:---|:---|:---|
| 设备模型选择 | `请输入模型名称搜索` | **`请输入设备模型名称搜索`** |
| IP地址 | 未填写 | `请输入IP地址` (必填 *) |
| MAC地址 | 未填写 | `请输入MAC地址` (必填 *) |
| 厂商 | 未填写 | `请输入厂商` |
| 型号 | 未填写 | `请输入型号` |
| 关联元件 tab | `关联元件` | **`元件`** |

### 4. 场景4→5 页面衔接失败

场景4 的 PV 验证步骤点击了"查看详情"进入详情页，场景5 启动时不在列表页，`row = page.locator("tr")` 无匹配。

**修复**：场景4 末尾显式返回列表页并恢复搜索状态。
```python
page.goto(f"{BASE_URL}/element/eDeviceList", wait_until="networkidle")
page.get_by_placeholder("请输入元件名称").fill(EL_NAME)
page.get_by_role("button", name="搜索").click()
```

### 5. 场景8 详情页元件关联验证失败 (2026-06-08 第二次修复)

**错误**：详情页点击"元件"tab后，用 `page.locator("tr").filter(has_text=EL_NAME)` 查找关联元件 → 永远找不到。

**根因**：设备详情页的"元件"tab使用 **Element Plus `<div class="el-tree">`** 组件渲染，不是 `<tr>` 表格行。DOM 结构：
```html
<div class="el-tree" role="tree">
  <div class="el-tree-node" role="treeitem">
    <div class="el-tree-node__content">
      <div class="tree-node">
        <div class="node-index">1</div>
        <span class="node-label">自动化测试-元件模型(v1)</span>
        <div class="node-actions">自动化测试-元件v2</div>
      </div>
    </div>
  </div>
</div>
```

**修复**：改为检查 `.el-tree` 容器的 `inner_text()` 是否包含元件名称：
```python
el_tree = page.locator(".el-tree")
el_associated = False
if el_tree.count() > 0:
    el_text = el_tree.inner_text()
    el_associated = EL_NAME in el_text
```

**经验**：详情页的关联数据可能使用 Tree、Card、Description 等非表格组件展示。不要默认假设所有列表都是 `<tr>` 表格行。验证步骤：用 `browser` 工具的 `browser_vision` 或 JS evaluate 查看 DOM 判断渲染组件。

### 6. "确定"按钮选择器统一

**问题**：同一脚本中场景 3/5/7/9 的确认对话框按钮使用不同选择器：
- 场景 3: `page.locator("button").filter(has_text="确定").first`（无作用域）
- 场景 5: `page.locator(".el-message-box__btns button, .el-dialog button")`（有作用域）

**修复**：统一为作用域限定模式：
```python
confirm = page.locator(".el-message-box__btns button, .el-dialog button, .el-message-box button").filter(has_text="确定").first
```

### 7. NON_BLOCKING 逻辑修复

**问题**：`NON_BLOCKING = {4, 5}` 将场景4(创建元件)和场景5(发布元件)标记为"不阻塞后续场景"。但实际上场景4/5的数据是场景6-9的前置依赖。

**修复**：改为空集 `NON_BLOCKING = set()`，任一场景失败即停止后续执行。

### 8. 断言增强：从"非空检查"升级为"语义内容检查"

`assert_ui()` 仅检查元素内容非空，无法验证具体语义。对发布状态/版本信息等关键字段，改为显式语义检查：

```python
# 版本信息 — 检查 "发布:1"
ver_cell = page.locator("tr").filter(has_text=name).locator("td").nth(4).first
if ver_cell.count() > 0:
    ver_text = ver_cell.text_content(timeout=5000) or ""
    is_published = "发布:1" in ver_text
    report.assertion("UI: 版本信息含发布标记", is_published, ver_text[:80])
else:
    report.assertion("UI: 版本信息含发布标记", False, "未找到版本信息列")

# 发布状态 — 检查 "发布"
status_cell = page.locator("tr").filter(has_text=name).locator("td").nth(4).first
if status_cell.count() > 0:
    status_text = status_cell.text_content(timeout=5000) or ""
    is_released = "发布" in status_text
    report.assertion("UI: 设备已发布", is_released, status_text[:40])
else:
    report.assertion("UI: 设备已发布", False, "未找到状态列")
```

### 9. el-select 下拉选项显式等待

```python
# ❌ 脆弱：固定sleep
rw_sel.click(); time.sleep(0.5)
ro = page.locator("[role='option']").filter(has_text="读写").first
if ro.count() > 0: ro.click()

# ✅ 健壮：显式等待
rw_sel.click()
rw_opt = page.locator("[role='option']").filter(has_text="读写").first
rw_opt.wait_for(state="visible", timeout=3000)
rw_opt.click()
```

## 完整数据依赖链

```
PV → 元件模型(创建→发布) → 元件(创建→关联PV→发布)
          ↓
    设备模型(创建→添加属性→添加元件模型→发布)     ← 遗漏此关联导致无法关联元件
          ↓
    设备(创建→选择设备模型→输入IP/MAC/厂商/型号→关联元件→发布)
```

## 表单 placeholder 的浏览器验证方法

```python
# 1. 导航到编辑页
page.goto(f"{BASE_URL}/controller/cDeviceEdit?type=create")

# 2. 用 browser_snapshot 查看所有 textbox 的 accessible name
# 输出示例：
#   textbox "请输入设备名称" [ref=e29]
#   textbox "请输入设备编码" [ref=e30]
#   textbox "请输入安装位置" [ref=e31]
#   combobox [ref=e20] -> textbox "请输入设备模型名称搜索"
#   textbox "请输入IP地址" [ref=e32]
#   textbox "请输入型号" [ref=e33]
#   textbox "请输入厂商" [ref=e34]
#   textbox "请输入MAC地址" [ref=e35]

# 3. 按 snapshot 的 accessible name 写定位代码
page.get_by_placeholder("请输入设备模型名称搜索").click()
page.get_by_placeholder("请输入设备模型名称搜索").fill(MODEL_NAME)
```

## 关键经验

1. **表单字段占位符必须在 browser 中逐一核实** — 同一平台不同表单的 placeholder 前缀不一致
2. **关联关系是第四层断言** — 保存后必须导航到详情页验证关联实体可见
3. **场景末尾恢复列表页状态** — 详情验证后会离开列表页，下个场景需要先返回
4. **Playwright `--start-maximized` 参数不可用** — 用 viewport 固定尺寸代替
5. **详情页关联数据可能使用 el-tree 非 tr 表格** — 逐个断言验证 DOM 结构
6. **"确定"按钮统一使用作用域限定选择器** — 避免大范围 button 匹配误点
7. **显式等待优于固定 sleep** — `wait_for(state="visible")` 替代 `time.sleep + count()`
