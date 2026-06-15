# 故障目录（Failure Catalog）

> 从 `web-auto-pipeline` SKILL.md 及关联 reference 文件提取的完整故障目录。
> 包含故障信号表、静默失败诊断流程、DB 验证最佳实践。
>
> **提取时间：** 2026-06-09（v2: 增加分类目录）
> **来源文件：** `scripts/self_heal.py`（信号库）、`references/silent-save-debugging.md`、`references/core-principles.md`、`references/element_ui_patterns.md`、`references/el-autocomplete-trap.md`、`references/post-action-error-detection.md`、`references/check_page_errors-selector-false-positive.md`

---

## 快速诊断导航

按故障现象判断分类，直接定位修复策略：

```
遇到故障现象
  │
  ├─ 元素找不到 / 选择器不匹配 ─────────→ Category A: 元素/选择器问题
  ├─ 点击无反应 / 下拉不展开 / 保存静默 ─→ Category B: 点击/交互问题
  ├─ 页面状态不对 / 导航错位 / 场景中断 ─→ Category C: 导航/状态问题
  ├─ 表单保存失败 / 字段校验不通过 ─────→ Category D: 表单问题
  └─ 环境差异 / 报告误报 / 脚本异常 ────→ Category E: 环境问题
```

---

## 分类目录

### Category A: 元素/选择器问题（S001-S003, S012, S016）

当 Playwright 报错 "element not found"、"strict mode violation"、"timeout" 时优先查此分类。

| 信号 | 信号名称 | 一句话根因 | 快速修复 |
|:---|:---|:---|:---|
| S001 | 指针事件拦截 | Element UI `<span>` overlay 遮挡目标 | `force=True` 或 `dispatchEvent` |
| S002 | 严格模式违规 | 选择器匹配多个元素 | `.first` 或 `.nth(i)` 精确定位 |
| S003 | 超时（Timeout） | 元素未在指定时间内出现在 DOM 中 | 检查 URL、增等待、换定位方式 |
| S012 | el-select 无 role='option' | Element Plus 选项无 ARIA role | `locator('.el-select-dropdown__item')` 替代 |
| S016 | 搜索框 placeholder 超时 | label 标签优先于 placeholder 属性 | 降级用 `get_by_label()` 或 `[aria-label]` |

### Category B: 点击/交互问题（S004-S006, S015）

当点击后无反应、下拉不展开、保存后无数据写入时优先查此分类。

| 信号 | 信号名称 | 一句话根因 | 快速修复 |
|:---|:---|:---|:---|
| S004 | 下拉选项无法选中 | el-select teleport 或 popper 关闭 | `click(force=True)` 或 键盘 ArrowDown+Enter |
| S005 | el-autocomplete 静默失败 | 键盘选择不触发 Vue `@select` | `dispatchEvent('click')` 点击选项 |
| S006 | 保存后无数据写入 | 表单验证静默失败 或 popper overlay | 5步诊断流程（见 SKILL.md §诊断流程） |
| S015 | el-autocomplete popper 未关闭 | 透明 overlay 拦截后续点击 | 保存前 `page.keyboard.press("Escape")` |

### Category C: 导航/状态问题（S007, S009, S014, S025, S027）

当页面状态不对、导航错位、场景意外中断时优先查此分类。

| 信号 | 信号名称 | 一句话根因 | 快速修复 |
|:---|:---|:---|:---|
| S007 | 保存后 URL 未变化 | 平台设计不跳转/不弹成功消息 | **DB 直查**（唯一可靠方式） |
| S009 | Tab 切换后保存无效 | Vue SPA tab 切换导致 v-model 绑定丢失 | 直接在当前 Tab 保存 |
| S014 | 页面空白 | Session 过期 / token 重定向 | 导航到列表页继续 |
| S025 | 非关键场景阻断后续 | PV 关联等可选操作失败后直接 `return` | 引入 `NON_BLOCKING` 集合 |

