# el-autocomplete 静默失败陷阱（补充：2026-06-05 设备管理混合测试发现）

## 关键发现 1：`.el-autocomplete__popper li` 比 `[role='option']` 更可靠

在设备综合管理系统的设备创建页，el-autocomplete（选择设备模型）的选项有 `role='option'` 属性，但通过本次深度调试发现：

| 选择器 | 行为 |
|:---|:---|
| `[role='option']` | 部分 el-autocomplete 实例可用，但设备模型 el-autocomplete 的 `count() > 0` 后点击可能不生效 |
| `.el-autocomplete__popper li` | 更直接地定位渲染的 `<li>` 元素，配合 `force=True` 点击效果最可靠 |

**经验证的最佳方案：**
```python
inp = page.get_by_placeholder("请输入设备模型名称搜索")
inp.click(); inp.fill(model_name)
time.sleep(3)  # 等待 debounce + 后端返回
opt = page.locator(".el-autocomplete__popper li").filter(has_text=model_name).first
if opt.count() > 0:
    opt.click(force=True)  # force=True 绕过 Popper 可见性检查
    time.sleep(1)
else:
    # 降级: 用 role='option'
    opt2 = page.locator("[role='option']").filter(has_text=model_name).first
    if opt2.count() > 0: opt2.click(force=True); time.sleep(1)
```

## 关键发现 2：保存按钮不要在 el-autocomplete 未选中时用 force=True

当 el-autocomplete 选项未被正确触发 Vue `@select` 事件时，保存按钮可能处于 `is-disabled` 状态。用 `force=True` 点击会绕过禁用检查，导致看似点了保存但实际上后端不处理请求。

**正确做法：先用标准 `.click()` 触发表单验证，失败时检查 `.el-form-item__error` 确认是否是 autocomplete 未选中的问题。**

```python
# 第一步：用标准 click（不走 force）
page.get_by_role("button", name="保存").click()
time.sleep(2)

# 第二步：立即检查表单验证错误（el-form-item__error 出现快消失也快）
form_errs = []
for el in page.locator(".el-form-item__error").all():
    txt = el.text_content().strip()
    if txt: form_errs.append(txt)

if form_errs:
    log(f"表单验证错误: {'; '.join(form_errs)}", "❌")
    # 常见: '请输入正确的IP地址'、'请输入MAC地址'、'请选择设备模型'
else:
    time.sleep(3)  # 无错误才等后端处理
```

## 关键发现 3：IP/MAC 格式验证会导致保存失败

平台对 IP 地址和 MAC 地址有严格的格式校验：
- **IP 地址**：拒绝 `192.168.x.x` 格式，需使用 `10.x.x.x` 或 `172.x.x.x` 形式（内网地址）
- **MAC 地址**：需要连字符格式 `00-1A-2B-3C-4D-5E`，冒号格式 `00:1A:2B:3C:4D:5E` 可能被拒

如果 IP/MAC 格式不正确，表单验证错误 `.el-form-item__error` 会短暂出现后消失。**必须立即检查**（不延迟），否则会漏报。

## 关键发现 4：el-autocomplete 选项可能带版本后缀

搜索"自动化测试-设备模型"返回的选项文本可能是"自动化测试-设备模型 **v1**"。`has_text` 子串匹配（不要求全等）可以匹配到：

```python
# ✅ 子串匹配
opt = page.locator(".el-autocomplete__popper li").filter(has_text="自动化测试-设备模型").first
# 匹配 "自动化测试-设备模型 v1" ✅

# ❌ 如果误用 get_by_text 全等匹配
# page.locator(".el-autocomplete__popper li").get_by_text("自动化测试-设备模型")
# 不匹配 "自动化测试-设备模型 v1" ❌
```

## 关键发现 5：check_page_errors 初始 2 秒延迟导致表单验证错误漏检

**这是 2026-06-05 调试中最重要的修复。**

原 `check_page_errors` 函数在轮询循环开头有 `time.sleep(2)`，导致第一次检查发生在 save 操作 2 秒后。但 `.el-form-item__error` 表单验证错误可能出现时间极短（几百毫秒后就消失），被 2 秒初始延迟错过。

**修复：改为立即检查，仅在无错误时才 sleep。**

```python
def check_page_errors(page, report=None, step_name="检查"):
    errors, texts = [], []
    for rnd in range(4):
        round_errs = []
        # 检查各种错误
        for sel in [...]:
            ...
        if round_errs:
            errors.extend(round_errs)
            break
        time.sleep(2)  # 只在没发现错误时才等 ← 关键改动
```
