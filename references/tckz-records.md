# TCKZ 总控平台调试记录

## 调试发现

> 来源：tckz-debug-findings.md

# tckz（总控应用集成系统）调试发现

## 平台特征

- **技术栈**: Vue 3 + Ant Design + Vben Admin v5+, Hash-based SPA (`#/xxx`)
- **登录**: admin/admin123, 需选择租户（芋道源码）
- **表单模式**: Inline（非 Modal）— 点击"新增"后表单直接渲染在页面内
- **按钮文本**: 含空格 `确 认`、`取 消`、`重 置`、`搜 索`

## 组件交互

### 搜索选择器（Dialog 模式）
部分字段（设备选择、巡检项选择）不是标准 a-select，点击后打开独立 Dialog：
```python
inp = page.locator("input[placeholder='请选择巡检设备']")
inp.locator("..").locator("..").click(force=True)  # 打开 Dialog
# Dialog 结构：.ant-modal → .ant-modal-title + .ant-modal-body(table) + footer
rows = page.locator(".ant-modal .ant-table-tbody tr:not(.ant-table-placeholder)")
if rows.count() > 0:
    rows.first.click()
    page.locator(".ant-modal button").filter(has_text="确").first.click(force=True)
```

### 标准 a-select（文本内容匹配）
部分字段的 placeholder 以 DIV 文本形式存在：
```python
sel = page.locator(".ant-select").filter(has_text="请选择巡检项类型").first
sel.click(force=True)
opts = page.locator(".ant-select-dropdown:visible .ant-select-item-option")
opts.first.click(force=True)
```

### 保存失败处理
Inline 表单提交失败时表单保持打开，必须手动关闭：
```python
ant_confirm(page); time.sleep(3)
if page.locator("input[placeholder='请输入XX名称']").count() > 0:
    page.locator("button").filter(has_text="取 消").first.click(force=True)
```

## SPA 导航

**永远不要用 `page.goto` 导航 hash URL** — 触发全量重载失去 auth：
```python
# 仅首次加载用 goto
page.goto(f"{BASE}/#/auth/login")
# 后续页面切换用 JS hash
page.evaluate("window.location.hash = '#/maintenance/item'")
```

## 数据来源

设备数据来自 IoT 物联管理平台，不是 tckz 自身创建。编写测试时不应预置 `ope_machine` 数据，应通过 Dialog 选择已有数据。

---

## 表单结构

> 来源：tckz-inspection-form-structure.md

# 总控集成系统（tckz）巡检模块表单结构

> 平台：http://10.30.25.186:5001
> 框架：Vue 3 + Ant Design + Vben Admin v5
> 数据库：jws (PostgreSQL 17.5, 145 tables)

## 表单交互模式

### Inline 表单（非 Modal）

点击"新增"后表单直接渲染在页面内作为第二个 `<form>`，不是弹窗：

```
before click: forms=1
after  click: forms=2, modals=0, drawers=0
```

检测方式：`document.querySelectorAll(".ant-modal").length === 0`
保存失败后需手动点"取消"关闭表单，否则 `<div data-dismissable-modal>` 遮挡页面。

### Dialog 选择器

部分字段（设备选择、巡检项选择）不是标准 a-select，而是点击后打开独立 Dialog：

```
点击 input wrapper (祖父级 div) → 弹出 .ant-modal 标题为 "设备选择"/"巡检项选择"
  ├── .ant-modal-header: 标题
  ├── .ant-modal-body: .ant-table (编号/名称/类型)
  └── .ant-modal-footer: 取消/确定
```

标准交互模式（已调试通过）：
```python
inp = page.locator("input[placeholder='请选择巡检设备']")
inp.locator("..").locator("..").click(force=True)  # 祖父级 div
time.sleep(2)
rows = page.locator(".ant-modal .ant-table-tbody tr:not(.ant-table-placeholder)")
if rows.count() > 0:
    rows.first.click()
    page.locator(".ant-modal button").filter(has_text="确").first.click(force=True)
else:
    page.locator(".ant-modal button").filter(has_text="取").first.click(force=True)
```

### 按钮文本

Vben Admin 特征：中文字符间有空格

| English | Chinese with spaces |
|:---|:---|
| Confirm | `确 认` |
| Cancel | `取 消` |
| Reset | `重 置` |
| Search | `搜 索` |
| OK (alternate) | `确 定` |

匹配策略：优先 `确 认`，回退 `确 定`

### 下拉选择器定位

**文本内容匹配**（标准模式）：placeholder 作为 text content 渲染时可用
```python
sel = page.locator(".ant-select").filter(has_text="请选择巡检项类型").first
```

**placeholder 属性匹配**（搜索模式）：placeholder 作为 input 属性时，`:has()` 选择器
```python
sel = page.locator(".ant-select:has(input[placeholder='请选择巡检设备'])").first
```
注意：Playwright 支持 CSS `:has()`，但需要在 `.ant-select` 级别使用。

## 巡检项创建表单

点击"新增巡检项"后的 inline 表单字段：

| 字段 | 定位方式 | 类型 | 必填 |
|:---|:---|:---:|:---:|
| 巡检项名称 | `placeholder="请输入巡检项名称"` | text input | ✅ |
| 巡检项类型 | `.ant-select` has_text `请选择巡检项类型` | a-select | ✅ |
| 巡检项方法 | `.ant-select` has_text `请选择巡检项方法` | a-select | ✅ |
| 巡检项逻辑类型 | `.ant-select` has_text `请选择巡检项逻辑类型` | a-select | ✅ |
| 是否包含边界值 | `.ant-select` has_text `请选择是否包含边界值` | a-select | ✅ |
| 告警类型 | `.ant-select` has_text `请选择告警类型` | a-select | ✅ |
| 是否必检 | `.ant-select` has_text `请选择是否必检` | a-select | ✅ |
| 关联设备 | `placeholder="请选择巡检设备"` | Dialog 选择 | ✅ |

## 巡检计划创建表单

点击"新增巡检计划"后的 inline 表单字段：

| 字段 | 定位方式 | 类型 | 必填 |
|:---|:---|:---:|:---:|
| 计划名称 | `placeholder="请输入巡检计划名称"` | text input | ✅ |
| 巡检周期 | `.ant-select` has_text `请选择周期` | a-select | ✅ |
| 负责人 | `.ant-select` has_text `请选择负责人` | a-select | ✅ |
| 巡检项 | `placeholder="请选择巡检项"` | Dialog 选择 | ✅ |

## 调试技巧

1. **页面结构诊断**：使用 `page.evaluate("document.querySelectorAll('.ant-modal').length")` 判断是否为 Modal
2. **表单字段发现**：`page.evaluate("Array.from(document.querySelectorAll('input[placeholder]')).map(i=>i.getAttribute('placeholder'))")` 列出所有输入框 placeholder
3. **按钮文本发现**：`page.evaluate("Array.from(document.querySelectorAll('button')).map(b=>b.textContent.trim()).filter(t=>t)")`
4. **Select 类型判断**：`document.querySelectorAll(".ant-select")` 数量为 0 时，选择器可能是 Dialog 或自定义组件
5. **保存失败诊断**：`page.evaluate("Array.from(document.querySelectorAll('[class*=error],[aria-invalid=true]')).map(e=>e.textContent.trim()).filter(t=>t)")` 列出验证错误