### Category D: 表单问题（S008, S010-S011, S017, S020-S024）

当表单保存失败、字段校验错误、状态未变更时优先查此分类。

| 信号 | 信号名称 | 一句话根因 | 快速修复 |
|:---|:---|:---|:---|
| S008 | DB 唯一约束冲突 | 跨运行未生成唯一值 | 运行时生成唯一值 + 清理前置 |
| S010 | 发布状态未变更 | 后端异步处理延迟 | 循环轮询 6 次 × 5 秒 |
| S011 | NPE / NullPointerException | IoT 平台后端 BUG | 确认前置场景已完成 |
| S017 | 子设备要求未满足 | 设备模型含 sub-device 结构 | 改用不含子设备的模型 |
| S020 | 按钮 disabled | 表单验证未通过 | 先修复表单，不用 `force=True` 绕过 |
| S021 | 表单验证错误漏检 | check_page_errors 延迟导致错过 | 保存后立即检查（无 sleep） |
| S022 | 保存按钮不在 `<form>` 内 | 按钮在 header 区域独立 `<div>` | `page.locator("button").filter(has_text="保存")` |
| S023 | 自动关联表IP字段 — 设备IP与PV IP冲突（→ S027 细化版） | 跨实体的IP唯一约束（设备IP不能等于已有PV的IP） | 设备创建设置独立IP（如`10.20.30.40`），不与已有PV/IP字段重复；保存后用DB直查验证 |
| S024 | autocomplete 选项带版本后缀 | 选项文本含 "v1" 后缀 | 用 `filter(has_text=...)` 子串匹配 |

### Category E: 环境问题（S013, S018-S019, S026）

当有头/无头行为不同、报告误报、脚本异常中断时优先查此分类。

| 信号 | 信号名称 | 一句话根因 | 快速修复 |
|:---|:---|:---|:---|
| S013 | 有头/无头差异 | 渲染速度或浏览器焦点差异 | 增等待 + `force=True` |
| S018 | check_page_errors 假阳性（选择器过宽） | 选择器过宽混入成功消息 | 选择器只保留 `--error`/`--warning` 后缀 |
| S028 | check_page_errors 假阳性（body关键词误判） | `backend_keywords` 含 `"404"`/`"500"`/`"error"` 等通用词，URL或正常文案中误匹配 | 从 `backend_keywords` 中移除数字编码和泛化词；保留 `"Cannot invoke"`、`"NullPointerException"` 等确切错误模式 |
| S019 | 输入框 disabled | 编辑页字段只读/禁用 | 检查后改用其他字段 |
| S026 | 场景步数冗余 | check_page_errors 内部含 `report.step()` | 从 check_page_errors 中移除 step 调用 |

---

## 1. 故障信号表

> 每行一个已知故障信号，包含信号描述、常见原因、恢复策略。

