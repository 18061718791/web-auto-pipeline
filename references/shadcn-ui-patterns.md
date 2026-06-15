# Shadcn UI / Radix UI 组件交互参考

> 基于 惠联新质（电厂AI管家）平台探索 — Next.js + Shadcn UI + Radix UI + Tailwind CSS
> 与 Element Plus / Vue 体系的根本区别在于：Radix UI 组件通过 Portal 渲染到 body 层级。
> **2026-06-11 更新**：验证确认 Playwright 原生 `click()` 对 Radix UI v2（该平台使用的版本）完全有效。不需要手动 dispatchEvent PointerEvent 链。

## 平台结构特征

| 特征 | Shadcn UI (Radix UI) | Element Plus (Vue) |
|:---|:---|:---|
| 框架 | React (Next.js) | Vue 3 |
| CSS | Tailwind CSS | scoped CSS |
| 组件库 | @radix-ui/react-* (无头组件) | Element Plus (自带样式) |
| Portal 渲染 | 对话框/下拉菜单通过 Portal 到 body | 通常在同级 DOM |
| 定位方式 | `data-slot` / `data-sidebar` 属性 | `.el-*` class 前缀 |
| 无障碍 | ARIA role 完整 | ARIA role 部分实现 |
| 文件上传 | 隐藏 `input[type="file"]` + dropzone | `.el-upload` 包装器 |

## 全局布局结构

```
<div id="root">
  <div class="sidebar-wrapper">          <!-- 侧边栏 -->
    <div data-sidebar="sidebar">
      <div data-slot="sidebar-header">   <!-- 顶部：工作空间切换 -->
        <button data-slot="dropdown-menu-trigger">
          <!-- Radix UI DropdownMenu -->
        </button>
      </div>
      <div data-slot="sidebar-content">  <!-- 中间：菜单组 -->
        <div data-slot="sidebar-group-label">工作空间</div>
        <a data-slot="sidebar-menu-button" href="/kbs">知识管理</a>
      </div>
      <div data-slot="sidebar-footer">   <!-- 底部：用户菜单 -->
        <button data-slot="dropdown-menu-trigger">
          <!-- 用户名 + 退出登录 -->
        </button>
      </div>
    </div>
  </div>
  <div>                                  <!-- 主内容区 -->
    <header data-testid="layout-header"> <!-- 顶部栏 -->
    <main>                               <!-- 页面内容 -->
  </div>
</div>
```

## 组件交互（已验证有效）

### DropdownMenu / Combobox

**Playwright 原生 `click()` 有效。** 不需要手动 dispatchEvent：

```python
# ✅ 验证通过：Click 触发 Radix UI DropdownMenu
page.locator('button').filter(has_text='路小2').first.click()
time.sleep(0.5)

# ✅ 验证通过：选择 menuitem
page.locator('[role="menuitem"]').filter(has_text='退出').first.click()

# ✅ 验证通过：Combobox (分类选择)
dialog.locator('[role="combobox"]').click()
page.locator('[role="option"]').filter(has_text='项目与设计档案类').first.click()

# ✅ 验证通过：Dialog 内的上传按钮
dialog.get_by_role('button', name='上传').click()
```

### AlertDialog（确认弹窗）

退出登录等操作触发 AlertDialog，需要点击确认按钮：

```python
# 点击"退出" → 弹出确认弹窗
page.locator('[role="menuitem"]').filter(has_text='退出').first.click()
time.sleep(0.5)

# 点击"确认退出"
page.get_by_role('button', name='确认退出').first.click()
time.sleep(1)
```

### Tab

使用 `get_by_role("tab")`，普通 click 有效：

```python
page.get_by_role('tab', name='审批列表').click()
page.get_by_role('tab', name='文件列表').click()
```

### 文件上传

Shadcn UI 使用隐藏的 `input[type="file"]` + 可点击的 dropzone div。

