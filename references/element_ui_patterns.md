# Element UI 组件交互参考

基于真实平台（Element UI + Vue 3）的自动化测试中积累的组件交互模式和坑点。

## 导航组件

### el-menu（侧边栏菜单）
```
结构：el-menu > el-sub-menu > el-menu-item
ARIA: role="menubar" > role="menuitem"[expanded] > role="menuitem"
```

**展开子菜单：**
```python
# 方法1: ARIA 点击
await page.get_by_role("menuitem", name="设备管理").click()
await page.wait_for_timeout(1000)

# 方法2: JS 强制展开（用于批量收集菜单项）
await page.evaluate("""
() => document.querySelectorAll('.el-sub-menu').forEach(el => {
    el.classList.add('is-opened');
    el.setAttribute('aria-expanded', 'true');
})
""")
```

**坑点：** 同一名称匹配多个元素时抛出 `strict mode violation`。例如"设备"可能匹配父菜单和叶子菜单。
**修复：** 使用 `.first` 或 `.filter(has_text="^精确名称$")`。

### el-sub-menu（可展开菜单项）
**ARIA 属性：** `aria-haspopup="true"` 表示可展开，`aria-expanded="true"` 表示已展开。

**点击叶子菜单的正确方式：**
```python
# 先点击父级展开
await page.get_by_role("menuitem", name="装置管理").click()
await page.wait_for_timeout(800)
# 再点击叶子
await page.get_by_role("menuitem", name="设备模型").click()
await page.wait_for_timeout(2000)
```

## 表单组件

### el-select（下拉选择框）
**最常见的坑：** `<span>` 覆盖层拦截点击。标准 `.click()` 会等待30秒后超时。

**错误日志特征：**
```
<span>测试装置</span> from <div class="el-select__selected-item">...</div> subtree intercepts pointer events
```

**修复方案（按优先级）：**
```python
# 方案1: force=True 绕过拦截（推荐）
await page.get_by_role("combobox").first.click(force=True)

# 方案2: 点击覆盖的 <span> 文本
await page.locator("span:has-text('选项文本')").first.click()

# 方案3: JavaScript 直接触发
await page.evaluate("document.querySelector('.el-select').click()")

# 方案4: 直接输入（适用于搜索型下拉）
await page.get_by_role("combobox").fill("值")

**下拉选项不可见问题（严重）：**
el-select 的 dropdown 选项在 DOM 中存在但不可见。Popper 关闭后 `<li>` 仍留在 DOM 中但 `display: none` 或父容器隐藏。

**错误日志特征：**
```
locator resolved to <li role="option">XXX</li>
- attempting click action
  2 × waiting for element to be visible, enabled and stable
    - element is not visible
```

**可用方案（按Vue事件触发可靠性排序）：**
```python
# 方式1（推荐）：fill后等下拉渲染 → ArrowDown → Enter
# 键盘事件能正确触发 Vue 处理器
await page.get_by_placeholder("搜索").fill(text)
await page.wait_for_timeout(2000)
await page.keyboard.press("ArrowDown")
await page.wait_for_timeout(300)
await page.keyboard.press("Enter")

# 方式2：dispatch_event（不检查可见性，但Vue可能不更新）
option = page.locator(".el-select-dropdown__item").filter(has_text=text).first
if await option.count() > 0:
    await option.first.dispatch_event("click")

# 方式3：force=True（选项不可见时仍会抛异常）
await option.click(force=True)

# 方式4：evaluate点击（Vue v-model可能不更新）
await option.evaluate("el => el.click()")
```

**判定标准：** 点击后检查 el-select 显示文本是否已变。未变则Vue模型未更新。
```python
still_default = page.locator(".el-select").filter(has_text="请选择标签状态")
if await still_default.count() > 0:
    log("下拉未选中", "失败")
else:
    log("下拉已选中", "成功")
```
```

### el-autocomplete（可搜索自动补全 — 关键差异）

**与 el-select 的根本区别：**
- `el-autocomplete` 输出的是 `<div class="el-autocomplete">`，不是 `.el-select`
- 下拉项渲染在 **`.el-autocomplete__popper`** 或 **`.el-popper`** 容器中（非 `.el-select-dropdown`）
- 输入框的 placeholder 通常是 `"请输入XXX名称搜索"`（带"搜索"后缀）
- 通过 input 的 fill 事件触发异步后端搜索（`fetchSuggestions`），有 debounce

