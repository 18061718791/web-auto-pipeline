# Page Manifest 系统

## 格式说明

> 以下内容合并自 manifest-to-script-pipeline.md + page-manifest-format.md（已去重）

### 定位

这是从 AI 探索到确定性脚本执行的中间桥梁：

```
Hermes AI探索 (Hermes Browser) → Page Manifest JSON → generate_script.py → Playwright脚本 → 执行+报告
```

平台探索器除了生成 HTML 报告外，还应生成一份结构化 JSON 文件（Page Manifest），
这份清单可以直接被自动化脚本生成器消费，打通"探索→开发"的流水线。

### Manifest 格式

一个 Manifest JSON 包含平台信息、数据库配置、以及按场景编排的页面描述：

```json
{
  "platform": "设备综合管理系统",
  "base_url": "http://...",
  "db_config": {"host": "...", "port": 5432, ...},
  "scenes": [
    {
      "id": 1,
      "name": "创建设备",
      "url": "/controller/cDeviceEdit?type=create",
      "list_url": "/controller/cDeviceList",
      "fields": [
        {"placeholder": "请输入设备名称", "type": "input", "required": true, "data_key": "DEVICE_NAME"},
        {"placeholder": "请输入设备模型名称搜索", "type": "el-autocomplete", "required": true, "data_key": "MODEL_NAME"}
      ],
      "tabs": [{"name": "元件", "fields": [...]}],
      "buttons": ["保存"],
      "assert_db": "device",
      "db_key_field": "device_name",
      "row_action": true
    }
  ]
}
```

### 文件位置

探索输出目录下：
```
{平台名称}/平台探索/{时间戳}/
├── report.html          # 给人看的HTML报告
├── page_manifest.json   # 给机器用的结构化清单 ← 新增
└── screenshots/
```

### 组件类型映射

| Manifest type | 生成的 Playwright 交互代码 |
|:---|:---|
| `input` | `page.get_by_placeholder("...").fill(value) + time.sleep(0.3)` |
| `el-select` | `click(force=True) → sleep 1.5 → .el-select-dropdown__item → click(force=True) → Enter` |
| `el-autocomplete` | `click() → fill(value) → sleep 2.5 → [role=option].dispatch_event('click')` |
| `el-cascader` | `click(force=True) → evaluate 点 .el-cascader-node .el-checkbox → Escape` |

### 脚本生成规则

1. **每个场景一个函数** — `scene_N(page, report, conn)`，返回 `scene_ok` 布尔值
2. **表单填充顺序** — 按 Manifest fields 数组顺序，input 之间插入 `time.sleep(0.3)` 让 Vue 处理
3. **保存后检查** — 4轮轮询检测 `el-message--error` 和 `el-form-item__error`（表单验证错误）
4. **行内操作** — `row_action: true` 的场景走"搜索→定位行→点行内按钮→轮询等待"逻辑
5. **DB 断言** — 每个场景保存后查 `SELECT * FROM {assert_db} WHERE {db_key_field} = %s`
6. **报告集成** — 调用 `TestReport.generate_html()` 输出 HTML 报告

### 已验证的脚本结构

```
#!/usr/bin/env python3
import ...
from config import BASE_URL, get_db_connection
from report_helper import TestReport

# 测试数据常量
DATA_PREFIX = 'iot_auto_test'
DEVICE_NAME = f'{DATA_PREFIX}-设备-{RUN_TS}'

# 辅助函数: ensure_on_page, check_errors, do_db_assert

# 场景函数
def scene_1(page, report, conn): ...
def scene_2(page, report, conn): ...

# 清理函数
def cleanup_test_data(): ...

# 主函数 (argparse: --headless, --start-scene)
def main(): ...
```

### 生成器实现