```python
# ✅ 方案1（推荐）：直接操作隐藏 input
file_input = page.locator('input[type="file"]')
assert file_input.count() > 0, "文件输入框不存在"
file_input.set_input_files("E:/path/to/file.docx")
time.sleep(1)

# ✅ 方案2：点击 dropzone 触发 expect_file_chooser
with page.expect_file_chooser() as fc_info:
    page.locator("text=点击或拖拽上传文档").click()
    time.sleep(1)
file_chooser = fc_info.value
file_chooser.set_files("E:/path/to/file.docx")
```

**注意：** 隐藏 input 的 class 为 `sr-only`（screen-reader only），必须使用 `page.locator('input[type="file"]')` 定位。

### SPA 登录认证

**关键陷阱：SPA 应用登录后 URL 不变**。该平台使用 Next.js SPA 模式，登录后 URL 仍为 `/auth/signin`，但页面内容已替换为应用内容。

```python
# ❌ 错误：检查 URL 变化
assert '/auth/signin' not in page.url  # SPA 模式下永远失败！

# ✅ 正确：检查页面内容
body = page.locator('body').inner_text()
assert '用户名' not in body or '退出' in body, '登录失败'
```

### 用户菜单 + 退出登录

```python
# 1. 打开用户菜单
page.locator('button').filter(has_text='用户名').first.click()
time.sleep(0.5)

# 2. 点击退出
page.locator('[role="menuitem"]').filter(has_text='退出').first.click()
time.sleep(0.5)

# 3. 确认退出弹窗
confirm_btn = page.get_by_role('button', name='确认退出').first
confirm_btn.click()
time.sleep(1)

# 4. 验证退出成功（URL 变回 /auth/signin）
assert 'auth/signin' in page.url or '登录' in page.locator('body').inner_text()
```

### 输入框定位

Shadcn UI 的输入框使用 `get_by_placeholder()` 定位，与 Element Plus 一致。常见 placeholder：

| 页面 | Placeholder |
|:---|:---|
| 知识管理-搜索文档 | `搜索文档...` |
| 知识萃取-搜索知识库 | `搜索知识库，支持关键词、问题等搜索方式` |
| 知识问答-输入框 | `随便问点什么...` |
| 上传文档-描述 | `输入文档描述` |

### 侧边栏定位

```python
# 导航到知识管理页面
link = page.locator('a[href="/kbs"]').first
if link.count() > 0:
    link.click()
else:
    page.goto("http://host:port/kbs")
```

### 表格

Shadcn UI 的表格使用标准 `<table>` 元素：

```python
headers = page.locator("thead th").all_inner_texts()
rows = page.locator("tbody tr")
data = rows.all_inner_texts() if rows.count() > 0 else []
```

## 平台探索流程（非 Element Plus 平台）

### 1. 确认框架类型
```javascript
document.querySelector('[data-sidebar]')          // → Shadcn sidebar
document.querySelector('[data-slot]')              // → Shadcn 组件
document.querySelector('#__next')                  // → Next.js
```

### 2. 确认交互模式（Playwright 原生 click 是否足够）
先写一段简单测试验证 click 能否触发下拉菜单。如能正常触发（已验证 Radix UI v2 可以），则无需任何 dispatchEvent 代码。

### 3. 路由收集
```javascript
Array.from(document.querySelectorAll('a[href]'))
  .filter(a => a.href.startsWith(location.origin))
  .map(a => a.innerText.trim() + ': ' + a.href.replace(location.origin, ''))
```

### 4. SPA 登录验证
登录后检查 `page.locator('body').inner_text()` 是否包含应用内容，而非检查 URL。

## 平台参考（hlxinzhi 惠联新质·电厂AI管家）

| 项目 | 值 |
|:---|:---|
| 基础 URL | `http://10.20.42.22:8081` |
| 登录页 | `/auth/signin?redirect=...` |
| 知识管理 | `/kbs` |
| 知识萃取 | `/extractions` |
| 知识问答 | `/ai-assistant` |