**适用场景：** 元件编辑页的"元件模型"、设备编辑页的"设备模型"字段。

**选择策略（多级回退）：**
```python
# 1. 优先尝试 el-form-item 内定位（如果 label 关联正确）
select_el = page.locator(".el-form-item:has-text('{label}') .el-autocomplete").first

# 2. 兜底：全局 el-autocomplete
if await select_el.count() == 0:
    select_el = page.locator(".el-autocomplete").first

# 3. 触发下拉
inner_input = select_el.locator("input").first
await inner_input.click()
await page.wait_for_timeout(300)

# 4. 清空后输入搜索文本（el-autocomplete 必须 fill 触发 fetch）
await inner_input.fill("")
await page.wait_for_timeout(300)
await inner_input.fill(option_text)
await page.wait_for_timeout(2500)  # 等 debounce + 异步渲染

# 5. 再点击一次确保 popper 显示
await inner_input.click()
await page.wait_for_timeout(1500)
```

**⚡ el-select 下拉选项点击不生效的终极解决：使用键盘选择**

当 el-select 的 dropdown popper 关闭后，下拉选项 `<li>` 仍在 DOM 中但不可见（`display:none` 或 popper 容器隐藏），此时 Playwright 的 `.click()`（含 `force=True`）和 `.evaluate("el => el.click()")` 均无法触发 Vue 的 v-model 更新。

**正确做法（已验证通过）：**
```python
# 1. 点击输入框打开下拉
page.get_by_placeholder("请输入搜索").click()
time.sleep(0.5)

# 2. 输入搜索文本
page.get_by_placeholder("请输入搜索").fill(option_text)
time.sleep(2)  # 等过滤渲染

# 3. ★ 使用键盘 ArrowDown + Enter 选择（这是触发 Vue select 事件最可靠的方式）
page.keyboard.press("ArrowDown")
time.sleep(0.3)
page.keyboard.press("Enter")
time.sleep(1)
```

**为什么键盘有效？** ArrowDown 将焦点移到选项列表，Enter 触发了选项的 `click` 事件，该事件经由 Vue 的事件系统正常冒泡到 el-select 的 `handleOptionClick`，从而正确更新 v-model。而 `.click(force=True)` 绕过可见性检查但 Vue 可能没有正确响应。

**查找下拉项的兜底顺序（按精确度）：**
```python
option = page.locator(f".el-select-dropdown__item:has-text('{option_text}')").first
if await option.count() == 0:
    option = page.locator(f"li:has-text('{option_text}')").first
if await option.count() == 0:
    option = page.locator(f"[role='option']:has-text('{option_text}')").first
if await option.count() == 0:
    option = page.locator(f".el-autocomplete-suggestion__list li:has-text('{option_text}')").first
if await option.count() == 0:
    option = page.locator(f".el-autocomplete__popper li:has-text('{option_text}')").first
if await option.count() == 0:
    option = page.locator(f".el-popper li:has-text('{option_text}')").first  # 最宽泛兜底
```

**验证是否命中：** 如果以上都找不到，可在浏览器 console 中注入 JS 强制显示 popper 检查是否有下拉项：
```javascript
document.querySelector('.el-autocomplete__popper').style.display = 'block'
```

### el-cascader（级联选择器）
**适用场景：** 标签选择。

**交互方式：**
```python
# 点击 cascader 展开
cascader = page.locator(".el-cascader").first
await cascader.click()
await page.wait_for_timeout(1000)

# 在级联面板中选择
option = page.locator(f".el-cascader-node:has-text('{option_text}')").first
if await option.count() > 0:
    await option.click()
```

### el-input（输入框）
```python
# 通过 aria-label 定位（推荐）
await page.get_by_role("textbox", name="* 模型名称").fill("值")

# 通过 placeholder 定位（次选）
await page.locator("input[placeholder='请输入模型名称']").fill("值")

# 通过 label 文字定位
await page.locator("text=模型名称").locator("..").locator("input").fill("值")
```

### el-form（表单）
**必填项标记：** 带 `*` 前缀的 label 文本。新增/编辑页的操作按钮通常是"保存"。

**重要：el-form-item 可能不含 el-form-item__label（Vue 3 自定义渲染）**