| 信号 | 常见原因 | 恢复策略 |
|:---|:---|:---|
| **指针事件拦截**（intercepts pointer events） | Element UI `<span>` overlay 遮挡目标元素（如 `.el-select__selected-item`） | 使用 `force=True` 或 JS 原生点击（`dispatchEvent`）绕过 overlay 拦截 |
| **严格模式违规**（strict mode violation） | 选择器匹配到多个元素（如"设备"同时匹配父菜单和叶子菜单），Playwright 无法确定目标 | 使用 `.first` 或 `.nth(i)` 精确定位，或增加更具体的过滤条件（`filter(has_text=...)`） |
| **超时**（Timeout 30000ms exceeded） | 元素未在指定时间内出现在 DOM 中 | 检查 URL 是否正确、前置操作是否完成、增加等待时间。分三种子场景：① `get_by_placeholder` 超时 → 输入框可能由 `<label>` 标记而非 placeholder，降级用 `get_by_label()`；② `get_by_role("button")` 超时 → 按钮可能不是原生 button（如 `<a>` 标签），改用 locator 定位；③ `get_by_role("option")` 超时 → el-select 选项无 `role='option'`，用 `.el-select-dropdown__item` |
| **下拉选项无法选中**（el-select 点击不生效） | el-select 的 teleport 渲染到 `<body>` 末尾，Playwright 可见性检查失败；下拉后 popper 关闭，选项 `<li>` 在 DOM 中但不可见（`display:none`） | `click(force=True)` 打开下拉 → 等待 1.5s → `click(force=True)` 或 **键盘 ArrowDown+Enter** 选择 `.el-select-dropdown__item` |
| **el-autocomplete 静默失败**（v-model 未更新） | 键盘选择（ArrowDown+Enter）不会触发 Vue `@select` 事件；Popper overlay 遮挡后续点击 | fill 输入 → 等待 2.5s（debounce） → 用 `dispatchEvent('click')` 点击 `.el-autocomplete__popper li` 选项；保存前按 Escape 关闭 popper |
| **el-autocomplete popper 未关闭** | 点击下拉选项后 popper 元素停留在 DOM 中（transparent overlay），拦截后续所有点击事件 | 在保存前执行 `page.keyboard.press("Escape")` 确保 popper 关闭；诊断：`document.querySelectorAll('.el-autocomplete__popper:not([style*="display: none"])').length > 0` |
| **DB 唯一约束冲突**（"XXX 已被使用"） | 数据库唯一约束冲突（MAC 地址、编码、名称等字段重复），跨运行未生成唯一值 | 给每次运行生成唯一值：`f'00:1A:2B:{hash(name) % 65536:04x}'`；清理 SQL 置于脚本开头保证幂等性 |
| **Tab 切换后保存按钮无效** | Vue SPA tab 切换导致表单组件卸载/重建，部分 v-model 绑定丢失 | 如果目标 Tab 无内容（显示"暂无数据"），不要切换过去——直接在当前 Tab 保存即可 |
| **搜索框 placeholder 超时** | `get_by_placeholder` 超时，输入框可能由 `<label>` 标记而非 placeholder 属性；或 placeholder 值在 snapshot 中显示为 label 文本而非 HTML 属性值 | 用 `browser_console` 验证真实 placeholder 值；降级使用 `get_by_label()`、`[aria-label]` 或遍历 textbox 按描述匹配 |
| **保存后 URL 未变化**（无跳转） | 部分平台的创建表单保存后不跳转、不弹成功消息（平台设计如此） | 不要靠 URL 或消息判断保存成功；唯一可靠的验证方式是 **DB 直查** |
| **子设备要求** | 选择的设备模型包含 sub-device 结构，必须在元件 Tab 中为每个子设备关联具体元件实例 | 改用不包含子设备要求的模型；或在保存前切换到元件 Tab 搜索并关联已有元件 |
| **页面空白**（about:blank） | Session 过期或导航异常（token 过期被重定向到登录页） | 导航到列表页（不要重复创建），检查登录状态，从列表页搜索继续 |
| **保存后无数据写入**（UI + DB 均为空） | 表单验证静默失败（如 IP/MAC 格式校验）或 el-autocomplete popper overlay 遮挡保存按钮 | ① 点击保存前按 Escape 关闭 popper；② 检查 `.el-form-item__error` 确认验证错误；③ 监听 `page.on('request')` 确认网络请求；④ DB 直查验证 |
| **有头/无头模式差异** | 有头模式渲染速度差异或浏览器焦点/窗口层级问题；有头模式失败但无头通过 | 优先用 `force=True`；增加等待时间；用 `page.locator` 替换 `get_by_role` |
| **输入框 disabled** | 输入框处于只读/禁用状态（如编辑页某些字段不可修改） | 检查 `input.disabled` 或 `el-input.is-disabled`；通过 JS 启用或改用其他字段 |
| **按钮 disabled** | 按钮处于禁用状态（如 el-autocomplete 未正确选中时保存按钮 `is-disabled`） | 按钮不可用时不要用 `force=True` 绕过——检查 `.el-form-item__error` 确认根本原因（通常是 autocomplete 未选中），先修复表单 |
| **发布状态未变更** | 后端 PV 连通性检查延迟，发布操作执行后状态列仍为"草稿"（空） | 循环轮询 6 次 × 5 秒，检查行内状态列 td 文本是否为"发布"。注意：列表页默认显示草稿记录，状态列为**空**，发布后变为"发布" |
| **NPE / NullPointerException** | IoT 平台后端 BUG：`ThingModelVersion.getId()` 返回 null。可能因缺少版本记录 | 确认前置场景已执行（创建模型→发布→版本生成）；如操作无误则报告平台 BUG |
| **el-select 选项无 `role='option'`** | Element Plus 的 el-select 选项 DOM 没有 `role='option'` 属性，`get_by_role('option')` 找不到 | 用 `locator('.el-select-dropdown__item')` 替代 `get_by_role('option')` |
| **check_page_errors 假阳性** | 选择器过宽（如 `.el-message` 不含 `--error` 后缀），成功消息（如"发布成功"）被误判为错误 | 选择器只保留 error/warning 级别：`.el-message--error`、`.el-message--warning`，移除无后缀的 `.el-message`、`.ant-message` |
| **非关键场景阻断后续场景** | PV 关联等可选操作失败后立即 `return report`，阻断场景 5-9，但元件本身创建成功后续仍可执行 | 引入 `NON_BLOCKING` 集合（如场景 4、5），非关键失败不阻断；保存后报错不 `return`，让后续断言验证实际结果 |
| **表单验证错误（el-form-item__error）漏检** | `check_page_errors` 初始 2 秒延迟导致表单验证错误（出现时间短）被错过 | 改为立即检查，仅在无错误时才 `time.sleep(2)`；保存后用标准 `.click()` 触发表单验证，立即检查 `.el-form-item__error` |
| **保存按钮不在 `<form>` 内** | Vue/Element Plus 的保存按钮在页面 header 区域的独立 `<div>` 中，不在表单 `<form>` 内 | 用 `page.locator("button").filter(has_text="保存").first.click()` 原生点击（真实浏览器事件冒泡被 Vue 事件委托捕获） |
| **正确保存后无任何反馈**（平台设计） | 部分平台的创建表单保存后：不跳转、不弹出成功消息、停留在创建页 | 唯一可靠的验证方式是 **DB 直查**。不要依赖 URL 变化、成功消息或 alert 判断保存成功 |
| **IP/MAC 格式验证失败** | 平台对 IP/MAC 有严格格式校验：IP 拒绝 `192.168.x.x`；MAC 需连字符格式 `00-1A-2B-3C-4D-5E` | 使用 `10.x.x.x` 或 `172.x.x.x` 格式 IP；MAC 用连字符格式；保存后立即检查 `.el-form-item__error` |
| **el-autocomplete 选项带版本后缀** | 搜索"设备模型"返回的选项文本可能带版本后缀（如"设备模型 v1"），`get_by_text` 全等匹配失败 | 用 `filter(has_text=...)` 子串匹配替代全等匹配 |
| **场景步数冗余**（保存后 3 个 step） | `check_page_errors` 内部包含 `report.step()`, 调用方又追加 `report.step()` | 从 `check_page_errors` 中移除所有 `report.step()`，只保留 `report.assertion()`；step 由调用方在调用前统一管理（1 step） |
| **IP 冲突致静默保存失败** | 设备创建表单中IP字段与已有PV IP重复，后端API返回200但DB唯一约束导致写入失败且页面无错误提示 | 设备IP使用独立值（`10.20.30.40`），不与PV IP重复；保存后追加DB直查验证写入；API监听：`page.on("response")` 过滤 `addDeviceInfo` 确认响应200 |
| **check_page_errors body 关键词误判** | backend_keywords 含 `"404"`, `"500"`, `"error"`, `"失败"` 等通用词，页面URL或正常文案中包含这些字串导致false positive | 从 backend_keywords 中移除数字编码（404/500）和过于泛化的词（error/失败）——它们可能在URL、页码、或正常文案中出现；保留 `"Cannot invoke"`, `"NullPointerException"`, `"系统繁忙"` 等确切错误模式 |

