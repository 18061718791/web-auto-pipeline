# 原子测试脚本构建规范

> 源自 `pv_atomic_test.py` 的实践验证（2026-06-08）

## 核心原则

### 1. 自包含

每个菜单维度的原子脚本完全独立：
- **自造数据**：使用 `AUTO_{MENU}_{TIMESTAMP}` 前缀创建测试数据
- **自清理**：脚本开头检查+清理旧数据，结尾清理本次创建的数据
- **不依赖**：不依赖任何端到端脚本或其他原子脚本的数据

### 2. 数据隔离

| 类型 | 数据前缀 | 清理策略 |
|:---|:---|:---|
| 原子脚本数据 | `AUTO_菜单_{时间戳}_*` | 脚本开头按双条件清旧 + 场景内用完即删 |
| 端到端脚本数据 | 独立前缀 | 按各自规范清理 |
| 用户 mock 数据 | 无前缀 | 只读操作（编辑/连通性/搜索），不删除 |

### 3. 清理规范

#### 脚本开头（场景1 第一步）—— 双条件查重 + 清理

```python
# 双条件检查：PV名称+IP，确保精确匹配唯一记录
existing = find_pv_by_code_ip(PV_CODE, PV_IP)
if existing:
    delete_pv_by_code(PV_CODE)  # 硬删除，不留软删除残留
```

> **为什么用双条件？** 仅用名称匹配可能命中其他用户的同名数据。名称+IP 基本可唯一确定一条记录。

#### 脚本结尾（最终场景）

```python
# 按前缀匹配删自己创建的数据
delete_pv_by_prefix("AUTO_PV_0608172311")
```

#### 「用完即删」模式

对于中间产生的数据（如导入测试的 PV、删除测试用的草稿 PV），在验证通过后立即删除，而不是等到脚本结尾统一清理。

#### 软删除验证模式（关键陷阱）

UI 删除操作通常触发 **软删除**（`is_delete=True`），记录仍在 DB 中。使用 `find_pv_by_code()` 仍能查到，导致断言误判。

**错误做法：**
```python
report.assertion("DB: PV已删除", find_pv_by_code(code) is None, "")
# → 失败！软删除后记录仍在 DB 中，find_pv_by_code 仍返回数据
```

**正确做法：**
```python
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT is_delete FROM pv_data_info WHERE pv_code=%s", (code,))
row = cur.fetchone()
cur.close(); conn.close()
report.assertion("DB: PV已软删除", row is not None and row[0], f"is_delete={row[0]}")
```

> **注意**：`find_pv_by_code` 类的函数不应在内部处理软删除（如自动恢复 is_delete=False）。删除验证应直接查 `is_delete` 字段，避免 `find_*` 函数干扰断言结果。

## 标准6场景结构

```text
场景1: 清理旧数据 → 新增主测试数据
场景2: 搜索验证（精确搜索 + 列表确认）
场景3: 功能测试（连通性测试等按钮操作 / 编辑 → 二次确认）
场景4: 编辑 → DB验证 → 二次进入编辑页UI确认  /  状态验证（实例无版本管理时）
场景5: 删除 → 列表验证 → DB软删除验证  /  查看详情验证
场景6: 批量导入 / 详情验证 / 删除
```

## 实例脚本 vs 模型脚本的差异（2026-06-09 补充）

| 方面 | 模型脚本（元件/设备/段模型） | 实例脚本（元件/设备/SN） |
|:---|:---|:---|
| **场景4 发布** | 使用"版本详情"→"发布版本"UI操作 | 设备/元件列表无"版本详情"按钮，改为DB状态验证：`db_check(name) → status in ('draft','release')` |
| **场景6 删除** | 先清理版本记录(`DELETE thing_model_version`)，再UI删除，断言`find_thing_model() is None`（物理删除） | UI删除后是软删除（`is_delete=1`），断言用`db_check_deleted()`函数查`is_delete`标志 |
| **DB函数** | `find_thing_model()` 查 thing_model 表 | `db_check()` 查 device/device_sn 表 |
| **表单定位** | `page.get_by_label("模型名称")`（有label） | `page.get_by_placeholder("请输入设备名称")`（无label） |
| **额外表单字段** | 无IP/MAC/厂商 | 设备有IP/MAC/型号/厂商必填字段 |

### `db_check_deleted` 标准实现

```python
def db_check_deleted(name):
    """验证软删除：查 is_delete 标志位"""
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT is_delete FROM device WHERE device_name=%s", (name,))
    row = cur.fetchone(); cur.close(); conn.close()
    return row[0] == 1 if row else True  # 记录不存在也算已删除
```

### 实例场景4（状态验证）标准实现

```python
# 场景4: 状态验证（实例无发布按钮时替代方案）
if start_scene <= 4:
    report.scene_start("场景4", f"状态验证: {INSTANCE_NAME}")
    ensure_on_page(page, LIST_URL)
    page.get_by_placeholder("请输入设备名称").fill(INSTANCE_NAME)
    page.get_by_role("button", name="搜索").click(); time.sleep(2)
    row = page.locator("tr").filter(has_text=INSTANCE_NAME)
    if row.count() > 0:
        vs = db_check(INSTANCE_NAME)
        status_ok = vs and vs[2] in ('draft', 'release', 'published', 'online', 'offline')
        report.assertion("DB: 状态有效", status_ok, f"status={vs[2] if vs else 'NULL'}")
    report.step("状态验证", screenshot=page)
    report.scene_end(True)
```

## 通用交互模式

| 操作 | 正确方式 | 易错点 |
|:---|:---|:---|
| 列表页搜索 | `page.get_by_label("字段名").fill(value)` | 误用 `get_by_placeholder` |
| 新增/编辑表单 | `page.get_by_placeholder("提示文本").fill(value)` | 误用 `get_by_label` |
| 表格行定位 | `page.locator("table[class] >> nth=1 tr")` 或 `table[class] tr[class]` | 两个 `<table>` 是兄弟元素，非嵌套；`table table tr` 不生效 |
| 操作按钮（编辑/删除/连通测试） | `page.get_by_role("button", name="按钮名").first` | 按钮文本要精确匹配 |
| 对话框关闭 | `page.get_by_role("button", name=re.compile(r"确[认定]")).click()` | 不关闭对话框会阻塞后续所有点击操作 |
| 导入结果弹窗 | 导入成功后有"导入结果"模态框，必须关 | `page.locator("[role='dialog']").filter(has_text="导入结果")` → 点确定按钮 |
| API监听 | `page.on("response", handler)` | 必须在页面跳转前注册 |
| 导入API超时 | 后端处理Excel可能耗时30-90秒 | 轮询超时应设为90秒，`for i in range(90)` |
| 文件上传 | `expect_file_chooser()` + `.click(force=True)` + `set_files()` | 点击 `.el-upload` 包装器，非内部 button |