部分 Element UI 版本中（尤其是 Vue 3），表单项的 label 文本通过 **ARIA accessibility / LabelText** 渲染而不是标准的 `.el-form-item__label` 元素。此时：
- `form_item.locator(".el-form-item__label")` 找不到
- `form_item.text_content()` 可能是空
- 但 `form_item:has-text('X')` 通常仍能匹配

**fallback 选择器链定位 combobox/autocomplete/cascader：**
```python
# 通过 form-item 的文本内容定位
form_item = page.locator(f".el-form-item:has(.el-form-item__label:has-text('{label}'))").first
if await form_item.count() == 0:
    form_item = page.locator(f".el-form-item:has(label:has-text('{label}'))").first
if await form_item.count() == 0:
    form_item = page.locator(f".el-form-item:has-text('{label}')").first

# 在 form-item 内查找组件
select_el = form_item.locator(".el-select").first
if await select_el.count() == 0:
    select_el = form_item.locator(".el-autocomplete").first
if await select_el.count() == 0:
    select_el = form_item.locator(".el-cascader").first
```

**保存操作（通用模式）：**
```python
btns = page.get_by_role("button")
for i in range(await btns.count()):
    txt = (await btns.nth(i).inner_text()).strip()
    if txt in ["保存", "确定", "提交"]:
        await btns.nth(i).click()
        break
```

## 数据显示组件

### el-table（表格）
**检测是否有数据：** 检查页面是否包含"暂无数据"文本。

**表格行选择器（两个版本兼容）：**
```python
# 版本1：Element Plus 标准（有 el-table__row class）
rows = page.locator("tr.el-table__row")

# 版本2：标准 <table> 渲染（无附加 class）
rows = page.locator("table table tr")

# 兼容写法：先用 class 尝试，失败降级
rows = page.locator("tr.el-table__row")
if rows.count() == 0:
    rows = page.locator("table table tr")
```

**获取表头：**
```python
rows = await page.get_by_role("table").nth(0).get_by_role("row").all()
if rows:
    headers = []
    for h in await rows[0].get_by_role("columnheader").all():
        headers.append((await h.inner_text()).strip())
```

### el-tabs（标签页）
**切换Tab：**
```python
await page.get_by_role("tab", name="属性").click()
await page.wait_for_timeout(1000)
```

**坑点：** aria-selected="true" 表示当前选中Tab。切换后可能需要等待内容渲染。

### ⚠️ 关键陷阱：可访问性树 ≠ 实际HTML属性

**这是一个极为常见的探索阶段陷阱。**

Hermes `browser_snapshot` 显示的是 **可访问性树（accessibility tree）**，不是实际 DOM。输入框在可访问性树中的名称来自 **表单 label 文本**，而 Playwright 的 `get_by_placeholder()` 匹配的是 **HTML `placeholder` 属性**。二者往往不同。

### 典型场景：标签新增页的输入框

```html
<!-- 可访问性树显示：textbox "* 标签名称" -->
<!-- 但实际的 HTML 是： -->
<input class="el-input__inner" placeholder="请输入标签名称">
```

| 来源 | 显示值 | Playwright API |
|:---|:---|:---|
| 可访问性树（snapshot） | `* 标签名称` | `get_by_role("textbox", name="* 标签名称")` |
| 实际 DOM `placeholder` | `请输入标签名称` | `get_by_placeholder("请输入标签名称")` |

### 规则

1. **填值用 `get_by_placeholder()`**（匹配 HTML placeholder 属性），**不用 snapshot 显示的 label 文本**
2. **每次探索一个新页面，必须用 `browser_console` 验证真实 `placeholder` 值**：

```javascript
// 在 browser_console 中执行
document.querySelector('input').placeholder
// → "请输入标签名称"  ← 这才是 get_by_placeholder 需要的值

// 查看所有输入框
[...document.querySelectorAll('input')].map(i => i.placeholder)
```

3. **textarea 的 placeholder 也需要独立确认**：

```javascript
document.querySelector('textarea')?.placeholder
```

4. **Manifest 中的 `placeholder` 字段始终写 HTML placeholder 的实际值**，不是 snapshot 显示的 label 文本

### 适用范围

所有使用 `get_by_placeholder()` 定位的 Element UI 输入框。这个陷阱极其隐蔽——snapshot 显示的文本看起来完全合理，但脚本就是找不到元素。

