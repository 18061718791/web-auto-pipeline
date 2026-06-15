# IoT 物联管理平台差异参考

> 本文件从 `web-auto-pipeline` skill 的 SKILL.md 中提取所有 IoT 平台特定的 URL、placeholder、BUG 差异信息。
>
> 用于平台 Profile 切换时的参考对照，新增 IoT 平台自动化脚本时以此为基准。

---

## 1. 页面/URL 差异表

| 页面 | URL | 备注 |
|:---|:---|:---|
| 设备模型创建 | `/controllerType/cEdit?type=create` | ❌ 不是 `/controller/cModelEdit?type=create`（404），也不是 `/deviceType/eDeviceTypeEdit`（404） |
| 设备模型列表 | `/controllerType/clist` | ❌ 不是 `/controller/cModelList`（404） |
| 设备创建 | `/controller/cDeviceEdit?type=create` | |
| 设备列表 | `/controller/cDeviceList` | |
| 元件创建 | `/element/eDeviceEdit?type=create` | |
| 元件列表 | `/element/eDeviceList` | |
| 元件模型创建 | `/elementType/eEdit?type=create` | |
| PV创建 | `/pv/edit?type=create` | 表单用 placeholder 定位，详见 §10 |
| Bypass关联列表 | `/pv/relation` | |
| Bypass关联编辑 | `/pv/relationEdit?type=create` | 搜索框用 `<label>` 定位，不是 `placeholder` |
| PV导入按钮位置 | **PV列表页** (`/pv/list`)，非导入页 | 按钮是 `.el-upload` 包装器，文本"PV导入" |
| 批次导入历史页 | `/pv/import` | 仅展示历史批次列表，无上传控件 |

---

## 2. 表单 placeholder 差异表

> 必查，不能假定不同页面相同。

| 字段 | 设备模型页 | 设备页 | 元件页 |
|:---|:---:|:---:|:---:|
| 名称 | 请输入模型名称 | 请输入设备名称 | 请输入元件名称 |
| 编码 | 请输入模型编码 | 请输入设备编码 | 请输入元件编码 |
| 描述 | 请输入模型描述 | 请输入描述信息 | 请输入描述信息 |
| 安装位置 | ❌ | ✅ | ✅ |
| 厂商 | ❌ | ✅ | ❌ **不存在** |
| IP/MAC | ❌ | ✅ | ❌ |
| 关联元件模型 | ✅ 按钮"添加元件模型" | ❌ | ❌ |
| 关联元件实例 | ❌ | ✅ 元件tab | ❌ |
| 关联PV | ❌ | ❌ | ✅ 物模型tab |
| 属性行 | ✅ 动态行 | ❌ | ❌ |

---

## 3. 三种下拉/选择组件的区分表（极易混淆）

| 特征 | el-select filterable | el-autocomplete | el-cascader（多选） |
|:---|:---|:---|:---|
| 下拉容器 | `.el-select-dropdown` | `.el-autocomplete__popper` | `.el-cascader__dropdown` |
| 选项元素 | `.el-select-dropdown__item` | `.el-autocomplete-suggestion__list li` | `.el-cascader-node` |
| 选项内有复选框 | 单选：无 / 多选：有 `.el-checkbox` | 无 | **有** `.el-checkbox` |
| 数据来源 | 本地过滤 | 远程异步回调 | 本地树形数据 |
| 典型场景 | 设备创建页选"设备模型"，标签状态下拉筛选 | 元件创建页选"元件模型"，PV绑定 | **设备编辑页选标签** |
| 交互方式 | `click(force=True)` 打开 + `.el-select-dropdown__item` + `force=True` 点选项 + Enter确认 | fill → 等2.5s → **dispatch_event('click')** 点选项（标准click可能不触发Vue @select） | `click(force=True)` 打开 → **点 `.el-cascader-node` 内的 `.el-checkbox`** → Escape关闭 |
| 选择确认方式 | 点选项自动选中 | 点选项自动选中 | **需点checkbox**，节点文本点击展开下一级 |

### 关键陷阱

- el-autocomplete 输入后必须**点击下拉选项**触发 Vue select 事件，仅键盘选择（ArrowDown+Enter）不会更新 v-model
- **el-cascader 多选必须点击 checkbox，不能点节点文本** — 节点文本点击会展开子菜单而非选择当前项
- el-select 的选项在 aria tree 中无 `role="option"`，必须用 `.el-select-dropdown__item` 定位
- el-autocomplete 的 popper 选项是 `<li>`，没有 `role='option'`，必须用 `.el-autocomplete__popper li`

---

## 4. 三种发布流程

| 发布类型 | 操作入口 | 对话框文案 | 等待 |
|:---|:---|:---|:---|
| 模型发布（元件/设备/段模型） | 版本详情页 → "发布版本" | "确认发布吗？" | 短 |
| 元件/设备实例发布 | 列表页**无"版本详情"按钮** — 实例无版本管理 | 无独立发布步骤 | N/A |