---

## 2. 静默失败诊断流程（5 步排查）

当保存按钮 `click()` 后出现：**无网络请求、无错误提示、无表单验证错误、DB 无数据**时，按以下顺序排查：

### 第 1 步：检查 el-autocomplete popper 是否未关闭（最常见）

点击 el-autocomplete 的下拉选项后，popper 元素可能停留在 DOM 中（透明 overlay 拦截后续所有点击事件）。

```python
# 诊断命令
page.evaluate("""
    document.querySelectorAll('.el-autocomplete__popper:not([style*="display: none"])').length
""")
# > 0 表示 popper 未关闭
```

**修复：** 在点击任何 el-autocomplete 元素后、点击保存前，执行 `page.keyboard.press("Escape")` 确保 popper 关闭。

### 第 2 步：检查设备模型是否有子设备要求

选择的设备模型可能包含 sub-device 结构，需要额外操作。

**诊断：** 保存后立即检查 `.el-message--warning` 内容（如"请为所有子设备选择具体的元件"）。
**修复：** 改用不包含子设备要求的模型，或在保存前切换到元件 Tab 搜索并关联已有元件。

### 第 3 步：检查保存按钮是否在 `<form>` 内

Vue/Element Plus 的常见设计：保存按钮在页面 header 区域，不在表单 `<form>` 内。