## 数据表格列索引

验证表格列内容时，`nth()` 是 **0-based** 索引。

```python
# 表格列定义：
# 序号(0) | 标签名称(1) | 标签编码(2) | 标签状态(3) | 创建时间(4) | 操作(5)

# ❌ 错误：nth(2) 获取的是"标签编码"列，不是"标签状态"
status_cell = row.locator("td").nth(2).text_content()

# ✅ 正确：nth(3) 才是"标签状态"列
status_cell = row.locator("td").nth(3).text_content()
```

**常见错误：** 数人类可见的列号时从1开始数（序号=1, 标签名称=2, ..., 标签状态=4），但 `nth()` 从0开始。看到手册说"第4列"就直接写 `nth(4)`，实际应该是 `nth(3)`。

**审计清单：** 写完每段表格列验证代码后，回头数一下索引：`nth(0)`=第一列, `nth(1)`=第二列, ...

## el-pagination（分页）
当数据超过一页（通常>10条）时自动出现。需检查是否有"下一页"按钮。

## 弹窗组件

### 操作后对话框处理（连通性测试/导入结果等）

点击"连通测试"或导入文件后，平台会弹出对话框（如「PV连通测试结果」「导入结果」）。如果不关闭此对话框，后续页面的所有按钮点击都会被 **dialog overlay 拦截**，报 `intercepts pointer events` 错误。

**标准关闭流程：**
```python
# 尝试关闭对话框
dialog = page.locator("[role='dialog']")
if dialog.count() > 0:
    # 找关闭按钮
    close_btn = page.get_by_role("button", name=re.compile(r"关闭|确定|知道了"))
    if close_btn.count() > 0:
        close_btn.click()
        time.sleep(1)
    else:
        # 兜底：Escape 键
        page.keyboard.press("Escape")
        time.sleep(1)
else:
    # 可能是消息提示自动消失
    time.sleep(3)
```

**注意：** 脚本中每个可能触发对话框的操作后，都需要执行此清理，否则后续场景的 `page.goto()` 和点击都会被阻塞。
```python
dialog = page.locator("[role='dialog'], .el-dialog, .el-drawer")
if await dialog.count() > 0:
    # 处理弹窗
    pass
else:
    # URL变化，进入独立页面
    pass
```

### 确认对话框（删除操作）
```python
await click(page, "button", "删除", "删除")
await page.wait_for_timeout(1000)
try:
    confirm = page.get_by_role("button", name=re.compile("确定|确认|是"))
    if await confirm.count() > 0:
        await confirm.first.click()
        await page.wait_for_timeout(2000)
except:
    pass
```

## 树组件

### el-tree — 导航/展开模式

```python
# 展开树节点
treeitem = page.get_by_role("treeitem", name="测试装置")
if await treeitem.count() > 0:
    await treeitem.click()
    await page.wait_for_timeout(1000)
```

### el-tree — 数据展示模式（详情页关联实体）

**背景**：`el-tree` 不仅用于导航展开/收起，也被 Element Plus 用作**详情页的数据展示组件**，尤其是展示实体间的关联关系（如设备关联的元件、模型关联的属性等）。此时它替代了 `el-table`，使用树节点结构而非表格行。

**⚠️ 常见陷阱：脚本用 `page.locator("tr")` 查找关联实体，但因 DOM 结构为 `el-tree` 永远找不到。**

**DOM 结构特征（源自设备详情页「元件」tab 实际抓取）：**

```html
<div class="device-children">
  <div class="table-header">                            <!-- 模拟表头（非 <table>） -->
    <div class="header-item index">序号</div>
    <div class="header-item name">元件模型名称(版本号)</div>
    <div class="header-item device">元件名称</div>
    <div class="header-item action">操作</div>
  </div>
  <div class="el-tree" role="tree">
    <div class="el-tree-node is-expanded" role="treeitem">
      <div class="el-tree-node__content">
        <div class="tree-node">
          <div class="node-index">1</div>
          <span class="node-label">模型名称(v1)</span>
          <div class="node-actions">具体实体名称</div>      <!-- ★ 实体名称在此 -->
          <div class="node-info">
            <button>查看详情</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

**关键元素**：

| 元素 | 含义 | 断言用途 |
|:---|:---|:---|
| `.table-header` | 自定义表头（`<div>` 非 `<th>`） | — |
| `.el-tree` | 树容器 | 检查是否有数据 |
| `.el-tree-node` | 每个关联实体一个节点 | count = 关联数 |
| `.node-label` | 模型/模板名称（含版本号） | 验证关联了正确的模型 |
| **`.node-actions`** | **具体实体名称** | **主断言目标** |

**断言写法（Playwright sync API）**：

```python
# ✅ 正确方式1 — 检查 el-tree 内文是否包含实体名称（推荐，简洁可靠）
el_tree = page.locator(".el-tree")
if el_tree.count() > 0:
    tree_text = el_tree.inner_text()
    el_associated = EL_NAME in tree_text