**关键区别（2026-06-09 修正）**：设备(controller/cDeviceList)和元件(element/eDeviceList)的列表页行内按钮为**注销/查看详情/编辑/删除**，不存在"版本详情"或"发布"按钮。实例创建后状态为`draft`（草稿），可正常执行CRUD操作。原子测试中实例的"场景4 发布"应改为DB状态验证而非UI发布操作。

**模型发布必须进版本详情页**，列表页行内"发布"按钮不生效。
**元件/设备实例不进详情页发布**，直接在列表页点行内按钮（若有）或不做发布。

### 模型列表页 vs 实例列表页的按钮差异

| 按钮 | 模型列表页（元件/设备/段模型） | 实例列表页（元件/设备） |
|:---|:---:|:---:|
| 版本详情 | ✅ | ❌ |
| 查看详情 | ❌ | ✅ |
| 编辑 | ✅ | ✅ |
| 删除 | ✅ | ✅（软删除 -> is_delete=1） |
| 发布（状态切换） | ❌ | ❌（非模型场景） |
| 注销 | ❌ | ✅（仅已发布设备） |

### 保存按钮文案差异

不同模块文案不同：`保存` / `确定` / `确认` / `提交`（SN模块）。检测逻辑必须包含全部四种。

### 发布后轮询检测条件

- 列表页默认显示草稿状态的记录，状态列为**空**，操作列含"发布"按钮
- 发布成功后，状态列显示为"发布"（即 `td` 中 `has_text="发布"` 表示**已发布状态**）
- 检测时查行内 `td` 的文本，而非查按钮文本

---

### 搜索框定位方式差异（常见陷阱）

该平台的搜索输入框存在多种不同的可访问名称来源，使用错误的定位方式会导致 `TimeoutError`：

| 来源 | 特征 | 正确定位方式 | 典型案例 |
|:---|:---|:---|:---|
| `placeholder` 属性 | 输入框内显示灰色提示文字 | `page.get_by_placeholder("提示文字")` | PV创建/编辑页表单 |
| `<label>` 关联元素 | 输入框上方有 `LabelText`，通过 `for` 属性关联 | `page.get_by_label("标签文字")` | PV列表页搜索框「PV名称」「设备名称」「IP」 |
| `aria-label` 属性 | 输入框有 `aria-label` HTML 属性 | `page.locator("[aria-label*='...']")` | 较少见 |

### 快速诊断

当 `page.get_by_placeholder()` 超时时，检查页面的 accessibility tree 中 textbox 的显示名称：
- `textbox "文字"` 且上方有 `LabelText "文字"` → 用 `get_by_label("文字")`
- `textbox "请输入文字"` → 用 `get_by_placeholder("请输入文字")`
- 用 `browser_console` 执行 `document.querySelector('input').placeholder` 可快速确认

---

## 6. 已确认平台 BUG

| BUG | 场景 | 现象 | 复现方式 |
|:---|:---|:---|:---|
| el-autocomplete下拉选项难定位 | 场景4 | 下拉选项选不上 → PV绑定失败 | 选项是`<li>`无`role='option'`，需用 `.el-autocomplete__popper li` 定位 |
| **PV绑定不持久化** | **场景4** | **el-autocomplete选值正确(输入框显示) → 保存成功 → 详情页PV字段为空** | **正确选择器+正确流程下必现。JS强制设Vue modelValue也无效。用户已确认是平台BUG** |

---

## 7. 关键表字段及删除顺序

### 关键表字段

| 表名 | 关键字段 | 注意 |
|:---|:---|:---|
| pv_data_info | pv_code, ip, port, pv_desc, **is_delete(boolean)** | is_delete=True 表示软删除，UI列表不显示。**描述列是 pv_desc 不是 description** |
| thing_model | id, thing_name, thing_code, thing_status (draft/release), **thing_desc** | **状态列是 thing_status 不是 status，描述列是 thing_desc 不是 description**（PostgreSQL保留字冲突） |
| thing_model_version | id, thing_model_id, thing_model_version, version_status | |
| device | id, device_name, device_code, device_status, sn, device_tags(JSON), properties(JSON), **is_delete** | 是软删除表，is_delete=1表示已删除但DB记录保留 |
| device_sn | id, sn, sn_state, is_delete, create_at, create_by, update_at, update_by, region_id | **表名是 device_sn 不是 sn** |
| tag | id, tag_name, tag_code, tag_type, tag_status (draft/release/archive), create_time | |

### SN 状态映射（DB → UI）

| DB sn_state | UI显示 | 含义 |
|:---|:---:|:---|
| pend_assign | 待分配 | 已创建，未分配设备 |
| wait_activate | 待激活 | 已分配设备，等待设备激活（测试环境无真实设备，到此为止） |
| effective | 生效 | 设备已激活，SN正式生效 |
| expired | 过期 | SN已过期 |

### 删除顺序（外键约束）⚠️ 顺序错误导致数据残留

> 错误的顺序会导致外键冲突、事务回滚、数据残留（rowcount 非零但实际未删除）。
> 必须按依赖关系删：先删引用表，再删被引用表。

