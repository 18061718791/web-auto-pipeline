# 场景完整性设计规范（Scene Design Specification）

> 提取自 `web-auto-pipeline` skill 的 SKILL.md §十一，结合已验证脚本（`device_managent_test.py`、`tag_lifecycle_test.py`、`bypass_lifecycle_test.py`、`sn_lifecycle.py`）的实践沉淀。
>
> **提取时间：** 2026-06-08（2026-06-08 更新：新增原子功能 vs 端到端场景分类 §八，更新覆盖率分析 §六和IoT场景规划 §九）

## 目录

1. [核心原则](#一核心原则)
2. [场景设计检查清单](#二场景设计检查清单)
3. [Manifest Lifecycle 元数据](#三manifest-lifecycle-元数据)
4. [scenes.json 模板](#四scenesjson-模板)
5. [工作流整合](#五工作流整合)
6. [覆盖率分析方法论](#六覆盖率分析方法论)
7. [原子功能 vs 端到端业务场景分类](#八原子功能-vs-端到端业务场景分类2026-06-08-新增)
8. [IoT 平台后续场景规划](#九iot-平台后续场景规划2026-06-08-更新)

---

## 一、核心原则

### 1.1 单一职责场景

每个场景只测试**一个完整的操作闭环**（CRUD 的一步 + 对应断言）。不要在一个场景中混杂多个操作目标。

```python
# ✅ 正确：每个场景一个闭环
# 场景1: 创建PV → 搜索PV → DB验证 → UI验证
# 场景2: 创建元件模型 → 搜索模型 → DB验证 + UI确认
# 场景3: 发布元件模型 → 轮询状态 → DB确认

# ❌ 错误：场景内混杂多个目标
# 场景1: 创建PV + 创建元件模型 + 创建设备（耦合度高，失败难以定位）
```

### 1.2 金字塔验证（三层断言）

每个操作步骤后必须有三层验证，确保数据从前端到后端的一致性：

```
┌──────────────┐
│  UI 断言      │ ← 页面元素真实可见、状态正确（文本/计数/勾选框）
├──────────────┤
│  DB 断言      │ ← 数据真正写入数据库、字段值正确（最可靠）
├──────────────┤
│  异步轮询      │ ← 发布/上线等操作等待后台状态收敛（最多 30 秒 6 次轮询）
└──────────────┘
```

### 1.3 场景衔接与状态复用

**使用 `ensure_on_page` 避免重复导航。** 场景 N 结束时的页面状态应被场景 N+1 直接复用，除非 `--start-scene N` 断点续跑需要独立入口。

```python
# 场景设计时的状态流分析：
# 场景1结束: 保存后自动跳转到列表页 → URL = LIST_URL
# 场景2开始: ensure_on_page(page, LIST_URL) → 跳过 goto，直接搜索操作
# 场景2结束: 搜索后停留在列表页 → URL = LIST_URL
# 场景3开始: ensure_on_page(page, LIST_URL) → 同样跳过 goto
```

**SPA 平台注意事项：** 对于 hash-based SPA（Vue Router hash 模式），永远使用 `page.evaluate("window.location.hash = '#/xxx'")` 而非 `page.goto`，避免全量重载丢失 auth 状态。

### 1.4 场景依赖关系（阻塞 vs 非阻塞）

场景之间的数据依赖决定失败时是否阻断后续场景：

| 依赖类型 | 行为 | 示例 |
|:---|:---|:---|
| **阻塞（Blocking）** | 前序场景失败 → 跳过全部后续场景 | PV 创建失败 → 跳过模型/设备创建 |
| **非阻塞（Non-blocking）** | 前序场景失败 → 继续后续场景 | PV 关联失败 → 元件/设备流程继续 |
| **消费型依赖** | 依赖数据必须在 DB 中存在 | SN 场景依赖设备已发布数据 |

```python
NON_BLOCKING = {4, 5}  # PV关联、发布等非核心 → 不阻断
```

### 1.5 数据清理前置

**清理放在脚本开头（非结尾），不留后患，支持多脚本数据复用：**

```
cleanup_database()  # 脚本最开头
    ↓
场景1..9 执行       # 产出数据供消费型脚本使用
    ↓
(脚本结束，数据保留在 DB 中)
    ↓
消费型脚本（sn/tag/bypass）执行前 DB 直查依赖数据
```

### 1.6 每个场景必有 ==check_page_errors==

保存/发布/提交/确定等"写操作"后，必须立即截图 + 调用 `check_page_errors`：

```python
report.step("保存元件模型", screenshot=page)        # 先截图记录
has_err, err_txt = check_page_errors(page, report, ...)  # 再检测错误
if has_err: return report  # 关键失败则阻断
```

### 1.7 编辑后二次确认（UI 回查）

保存后仅做 DB 断言不够。必须重新进入编辑页验证 UI 渲染正确：

```python
# 层1：DB 断言
report.assertion("DB: 关联已更新", len(rels) == 2, "")

# 层2：重新搜索 → 进入编辑页 → 验证 UI
ensure_on_page(page, LIST_URL)
page.get_by_label("名称").fill(NAME)
# ... 搜索 → 点击编辑 → 验证编辑页数据
report.assertion("UI确认: 编辑页含目标数据", TEXT in edit_body, "")
```

### 1.8 场景可独立运行（断点续跑）

每个场景通过 `if should_run(N)` + `--start-scene N` 参数支持断点续跑：

```python
def run(start_scene=1):
    if start_scene <= 1:  # 场景1
        ...
    if start_scene <= 2:  # 场景2
        ...
```

### 1.9 等价类与边界值（设计补充）

| 验证维度 | 要求 | 示例 |
|:---|:---|:---|
| **等价类划分** | 每个字段至少测试 valid / boundary / invalid 三种 | 名称: 正常/空/超长 |
| **边界值分析** | 空字符串、最大长度、特殊字符、SQL注入 | `"'"`, `"<script>"`, `"%"` |
| **逆向场景** | 必填为空、重复名称、非法状态转换 | 编辑时名称=空, 已发布记录再次发布 |
| **状态机覆盖** | 每个状态和转换至少有一个测试覆盖 | draft→release, release→draft(禁止) |

---

## 二、场景设计检查清单

设计新场景时，回答以下 **4 个核心问题**，确保场景完整性。

### Q1: 状态机分析

**识别被测对象的状态流转，覆盖所有合法路径和非法路径。**

```text
问题：这个业务模块有哪些状态？状态之间如何流动？

示例（标签模块）：
  draft ──发布──→ active ──注销──→ inactive
    ↑                │
    └── 编辑 ────────┘

覆盖要求：
  ✅ 每个状态至少要有一个场景到达
  ✅ 每个合法转换至少有一个场景覆盖
  ✅ 至少测试一个非法转换（如 active → draft）
```

**IoT 平台已知状态机：**

| 模块 | 状态机 |
|:---|:---|
| 元件/设备模型 | `draft → 发布版本 → release`（发布后不可回退） |
| 设备标签 | `draft → 发布 → active → 注销 → inactive` |
| 设备 | `draft → 发布 → release`（发布需异步轮询） |
| Bypass 关联 | `新增 → 关联PV → 编辑(增删PV) → 删除` |

### Q2: CRUD + 状态转换

**检查每个 C/R/U/D 操作以及状态变更操作的覆盖完整性。**

```text
问题：这个模块的 CRUD + 状态变更是否都有场景覆盖？

┌─────────────────────────────────────────────┐
│  模块: 分类标签               脚本: 7个场景    │
├─────────────┬───────────────────────────────┤
│  场景1      │ 新增标签 (C)                    │
│  场景2      │ 编辑标签文本 (U)                 │
│  场景3      │ 编辑标签状态 (U + 状态转换)       │
│  场景4      │ 发布标签 (U: draft→active)       │
│  场景5      │ 注销标签 (U: active→inactive)    │
│  场景6      │ 设备关联标签 (R: 关联验证)        │
│  场景7      │ 删除关联 → 删除标签 (D)           │
└─────────────┴───────────────────────────────┘

检查：CREATE ✅ | READ ✅ (搜索+详情) | UPDATE ✅ | DELETE ✅ | 状态转换 ✅
```

**"只增不改"反模式的禁止：** 端到端脚本必须包含 DELETE 和 UPDATE 操作。只创建不删除/编辑的脚本不可验收。

### Q3: 模块关联

**检查被测模块与其他模块之间的数据依赖关系，确保关联操作被测试。**

```text
问题：这个模块会关联/引用哪些其他模块的数据？

示例（创建设备）：
  设备模型 ──→ 关联 ──→ 元件模型
    ↓                      ↓
  设备 ────→ 关联 ────→ 元件
    ↓
  SN 号 ────→ 分配到 ───→ 已发布设备

需要覆盖的关联场景：
  ✅ 创建设备时关联设备模型（选择验证）
  ✅ 创建设备时关联元件（元件tab + 搜索选择）
  ✅ 设备详情页验证关联元件存在
  ✅ SN分配设备（功能关联）
```

### Q4: 状态差异

**检查相同操作在不同状态下产生的 UI/行为差异。**

```text
问题：同一条数据在不同状态下，UI 展示和行为有何不同？

示例（设备列表页）：
┌────────────┬──────────────┬─────────────────────┐
│  状态       │ 操作按钮      │ 状态列显示            │
├────────────┼──────────────┼─────────────────────┤
│  draft     │ [发布]        │ (空 / 无状态文字)     │
│  release   │ 不可操作       │ "发布"               │
└────────────┴──────────────┴─────────────────────┘

覆盖要求：
  ✅ draft 状态 → 显示"发布"按钮
  ✅ release 状态 → 状态列显示"发布"，按钮消失/禁用
  ✅ 列表默认只显示 draft 记录
  ✅ 发布后需 goto 刷新才能看到状态变化（异步）
```

---

## 三、Manifest Lifecycle 元数据

以下元数据为每个场景在 Page Manifest 中的完整生命周期描述。

### 3.1 场景元数据字段表

| 字段 | 类型 | 必填 | 说明 |
|:---|:---|:---:|:---|
| `id` | `string` | ✅ | 场景唯一标识，如 `scene-1` |
| `name` | `string` | ✅ | 场景名称，如 "创建PV" |
| `description` | `string` | ✅ | 场景功能描述 |
| `url` | `string` | ✅ | 场景起始页面 URL |
| `type` | `string` | ✅ | 场景类型：`create` / `update` / `read` / `delete` / `state_transition` / `association` |
| `depends_on` | `string[]` | | 依赖的其他场景 ID |
| `blocking` | `boolean` | | 失败是否阻断后续场景（默认 `true`） |
| `states` | `object` | ✅ | 状态机定义 |
| `states.before` | `string` | ✅ | 操作前状态（如 `"none"`） |
| `states.after` | `string` | ✅ | 操作后期望状态（如 `"draft"`） |
| `states.transition` | `string` | ✅ | 状态转换动作（如 `"create_pv"`） |
| `assertions` | `object[]` | ✅ | 断言列表 |
| `assertions[].type` | `string` | ✅ | `ui` / `db` / `polling` |
| `assertions[].target` | `string` | ✅ | 断言目标描述 |
| `associated_modules` | `string[]` | | 关联的模块名列表 |
| `data_cleaned` | `string` | | 本场景涉及的数据清理 SQL 或描述 |
| `data_created` | `string` | | 本场景创建的测试数据名 |
| `notes` | `string` | | 已知问题/注意事项 |

### 3.2 场景元数据示例（设备管理-场景1）

```json
{
  "id": "scene-1",
  "name": "创建PV",
  "description": "新增PV数据源，填写名称/IP/端口/描述，保存后验证DB和列表",
  "url": "{BASE_URL}/pv/edit?type=create",
  "type": "create",
  "depends_on": [],
  "blocking": true,
  "states": {
    "before": "none",
    "after": "draft",
    "transition": "create_pv"
  },
  "assertions": [
    {"type": "db", "target": "pv_data_info 表包含新PV记录"},
    {"type": "ui", "target": "PV列表页搜索显示新PV"},
    {"type": "ui", "target": "列表行包含正确名称/IP/端口"}
  ],
  "associated_modules": [],
  "data_cleaned": "DELETE FROM pv_data_info WHERE pv_code='{PV_CODE}'",
  "data_created": "PV ({PV_CODE})",
  "notes": "PV是后续所有模块的基础数据依赖"
}
```

### 3.3 场景类型分类

| 类型 | 说明 | 验证重点 |
|:---|:---|:---|
| `create` | 新增记录 | 列表存在 + DB 存在 + 字段值正确 |
| `update` | 编辑修改 | DB 更新 + UI 二次确认 + 关联数据一致性 |
| `read` | 查询/搜索 | 筛选正确 + 详情页展示完整 |
| `delete` | 删除/注销 | DB 标记删除(is_delete) + 列表不再显示 + 软删除可恢复性 |
| `state_transition` | 状态变更（发布/激活/注销） | 异步轮询收敛 + DB 状态字段 + UI 按钮变化 |
| `association` | 关联/取消关联 | 关联表记录 + 编辑页回查 |

---

## 四、scenes.json 模板

### 4.1 标准结构

```json
{
  "platform": "${platform_name}",
  "script_id": "${script_id}",
  "version": "1.0.0",
  "description": "${整体描述}",
  "dependencies": {
    "depends_on_scripts": ["${前置脚本名}"],
    "check_prerequisites": ["${前置检查函数名}"]
  },
  "data_cleanup": {
    "sql": ["DELETE FROM ... WHERE ..."],
    "order": ["先删依赖表", "再删主表"]
  },
  "scenes": [
    {
      "id": "scene-1",
      "name": "场景1名称",
      "description": "场景描述",
      "type": "create|update|read|delete|state_transition|association",
      "blocking": true,
      "url": "${场景起始URL}",
      "states": {
        "before": "",
        "after": "",
        "transition": ""
      },
      "assertions": [
        {"type": "ui", "target": "", "detail": ""},
        {"type": "db", "target": "", "sql": "SELECT ..."},
        {"type": "polling", "target": "", "timeout_seconds": 30}
      ],
      "associated_modules": [],
      "data_created": "",
      "notes": ""
    }
  ]
}
```

### 4.2 完整示例（设备管理 9 场景）

```json
{
  "platform": "IoT 物联管理平台",
  "script_id": "device_managent_test",
  "version": "1.0.0",
  "description": "端到端设备管理：PV→元件模型→发布→元件→设备模型→设备→发布",
  "dependencies": {
    "depends_on_scripts": [],
    "check_prerequisites": []
  },
  "data_cleanup": {
    "sql": [
      "DELETE FROM device WHERE device_name LIKE '自动化测试%'",
      "DELETE FROM thing_model_version WHERE thing_model_id IN (SELECT id FROM thing_model WHERE thing_name LIKE '自动化测试%')",
      "DELETE FROM thing_model WHERE thing_name LIKE '自动化测试%'",
      "DELETE FROM pv_data_info WHERE pv_code = '{PV_CODE}'"
    ],
    "order": ["先删设备/元件", "再删版本", "再删模型", "最后删PV"]
  },
  "scenes": [
    {
      "id": "scene-1",
      "name": "创建PV",
      "description": "新增PV数据源，填写名称/IP/端口/描述，保存后DB验证",
      "type": "create",
      "blocking": true,
      "url": "/pv/edit?type=create",
      "states": {"before": "none", "after": "draft", "transition": "create_pv"},
      "assertions": [
        {"type": "db", "target": "pv_data_info", "sql": "SELECT pv_code, ip, port FROM pv_data_info WHERE pv_code=%s"}
      ],
      "data_created": "PV (PV_CODE)"
    },
    {
      "id": "scene-2",
      "name": "添加元件模型（带属性）",
      "description": "创建元件模型，添加属性（名称/描述/读写/数据类型），保存后列表+DB验证",
      "type": "create",
      "blocking": true,
      "url": "/elementType/eEdit?type=create",
      "states": {"before": "none", "after": "draft", "transition": "create_element_model"},
      "assertions": [
        {"type": "ui", "target": "列表搜索显示新模型"},
        {"type": "db", "target": "thing_model", "sql": "SELECT thing_name, thing_code, thing_status FROM thing_model WHERE thing_name=%s"}
      ],
      "data_created": "元件模型 (EL_MODEL_NAME)"
    },
    {
      "id": "scene-3",
      "name": "发布元件模型",
      "description": "进入模型版本详情，点击发布，版本详情页验证，列表验证，DB验证",
      "type": "state_transition",
      "blocking": true,
      "url": "/elementType/elist",
      "states": {"before": "draft", "after": "release", "transition": "publish_element_model"},
      "assertions": [
        {"type": "ui", "target": "版本详情页显示发布标记"},
        {"type": "db", "target": "thing_model_version", "sql": "SELECT version_status FROM thing_model_version WHERE ..."},
        {"type": "polling", "target": "列表状态列显示'发布'", "timeout_seconds": 15}
      ]
    },
    {
      "id": "scene-4",
      "name": "新增元件 + 关联PV",
      "description": "创建元件，关联发布的元件模型，关联PV（el-autocomplete），保存后列表+DB+详情验证",
      "type": "create",
      "blocking": false,
      "url": "/element/eDeviceEdit?type=create",
      "states": {"before": "none", "after": "draft", "transition": "create_element"},
      "associated_modules": ["元件模型", "PV"],
      "assertions": [
        {"type": "ui", "target": "元件列表存在"},
        {"type": "db", "target": "device", "sql": "SELECT device_name, device_code, device_status FROM device WHERE device_name=%s"},
        {"type": "ui", "target": "详情页物模型tab验证PV绑定"}
      ],
      "data_created": "元件 (EL_NAME)",
      "notes": "PV关联可能因el-autocomplete静默失败而失败（已知BUG），但不阻断后续场景"
    },
    {
      "id": "scene-5",
      "name": "发布元件",
      "description": "从列表点击行内发布，确认弹窗，轮询等待状态变为'发布'，DB验证",
      "type": "state_transition",
      "blocking": false,
      "url": "/element/eDeviceList",
      "states": {"before": "draft", "after": "release", "transition": "publish_element"},
      "assertions": [
        {"type": "polling", "target": "列表状态列显示'发布'", "timeout_seconds": 30},
        {"type": "db", "target": "device", "sql": "SELECT device_status FROM device WHERE device_name=%s"}
      ]
    },
    {
      "id": "scene-6",
      "name": "创建设备模型",
      "description": "创建设备模型，关联已发布的元件模型，保存后列表+DB验证",
      "type": "create",
      "blocking": true,
      "url": "/controllerType/cEdit?type=create",
      "states": {"before": "none", "after": "draft", "transition": "create_device_model"},
      "associated_modules": ["元件模型"],
      "assertions": [
        {"type": "ui", "target": "设备模型列表存在"},
        {"type": "db", "target": "thing_model", "sql": "SELECT ... FROM thing_model WHERE thing_name=%s"}
      ],
      "data_created": "设备模型 (CON_MODEL_NAME)"
    },
    {
      "id": "scene-7",
      "name": "发布设备模型",
      "description": "进入版本详情，发布版本，列表+DB验证",
      "type": "state_transition",
      "blocking": true,
      "url": "/controllerType/clist",
      "states": {"before": "draft", "after": "release", "transition": "publish_device_model"},
      "assertions": [
        {"type": "ui", "target": "版本信息含发布标记"},
        {"type": "db", "target": "thing_model_version", "sql": "SELECT version_status ..."}
      ]
    },
    {
      "id": "scene-8",
      "name": "创建设备 + 关联元件",
      "description": "创建设备，填写完整字段，关联设备模型+元件，保存后列表+详情+DB验证",
      "type": "create",
      "blocking": true,
      "url": "/controller/cDeviceEdit?type=create",
      "states": {"before": "none", "after": "draft", "transition": "create_device"},
      "associated_modules": ["设备模型", "元件"],
      "assertions": [
        {"type": "ui", "target": "设备列表存在"},
        {"type": "ui", "target": "详情页元件tab含关联元件"},
        {"type": "db", "target": "device", "sql": "SELECT ... FROM device WHERE device_name=%s"}
      ],
      "data_created": "设备 (CON_NAME)"
    },
    {
      "id": "scene-9",
      "name": "发布设备",
      "description": "行内发布，确认弹窗，异步轮询状态，DB验证（重试3次）",
      "type": "state_transition",
      "blocking": true,
      "url": "/controller/cDeviceList",
      "states": {"before": "draft", "after": "release", "transition": "publish_device"},
      "assertions": [
        {"type": "polling", "target": "列表状态列显示'发布'", "timeout_seconds": 30},
        {"type": "db", "target": "device_status='release'", "sql": "SELECT ...", "notes": "DB重试3次"}
      ]
    }
  ]
}
```

### 4.3 消费型脚本 scenes.json 示例（SN 全生命周期）

```json
{
  "platform": "IoT 物联管理平台",
  "script_id": "sn_lifecycle",
  "version": "1.0.0",
  "description": "SN号全生命周期：新增→分配→设备详情验证",
  "dependencies": {
    "depends_on_scripts": ["device_managent_test"],
    "check_prerequisites": ["db_check_pv_exists", "db_check_device_released"]
  },
  "scenes": [
    {
      "id": "scene-1",
      "name": "新增SN号",
      "description": "新增SN码，验证列表存在+状态+按钮+DB",
      "type": "create"
    },
    {
      "id": "scene-2",
      "name": "分配SN到设备",
      "description": "弹窗选择已发布设备，状态变待激活，验证设备SN字段",
      "type": "update"
    },
    {
      "id": "scene-3",
      "name": "设备详情验证SN",
      "description": "进入已分配设备详情页，验证SN字段显示正确",
      "type": "read"
    }
  ]
}
```

---

## 五、工作流整合

### 5.1 在 Phase 2 中的位置

场景设计在流水线中的位置：

```text
Phase 0: 平台探索
  产出: Page Manifest JSON（含页面结构/组件类型/状态机）
         ↓
Phase 1: 脚本骨架生成
  产出: 场景框架代码（含 scene_start/end, step 占位, 断言占位）
         ↓
Phase 2: 场景填充 → 执行验证  ★ 本规范主要应用阶段 ★
  ├─ 1. 根据 scenes.json 设计场景数据流
  ├─ 2. 填充场景函数体（表单交互 + 三层断言）
  ├─ 3. 添加 check_page_errors 和截图（每写操作后）
  ├─ 4. 添加 ensure_on_page 实现场景衔接
  ├─ 5. 运行 single scene 调试
  ├─ 6. 全场景串行执行验证
  └─ 7. master_runner 聚合 → CI/CD
```

### 5.2 场景设计模板使用流程

1. **编写 scenes.json** — 使用 §四的模板设计场景元数据
2. **生成场景框架** — 从 scenes.json 生成 Python 代码骨架
3. **填充交互细节** — 根据 Page Manifest 中的组件类型选择对应交互方案（见 `element_ui_patterns.md`）
4. **添加三层断言** — UI 断言 + DB 断言 + 异步轮询
5. **实现场景衔接** — 使用 `ensure_on_page` 管理页面状态
6. **调试单个场景** — `--start-scene N` 逐个验证
7. **全流程运行** — `python xxx.py` 无参数运行
8. **集成到 master_runner** — 注册到 `SCRIPTS` 数组

### 5.3 脚本模板参考

```python
#!/usr/bin/env python3
"""场景脚本模板"""
import sys, time, argparse
from config import BASE_URL, get_db_connection
from report_helper import TestReport

# ── 场景元数据 ──
SCENES = [
    {"id": "scene-1", "name": "场景1名称", "blocking": True},
    {"id": "scene-2", "name": "场景2名称", "blocking": False},
]

# ── 数据清理 ──
def db_cleanup():
    pass  # 按 scenes.json 的 data_cleanup 实现

# ── 断言辅助 ──
def check_page_errors(page, report=None, ...):
    pass  # 标准实现

def assert_ui(page, locator_fn, desc):
    pass  # 标准实现

# ── 场景衔接（必须） ──
def ensure_on_page(page, target_url, wait_seconds=3):
    pass  # 标准实现

# ── 主运行函数 ──
def run(start_scene=1, headless=False, cleanup=True):
    report = TestReport("脚本标题")
    if cleanup:
        db_cleanup()

    def should_run(n):
        return n >= start_scene

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        try:
            # 场景1
            if should_run(1):
                report.scene_start("场景1", "描述")
                # ... 交互 + step + 截图 ...
                report.step("操作名", screenshot=page)
                has_err, _ = check_page_errors(page, report)
                if has_err: return report
                # 断言
                report.assertion("", True, "")
                report.scene_end(True)
            else:
                report.scene_skip("场景1", "跳过")

            # 后续场景...
        except Exception as e:
            if report.current_scene:
                report.scene_end(False)
        finally:
            browser.close()

    report.generate_html(...)
    return report

# ── 入口 ──
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-scene", type=int, default=1)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--cleanup-only", action="store_true")
    args = parser.parse_args()
    if args.cleanup_only:
        db_cleanup()
        sys.exit(0)
    run(start_scene=args.start_scene, headless=args.headless, cleanup=not args.no_cleanup)
```

### 5.4 与 master_runner 的集成

在 `master_runner.py` 的 `SCRIPTS` 数组中注册：

```python
SCRIPTS = [
    {
        "name": "设备管理",
        "file": "device_managent_test.py",
        "scenes": 9,         # 场景数（来自 scenes.json）
        "depends_on": [],     # 前置依赖脚本
        "scene_file": "references/scenes-device_managent.json"  # 场景描述文件路径
    },
    {
        "name": "SN全生命周期",
        "file": "sn_lifecycle.py",
        "scenes": 3,
        "depends_on": ["device_managent_test"],
        "scene_file": "references/scenes-sn_lifecycle.json"
    },
]
```

---

## 六、覆盖率分析方法论

### 6.1 基本原则

**覆盖度分析必须以「已验证/可运行的场景」为基准**，而不是以「尝试过的用例」—— 失败的自动化尝试不代表有效覆盖。分析步骤：

```text
Step 1: 从平台探索数据（all_urls.json / 截图记录）提取全量页面路由清单
Step 2: 只计入已验证通过、可重复运行的场景
Step 3: 将已验证场景逐一映射到页面路由，标记覆盖率：✅完全 / 🔶部分 / ❌未覆盖
Step 4: 按业务价值 + 技术风险 + CRUD 完整性给优先级（P0→P1→P2）
```

**P0/P1/P2 优先级定义：**

| 优先级 | 含义 | 策略 |
|:---:|:---|:---|
| **P0** | 核心业务闭环完整性 — 必须实现 | 新建独立脚本或追加到已有脚本 |
| **P1** | 高频/高风险业务功能 — 强烈推荐 | 追加到已有脚本或新建脚本 |
| **P2** | 异常/边界/安全 — 健壮性增强 | 融入现有脚本的追加场景 |

---

## 八、原子功能 vs 端到端业务场景分类（2026-06-08 新增）

> **重要设计原则：两类场景必须严格区分，数据完全隔离。**

### 8.1 定义

#### 原子功能（基础功能）

按 **功能菜单维度** 编写的独立自动化测试脚本。每个菜单对应一个独立的 `.py` 文件。

| 特性 | 说明 |
|:---|:---|
| **维度** | 一个菜单一个脚本（如 `pv_atomic_test.py` 只测 PV 管理菜单） |
| **数据** | 自造数据、自清理，不依赖任何其他脚本 |
| **独立性** | 不与端到端脚本共享数据；即使同一操作在两端都有，也必须各自执行 |
| **覆盖** | 该菜单下所有 CRUD + 功能按钮 + 搜索的全部原子操作 |
| **命名** | `{menu}_atomic_test.py`（如 `pv_atomic_test.py`, `sn_atomic_test.py`） |

```python
# ✅ 正确：pv_atomic_test.py 独立创建自己的测试数据
from config import BASE_URL, get_db_connection

AUTO_PREFIX = f"AUTO_PV_{TIMESTAMP}"   # 独立前缀，不与任何脚本共享
...
db_cleanup():  # 只清理 AUTO_PREFIX 的数据
    DELETE FROM pv_data_info WHERE pv_code LIKE 'AUTO_PV_%'

# 场景1: 新增PV（使用用户提供的mock数据）
# 场景2: 查看详情
# 场景3: 连通性测试
# 场景4: 编辑PV
# 场景5: 搜索PV
# 场景6: 删除PV（使用自定义草稿PV）
# 场景7: 批量导入
# 场景8: 清理
```

一个完整原子脚本应包含的原子操作清单（以 PV 管理为例）：

| 原子操作 | 说明 | 依赖条件 | 数据策略 |
|:---|:---|:---|:---|
| **新增** | 创建一条新记录 | 无 | 使用用户提供的mock数据 |
| **编辑** | 搜索 → 修改字段 → 保存 → DB验证 → 二次确认UI | 已有记录（不存在则先创建） | 直接操作mock数据 |
| **查看详情** | 搜索 → 点详情 → 验证字段 | 已有记录 | 复用mock数据 |
| **删除** | 创建草稿 → 删除 → 确认 → 列表验证 + DB | 草稿状态 | 使用自定义前缀（`AUTO_DEL_`） |
| **搜索** | 模糊搜索 + 精确搜索 → UI验证 + DB验证 | 已有数据 | 复用mock数据 |
| **功能性按钮** | 如连通性测试 → 点击 → 验证响应 | 已有数据 + 有效IP/端口 | 使用mock数据 |
| **批量导入** | 模板生成 → 文件上传 → API监听 → DB验证 | 无 | 使用独立前缀（`AUTO_IMPORT_`） |

#### 端到端业务场景（业务功能）

由 **多个功能模块组合** 而成的完整业务流。

| 特性 | 说明 |
|:---|:---|
| **维度** | 一个业务流一个脚本（如 `device_managent_test.py` 覆盖 PV→模型→元件→设备→发布） |
| **数据** | 在脚本内按依赖链依次创建，消费型脚本（如 sn_lifecycle）可直接查询依赖数据 |
| **独立性** | 不依赖原子脚本的数据；与原子脚本即使操作同一模块，数据也完全隔离 |
| **覆盖** | 跨模块的完整业务闭环（非单一菜单） |
| **命名** | `{business_flow}_test.py`（如 `device_managent_test.py`） |

### 已验证的原子脚本标准结构（6 场景）

> 源自 `pv_atomic_test.py` 的实践验证。每个原子脚本应遵循此场景序列：

```text
场景1: 双条件查重 + 清理旧数据 → 新增主测试数据（使用用户提供的 mock 数据）
场景2: 搜索验证（精确搜索 + 列表行确认）
场景3: 功能按钮测试（连通性测试等 → 关闭结果弹窗）
场景4: 编辑 → DB验证 → 二次进入编辑页UI确认
场景5: 搜索 → 删除 → UI验证 + DB软删除验证
场景6: 批量导入 → 下载模板 → 上传 → 关闭导入结果弹窗 → 搜索 → DB删除
```

### 8.2 MUST 级规则

#### 规则 1：数据隔离

原子脚本与端到端脚本之间 **完全数据隔离**。即使操作同一张 `pv_data_info` 表：

```python
# pv_atomic_test.py（原子功能）
PV_CODE = "IP-SAFE-RFQ-CR:TMP01:Vol_Rd"
AUTO_PREFIX = "AUTO_PV_MMDDHHMMSS_"

# device_managent_test.py（端到端场景）
PV_CODE = "IP-SAFE-RFQ-CR:MDP01:RunFreq_Rd"  # 不同值
CLEANUP_PREFIX = "自动化测试%"
```

#### 规则 2：原子脚本不依赖端到端脚本

原子脚本不能假定端到端脚本已运行产生数据。即使在端到端脚本中已经创建过同类型数据，原子脚本也必须自己执行创建操作。

#### 规则 3：端到端脚本不依赖原子脚本

端到端脚本不能假定原子脚本已运行。端到端脚本维护自己的数据链。

#### 规则 4：数据清理只清理自己创建的数据

- 原子脚本：使用独立前缀（如 `AUTO_PV_`、`AUTO_IMPORT_`），清理时只删匹配前缀的记录
- 端到端脚本：使用独立标识（如 `自动化测试%`），清理时只删自己的数据
- **严禁**：清理时使用无条件 `DELETE` 或没有精确匹配条件的 `LIKE`

#### 规则 5：mock 数据可以自由操作

用户提供的 mock 数据（非生产数据）可以在场景中自由操作——包括编辑、删除、连通性测试。
**不要给用户数据加"不可删除/修改"的限制标注**，除非用户明确指明。

```python
# ✅ 正确：mock 数据无限制标准
PV_CODE = "IP-SAFE-RFQ-CR:TMP01:Vol_Rd"

# ❌ 错误：不应假设"不可删除/修改"
REAL_PV_CODE = "IP-SAFE-RFQ-CR:TMP01:Vol_Rd"  # 标注为"真实PV不可删除"是错误假设
```

### 8.3 脚本命名规范

| 类别 | 模式 | 示例 |
|:---|:---|:---|
| 原子功能 | `{menu}_atomic_test.py` | `pv_atomic_test.py`, `sn_atomic_test.py` |
| 端到端场景 | `{business_flow}_test.py` 或 `{business_flow}_lifecycle.py` | `device_managent_test.py`, `sn_lifecycle.py` |
| 原子+导入合并 | 原子脚本内部包含批量导入场景 | `pv_atomic_test.py` 含场景7（导入） |

### 8.4 场景设计流程（补充）

设计新测试脚本时，先回答：

```text
Q1: 属于原子功能还是端到端场景？
  → 原子功能：一个菜单一个脚本，自造数据
  → 端到端场景：跨模块组合，维护独立数据链

Q2: 如果是原子功能，该菜单下有哪些原子操作？
  列出全部：增/编/查/删/功能性按钮/搜索/批量导入...

Q3: 数据前缀/标识是什么？
  确保与其他脚本不冲突，清理条件精确

Q4: 用户是否提供了 mock 数据？
  如果有，标记为可自由操作；如果没有，使用自定义前缀
```

---

## 九、IoT 平台后续场景规划（2026-06-08 更新）

> 基于平台探索（all_urls.json，~60 页面路由）与 26 个已验证场景的精确映射分析。
> **不包含旧框架遗留的失败用例** — 仅以当前已验证通过的脚本为基准。

### 9.1 已验证场景覆盖现状

| 脚本 | 场景数 | 覆盖 ~60 路由中的 | 占比 |
|:---|:---:|:---:|:---:|
| `device_managent_test.py` | 9 | PV创建、元件模型创建/发布、元件创建/发布、设备模型创建/发布、设备创建/发布 | ~15% |
| `sn_lifecycle.py` | 3 | SN新增、分配、设备验证 | ~5% |
| `tag_lifecycle_test.py` | 7 | 分类标签全生命周期 | ~3% |
| `bypass_lifecycle_test.py` | 5 | Bypass关联全生命周期 | ~3% |
| `pv_import_test.py` | 2 | PV批次导入 | ~2% |
| **总计** | **26** | **~13 个路由有覆盖** | **~21%** |

### 9.2 覆盖率图谱（按子模块）

#### 装置管理

| 子模块 | 页面路由数 | 覆盖状态 |
|:---|:---:|:---:|
| PV管理 (pv/list, import, todo, done) | 4 | 🔶 PV创建+导入有覆盖；待办/已办 ❌ |
| Bypass管理 (pv/relation, relationEdit) | 2 | ✅ 全生命周期覆盖 |
| 分类标签 (tag/list) | 1 | ✅ 全生命周期覆盖 |
| SN管理 (sn/list) | 1 | 🔶 新增+分配有覆盖；回收/编辑/删除 ❌ |
| 设备模型 (clist, cEdit, cInstrument, cversion-list) | 4 | 🔶 创建+发布有覆盖；编辑/删除/版本管理 ❌ |
| 设备 (cDeviceList, cDeviceEdit, cDeviceDetail, elementDetail) | 4 | 🔶 创建+发布有覆盖；编辑/删除/详情 ❌ |
| 元件模型 (elist, eEdit, eInstrument, eversion-list) | 4 | 🔶 创建+发布有覆盖；编辑/删除/版本管理 ❌ |
| 元件 (eDeviceList, eDeviceDetail, eDeviceEdit) | 3 | 🔶 创建+发布有覆盖；编辑/删除 ❌ |
| 装置/装置模型 (eqcTypeList/Edit/Detail/version-edit) | 4 | ❌ 未覆盖 |
| 装置/装置设备 (eqcDeviceList/Edit/QuickInit/Detail/SubDetail) | 5 | ❌ 未覆盖 |
| 段/模型管理 (cTypeList/Edit/Detail/version-edit) | 4 | ❌ 未覆盖 |
| 段/段 (cDeviceList/Edit/Detail/SubDetail) | 4 | ❌ 未覆盖 |
| 故障快照 (Snapshot/list) | 1 | ❌ 未覆盖 |
| 系统视图 + 全局视图 | 3 | ❌ 未覆盖 |

#### 运行管理（全部 ❌ 未覆盖）

| 子模块 | 页面路由数 |
|:---|:---:|
| 设备控制 + 操作历史 | 2 |
| 场景联动规则 + 规则配置 | 2 |
| 执行日志 | 1 |
| 系统日志 | 1 |
| 类型设置 | 1 |
| 告警管理 + 告警编辑 | 2 |
| 告警总览 | 1 |

#### 系统管理及其他（全部 ❌ 未覆盖）

| 子模块 | 页面路由数 |
|:---|:---:|
| 系统管理（系统+新增设备） | 2 |
| 设备订阅 + 新增订阅 | 2 |
| 业务字典 | 2 |
| 数据权限 + 新增标签 | 2 |
| 个人中心 | 1 |

### 9.3 必测场景推荐（22 个场景群）

#### P0（核心业务闭环 — 7 个场景群）

| # | 场景群 | 所属模块 | 说明 | 策略 |
|:-:|:---|:---|:---|:---:|
| 1 | **设备/元件/模型 编辑与删除闭环** | 设备管理 | 补全现有 device_managent_test 缺失的 U/D 操作 | 追加 4 场景 |
| 2 | **装置模型 CRUD** | 装置/装置模型 | 装置是设备的上层聚合，完全未覆盖 | 新建脚本 4 场景 |
| 3 | **段(复合设备) CRUD** | 装置/段 | 复合设备管理完全未覆盖 | 新建脚本 5 场景 |
| 4 | **告警管理 CRUD** | 运行管理 | 告警是 IoT 平台核心运行态功能 | 新建脚本 4 场景 |
| 5 | **设备控制 + 操作历史** | 运行管理 | 设备启停控制，最高风险操作 | 新建脚本 3 场景 |
| 6 | **场景联动规则 CRUD** | 运行管理 | 自动化规则的核心配置 | 新建脚本 4 场景 |
| 7 | **设备订阅 CRUD** | 系统管理 | 用户高频使用的数据订阅功能 | 新建脚本 3 场景 |

#### P1（高频业务 — 7 个场景群）

| # | 场景群 | 所属模块 | 说明 | 策略 |
|:-:|:---|:---|:---|:---:|
| 8 | **PV待办/已办流程** | PV管理 | 流程审批环节，有历史失败记录 | 新建脚本 3 场景 |
| 9 | **数据权限配置** | 系统管理 | 多租户权限控制 | 新建脚本 2 场景 |
| 10 | **业务字典配置** | 系统管理 | 基础枚举数据管理 | 新建脚本 2 场景 |
| 11 | **故障快照查询** | 装置管理 | 设备故障溯源，运维核心 | 新建脚本 2 场景 |
| 12 | **SN回收再分配** | SN管理 | 释放已分配SN → 状态回退 → 重新分配 | 追加 2 场景 |
| 13 | **标签设备关联取消** | 设备标签 | 已有标签关联场景，缺少取消关联 | 追加 1 场景 |
| 14 | **类型设置验证** | 运行管理 | 系统配置的只读+修改验证 | 新建脚本 2 场景 |

#### P2（边界/异常 — 8 个场景群）

| # | 场景群 | 策略 |
|:-:|:---|:---|
| 15 | 重复名称创建拒绝 | 追加到各创建场景 |
| 16 | 必填字段为空提交 | 追加到各创建场景 |
| 17 | 搜索/筛选组合验证 | 追加到各列表页场景 |
| 18 | 已删除数据不可见 | 追加到各删除场景后 |
| 19 | 批量操作（删除/发布） | 追加到设备管理脚本 |
| 20 | 超长字段输入 | 追加到各创建场景 |
| 21 | 个人中心信息修改 | 新建脚本 2 场景 |
| 22 | 已发布数据不可重复发布 | 追加到各发布场景 |

### 9.4 执行路线

```
Phase 1: 补全 CRUD 闭环（P0 #1-#3，工作量最小）
  device_managent_test 追加编辑/删除 → 装置模型新脚本 → 段新脚本

Phase 2: 运行管理核心（P0 #4-#7，业务最重要）
  告警管理 → 设备控制 → 场景联动 → 设备订阅

Phase 3: 高频功能（P1 #8-#14）
  PV待办/已办 → 数据权限 → 业务字典 → 故障快照 → SN回收 → 标签取消关联 → 类型设置

Phase 4: 边界异常（P2 #15-#22）
  负面验证 → 批量操作 → 边界条件
```

### 9.5 数据依赖关系图

```text
已验证 26 场景（5 个脚本）：
  device_managent_test (9场景) ← 无依赖
    ├─ PV 创建 → 元件模型+发布 → 元件+PV绑定+发布 → 设备模型+发布 → 设备+元件关联+发布
    │
    ├─ sn_lifecycle (3场景) ← 依赖 device_managent 数据
    │   └─ 新增 SN → 分配设备 → 设备详情验证
    │
    ├─ tag_lifecycle_test (7场景) ← 依赖 device_managent 数据
    │   └─ 新增 → 编辑 → 查询 → 发布 → 注销 → 设备关联 → 删除
    │
    ├─ bypass_lifecycle_test (5场景) ← 依赖 device_managent PV数据
    │   └─ 新增 → 查询 → 编辑(增PV) → 编辑(删PV) → 删除
    │
    └─ pv_import_test (2场景) ← 无依赖
        └─ 模板生成+导入 → 清理

P0 新增（20+ 场景）:
  追加: device_managent_test +4              ← 复用浏览器和数据
  新建: device_type_test +4                  ← 装置模型
  新建: composite_device_test +5             ← 段(复合设备)
  新建: alarm_lifecycle_test +4              ← 告警管理
  新建: device_control_test +3               ← 设备控制
  新建: scene_linkage_test +4                ← 场景联动
  新建: subscribe_test +3                    ← 设备订阅

P1 新增（14+ 场景）:
  新建: pv_workflow_test +3                  ← 待办/已办
  追加: sn_lifecycle +2                      ← 回收再分配
  追加: tag_lifecycle_test +1                ← 取消关联
  ...

P2 新增（10+ 场景）:
  追加到各现有脚本                            ← 负面/边界

目标: 26 + 20 + 14 + 10 = ~70 场景
```

---

> 本文档由 `web-auto-pipeline` SKILL.md 的 §十一（场景完整性设计规范）提取，并结合已验证脚本实践整理。
> 原文位于 `web-auto-pipeline` skill 的 SKILL.md。
> 生成日期：2026-06-08