# ✅ 正确方式2 — 精确到 .node-actions 元素
el_actions = page.locator(".node-actions").filter(has_text=EL_NAME)
el_associated = el_actions.count() > 0

# ✅ 正确方式3 — 在当前可见 tabpanel 中搜索
visible_panel = page.locator('[role="tabpanel"]:not([aria-hidden="true"])')
el_associated = EL_NAME in visible_panel.inner_text()

# ❌ 错误方式 — 用 <tr> 定位
# el_in_detail = page.locator("tr").filter(has_text=EL_NAME)  # 永远为0
```

**诊断步骤（当断言失败时）**：

```python
# 1. 验证元素是否在页面中存在（只是找错地方了）
all_text = page.locator("body").inner_text()
if EL_NAME in all_text:
    print("元素在页面中，但不在 tr 内 — 检查 el-tree")
    
    # 2. 检查树结构
    trees = page.locator(".el-tree").all()
    for i, t in enumerate(trees):
        print(f"Tree {i}: {t.inner_text()[:200]}")
    
    # 3. 检查哪些 tabpanel 是可见的
    panels = page.locator('[role="tabpanel"]').all()
    for i, p in enumerate(panels):
        print(f"Panel {i}: visible={p.is_visible()}, text={p.inner_text()[:100]}")

# 4. 保存全量 HTML 离线分析
html = page.content()
with open("detail_debug.html", "w", encoding="utf-8") as f:
    f.write(html)
```

**适用场景（IoT 物联管理平台）**：

| 页面 | 关联 tab | 表现形式 |
|:---|:---|:---|
| 设备详情页 | "元件" tab | 显示关联的元件（模型名称+版本, 具体元件名称） |
| 设备模型详情页 | "元件模型" tab | 显示关联的元件模型（版本信息） |
| 设备创建页 | "元件" tab | 关联已发布的元件（el-select 搜索模式） |

**⚠️ 重要区分**：创建页的"元件"tab 使用 `el-select` 下拉选择器，详情页的"元件"tab 使用 `el-tree` 树展示。同一个 tab 名称，**创建模式下是选择器，详情模式下是树组件**，断言策略完全不同。

## 按钮点击多策略回退（重要！）

Element UI 按钮的 accessible name 是完整文本（如"新增系统"），用 `get_by_role("button", name="新增")` 精确匹配会失败。

**Craft 脚本中 click() 函数的多策略顺序：**

```python
async def click(page, role, name, desc) -> bool:
    for attempt in range(3):
        try:
            # 策略1: locator支持文本匹配(适配Element UI，has-text匹配子串)
            parts = [f"text={name}"]
            if role == "button":
                parts.append(f"button:has-text('{name}')")
                parts.append(f"css=button >> text={name}")
            else:
                parts.append(f"[role='{role}']:has-text('{name}')")
            el = page.locator(", ".join(parts)).first
            if await el.count() == 0:
                # 策略2: role精确匹配
                el = page.get_by_role(role, name=name)
            if await el.count() == 0:
                # 策略3: role模糊匹配（re.compile解决"新增"匹配"新增系统"）
                el = page.get_by_role(role, name=re.compile(name))
            await el.wait_for(state="visible", timeout=3000)
            await el.click(timeout=5000)
            ...