**路由全表**：
- `/notifications` — 通知管理
- `/alarm` — 告警管理
- `/reports` — 生产报表
- `/report-data` — 数据上报
- `/ai-assistant` — 知识问答
- `/kbs` — 知识管理（文件上传/审批）
- `/extractions` — 知识萃取
- `/chatbi` — 智能问数
- `/system/users` — 用户管理
- `/system/roles` — 角色管理
- `/system/logs` — 操作日志
- `/system/dicts` — 字典管理
- `/kb-prompts` — 指令管理

**分类选项（10个）**：
1. 生产运维规程类
2. 设备全生命周期类
3. 安全生产与合规管理类
4. 公司制度管理类
5. 生产经营数据类
6. 技术与行业标准类
7. 故障处置与案例库类
8. 培训与知识传承类
9. 项目与设计档案类
10. 其他类型

## 常见陷阱

| 陷阱 | 表现 | 修复 |
|:---|:---|:---|
| 登录断言错 | 使用 URL 变化判断登录是否成功（SPA 模式 URL 不变） | 改用 body 内容判断 |
| 文件上传找不到 input | `get_by_role("textbox")` 定位不到 | 使用 `locator('input[type="file"]')` |
| Dialog 按钮点击无效 | 上传/取消按钮点了没反应 | 尝试 Tab 聚焦 + Enter 提交。先点击 dialog 内输入框确保焦点 → Tab 到目标按钮 → Enter。见下方 Radix UI 强制降级方案 |
| 退出不彻底 | 点了"退出"但未实际登出 | 缺少 AlertDialog 的"确认退出"步骤 |
| 会话自动过期 | 导航后回到登录页 `/auth/signin` | 在关键操作前检测是否需要重新登录 |
| 工作空间不是目标 | 登录后默认进了其他 workspace | 先检查 sidebar 文本，再决定是否切换 |

### ⚠️ Radix UI Dialog 按钮 click 无效（强制降级方案）

部分 Radix UI Dialog 内的按钮（特别是表单提交类如"上传"），Playwright 的 `click(force=True)`、`dispatchEvent()`、JS `focus()+Enter` 均可能无效。**2026-06-11 实测 Tab 链聚焦 + Enter 有效**：

```python
# 降级方案：点击 dialog 内元素建立焦点 → Tab 到目标按钮 → Enter
page.get_by_placeholder("输入文档描述").click()   # 确保焦点在 dialog 内
time.sleep(0.2)
for i in range(6):                              # 最多 Tab 6 次
    page.keyboard.press("Tab")
    time.sleep(0.15)
    focused = page.evaluate("document.activeElement?.innerText || ''")
    if "上传" in focused:                         # 目标按钮文本
        break
page.keyboard.press("Enter")
```

**适用场景**：Dialog 内的"上传"、"保存"、"提交"等按钮。2026-06-11 在 hlxinzhi 平台的 Shadcn UI 上传面板中 `click()` 完全无效，Tab+Enter 是唯一可用的方式。

### ⚠️ Strict Mode Violation

Shadcn UI 中常有两个功能不同的按钮共享相同 accessible name：

| 场景 | 冲突元素 | 修复 |
|:---|:---|:---|
| **弹窗关闭** | 底部文本"关闭" + 右上角 X 图标按钮 | `.last` 选文本按钮 |
| **搜索按钮** | "搜索"按钮 + 清空重置按钮 | `[data-testid="extraction-search-btn"]` |
| **确认按钮** | 弹窗中的"确认"+ 其他同名按钮 | 缩小到 `[role="dialog"]` 内 |

```python
# 关闭弹窗：用 .last 避开右上角 X 图标按钮
page.get_by_role("button", name="关闭").last.click()

# 搜索按钮（知识萃取页）：用 data-testid 区分
page.locator('[data-testid="extraction-search-btn"]').first.click()

# 确认按钮
page.get_by_role("button", name="确认").last.click()
```
