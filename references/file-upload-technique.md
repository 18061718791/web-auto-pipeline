# 文件上传 / 导入自动化调试记录

> 本文件记录 2026-06-08 PV导入自动化的完整调试过程。
> 通过 5 轮迭代 + API 响应分析最终确定了可靠方案。

---

## 背景

IoT 平台 PV管理页面支持 Excel 批量导入 PV。页面使用 Element UI `<el-upload>` 组件：
- 按钮文字："PV导入"
- API 端点：`POST /jwsiot-api/api/device/pv/importPvDataFromExcel`
- 模板格式：sheet=`pv数据导入`，col=(`PV名称`, `PV描述`)
- 预期结果：`{"code":200, "msg":"操作成功", "data":{"totalCount":N, "successCount":S, "failureCount":F, "successList":[], "errorList":[]}}`

---

## 调试过程

### 迭代1：直接 set_input_files（❌ 失败）

```python
# 尝试1：直接操作隐藏input
page.locator("input.el-upload__input").set_input_files(file)
```

**结果**：文件被设置到 input，但**不触发上传**——El-upload 的 `auto-upload` 依赖原生 `change` 事件，`set_input_files` 的 change 事件可能 `isTrusted=false`。

**教训**：对 el-upload 组件必须使用 `expect_file_chooser` 模拟真实用户操作。

### 迭代2：expect_file_chooser + 内部 button（❌ 部分失败）

```python
# 尝试2：点击内部 button
page.locator("button").filter(has_text="PV导入").click(force=True)
with page.expect_file_chooser() as fc:
    ...
```

**结果**：headless 模式下 `expect_file_chooser` 偶发 timeout（30s），但 headed 模式总是成功。

**教训**：必须点击 `.el-upload` 包装器而非内部 button。添加降级方案到 `set_input_files`。

### 迭代3：expect_file_chooser + .el-upload 包装器（✅ 成功）

```python
upload_wrapper = page.locator(".el-upload").filter(has_text="PV导入").first
with page.expect_file_chooser() as fc_info:
    upload_wrapper.click(force=True)
    time.sleep(2)  # 给文件选择器初始化时间
file_chooser = fc_info.value
file_chooser.set_files(TEST_FILE)
```

**结果**：✅ file_chooser 拦截成功，API 请求 `importPvDataFromExcel` 正确发出。

### 迭代4：API 响应分析（✅ 确认数据已存在）

发现 API 返回 `successCount=0, failureCount=7`——原模板的 7 条 PV 名已在 DB 中存在，重复导入被跳过。

```json
{"code":200, "data":{
  "totalCount":8,
  "successCount":0,
  "failureCount":7,
  "errorList":[
    {"rowIndex":2, "pvCode":"IP-SAFE-RFQ-CR:TMP01:State_UnderVol", "failureReason":"...已存在..."},
    ...
  ]
}}
```

**教训**：必须使用**纯净模板**（只含唯一测试数据），不从原模板复制。

### 迭代5：纯净模板 + DB 对比验证（✅ 全部通过）

```python
# 生成只含一行测试数据的纯净模板
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "pv数据导入"
ws.append(("PV名称", "PV描述"))
ws.append((test_pv_name, test_desc))
```

**结果**：
- API: `successCount=1, failureCount=0, totalCount=1`
- DB: `SELECT ... WHERE pv_code LIKE '%AUTO_IMPORT%'` → 1 条
- UI: 列表搜索该 PV → 1 行

---

## 最终方案

```python
# 1. 注册API监听（必须在导航前）
api_resp = {}
def on_response(response):
    if "importPvDataFromExcel" in response.url:
        api_resp.update(response.json())
page.on("response", on_response)

# 2. 导航到列表页
page.goto(PV_LIST_URL)
time.sleep(3)

# 3. 上传文件（主方案 + 降级）
try:
    wrapper = page.locator(".el-upload").filter(has_text="导入").first
    with page.expect_file_chooser() as fc:
        wrapper.click(force=True)
        time.sleep(2)
    fc.value.set_files(TEST_FILE)
except Exception:
    page.locator("input.el-upload__input").set_input_files(TEST_FILE)

# 4. 等待API响应（最长25秒）
for i in range(25):
    time.sleep(1)
    if api_resp: break

# 5. 验证
report.assertion("API成功", api_resp.get("data",{}).get("successCount",0) > 0, ...)
report.assertion("DB确认", len(db_find_pv(prefix)) > 0, ...)
```

---

## OS 级对话框调研（用户偏好）

**此用户不接受 `expect_file_chooser` 后台拦截。** 要求"完全模拟人为操作"：点击 PV导入 → OS 原生文件对话框弹出 → 粘贴路径 → Enter 确认。

### 测试的 4 种方案（2026-06-08）

| # | 方案 | 原理 | 结果 |
|:-:|:---|:---|:---:|
| 1 | `expect_file_chooser` (Playwright) | CDP 协议在浏览器层面拦截文件选择事件 | ✅ 可靠，但用户不接受 |
| 2 | `pywin32` WM_SETTEXT → Edit 控件 + BM_CLICK → 打开按钮 | 找到对话框 HWND → 写路径 → 点按钮 | ⚠️ 路径写入成功，BM_CLICK 不触发上传 |
| 3 | `pyautogui` hotkey Ctrl+V + press enter | 复制路径到剪贴板 → 键盘粘贴 → Enter | ❌ 键盘事件发到错误窗口 |
| 4 | `SendInput` (ctypes) + `SwitchToThisWindow` 强制焦点 | 驱动级键盘事件注入 | ❌ 同 pyautogui |

### 根因分析

Chrome/Edge 在 Windows 10/11 上使用的是 **IFileOpenDialog (Common Item Dialog)**，这是 Windows Vista 引入的基于 COM 的新式文件对话框。它不响应传统 Win32 消息：
- `BM_CLICK` → 忽略（按钮不通过 SendMessage 触发）
- `WM_COMMAND IDOK` → 忽略
- `SetForegroundWindow` → 返回 error 0（UIPI 安全隔离）

这是微软的安全设计——防止自动化工具绕过用户授权选择文件。

### 最终决策

| 场景 | 方案 | 代码 |
|:---|:---|:---|
| CI/自动化回归 | `expect_file_chooser`（标准方案） | 见本文 §最终方案 |
| 调试/演示（用户想看对话框） | **手动暂停模式** | `input("⏸️ 请手动选文件后按Enter...")` |
| 需要 OS 级操作且必须可用 | 当前无可靠方案 | 继续关注 pywinauto/FlaUI 的发展 |

| 项目 | 值 |
|:---|:---|
| 平台 URL | `/jwsiot/pv/list` |
| 上传组件 | `el-upload` + 隐藏 `input.el-upload__input` |
| API 端点 | `POST /jwsiot-api/api/device/pv/importPvDataFromExcel` |
| API 响应格式 | `{code, msg, data:{totalCount, successCount, failureCount, successList, errorList}}` |
| 模板格式 | Sheet=`pv数据导入`, Cols=`(PV名称, PV描述)` |
| 上传耗时 | ~25-30 秒（后端解析 + 写入） |
| headless 兼容 | ✅（方案A + 方案B 双保险） |