```python
# 诊断
page.evaluate("""
() => {
    var btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('保存'));
    if (!btn) return {error: 'no button found'};
    var rect = btn.getBoundingClientRect();
    var cx = rect.left + rect.width/2;
    var cy = rect.top + rect.height/2;
    var top = document.elementFromPoint(cx, cy);
    return {
        disabled: btn.disabled,
        hasDisabledClass: btn.classList.contains('is-disabled'),
        inForm: btn.form !== null,
        topElement: top ? top.tagName + '.' + (top.className||'').slice(0,30) : 'none',
        isTopBtn: top === btn,
        popperOpen: document.querySelectorAll('.el-autocomplete__popper:not([style*="display: none"])').length,
        formErrors: Array.from(document.querySelectorAll('.el-form-item__error'))
            .map(e => e.textContent.trim())
    };
}
""")
```

**修复：** 使用 `page.locator("button").filter(has_text="保存").first.click()` 原生 Playwright 点击（无需 `force=True`），生成真实浏览器事件冒泡被 Vue 事件委托捕获。

### 第 4 步：检查表单验证错误（el-form-item__error）

IP/MAC 格式校验等表单验证错误 `.el-form-item__error` 可能出现时间极短（几百毫秒后消失）。

**关键：** 保存后**立即**检查，不能有延迟。

```python
# 保存后立即检查（无 sleep）
form_errs = []
for el in page.locator(".el-form-item__error").all():
    txt = el.text_content().strip()
    if txt: form_errs.append(txt)
if form_errs:
    log(f"表单验证错误: {'; '.join(form_errs)}", "❌")
```

**常见错误文本：** "请输入正确的IP地址"、"请输入MAC地址"、"请选择设备模型"。

### 第 5 步：确认平台设计是否无反馈

部分平台创建表单保存后：不跳转、不弹出成功消息、停留在创建页。

**诊断：** 唯一可靠的验证方式是 **DB 直查**。`page.on("request")` 也可能捕获不到（XHR 已发出但页面无反馈）。

**修复：** 脚本中始终包含 DB 断言 `SELECT ... WHERE device_name = test_name`；不要依赖 URL 变化、成功消息或 alert 来判断保存成功。

### 第 6 步：API 级监听（进阶诊断）

当 DB 直查确认数据未写入但页面无报错时，挂载 API 响应监听器确认后端实际返回：