```

**核心原理：** `has-text('新增')` 匹配任何包含"新增"文本的按钮，而 `get_by_role("button", name="新增")` 要求完整精确匹配。

## 输入框填值多策略回退（重要！）

```python
async def fill(page, placeholder_or_role, value, desc) -> bool:
    for attempt in range(3):
        try:
            # 策略1: placeholder优先(Element UI el-input 最可靠)
            el = page.get_by_placeholder(placeholder_or_role)
            if await el.count() == 0:
                # 策略2: label textbox
                el = page.get_by_role("textbox", name=placeholder_or_role)
            if await el.count() == 0:
                # 策略3: CSS选择器
                el = page.locator(placeholder_or_role)
            if await el.count() == 0:
                # 策略4: input+placeholder CSS通配
                el = page.locator(f"input[placeholder*='{placeholder_or_role}']")
            await el.fill(value)
            ...
```

**核心原理：** `get_by_placeholder("请输入系统名称")` 是 Element UI 输入框最可靠的定位方式。`get_by_role("textbox")` 在 Vue 3 中有时匹配不到。

**exact_placeholder 精确匹配模式（防误填关键）：**

当 `label` 参数 placeholder 在页面中可能有多个模糊匹配时（如"名称"可能匹配"请输入模型名称"和属性行"名称"），必须使用精确匹配：

```python
# 精确匹配 - 只匹配 placeholder 完全等于 label 的 input
el = page.get_by_placeholder(label, exact=True)

# 不要使用 re.compile 模糊匹配
# ❌ 错误：re.compile("名称") 会匹配到 "请输入模型名称"
el = page.get_by_role("textbox", name=re.compile(label))
```

**适用场景：** 元件模型新增页的属性行填写。属性行"名称"的 placeholder 就是 `"名称"`，而基础信息"模型名称"的 placeholder 是 `"请输入模型名称"`。模糊匹配会导致属性行被填到模型名称字段。

**策略5 — 遍历按描述匹配（兜底，解决label/placeholder不匹配）：**

```python
if await el.count() == 0:
    # 策略5: 遍历所有文本框按描述匹配
    all_tb = page.get_by_role("textbox")
    tb_count = await all_tb.count()
    for i in range(tb_count):
        lbl = (await all_tb.nth(i).get_attribute("aria-label") or "")
        ph = (await all_tb.nth(i).get_attribute("placeholder") or "")
        if any(kw in lbl or kw in ph for kw in [desc, placeholder_or_role.replace('请输入', '')]):
            el = all_tb.nth(i)
            break
```

**适用场景：** 当页面输入框的 aria-label 是 `"* 模型名称"` 但脚本传入的 placeholder_or_role 是 `"请输入设备模型名称"` 时，前4个策略全部失效。策略5利用 `desc` 参数（如 `"设备模型名称"`）遍历所有 textbox，匹配 `"模型名称"` 子串找到目标输入框。

**使用限制：** 策略5是 O(n) 遍历，当页面 textbox 较多时较慢。搜索类脚本因此耗时增加（从~30s 到 ~100s），但能显著提升通过率。

## f-string 生成脚本时的陷阱：编译时 vs 运行时判定

**问题：** 用 f-string 模板生成 Python 脚本时，条件判断 `if placeholder_code:` 如果没放在大括号中，会作为字面文本写入生成的脚本中，导致运行时 NameError。

**错误写法（placeholder_code泄露到生成的脚本中）：**
```python
def gen_create_steps(placeholder_code=None):
    return f"""
    if placeholder_code:   # ← 这是字面文本，不是f-string插值！
        await fill(page, "{placeholder_code}", entity_code, "编码")
    """
```

**正确写法（编译时决定是否包含代码行）：**
```python
def gen_create_steps(placeholder_code=None):
    code_fill = ""
    if placeholder_code:  # ← 在Python编译时判定
        code_fill = f'    await fill(page, "{placeholder_code}", entity_code, f"{{entity_cn}}编码")\n'
    return f"""
    {code_fill}  # ← 通过变量插值控制内容
    """
```

**规则：** 在模板生成器中，所有条件逻辑必须在"外层 Python"（f-string 外部）处理，不要依赖生成的脚本去判定由模板参数决定的条件。

## Playwright 异步上下文管理陷阱

### `async with` 作用域溢出（致命）

**错误日志特征：**
```
Browser.new_context: Target page, context or browser has been closed
[错误] 测试执行异常: Browser.new_context: Target page, context or browser has been closed
```

**问题：** `generate_all.py` 生成的脚本中，`async with async_playwright() as p:` 块有时只包裹了 `browser = await p.chromium.launch()`，而后续的 `browser.new_context()`、`page.goto()`、`await browser.close()` 都在块外。当 `async with` 退出时 Playwright 实例 `p` 关闭，后面所有操作都报错。

**错误结构：**
```python
try:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
    ctx = await browser.new_context(...)   # ← 在 async with 外！
    page = await ctx.new_page()            # ← 在 async with 外！
    ...
    await browser.close()                  # ← 在 async with 外！