参考实现：[D:\AI\web-autotest-skill\scripts\generate_script.py](file:///D:/AI/web-autotest-skill/scripts/generate_script.py)

```bash
python scripts/generate_script.py --manifest manifest.json --output output/
```

### 完整格式规范

```json
{
  "platform": "平台中文名称",
  "base_url": "http://...",
  "explored_at": "2026-06-02T18:00:00",
  "db": {
    "type": "postgresql",
    "host": "",
    "port": 5432,
    "dbname": "",
    "user": "",
    "password": ""
  },
  "pages": [
    {
      "name": "页面业务名称（如'PV管理-创建页'）",
      "tags": ["crud", "device-management", "pv"],
      "url": "/路由路径",
      "list_url": "/列表页路径（创建/编辑页专用）",
      "is_list_page": false,
      "auth_required": false,
      "fields": [
        {
          "placeholder": "请输入XXX",
          "aria_label": "* XXX",
          "type": "el-input | el-select | el-autocomplete | el-cascader | el-textarea | el-switch",
          "required": true,
          "data_key": "字段名（如果已知）",
          "options": ["选项1", "选项2"],
          "popper": ".el-autocomplete__popper（el-autocomplete专用）",
          "option_selector": "li（el-autocomplete）或 [role='option']（el-select）",
          "debounce_seconds": 2,
          "known_trap": "该字段的已知陷阱描述"
        }
      ],
      "tabs": [
        {
          "name": "Tab名称（如'物模型'）",
          "tab_selector": "tab role name",
          "condition": "前置条件（如'需先选择模型'）",
          "fields": []
        }
      ],
      "tables": [
        {
          "name": "表格名称",
          "columns": ["列1", "列2"],
          "empty_hint": "暂无数据时的提示文本"
        }
      ],
      "buttons": ["保存", "提交", "确定"],
      "dialogs": [
        {
          "trigger": "触发操作（如'点击行内发布'）",
          "title": "确认发布设备 'XXX' 吗？",
          "confirm_text": "确定",
          "cancel_text": "取消"
        }
      ],
      "assert_db": "数据库表名",
      "db_key_field": "用于删除的字段名",
      "known_bugs": [
        "BUG1描述",
        "BUG2描述"
      ],
      "post_save_behavior": "stay | redirect_to_list",
      "special_notes": "任何额外的注意事项"
    }
  ]
}
```

### 字段详解

#### 顶级字段

| 字段 | 必填 | 说明 |
|:---|:---:|:---|
| `platform` | ✅ | 平台中文名，用于报告标题 |
| `base_url` | ✅ | 平台基础 URL，脚本中用于拼接 `page.goto(base_url + page.url)` |
| `explored_at` | ✅ | 探索时间戳，用于判断是否需要重新探索 |
| `db` | ❌ | 数据库连接信息，可选（在自动化脚本中通常硬编码） |

#### pages[].fields[] 字段

| 字段 | 必填 | 说明 | 脚本映射 |
|:---|:---:|:---|:---|
| `placeholder` | ✅ | input 的 placeholder 属性 | `page.get_by_placeholder("...")` |
| `aria_label` | ❌ | input 的 aria-label 属性（备选定位） | `page.get_by_role("textbox", name="...")` |
| `type` | ✅ | 组件类型 | 决定选择器策略（见下方） |
| `required` | ✅ | 是否必填 | 决定是否写入脚本 |
| `data_key` | ❌ | 后端字段名（如果已知） | assertion 和 DB 查询用 |
| `options` | ❌ | el-select 的可选项 | 脚本硬编码测试值 |
| `popper` | ❌ | el-autocomplete 的下拉容器选择器 | `.el-autocomplete__popper`（与 el-select 的 `.el-select-dropdown` 不同） |
| `option_selector` | ❌ | 下拉选项元素选择器 | `li`（el-autocomplete）或 `[role='option']`（el-select） |
| `debounce_seconds` | ❌ | el-autocomplete 搜索后的等待时间 | `time.sleep(N)` |
| `known_trap` | ❌ | 该字段的已知陷阱描述 | 脚本中加注释提醒 |

### 组件类型到选择器的映射

```python
TYPE_MAP = {
    "el-input": {
        "fill": 'page.get_by_placeholder("{placeholder}").fill("{value}")',
        "read": 'page.get_by_placeholder("{placeholder}").input_value()',
    },
    "el-select": {
        "fill": '''page.get_by_placeholder("{placeholder}").click()
page.get_by_placeholder("{placeholder}").fill("{value}")
time.sleep(1.5)
opt = page.locator("[role='option']").filter(has_text="{value}").first
if opt.count() > 0: opt.click()''',
    },
    "el-autocomplete": {
        "fill": '''page.get_by_placeholder("{placeholder}").click()
page.get_by_placeholder("{placeholder}").fill("{value}")
time.sleep({debounce})
opt = page.locator("{popper} {option_selector}").filter(has_text="{value_prefix}").first
for _ in range(3):
    if opt.count() > 0: break
    time.sleep(1.5)
assert opt.count() > 0, "下拉选项未出现"
opt.first.click()
time.sleep(1)''',
    },
    "el-cascader": {
        "fill": '''page.locator(".el-cascader").first.click()
page.wait_for_timeout(1000)
opt = page.locator(f".el-cascader-node:has-text('{value}')").first
if opt.count() > 0: opt.click()''',
    },
}
```

### 已知限制

| 限制 | 说明 |
|:---|:---|
| 不支持嵌套对话框 | dialog 内 dialog 的选择器需手动补充 |
| el-transfer 穿梭框 | 需要勾选框状态管理，未自动生成 |
| 文件上传 | input[type=file] 需手动处理 |
| el-radio-group | 当前按 input 类型处理 |

### 组件交互速查

| 组件 | 输入方式 | 等待 | 下拉选项定位 | 选择方式 |
|:---|:---|:---:|:---|:---:|
| input | `.fill(v)` | 0 | — | — |
| select(local) | `.fill(v)` → 键盘选择 | 2s | 不可见时用键盘ArrowDown+Enter | ⚡ 键盘比点击可靠 |
| autocomplete(remote) | `.fill(v)` → 点选 | 2-2.5s(debounce) | `.el-autocomplete__popper li` | 点击li触发select事件 |
| cascader | `.click()` → 点选 | 1s(面板出现) | `.el-cascader-node` | 点击节点 |
| switch | `.click()` | 0 | — | — |
| textarea | `.fill(v)` | 0 | — | — |

#### ⚠️ 关键探索陷阱：placeholder 不等于 aria-label

浏览器的 accessibility tree（snapshot）显示的 `textbox "* 标签名称"` 是 **form-item 的 label 文本**，不是 input 的 **HTML placeholder 属性**。

实际 Playwright 脚本需要的 `page.get_by_placeholder("请输入标签名称")` 需要查看真实的 DOM 属性：

```javascript
// 在 browser_console 中确认
document.querySelector('input').placeholder                  // "请输入标签名称"
document.querySelector('input').getAttribute('aria-label')   // 可能为 null
```

**规则：** 不要用 snapshot 显示的 textbox 名称作为 placeholder。必须用 `browser_console` 读取 `input.placeholder` 确认真实值。

---

## JSON Schema

> 来源：page-manifest-schema.md

# Page Manifest — 平台页面结构化描述规范

## 概述

Page Manifest 是"探索→开发"流水线的核心契约。一次平台探索的产出是一组 Manifest JSON 文件，
脚本骨架生成器直接读取 Manifest 生成 Playwright 代码。

## 文件结构

每个页面一个 JSON 文件，放在 `manifests/` 目录下。

```json
{
  "page_id": "snake_case_唯一标识",
  "title": "页面中文名",
  "group": "模块分组（如：装置管理/SN管理）",
  "url": "/路由路径",
  "base_url_ref": "BASE_URL（默认取脚本中的BASE_URL变量）",
  "fields": [ ... ],
  "tabs": [ ... ],
  "buttons": [ ... ],
  "dialogs": [ ... ],
  "assertions": { ... },
  "post_save": "stay | redirect_to_list | redirect_to_detail",
  "known_bugs": [ ... ]
}
```

## 字段定义

### 基础字段

| 属性 | 类型 | 必需 | 说明 |
|:---|:---|:---:|:---|
| `page_id` | string | ✅ | 唯一标识，用作文件名和函数名 |
| `title` | string | ✅ | 中文名称 |
| `group` | string | | 模块分组 |
| `url` | string | ✅ | 路由路径（不含BASE_URL） |
| `base_url_ref` | string | | 变量名，默认 `BASE_URL` |
| `post_save` | string | | 保存后行为：`stay`(留在当前页)，`redirect_to_list`(自动跳转列表)，`redirect_to_detail`(跳转详情) |

### fields[].component 类型系统

| 组件类型 | 标识 | Playwright 策略 | 额外属性 |
|:---|:---|:---|:---|
| 输入框 | `input` | `page.get_by_placeholder("...").fill(v)` | 无 |
| 下拉搜索(本地) | `select` | fill → 等2s → `[role='option']` 点选 | `option_selector`: 默认 `[role='option']` |
| 下拉搜索(远程) | `autocomplete` | fill → 等debounce → `.el-autocomplete__popper li` 点选 | `popper`, `option_selector`, `debounce_seconds` |
| 级联选择 | `cascader` | 点击 → 等面板出现 → 点选节点 | `panel_selector` |
| 开关 | `switch` | `.el-switch` click | 无 |
| 富文本 | `textarea` | `fill()` | 无 |
| 标签选择 | `tag` | 点击标签 | 无 |
| 按钮 | `button` | 仅在fields内用，普通按钮放 buttons[] | 无 |

**所有下拉组件通用属性：**

| 属性 | 类型 | 说明 |
|:---|:---|:---|
| `popper` | string | 下拉容器CSS选择器 |
| `option_selector` | string | 选项元素选择器（默认 `[role='option']`） |
| `debounce_seconds` | number | 输入后等待秒数（autocomplete必需） |
| `filter_mode` | string | `local`(el-select) 或 `remote`(el-autocomplete) |

### fields[] 通用属性

| 属性 | 类型 | 必需 | 说明 |
|:---|:---|:---:|:---|
| `name` | string | ✅ | 字段中文名 |
| `key` | string | ✅ | 变量名，脚本中用作参数 |
| `placeholder` | string | | 输入框 placeholder 文本 |
| `component` | string | ✅ | 组件类型标识 |
| `required` | bool | | 是否必填 |
| `test_value` | string | | 自动化测试用的默认值 |
| `known_bug` | bool | | 已知BUG，断言应软检查 |

### tabs[]

| 属性 | 类型 | 必需 | 说明 |
|:---|:---|:---:|:---|
| `name` | string | ✅ | Tab 名称 |
| `after_select` | string | | 前置字段key（如先选模型才显示tab内容） |
| `fields` | array | ✅ | 该tab下的字段列表 |

### buttons[]

| 属性 | 类型 | 必需 | 说明 |
|:---|:---|:---:|:---|
| `text` | string | ✅ | 按钮文字 |
| `action` | string | | `submit`, `cancel`, `search`, `add_row` |
| `dialog` | string | | 如果点击后弹确认框，弹框的确认按钮文字 |

### dialogs[]

| 属性 | 类型 | 必需 | 说明 |
|:---|:---|:---:|:---|
| `title` | string | | 弹窗标题 |
| `confirm_text` | string | ✅ | 确认按钮文字 |
| `cancel_text` | string | | 取消按钮文字 |
| `fields` | array | | 弹窗内字段 |

### assertions

```json
"assertions": {
  "ui_list": { "url": "/列表路由", "search_placeholder": "搜索框placeholder", "status_col": 3 },
  "db": { "table": "表名", "by_field": "查询字段", "by_key": "对应field的key" },
  "detail_tab": { "tab_name": "Tab名", "field_key": "验证字段key" }
}
```

## 完整示例

```json
{
  "page_id": "pv_create",
  "title": "PV创建",
  "group": "装置管理/PV管理",
  "url": "/pv/edit?type=create",
  "fields": [
    {
      "name": "PV名称",
      "key": "pv_name",
      "placeholder": "请输入PV名称",
      "component": "input",
      "required": true,
      "test_value": "IP-SAFE-RFQ-CR:MDP01:RunFreq_Rd"
    },
    {
      "name": "设备IP",
      "key": "ip",
      "placeholder": "请输入设备IP",
      "component": "input",
      "required": true,
      "test_value": "172.20.0.102"
    },
    {
      "name": "设备端口",
      "key": "port",
      "placeholder": "请输入设备端口",
      "component": "input",
      "required": true,
      "test_value": "5064"
    },
    {
      "name": "PV描述",
      "key": "desc",
      "placeholder": "请输入PV描述",
      "component": "input",
      "required": false,
      "test_value": "webwright自动化PV"
    }
  ],
  "buttons": [
    { "text": "保存" }
  ],
  "assertions": {
    "db": { "table": "pv_data_info", "by_field": "pv_code", "by_key": "pv_name" }
  },
  "post_save": "redirect_to_list"
}
```

### ⚠️ 关键探索陷阱：placeholder 不等于 aria-label

浏览器的 accessibility tree（snapshot）显示的 `textbox "* 标签名称"` 是 **form-item 的 label 文本**，不是 input 的 **HTML placeholder 属性**。

实际 Playwright 脚本需要的 `page.get_by_placeholder("请输入标签名称")` 需要查看真实的 DOM 属性：

```javascript
// 在 browser_console 中确认
document.querySelector('input').placeholder                  // "请输入标签名称"
document.querySelector('input').getAttribute('aria-label')   // 可能为 null
```

**规则：** 不要用 snapshot 显示的 textbox 名称作为 placeholder。必须用 `browser_console` 读取 `input.placeholder` 确认真实值。