```python
save_responses = []
def on_response(response):
    if "addDevice" in response.url or "addDeviceInfo" in response.url:
        try:
            status = response.status
            log(f"  保存API: {response.url.split('/')[-1]} → {status}")
            # status=200 但 DB 无数据 → IP/MAC 唯一约束冲突或后端事务回滚
        except:
            pass
page.on("response", on_response)

page.get_by_role("button", name="保存").click(force=True)
time.sleep(8)
# 检查 save_responses 判断 API 是否被调用
```

**典型模式：** API 返回 `200` 但 DB 无数据 → 通常是 **后端唯一约束冲突**（如设备IP与已有PV IP重复），API写入失败时事务回滚但前端不显示错误。**不可靠模式：** `check_page_errors` 可能漏报——后端返回 200 时页面无错误消息可供检测。

---

## 3. DB 验证最佳实践

### 3.1 三层断言金字塔

```
┌──────────────┐
│   UI断言      │ ← 页面元素真实可见、状态正确（输入框值、下拉文本、列表列内容）
├──────────────┤
│   DB断言      │ ← 数据真正写入、字段值正确（最可靠）
├──────────────┤
│   异步轮询    │ ← 发布等操作等待最终状态收敛（最多 30 秒）
└──────────────┘
```

### 3.2 DB 直查是最可靠的验证方式

保存/创建/编辑操作后，DB 直查是最可靠的判断方法——不依赖前端 UI 反馈。

```python
def db_check_record_exists(conn, table, key_field, key_value):
    """检查数据库记录是否存在"""
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {key_field} = %s", (key_value,))
    count = cur.fetchone()[0]
    return count > 0

def db_check_field_value(conn, table, key_field, key_value, check_field, expected_value):
    """检查数据库记录某个字段值是否正确"""
    cur = conn.cursor()
    cur.execute(f"SELECT {check_field} FROM {table} WHERE {key_field} = %s", (key_value,))
    row = cur.fetchone()
    if not row:
        return False, "记录不存在"
    return row[0] == expected_value, f"实际值={row[0]}, 期望值={expected_value}"
```

### 3.3 探针：先查 information_schema 确认字段名

**不要猜字段名。** 在写 DB 断言前先用探针查询确认表结构和字段名：

```sql
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
```

### 3.4 保存后的完整验证模式

每个保存操作后必须执行：

1. **UI 即时检查**：`check_page_errors()` 检测页面报错（1 step，含截图）
2. **UI 存在性检查**：导航到列表页搜索确认记录存在
3. **DB 直查**：查询数据库确认数据写入，字段值正确
4. **编辑后二次确认（★★★）**：重新进入编辑页验证 UI 渲染正确（避免 DB 有数据但 UI 不显示）

```python
# 完整模式
# Step 1: 检查页面报错
report.step("保存设备", screenshot=page)
has_err, err_txt = check_page_errors(page, report, "保存设备后检查",
                                      expected_url_change="/deviceList")
if has_err and err_txt and "NullPointerException" in err_txt:
    log(f"⚠️ 后端 NPE，但设备可能已创建", "⚠️")
    # 非关键错误不阻断，让后续断言判断

# Step 2: 搜索列表页确认存在
ensure_on_page(page, LIST_URL)
time.sleep(1)
page.get_by_placeholder("请输入设备名称").fill(DEVICE_NAME)
page.get_by_role("button", name="搜索").click()
time.sleep(2)
row_count = page.locator("tr").filter(has_text=DEVICE_NAME).count()
report.assertion("UI: 列表页存在设备记录", row_count > 0, f"行数={row_count}")

# Step 3: DB 直查
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT device_name FROM device_info WHERE device_name = %s", (DEVICE_NAME,))
db_row = cur.fetchone()
report.assertion("DB: 设备记录已写入", db_row is not None, f"device_name={DEVICE_NAME}")
cur.close()
conn.close()

# Step 4（可选）: 二次确认 - 进入编辑页验证 UI
page.get_by_role("button", name="编辑").first.click()
time.sleep(2)
edit_body = page.locator("body").inner_text()
report.assertion("UI确认: 编辑页含设备名称", DEVICE_NAME in edit_body, "")
```

