# Web 自动化调试技术

## 静默保存失败诊断

> 来源：silent-save-debugging.md

# 静默保存失败诊断：组件交互陷阱

## 问题现象
保存按钮 `click()` 后：无网络请求、无错误提示、无表单验证错误、DB 无数据。

## 根因排查清单（按频率排序）

### 1. el-autocomplete popper 未关闭（最常见）
点击 el-autocomplete 的下拉选项后，popper 元素可能停留在 DOM 中（display:none 或透明），其 transparent overlay 拦截后续所有点击事件。

**诊断**：`page.evaluate("document.querySelectorAll('.el-autocomplete__popper:not([style*=\\"display: none\\"])').length")` > 0

**修复**：点击任何一个 el-autocomplete 元素后，调用 `page.keyboard.press("Escape")` 确保 popper 关闭。

### 2. 设备模型有子设备要求
选择的设备模型包含 sub-device 结构，必须在元件 Tab 中为每个子设备关联具体的元件实例。

**诊断**：保存后检查 `.el-message--warning` 内容（如"请为所有子设备选择具体的元件"）

**修复**：改用不包含子设备要求的模型；或在保存前切换到元件 Tab，搜索并关联已有元件。

### 3. 保存按钮不在 `<form>` 内
Vue/Element Plus 的常见设计模式：保存按钮在页面 header 区域的独立 `<div>` 中，不在表单 `<form>` 内。
- `btn.form` → null（不在表单内）
- `document.querySelector('form')` → 存在但不包含保存按钮
- `btn.dispatchEvent(new MouseEvent('click', {bubbles:true}))` → Vue 事件系统通过事件委托捕获

**修复**：使用 `page.locator("button").filter(has_text="保存").first.click()` 原生 Playwright 点击（无需 force=True）。此点击会生成真实的浏览器事件 → 冒泡 → Vue 事件委托捕获。

### 4. 正确保存后无任何反馈（平台设计）
部分平台的创建表单保存后：不跳转、不弹出成功消息、停留在当前创建页。

**诊断**：唯一可靠的验证方式是 **DB 直查**。`page.on("request")` 也可能捕获不到（XHR 已发出但页面无反馈）。

**修复**：脚本中始终包含 DB 断言 `SELECT ... WHERE device_name = test_name`；不要依赖 URL 变化、成功消息、或者 alert 来判断保存成功。

## 调试工具函数
```python
def diagnose_save_button(page):
    """保存按钮诊断：返回按钮状态和页面遮挡情况"""
    return page.evaluate("""() => {
        var btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('保存'));
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
            formErrors: Array.from(document.querySelectorAll('.el-form-item__error')).map(e => e.textContent.trim())
        };
    }""")

def check_network_request(page):
    """检查点击保存后是否有网络请求发出"""
    before = page.evaluate("performance.getEntriesByType('resource').length")
    # ... click save ...
    page.wait_for_timeout(3000)
    after = page.evaluate("performance.getEntriesByType('resource').length")
    new_requests = after - before
    return new_requests > 0
```

---

## 操作后错误检测

> 来源：post-action-error-detection.md

# 关键操作后错误检测与场景依赖中断

## 背景

2026-06-03 调试 session 中，用户在手工操作时观察到网页顶部弹出后端 NPE 红色报错横幅。自动化脚本在同样的保存操作后未捕获该报错，导致：
1. 用户无法在 HTML 报告中第一时间定位是平台 BUG 还是脚本问题
2. 用户质疑"为什么有头模式看到了报错但脚本没报错"
3. 后续场景在前置场景实际已失败的情况下继续执行，出现 "browser has been closed" 等二次错误

本文档记录了问题根因、修复方案和可复用的 `check_page_errors` 标准实现。

## 观察到的后端错误

页面内嵌红色横幅（非标准 el-message）：
```
Cannot invoke "com.jws.iot.business.service.device.model.thingmodelversion.ThingModelVersionPageVo.getId()" because "thingModelVersion" is null
```

