# Web Auto Pipeline — 运营详细指南

> SKILL.md 的详细补充。核心规则速查见 SKILL.md，完整规则见 `references/core-principles.md`。

---

## 目录

1. [定位方式模式详解](#1-定位方式模式详解)
2. [断言增强与检查清单](#2-断言增强与检查清单)
3. [静默保存失败诊断](#3-静默保存失败诊断)
4. [文件上传与导入](#4-文件上传与导入)
5. [数据清理铁律](#5-数据清理铁律)
6. [HealingOrchestrator 完整文档](#6-healingorchestrator-完整文档)
7. [运行时依赖自愈](#7-运行时依赖自愈)
8. [用户输入模板规范](#8-用户输入模板规范)
9. [报告命名标准与清理机制](#9-报告命名标准与清理机制)
10. [目录结构规范](#10-目录结构规范)
11. [工作方式纪律](#11-工作方式纪律)
12. [常用工具陷阱](#12-常用工具陷阱)
13. [脚本标准模板](#13-脚本标准模板)
14. [Runner 使用速查](#14-runner-使用速查)
15. [报告通知与 delegate_task](#15-报告通知与-delegatetask)
16. [添加新平台步骤](#16-添加新平台步骤)

---

## 1. 定位方式模式详解

### 1.1 表单字段定位：Model 页 vs Instance 页

IoT 平台的 Element Plus 表单字段有两种定位模式，取决于页面是「模型定义」还是「实例管理」：

| 页面类型 | 正确定位方式 | 示例 | 原因 |
|:---|:---|:---|:---|
| **模型新增/编辑页** | `page.get_by_label("字段名")` | `get_by_label("模型名称")` | 表单有 `<label for="el-id-xx">` |
| **实例新增/编辑页** | `page.get_by_placeholder("请输入XXX")` | `get_by_placeholder("请输入元件名称")` | 表单无 label，placeholder 直接暴露文本 |
| **列表页搜索栏** | 逐页确认 | 部分用 label 部分用 placeholder | 不统一 |

### 1.2 FIELD_SCAN：字段定位诊断代码

```python
inputs = page.locator('input:visible, textarea:visible, .el-input__inner:visible').all()
for inp in inputs:
    pid = inp.get_attribute('id') or ''
    ph = inp.get_attribute('placeholder') or ''
    label_el = page.locator(f'label[for="{pid}"]').first
    label_text = label_el.inner_text().strip() if label_el.count() > 0 else ''
    aria = inp.get_attribute('aria-label') or ''
    print(f"  placeholder='{ph}' label='{label_text}' aria='{aria}'")
```

label 有值 → `get_by_label()`；label 无值但 placeholder 有值 → `get_by_placeholder()`

### 1.3 常见陷阱

| 陷阱 | 表现 | 正确做法 |
|:---|:---|:---|
| label 带星号 `* 模型名称` | `get_by_label("* 模型名称")` 失败 | 星号是 CSS `::before`，label 实际是 `模型名称` |
| 实例页用 label | `get_by_label("元件名称")` 超时 | 实例页用 `get_by_placeholder("请输入元件名称")` |
| `page.locator("input").first` 定到 el-select readonly 输入框 | `fill()` 超时 | 用 `get_by_label()` 或 `get_by_role("textbox", name=...)` |
| 同一页面 label 和 placeholder 混合 | 部分字段识别错误 | 一律用 FIELD_SCAN 确认后再写 |

### 1.4 表格行选择器

| 结构 | 正确选择器 |
|:---|:---|
| 标准嵌套 `<table>` | `tr.el-table__row` 或 `table tr` |
| 兄弟表格（两个 `<table>` 并列） | `table[class] >> nth=1 tr` 或 `table[class] tr[class]` |

> `table table tr` 仅在嵌套时有效。兄弟表格用 `browser_snapshot` 确认结构后选择正确选择器。

---

## 2. 断言增强与检查清单

### 断言覆盖检查清单

- [ ] **下拉选择**：选项出现才点击 → else 分支必须有 `report.assertion(..., False, "选项未出现")`
- [ ] **tab切换**：`tab.count() > 0` 的 false 分支必须有断言
- [ ] **保存后**：`check_page_errors` + UI 列表 + DB + **关联关系验证**
- [ ] **发布后**：UI 状态列 + DB 状态字段
- [ ] **搜索后**：搜索结果行数 > 0

### "场景通过"的定义

`scene_end(True)` 的充要条件：该场景内所有 `report.assertion` 均为 True + `check_page_errors` 无错误 + 无未捕获异常。如果某子操作因选项不存在而静默跳过，即使后续保存成功，**该场景也必须标记为失败**。

### DB 断言反模式：猜类型不查表

写 SQL 断言前，必须先查 `information_schema.columns` 确认数据类型。猜错类型会导致断言永远静默失败。

**反例**：`device_tags.is_delete` 是 `boolean` 类型，断言写成 `str(True) == "1"` → `"True" == "1"` → 永不通过。

**正确做法**：
```python
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='device_tags' AND column_name='is_delete'")
# data_type='boolean' → 用 db_row[0] is True
# data_type='integer'  → 用 db_row[0] == 1
```

### UI 文本断言反模式

用 `body.inner_text()` 做关键词匹配断言前，必须用 `browser_snapshot` 确认页面实际渲染的文本。版本详情页的状态可能是徽章/图标/缩写，不一定是预期文字。

**正确做法**：先截图保留现场，再根据实际渲染文本写断言。对不确定的文本，只截图不做文本断言。

### 断言增强：语义内容检查

`assert_ui()` 仅检查非空，无法验证语义。对状态列、版本信息等关键字段应使用显式断言：

```python
ver_cell = page.locator("tr").filter(has_text=name).locator("td").nth(4).first
if ver_cell.count() > 0:
    ver_text = ver_cell.text_content(timeout=5000) or ""
    is_published = "发布:1" in ver_text
    report.assertion("UI: 版本信息含发布标记", is_published, ver_text[:80])
else:
    report.assertion("UI: 版本信息含发布标记", False, "未找到版本信息列")
```

列索引需预先用 `browser` 工具确认（参见 `references/fragility-audit-checklist.md`）。

### el-select 下拉选项等待优化

```python
# ❌ 脆弱：固定sleep + count检查
rw_sel.click()
time.sleep(0.5)
ro = page.locator("[role='option']").filter(has_text="读写").first
if ro.count() > 0: ro.click()

# ✅ 健壮：显式等待选项可见
rw_sel.click()
rw_opt = page.locator("[role='option']").filter(has_text="读写").first
rw_opt.wait_for(state="visible", timeout=3000)
rw_opt.click()
```

---

## 3. 静默保存失败诊断

当保存按钮 `click()` 后出现无网络请求、无错误提示、无表单验证错误、DB 无数据时，按以下顺序排查：

1. **el-autocomplete popper 未关闭**（最常见）— `page.keyboard.press("Escape")` 确保关闭
2. **按钮 disabled** — 检查 `.el-form-item__error` 确认根因
3. **表单验证错误** — 保存后检查 `.el-form-item__error` 文本（IP/MAC格式校验）
4. **网络请求未发出** — `performance.getEntriesByType('resource').length` 对比前后
5. **JS Console 错误** — `performance.getEntriesByType('resource').filter(e => e.responseStatus >= 400)`
6. **API 确认** — `page.on("response")` 监听保存 API 返回 200 但 DB 无数据 → 后端唯一约束冲突
7. **Playwright click() auto-wait 阻塞** — 用 tic() 时间标记定位瓶颈：

```python
_T_LAST = time.time()
def tic(label):
    now = time.time()
    elapsed = now - _T_LAST
    print(f"  ⏱  {label}: {elapsed:.2f}s")
    _T_LAST = now

tic_reset()
page.goto(url)
tic("goto")
page.get_by_role("button", name="保存").click()
tic("click(保存)")
```

### 系统性解决方案：`verify_save()` → `h.save_and_verify()`

**推荐方案（新脚本）**：使用 `h.save_and_verify()`（位于 `core/healer/save_healer.py`），提供：
- 保存前自动关闭 el-autocomplete popper
- 检查 `.el-form-item__error` 表单验证错误
- API 响应监听（匹配 save/add/insert/edit/update）
- URL 变化检测 + 成功 toast 检测 + DB 直查轮询
- 15 秒超时，失败自动重试 2 次
- IP/MAC 格式校验错误自动修正

```python
# 新模式：h.save_and_verify() — 自愈 + 三重确认
ok = h.save_and_verify("保存元件模型", db_verify_fn=find_thing_model, db_args=[NAME])
report.step("保存", screenshot=page)
if not ok:
    report.scene_end(False)
    return report
has_err = check_page_errors(page, report)
if has_err:
    report.scene_end(False)
    return report
```

**旧方案（兼容）**：
```python
page.get_by_role("button", name="保存").click()
save_ok = verify_save(page, report, "步骤名", db_check_fn, [arg1, arg2],
                      expected_url_segment="List")
if not save_ok:
    report.scene_end(False)
    return report
```

**check_page_errors 调用模式**：`check_page_errors()` 记录失败后必须检查返回值并提前返回：
```python
has_err = check_page_errors(page, report)
if has_err:
    report.scene_end(False)
    return report
```

### check_page_errors 增强轮询

统一使用 6 次 x 3 秒轮询（原 4x2），给后端更长的处理窗口。

---

## 4. 文件上传与导入

### el-upload 标准方案

```python
upload_wrapper = page.locator(".el-upload").filter(has_text="导入").first
with page.expect_file_chooser() as fc_info:
    upload_wrapper.click(force=True)
    time.sleep(2)
file_chooser = fc_info.value
file_chooser.set_files(r"E:\path\to\template.xlsx")
```

### 用户偏好

此用户不接受 `expect_file_chooser` 后台拦截，要求 OS 对话框真实弹出。CI/自动化回归用 `expect_file_chooser`；需要演示/调试时用「手动暂停模式」。详见 `references/file-upload-technique.md`。

**关键规则**：
1. 点击 `.el-upload` 包装器而非内部 button
2. 降级方案：`page.locator("input.el-upload__input").set_input_files(path)` 直接操作隐藏 input
3. 文件格式要求：sheet 名和列名必须与后端接口匹配
4. 测试数据唯一性：避免重复导入导致 `successCount=0`

### 导入结果验证（三层策略）

| 层级 | 方法 | 可靠性 |
|:---|:---|:---:|
| **API** | `page.on("response")` 监听导入接口解析 `successCount` | ★★★ |
| **DB** | 导入前后对比记录数 | ★★★ |
| **UI** | 刷新列表后搜索导入记录 | ★★ |

推荐：API + DB 双重验证，UI 作为补充。

### 测试模板生成

```python
import openpyxl
from datetime import datetime

ts = datetime.now().strftime("%H%M%S")
test_pv_name = f"AUTO_IMPORT_{ts}_PV_001"

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "pv数据导入"
ws.append(("PV名称", "PV描述"))
ws.append((test_pv_name, "测试描述"))
wb.save("模板_测试.xlsx")
```

### 已知陷阱

- `expect_file_chooser` timeout 30s — headless 模式偶发，降级到 `set_input_files()`
- API 响应延迟 — 导入接口需 20-30 秒处理，轮询超时应设为 90 秒
- 导入结果弹窗必须手动关闭 — 否则阻塞后续所有操作
- 重复导入 — 模板中已有 PV 名会失败，务必使用纯净模板或唯一测试名

---

## 5. 数据清理铁律

### 两条 MUST 级原则

1. **命名前缀**：所有测试数据必须有 `AUTO_` 前缀
2. **强制清理**：脚本跑完后（无论成功还是失败），必须清理所有自动化产生的数据，包括 UI 交互触发后端自动创建的侧效应数据

### 后端侧效应数据清理模式

当 UI 操作触发后端自动创建记录，且后端无幂等判断时，使用**基线保留法**：

```python
# 保留每个名称最早的一条基线数据，删除后代重复
cur.execute("""
    DELETE FROM thing_model WHERE thing_type='SEGMENT'
    AND id NOT IN (
        SELECT MIN(id) FROM thing_model
        WHERE thing_type='SEGMENT' GROUP BY thing_name
    )
""")
seg_n = cur.rowcount
if seg_n:
    cur.execute("DELETE FROM thing_model_version WHERE thing_model_id NOT IN (SELECT id FROM thing_model)")
```

**适用条件**：侧效应记录名称固定，多次运行后每个名称存在多条。
**不适用**：名称不固定的侧效应记录，改用时间窗口清理。

### 数据清理反模式：时间戳前缀 + 不清理旧数据

原子脚本使用 `AUTO_{MODULE}_{TIMESTAMP}` 前缀，每次运行创建不同名字。仅按当前名字清理不会触及上一次运行的数据。

**正例：在 finally 块追加 LIKE 模式清理**：
```python
finally:
    browser.close()
    try:
        c = get_db_connection(); cu = c.cursor()
        cu.execute("DELETE FROM thing_model WHERE thing_name LIKE 'AUTO_MODULE_%'")
        cu.execute("DELETE FROM thing_model_version WHERE thing_model_id IN (SELECT id FROM thing_model WHERE thing_name LIKE 'AUTO_MODULE_%')")
        c.commit(); cu.close(); c.close()
    except: pass
```

### 清理必须按模块匹配正确表

不同模块的测试数据存于不同表。写 finally 清理前，先查 `information_schema.columns` 确认数据存在哪个表。

**覆盖表**：`thing_model`、`thing_model_version`、`thing_model_relation_ship`、`device`、`device_sn`、`device_tags`、`pv_data_info`、`pv_data_relation`、`facility_info`。删除顺序：先删版本/关联表，再删主表。

---

## 6. HealingOrchestrator 完整文档

`core/healer/` 提供 5 个运行时自愈模块 + 1 个调度器，替代裸 Playwright 操作。

### 快速集成（3 行代码）

```python
from core.healer import HealingOrchestrator
h = HealingOrchestrator(page, report, db_connection_fn=get_db_connection)

h.fill("请输入PV名称", "test-PV")                          # 自动 7 级降级
h.autocomplete_select("请输入模型名称搜索", "model-A")      # 3 级降级
h.save_and_verify("保存PV",                                 # API/URL/toast/DB 四路检测
    db_verify_fn=find_pv_by_code, db_args=[PV_CODE],
    expected_url="pv/list")
h.assert_db("DB: 已软删除", "device_tags", "is_delete", row[0], True)
h.heal_between_scenes(expected_url=PV_LIST_URL, scene_name="场景2")
h.print_summary()
```

### 设计原则

| 原则 | 说明 |
|:---|:---|
| **可独立使用** | 每个 Healer 可单独 import，不强制用 Orchestrator |
| **结果可见** | 自愈事件自动写入 `report.assertion`，不隐瞒失败 |
| **安全降级** | 全部降级失败返回 `False`，不抛异常，不影响流程 |
| **渐进集成** | 脚本可逐步引入，不改动即可继续使用原有断言模式 |

详见 `references/self-healing-v2-design.md`。已集成脚本：13 个完成基础集成，其中 3 个启用了高级 Healer。

### 批量集成陷阱

| 陷阱 | 表现 | 正确做法 |
|:---|:---|:---|
| Viewport 创建模式差异 | 部分 `page.set_viewport_size()`，部分 `browser.new_context(viewport=...)` | `h = HealingOrchestrator(...)` 必须在 `page = ctx.new_page()` **之后** |
| try-except 缩进破坏 | 在 try/except 间插入代码时缩进错乱 | `h.print_summary()` 放在 **try 块内部** |
| get_by_label fill 不应替换 | 批量替换把搜索栏 label fill 也转了 | 只替换表单字段的 placeholder fill |
| E2E 大脚本谨慎操作 | `device_management_test.py` 9 场景模式复杂 | 优先只添加 import+init，逐步替换关键操作 |

---

## 7. 运行时依赖自愈

端到端脚本依赖的外部数据缺失时，应**自动创建缺失数据**而非直接退出。

### 标准实现模板

```python
from config import get_db_connection

def create_entity_if_missing(name, **fields):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM table WHERE code=%s", (name,))
        row = cur.fetchone()
        if row:
            cur.close(); conn.close()
            return row[0]

        vals = ", ".join(["%s"] * len(fields))
        placeholders = ", ".join(fields.keys())
        cur.execute(
            f"INSERT INTO table ({placeholders}) VALUES ({vals}) RETURNING id",
            tuple(fields.values())
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        log(f"  🔧 自愈: 已创建 '{name}' (id={new_id})")
        cur.close(); conn.close()
        return new_id
    except Exception as e:
        conn.rollback()
        cur.close(); conn.close()
        log(f"  ❌ 自愈失败: {e}")
        return None
```

### 规则

| 规则 | 说明 |
|:---|:---|
| **必须在 `run()` 中调用** | 场景执行前检查，失败时 `sys.exit(1)` |
| **只创建纯数据** | 不创建依赖于其他脚本完整业务流的数据 |
| **DB 列名 + 类型必须用 information_schema 确认** | 猜错类型导致断言永远失败 |
| **不覆盖已有数据** | 如实体缺少关键字段，执行 UPDATE 修复而非跳过 |

---

## 8. 用户输入模板规范

### 标准模板位置

- `templates/user-input-template.md` — 用户填写此文件即可启动全流程
- `references/example-device-atomic.md` — 完整参考示例

### 模板 4 部分

| 部分 | 内容 | 工具能做什么 |
|:---|:---|:---|
| 一：平台连接 | URL、账号密码、前端框架、组件库 | 连接、登录、Phase 0 探索 |
| 二：数据库 | 类型、主机、库名、账号密码 | information_schema 自动检测 |
| 三：场景描述 | 自然语言操作步骤 + 每步校验 | 解析操作、生成脚本、执行、断言 |
| 四：已知数据（可选） | 存量 mock 数据清单 | 优先复用而非自建 |

### 字段约束标注语法

| 标注 | 含义 |
|:---|:---|
| `（必填）` | 字段不能为空，保存后检测表单验证错误 |
| `（最长N字符）` | 长度上限，超长自动截断 |
| `（不可重复）` | 唯一约束，冲突时自动追加时间戳后缀 |
| `（0-255格式）` | IP 地址格式校验 |
| `（下划线连接大写）` | MAC 地址格式校验 |
| `（从下拉搜索选择已发布的XXX）` | el-autocomplete/el-select 关联搜索+选择 |
| `注意：已发布不可编辑/删除` | 特定状态下按钮不可用 |
| `注意：软删除` | DB 断言查 is_delete 标志而非查记录是否存在 |
| `预期失败：XXX` | 断言错误提示出现而非等待超时 |
| `依赖声明：本脚本依赖「XXX」已发布` | 前置数据依赖，缺失则自动创建 |

---

## 9. 报告命名标准与清理机制

### 报告命名铁律

- **必须使用** `{script_id}_测试报告_{ts}.html` — 禁止裸 `测试报告_{ts}.html`
- JSON 报告已于 2026-06-10 弃用 — `JsonRenderer.save()` 为 no-op
- script_id 使用英文小写+下划线，一旦确定不可随意更改

### 报告清理策略

`run.py` / `core/runner.py` 启动时自动调用 `cleanup_old_reports()`：

| 条件 | 动作 |
|:---|:---|
| `e2e/{module-subdir}/` 或 `atomic/{module-subdir}/` 中报告 > 7 天 | 移入 `_archive/` |
| `_archive/` 中报告 > 30 天 | 自动删除 |
| 根级全量测试报告 | 永久保留 |

环境变量控制：`IOT_REPORT_RETENTION_DAYS=14`、`IOT_ARCHIVE_MAX_DAYS=60`

### 输出目录规范

| 内容 | 位置 |
|:---|:---|
| 端到端测试报告 | `platforms/{id}/docs/reports/e2e/{module-subdir}/` |
| 原子功能测试报告 | `platforms/{id}/docs/reports/atomic/{module-subdir}/` |
| 聚合报告 | `platforms/{id}/docs/reports/全量测试报告_{ts}.html` |
| 操作手册 | `platforms/{id}/docs/manuals/` |
| 录制脚本 | `platforms/{id}/recordings/` |
| 全局媒体 | `docs/media/` |
| 探索产出 | `platforms/{id}/manifests/` + `docs/output/{id}/explore_{ts}/` |

### 添加新脚本时的 checklist

- [ ] 确定类型：原子功能还是端到端场景
- [ ] 设置 script_id（`platforms/{id}/config.py` 的 `SCRIPTS` 或 `ATOMIC_SCRIPTS` 数组）
- [ ] 添加项目根目录到 `sys.path`
- [ ] import 中加入 `get_script_report_dir`
- [ ] **`TestReport("标题")` 必须传 `output_dir=get_script_report_dir('e2e|atomic', 'script_id')`**
- [ ] `generate_html(filename=f"{script_id}_测试报告_{_ts}.html")`
- [ ] 注册到 `platforms/{id}/config.py` 的脚本数组中

---

## 10. 目录结构规范

### 当前目录结构

```
项目根目录/
├── run.py               ← 统一入口 (python run.py --platform iot --headless)
├── config.py            ← 平台路由器（动态转发到 platforms.{PLATFORM}.config）
├── .env                 ← 全局配置
├── _cleanup.py          ← AUTO_ 前缀测试数据批量清理工具
├── core/                ← 通用核心代码（所有平台共享）
│   ├── runner.py        ← 调度器
│   ├── report_helper.py
│   ├── report_renderer.py  ← HTML 报告渲染器
│   ├── json_renderer.py    ← JSON 报告（已弃用，save() 为 no-op）
│   ├── manifest_generator.py
│   ├── component_strategies/  ← 组件交互策略
│   ├── healer/                ← 运行时自愈模块
│   └── templates/             ← J2 模板
└── platforms/           ← 各平台独立上下文
    ├── iot/             ← IoT 物联管理平台
    │   ├── config.py
    │   ├── scripts/e2e/ + scripts/atomic/
    │   ├── manifests/
    │   └── docs/reports/
    └── tckz/            ← 总控平台（开发中）
```

### 核心规范

| 维度 | 规范 |
|:---|:---|
| **根目录** | 只允许 `run.py`、`config.py`、`.env`、`requirements.txt` |
| **核心代码** | 全部在 `core/` 下，以包形式组织 |
| **平台代码** | 全部在 `platforms/{id}/` 下，按平台维度隔离 |
| **脚本分类** | `e2e/` = 跨模块业务流，`atomic/` = 单菜单基础功能操作 |

### 配置路由机制

根 `config.py` 是动态路由器：`from config import BASE_URL` 自动路由到当前平台。设 `PLATFORM=tckz` 即切换。

### Python import 路径

所有脚本需确保项目根目录在 `sys.path` 中。独立运行时每条脚本顶部添加：

```python
import sys, os
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
```

---

## 11. 工作方式纪律

1. **未知领域先调研再执行** — 当用户指出某技术方向存在成熟方案而你用了简单绕路方案时，先系统性列出所有可能方案、逐一验证、再给出推荐。不用"行业标准"为借口不深入。
2. **结论先说，细节后补** — 优先给出 A/B 选择或是否判断，追问再展开。
3. **调试脚本后清理** — `*_debug.py`、`*_test.png` 等临时文件验证通过后删除。
4. **破坏性文件操作必须预览征求同意** — 涉及 rm -rf、mv、批量删除时先列出受影响文件。
5. **先定义结构再执行** — 涉及目录结构变更时，先与用户确认结构定义。
6. **修改 reference 文件后必须维护交叉引用一致性** — 同步更新 SKILL.md 索引和规则一致性。
7. **决策场景只给最优方案，不给选择题** — 直接给出一个专业推荐方案并附理由。
8. **一次性执行完整计划，不递进式询问** — 制定完整执行计划后一次性完成。
9. **不提交需讨论的 todo** — 要么直接决策执行，要么明确标记"暂停/需确认"搁置。

### 交叉引用一致性检查清单

- [ ] SKILL.md 文件索引更新：新增文件必须加入索引表
- [ ] SKILL.md 规则一致性检查：新文件规则不能与 MUST 级规则冲突
- [ ] 跨文件函数签名一致性检查：`log()`、`check_page_errors()` 等签名必须完全一致
- [ ] 幽灵文件标记：历史记录文件开头添加 `> **⚠️ 已过时**` 标记 + 替代路径
- [ ] Ghost 文件清理：参见 `references/ghost-file-cleanup-methodology.md`

---

## 12. 常用工具陷阱

### ⚠️ Python 条件表达式优先级陷阱

`a + b if cond else c` 实际解析为 `(a + b) if cond else c`。当 cond=False 时整个 a+b 被丢弃。

```python
# ❌ 陷阱
result = a + b + content.split('---', 1)[-1] if '---' in content else content
# 如果 content 不包含 '---'，a+b 被完全丢弃！

# ✅ 正确：用括号明确条件范围
result = a + b + (content.split('---', 1)[-1] if '---' in content else content)
```

**核心原则**：混合 `+` 和 `if/else` 的表达式里，**始终用括号包围条件部分**。

**合并操作的标准安全模式**：
```python
# 方案 A：用 += 分步拼接（最清晰）
result = target_file
result += "\n\n---\n\n## 附录\n\n"
result += source_content
open(path, 'w').write(result)

# 方案 B：如果必须单表达式，加括号
result = target_file + "\n\n---\n\n" + (source_content if cond else fallback)
```

### ⚠️ read_file + write_file 截断与格式污染

`read_file` 默认限制 500 行。用 `read_file()` + `write_file()` 组合存在两个问题：
1. **截断**：源文件超过 500 行时后半段数据永久丢失
2. **格式污染**：行号前缀 `NN|` 被写入文件

**解决方案**：始终指定 `limit=2000`，或优先用 `patch` 工具和独立 Python 脚本做变换。

### ⚠️ DB 字段类型验证

`SELECT column_name FROM information_schema.columns` 只能确认「列存在」，不能确认「类型」。SQL 断言中类型假设错误会导致断言永远静默失败。

**完整查询模板**：
```python
conn = get_db_connection()
cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = %s
    ORDER BY ordinal_position
""", (table_name,))
for col in cur.fetchall():
    print(f"  {col[0]:25s} {col[1]:15s} nullable={col[2]:5s} default={col[3] or '-'}")
cur.close(); conn.close()
```

### ⚠️ terminal `python -c` 反斜杠转义陷阱（Windows）

git-bash 的 `terminal` 运行 `python -c "..."` 时 shell 会先处理反斜杠。**不要用 `python -c` + 内联代码做文件修改**，改用 `write_file` 写独立 `.py` 脚本再执行。

### ⚠️ sed 误伤

用 `sed` 做 Python import/函数调用的全局替换极易误伤。**始终用 Python 脚本做代码级文本变换**：

```python
import re
with open('file.py', encoding='utf-8') as f:
    content = f.read()
content = re.sub(r'TestReport\("([^"]+)"\)', r'TestReport("\1", output_dir=E2E_REPORT_DIR)', content)
with open('file.py', 'w', encoding='utf-8') as f:
    f.write(content)
```

### ⚠️ Playwright helper 函数必须用 sync API

所有 Playwright 脚本使用同步 API。编写 `scripts/component_utils.py` 等工具函数时必须用 `from playwright.sync_api import Page`，不用 async_api。

### ⚠️ terminal 后台模式输出缓冲（Windows）

`terminal(background=True)` 在 Windows bash 环境下不会捕获 stdout。解决方案：
- 方案 A：`terminal("... > output.txt 2>&1", background=True)` 重定向到文件
- 方案 B：`terminal(foreground=True, timeout=N)` 前台执行
- 方案 C：子进程使用 `python -u`（unbuffered）

---

## 13. 脚本标准模板

端到端脚本和原子脚本必须使用以下标准参数模板：

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="脚本描述")
    parser.add_argument("--headed", action="store_true", help="有头模式执行（默认无头）")
    parser.add_argument("--headless", action="store_true", dest="headless_",
                        help="无头模式（显式指定，兼容runner调用）")
    parser.add_argument("--start-scene", type=int, default=1, dest="start_scene",
                        help="起始场景编号")
    parser.add_argument("--no-cleanup", action="store_true", help="不清理数据库")
    args = parser.parse_args()

    is_headless = args.headless_ or not args.headed
    report = run(start_scene=args.start_scene, headless=is_headless,
                 cleanup=not args.no_cleanup)
```

- `headless` 默认 `True`，`--headed` 改为有头，`--headless` 显式指定无头
- `run()` 函数签名：`def run(start_scene=1, headless=True, cleanup=True)`
- 兼容 runner: runner 统一传 `--headless`

---

## 14. Runner 使用速查

| 问题 | 参考文件 |
|:---|:---|
| CLI 参数不匹配（--headless vs --headed） | `references/runner-cli-mismatch.md` |
| 报告解析 regex 兼容（3 种输出格式） | `references/runner-report-parsing-fix.md` |
| 全量执行、依赖跳过恢复、config 配置 | `references/runner-cli-mismatch.md` + `core/runner.py` |

**runner.py 独立 argparse 隔离**：`core/runner.py` 的 `main()` 有独立 argparse（只接受 `--headless`、`--exclude`、`--only`、`--list`）。**不要向 runner 传递 `--platform` 参数**。

```bash
# ✅ 正确：通过 run.py 入口
python run.py --headless

# ❌ 错误：runner 不认识 --platform
python run.py --platform iot --headless
```

---

## 15. 报告通知与 delegate_task

### 报告通知

全量跑完成后，可通过 `send_message` 工具发送测试结果到微信：

```python
# 查看可用的消息目标
send_message(action="list")

# 发送测试结果
send_message(action="send", target="weixin:<user_id>@im.wechat",
    message="✅ 全量测试通过\n脚本: n/total")

# 发送文件
send_message(action="send", target="weixin",
    message="MEDIA:D:/path/to/全量测试报告.html")
```

### delegate_task 超时陷阱

`delegate_task` 默认 600 秒超时。含大量浏览器操作的任务**不应通过子 agent 并行执行**：

| 问题 | 说明 |
|:---|:---|
| 浏览器操作慢 | 每个 `page.goto()` + `time.sleep()` 约 3-5 秒 |
| 子agent 无法恢复 | 600s 超时后中间产出可能丢失 |
| 无进度可见性 | 子 agent 中间日志不回流 |

**推荐做法**：脚本编写任务按模块独立串行，或设置 `timeout=900`。仅将无需浏览器的任务委托给子 agent。

### 子agent 编写测试脚本的已知陷阱

| 陷阱 | 约束 |
|:---|:---|
| 标签定位选择错误 | 强制先 `browser_navigate` + 字段诊断确认 |
| `log()` 签名不匹配 | 委托 context 中写明：`log(msg)` 只接受 1 个参数 |
| 点击不可见菜单项 | 菜单项用 JS evaluate 点击 |
| 忽略已有脚本模板 | 必须附上参考脚本 URL，严格遵循其风格 |
| 数据隔离前缀不一致 | 明确规定 `DATA_PREFIX = f'AUTO_{MODULE}_{RUN_ID}'` |
| 断言双分支遗漏 | else 分支必须有 `report.assertion(..., False, ...)` |

---

## 16. 添加新平台步骤

1. 在 `platforms/` 下创建新目录（如 `platforms/abc/`），复制 `iot/` 的目录骨架
2. 编写 `platforms/abc/.env` 和 `platforms/abc/config.py`
3. 设置 `PLATFORM_ID`、`SCRIPTS` 和 `ATOMIC_SCRIPTS`
4. 添加 `SCRIPT_REPORT_SUBDIRS` 字典，为每个脚本定义模块子目录
5. 运行 `python run.py --platform abc --list-scripts` 验证配置路由
6. 按照 `references/scene-design.md` 设计场景
7. **确认平台 UI 框架类型**：Element Plus → `references/element_ui_patterns.md`；Shadcn/Radix UI → `references/shadcn-ui-patterns.md`
8. 在 `scripts/e2e/` 或 `scripts/atomic/` 下编写脚本
9. 使用 `from core.report_helper import TestReport`、`from config import BASE_URL, get_script_report_dir`
10. 验证：`python run.py --platform abc --only <script_id>`