### 3.5 数据清理策略

- **清理在脚本开头**（不在结尾）—— 确保幂等性，同时为后续脚本保留数据
- **按平台前缀精确匹配** —— `WHERE name LIKE 'iot_auto_test_%'`，不交叉污染
- **使用 `ON CONFLICT DO NOTHING`** 保证 INSERT 幂等性
- **消费型脚本**（依赖其他脚本数据）→ 开头做前置 DB 检查，不自动创建依赖数据

### 3.6 前置数据恢复

当 `check_prerequisites()` 失败时（依赖数据在 DB 中不存在）：

1. 确认缺失项（查看脚本输出的缺失 ID 列表）
2. 简单的引用数据（PV、标签、字典项）→ 直接 INSERT 最小化字段
3. 复杂依赖链（完整模型-设备-元件链）→ 应运行上游脚本生成，而非手动 DB INSERT

---

## 附录：故障信号 ID 映射表

| ID | 信号名称 | 来源 | 严重级别 |
|:---|:---|:---|:---:|
| S001 | 指针事件拦截 | `self_heal.py` | error |
| S002 | 严格模式违规 | `self_heal.py` | error |
| S003 | 超时（Timeout） | `self_heal.py` | error |
| S004 | 下拉选项无法选中 | `self_heal.py` | warning |
| S005 | el-autocomplete 静默失败 | `self_heal.py` | error |
| S006 | 保存后无数据写入 | `self_heal.py` | error |
| S007 | 保存后 URL 未变化 | `self_heal.py` | info |
| S008 | DB 唯一约束冲突 | `self_heal.py` | error |
| S009 | Tab 切换后保存无效 | `self_heal.py` | warning |
| S010 | 发布状态未变更 | `self_heal.py` | warning |
| S011 | NPE / NullPointerException | `self_heal.py` | error |
| S012 | el-select 无 role='option' | `self_heal.py` | error |
| S013 | 有头/无头差异 | `self_heal.py` | warning |
| S014 | 页面空白 | `self_heal.py` | error |
| S015 | el-autocomplete popper 未关闭 | `silent-save-debugging.md` | error |
| S016 | 搜索框 placeholder 超时（label 非 placeholder） | `self_heal.py` + `element_ui_patterns.md` | error |
| S017 | 子设备要求未满足 | `silent-save-debugging.md` | warning |
| S018 | check_page_errors 假阳性 | `check_page_errors-selector-false-positive.md` | warning |
| S019 | 输入框 disabled | 多文件综合 | warning |
| S020 | 按钮 disabled | `el-autocomplete-trap.md` | error |
| S021 | 表单验证错误漏检 | `el-autocomplete-trap.md` | error |
| S022 | 保存按钮不在 `<form>` 内 | `silent-save-debugging.md` | info |
| S023 | IP/MAC 格式验证失败 | `el-autocomplete-trap.md` | error |
| S024 | el-autocomplete 选项带版本后缀 | `el-autocomplete-trap.md` | info |
| S025 | 非关键场景阻断后续 | `check_page_errors-selector-false-positive.md` | warning |
| S026 | 保存后场景步数冗余 | `check_page_errors-selector-false-positive.md` | info |
| S027 | IP 冲突致静默保存失败（设备IP与PV IP重复） | 2026-06-09 调试 session | error |
| S028 | check_page_errors body 关键词误判（404/500/error 从URL误匹配） | 2026-06-09 调试 session | error |

---

> 本文档由 `web-auto-pipeline` SKILL.md 及关联 reference 文件自动提取生成。
> 故障诊断引擎位于 `scripts/self_heal.py`，支持 `--report`, `--log`, `--analyze-script`, `--list-signals` 模式。
> 生成日期：2026-06-08