这是 Java NullPointerException 在前端的呈现。特征是 body 文本中包含 `Cannot invoke`、`because ... is null`、`thingModelVersion` 等关键词。此类错误只能用 body 文本关键词扫描捕获——CSS 选择器无法覆盖。

## 错误检测覆盖矩阵

| 错误形态 | 选择器/检测方式 | 备注 |
|:---|:---|:---|
| Element UI Message | `.el-message--error`, `.el-message--warning` | 标准组件 |
| Element Plus Notification | `.el-notification__content`, `.el-notification__title` | 标准组件 |
| Ant Design Message | `.ant-message-error`, `.ant-message-warning` | Vben Admin |
| Ant Design Notification | `.ant-notification-notice-description` | Vben Admin |
| 表单验证错误 | `.el-form-item__error`, `.ant-form-item-explain-error` | 必填/格式错误 |
| Alert/Result 组件 | `.el-alert--error`, `.ant-alert-error` | 内嵌提示 |
| **页面内嵌红色横幅（非标准）** | **body 文本关键词（Cannot invoke/is null/NullPointerException 等）** | **覆盖后台 NPE、自定义报错** |
| URL 未变化 | `urlparse(page.url).path` 与期望路径对比 | 保存失败的间接信号 |

## check_page_errors 标准实现（轮询版）

```python
def check_page_errors(page, report=None, step_name="操作后错误检查", expected_url_change=None):
    """
    检查页面是否有错误提示。发现任何错误则立即截图并记录到报告。
    轮询检测：每 2 秒检查一次，共 4 次（最长 8 秒），覆盖异步延迟后端的错误。
    """
    if report:
        report.step(f"{step_name} (即时截图)", screenshot=page)

    errors = []
    error_texts = []
    has_error = False

    for check_round in range(4):
        time.sleep(2)
        round_errors = []

        # 1. Message 组件（仅 error/warning 级别，排除 .el-message--success 假阳性）
        for sel in [".el-message--error", ".el-message--warning",
                    ".ant-message-error", ".ant-message-warning"]:
            for msg in page.locator(sel).all():
                txt = msg.text_content().strip()
                if txt and len(txt) > 3 and txt not in error_texts:
                    round_errors.append(f"[Message]{txt}")
                    error_texts.append(txt)

        # 2. Notification 组件
        for sel in [".el-notification__content", ".el-notification__title",
                    ".ant-notification-notice-description"]:
            for n in page.locator(sel).all():
                txt = n.text_content().strip()
                if txt and len(txt) > 3 and txt not in error_texts:
                    round_errors.append(f"[Notification]{txt}")
                    error_texts.append(txt)

        # 3. 表单验证错误
        for fe in page.locator(".el-form-item__error, .ant-form-item-explain-error").all():
            txt = fe.text_content().strip()
            if txt and txt not in error_texts:
                round_errors.append(f"[Form]{txt}")
                error_texts.append(txt)

        # 4. Alert / Result 组件
        for sel in [".el-alert--error", ".el-alert--warning", ".el-result__error",
                    ".ant-alert-error", ".ant-alert-warning"]:
            for a in page.locator(sel).all():
                txt = a.text_content().strip()
                if txt and len(txt) > 3 and txt not in error_texts:
                    round_errors.append(f"[Alert]{txt}")
                    error_texts.append(txt)

        # 5. body 关键词打底（捕获非标准组件错误）
        body_text = page.locator("body").inner_text()
        backend_keywords = [
            "Cannot invoke", "NullPointerException", "exception",
            "error", "失败", "系统繁忙", "请稍后重试",
            "服务端异常", "500", "404", "操作失败", "保存失败",
            "创建失败", "is null", "cannot be null"
        ]
        for kw in backend_keywords:
            if kw.lower() in body_text.lower():
                if not any(kw.lower() in e.lower() for e in error_texts):
                    round_errors.append(f"[Body]{kw}")
                    error_texts.append(kw)

        # 6. URL 变化检测
        if expected_url_change:
            from urllib.parse import urlparse
            cur_path = urlparse(page.url).path
            if expected_url_change not in cur_path:
                if not any("URL未变" in e for e in error_texts):
                    round_errors.append(f"[URL]保存后未跳转: {cur_path}")
                    error_texts.append(f"URL未变: {cur_path}")

        if round_errors:
            errors.extend(round_errors)
            has_error = True
            break

    if has_error:
        full_error = "; ".join(errors)
        if report:
            report.step(f"{step_name} ❌ {full_error[:120]}", screenshot=page)
            report.assertion("页面无报错", False, full_error[:400])
    else:
        if report:
            report.step(step_name, screenshot=page)
            report.assertion("页面无报错", True, "")

    return has_error, "; ".join(error_texts)
```