```sql
-- ✅ 正确顺序（依赖表先删）：
DELETE FROM device WHERE device_name IN (...);         -- 先删设备（可能引用模型）
DELETE FROM thing_model_version WHERE thing_model_id IN (...);  -- 再删版本
DELETE FROM thing_model WHERE thing_name IN (...);              -- 再删模型
DELETE FROM pv_data_info WHERE pv_code='...';                   -- 最后删 PV
```

```sql
-- ❌ 错误（PV 在最前，设备在最后 — 模型被设备 FK 引用导致回滚）：
DELETE FROM pv_data_info ...;        -- 删了
DELETE FROM thing_model_version ...; -- 删了
DELETE FROM thing_model ...;         -- ❌ 被 device 外键阻塞 → 事务全部回滚
DELETE FROM device ...;              -- 这行永远不会执行
```

### ⚠️ SN 清理特殊步骤（两步走）

清理 SN 测试数据时，**不能只删 device_sn 表**，还必须将 device 表中对应设备的 sn 字段置空：

```sql
DELETE FROM device_sn WHERE sn LIKE 'iot_auto_test%';
UPDATE device SET sn='' WHERE device_name LIKE 'iot_auto_test%';
```

否则相同 SN 再次绑定时会处于"已绑定"状态，无法重新分配。
**SN全生命周期脚本执行前必须先做此清理。**

### ⚠️ device_tags 存的是标签 ID，非标签名称

设备编辑页关联标签后，`device.device_tags` 字段存储的是**标签表的主键 ID**（逗号分隔的 JSON 数组），不是标签名称。

```python
# DB 验证时需通过关联查询获取标签名
def db_get_device_tag_names(device_name):
    rows = db_query("""
        SELECT t.tag_name FROM device d
        JOIN tag t ON t.id = ANY(
            SELECT unnest(string_to_array(d.device_tags, ','))::int
        )
        WHERE d.device_name = %s
    """, (device_name,))
    return [r[0] for r in rows]
```

**影响：**
- 编写 DB 断言时，必须做表关联查询（device.device_tags → tag.id），不能直接搜索名称
- el-cascader checkbox 选中后，input 区显示"n个项目"，不显示标签名列表
- 编辑页二次确认验证，通过 body 文本检查标签名（标签名会被渲染）

---

## 8. 平台配置层

### 统一配置层（config.py）

| 变量 | 默认值 | 说明 |
|:---|:---|:---|
| `BASE_URL` | `http://10.30.25.183:28080/jwsiot` | 平台 URL |
| `DB_HOST/PORT/NAME/USER/PASSWORD` | 开发环境值 | 数据库连接 |
| `RUN_ID` | 时间戳 (`%m%d%H%M`) | 测试数据隔离前缀 |
| `TIMEOUT_SHORT/MEDIUM/LONG` | 5/15/60 秒 | 等待超时 |
| `PYTHON` | `sys.executable` | Python 解释器路径 |
| `PLATFORM_ID` | `iot` | 平台标识（环境变量 `IOT_PLATFORM` 覆盖） |
| `REPORT_DIR` | `{WORK_DIR}/docs/output/{PLATFORM_ID}` | 报告输出目录（环境变量 `IOT_REPORT_DIR` 覆盖） |

### 测试数据命名规范

```python
PLATFORM_ID = "iot"
DATA_PREFIX = f"{PLATFORM_ID}_auto_test"

TAG_NAME = f"{DATA_PREFIX}-温度标签"
TAG_CODE = f"{DATA_PREFIX}-tag-temp"
DEVICE_NAME = f"{DATA_PREFIX}-设备v1"
PV_NAME = f"{DATA_PREFIX}-PV"
```

### 数据命名实际示例

```
PV:         IP-SAFE-RFQ-CR:MDP01:RunFreq_Rd
元件模型:    自动化测试-元件模型 (webwright-elementModel)
元件:       自动化测试-元件v2 (webwright-element-v2)
设备模型:    自动化测试-设备模型 (webwright-device-model)
设备:       自动化测试-设备v1 (webwright-device-001)
```

---

## 9. 已知前端错误检测关键词（IoT 平台特有）

IoT 平台的 NPE 报错 `Cannot invoke "ThingModelVersionPageVo.getId()" because "thingModelVersion" is null` 不是标准 `el-message` 组件，而是页面内嵌的自定义红色横幅，必须通过 **body 文本关键词匹配**捕获：

```python
backend_keywords = [
    "Cannot invoke", "NullPointerException", "exception",
    "error", "失败", "系统繁忙", "请稍后重试",
    "服务端异常", "500", "404", "操作失败", "保存失败",
    "创建失败", "is null", "cannot be null"
]
```

---

## 10. 平台数据依赖链

从 SKILL.md 端到端9场景推导的数据流向：

```
PV 创建 (场景1)
  → 元件模型创建 (场景2)
    → 发布元件模型 (场景3)
      → 元件创建 + 关联PV (场景4)
        → 发布元件 (场景5)
          → 设备模型创建 + 关联元件模型 (场景6)
            → 发布设备模型 (场景7)
              → 设备创建 + 关联元件 (场景8)
                → 发布设备 (场景9)
```

**依赖链简化（消费脚本前置检查参考）：**
```
PV → 元件模型 → 元件 → 设备模型 → 设备
```