except:
    ...
```

**修复（正确结构）：**
```python
try:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context(...)
        page = await ctx.new_page()
        ...
        await browser.close()
except:
    ...
```

**根本原因：** `generate_all.py` 的 f-string 模板缩进不一致。生成的脚本中所有 Playwright 操作（launch, new_context, new_page, goto, close）必须全部在 `async with` 块内。验证方法：检查输出脚本中 `browser.new_context()` 和 `browser.close()` 是否与 `browser = await p.chromium.launch()` 在同一缩进级别。

## 自愈规则（通用）

```python
FAILURE_RULES = {
    "intercepts pointer events": {"fix": "force_click"},
    "strict mode violation":     {"fix": "use_first_or_filter"},
    "Timeout 30000ms exceeded":  {"fix": "retry_longer_wait"},
    "status: 500":               {"fix": "wait_and_retry"},
}
```


---

## 附录：SPA 登录陷阱（来源：`spa-login-pitfalls.md`）

# SPA 登录与跨平台导航陷阱

## 问题：page.goto 触发 SPA 全量重载，Auth 状态丢失

Hash-based SPA（Vue Router hash 模式）中，`page.goto(url)` 触发**浏览器全量页面加载**，导致：
1. Vue 应用重新初始化
2. Pinia/Vuex 中的 auth 状态丢失
3. SPA 拦截导航并重定向到登录页

## 解决方案：循环检测 + 登录兜底

```python
def ensure_on_page(page, target_url, wait_seconds=3):
    tgt_hash = urlparse(target_url).fragment
    cur_hash = urlparse(page.url).fragment
    if cur_hash == tgt_hash:
        return True
    for attempt in range(2):
        page.goto(target_url, wait_until="domcontentloaded")
        time.sleep(wait_seconds)
        for check in range(5):
            now_hash = urlparse(page.url).fragment
            if now_hash == tgt_hash:
                return True
            if "login" in page.url:
                if attempt == 0:
                    do_login(page)  # 重新登录
                    break
                return False
            time.sleep(1)
    return False
```

## 为什么单次检查不行？

```
page.goto(url, wait_until="domcontentloaded")   # ← DOM 加载完毕即返回（<1s）
time.sleep(3)                                     # ← 3秒内 SPA 启动、路由判断、重定向…
if "login" in page.url:                           # ← 此时 URL 已变，能检测到
```

但 3 秒后的 `page.goto` 在 `domcontentloaded` 时返回，此时 SPA 的 JS 框架尚未完成路由判断。SPA 的异步重定向发生在 JS 解析执行之后，可能比 `domcontentloaded` 晚 0.5-2 秒。所以**必须用循环检查，不能只用一次 sleep+if**。

## 登录 + 租户选择完整模式（RuoYi-Vue-Pro / Vben Admin）

```python
def do_login(page):
    page.get_by_placeholder("请输入用户名").fill(USERNAME)
    page.get_by_placeholder("请输入密码").fill(PASSWORD)
    page.locator("button.ant-btn").filter(has_text="登").click()
    time.sleep(3)
    # 租户选择
    ts = page.locator(".ant-select").first
    if ts.count() > 0 and "租户" in page.locator("body").inner_text():
        ts.click(); time.sleep(1)
        opt = page.locator(".ant-select-item-option").first
        if opt.count() > 0: opt.click(); time.sleep(2)
    # 导航到工作台初始化 SPA
    page.goto(f"{BASE_URL}/#/workspace", wait_until="domcontentloaded")
    time.sleep(3)
```

## 新平台首次脚本开发黄金流程

1. 登录并导航到列表页
2. 打印所有 button、input placeholder、label、select 的实际结构
3. 点击"新增"按钮（弹出 Modal）
4. 再次打印 Modal 内全部按钮、输入框、select、label
5. **确认实际结构后再写定位代码**
6. 不要猜测 placeholder/label/button 文本