## 场景依赖中断

### 问题

设备管理 9 场景有严格依赖链（PV → 元件模型 → 发布模型 → 元件 → 发布元件 → 设备模型 → 发布设备模型 → 设备 → 发布设备）。场景 2 失败后，场景 3-9 不可能成功，但旧脚本的 `should_run` 只判断 `n >= start_scene`，导致后续场景继续执行并报"browser has been closed"。

### 修复

`should_run` 改为遍历 `report.scenes`，只要任何已执行场景的 `status == "failed"`，就跳过后续场景：

```python
def should_run(n):
    if n < start_scene:
        return False
    for scene in report.scenes:
        if scene.get("status") == "failed":
            return False
    return True
```

使用 `report.scene_skip(name, reason)` 在报告中标记跳过的场景。

## 检查清单（编写新场景时）

- [ ] 每个 `click(保存)` / `click(发布)` / `click(确定)` / `click(提交)` 后是否跟随了 `check_page_errors` 调用
- [ ] `check_page_errors` 是否传入了 `expected_url_change` 参数（保存后应跳转的路径）
- [ ] 检测到错误后是否立即 `report.scene_end(False)` 并 `return`
- [ ] `should_run` 是否通过 `report.scenes` 检索前置失败状态，而不是依赖局部变量


---

## 附录：check_page_errors 选择器假阳性（来源：`check_page_errors-selector-false-positive.md`）

# check_page_errors 选择器假阳性与 step 整合
    
## 问题1：成功消息被误判为错误

### 症状
场景5（发布元件）执行成功后，`check_page_errors` 捕获了"发布成功"消息，将其标记为错误，导致场景5失败、场景6-9被跳过。

### 根因
`check_page_errors` 的 selector 列表中包含 `.el-message` 和 `.ant-message`（不带 `--error`/`--warning` 后缀），这些选择器匹配**所有消息类型**：

| 选择器 | 匹配范围 | 问题 |
|:---|:---|:---|
| `.el-message--error` | 仅错误消息 | ✅ 正确 |
| `.el-message--warning` | 仅警告消息 | ✅ 正确 |
| `.el-message` | 所有消息（含成功/信息） | ❌ 捕获"发布成功" |
| `.ant-message` | 同上 | ❌ 同理 |

同理，`.el-notification__title` 可能包含"操作成功"等成功标题。

### 修复
移除通用选择器，只保留 error/warning 级别的具体选择器。同时移除 `check_page_errors` 内部的 `report.step()` 调用，只做断言（step 由调用方管理）：

```python
# ❌ 过宽（已移除）
".el-message", ".ant-message", ".el-notification__title"
# ❌ 函数内 report.step() 已移除（只保留 report.assertion()）

# ✅ 正确（保留）
".el-message--error", ".el-message--warning",
".ant-message-error", ".ant-message-warning",
".el-notification__content",
".ant-notification-notice-description", ".ant-notification-notice-message"
# ✅ step 由调用方统一管理（report.step(..., screenshot=page) 在 check_page_errors 之前）

## 问题：非关键场景失败阻断后续所有场景

### 症状
场景4（新增元件+关联PV）中PV关联失败 → 脚本立即 `return report` → 场景5-9全部跳过。

### 根因
`should_run()` 函数一旦检测到任何场景失败，就跳过所有后续场景。但PV关联是可选操作，元件创建本身成功，后续场景（发布元件、创建设备模型等）仍可执行。

### 修复方案

**1. 引入 NON_BLOCKING 概念**

```python
def should_run(n):
    if n < start_scene:
        return False
    NON_BLOCKING = {4, 5}  # 非阻塞场景
    for scene in report.scenes:
        if scene.get("status") == "failed":
            import re
            m = re.search(r'\d+', str(scene.get("id", "")))
            scene_num = int(m.group()) if m else 0
            if scene_num not in NON_BLOCKING:
                return False
    return True
```

**2. 保存后报错不立即 `return report`**

```python
has_err, err_txt = check_page_errors(page, report, "保存元件后检查")
if has_err:
    log(f"⚠️ 保存有报错（可能是PV关联问题，继续执行）: {err_txt[:120]}")
    # 不 return — 元件本身可能已创建成功，让后续断言验证
```

### 依赖关系决策树

| 场景 | 关键数据产出 | 后续依赖 | 是否阻断 |
|:---|:---|:---|:---:|
| 场景1 PV创建 | PV记录 | 场景4(元件PV关联) | ✅ 阻断 |
| 场景2 元件模型 | 元件模型(draft) | 场景3(发布), 场景4(元件创建) | ✅ 阻断 |
| 场景3 发布元件模型 | 元件模型(release) | 场景4(创建元件), 场景6(设备模型) | ✅ 阻断 |
| 场景4 元件+PV | 元件(draft) | 场景5(发布), 场景8(设备关联) | ❌ 不阻断 |
| 场景5 发布元件 | 元件(release) | 场景8(关联发布过的元件) | ❌ 不阻断 |
| 场景6 设备模型 | 设备模型(draft) | 场景7(发布) | ✅ 阻断 |
| 场景7 发布设备模型 | 设备模型(release) | 场景8(创建设备) | ✅ 阻断 |
| 场景8 设备+元件 | 设备(draft) | 场景9(发布) | ✅ 阻断 |
| 场景9 发布设备 | 设备(release) | — | ✅ 阻断（最后一个场景） |

## 问题3：Step 整合 — 保存/发布后冗余的 3 个 step

### 症状
每个保存/发布操作在报告中有 3 个冗余 step：
1. `"保存后检查 (即时截图)"` — check_page_errors 内部
2. `"保存后检查"` — check_page_errors 内部（轮询后）
3. `"保存xx"` — 调用方（重复截图）

### 根因
`check_page_errors` 内部包含了 `report.step()` 调用（带截图），调用方又追加了一个 `report.step()`，导致同一个操作产生 3 个 step。

### 修复
1. 从 `check_page_errors` 中移除所有 `report.step()` 调用，只保留 `report.assertion()`
2. 调用方在调用 `check_page_errors` 之前记录 **1 个** `report.step(..., screenshot=page)`
3. 移除调用方原有的冗余 `report.step()`（在 check_page_errors 之后的那个）

```python
# ✅ 新方案（1 step）
report.step("保存元件", screenshot=page)          # 1 step（调用方统一管理）
has_err, err_txt = check_page_errors(page, report, "保存元件后检查")
if has_err:
    log(f"⚠️ 保存报错: {err_txt[:120]}")
    # 非关键失败不 return，让后续断言验证
```

**注意：`step()` 必须在 `assertion()` 之前调用（断言绑定到最近记录的步骤序号）。** 将 step 移到 check_page_errors 之前既满足了此约束，也简化了报告。
