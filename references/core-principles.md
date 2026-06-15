# 核心原则（Core Principles）

> 本文档从 `web-auto-pipeline` SKILL.md 的 §〇（前置背景）和 §一（核心原则）提取，包含流水线总览、多平台数据隔离设计、Phase 0 平台探索方法、以及 13 条核心原则的完整解释、代码示例和反例。
>
> **原文位置：** `web-auto-pipeline` skill 的 SKILL.md
> **提取时间：** 2026-06-08

---

## §〇 前置背景

### 〇.1 流水线总览

本流水线定义了一套完整的 Web 端到端自动化流水线，覆盖从零到持续维护的全过程：

```
Phase 0: 平台全量探索（自动）
  ├─ Vue Router 全量路由发现
  ├─ 逐页深度探索（截图+组件识别+交互验证）
  ├─ 数据依赖关系分析
  └─ 产出: Page Manifest JSON + HTML分析报告
         ↓
Phase 1: 脚本骨架生成
  └─ manifest_generator.py 读取 Manifest → Playwright 脚本骨架
         ↓
Phase 2: 场景填充 → 执行验证
  ├─ 填充测试数据
  ├─ 三层断言金字塔（UI → DB → 异步轮询）
  ├─ check_page_errors 检测
  └─ HTML 测试报告 + 截图
         ↓
Phase 3: 多脚本聚合 → CI/CD
  ├─ core/runner.py 依赖链调度
  ├─ JSON + JUnit XML 输出
  └─ 聚合总报告
  ├─ JSON + JUnit XML 输出
  └─ 聚合总报告
         ↓
Phase 4: 自愈与技能进化（持续）
  ├─ 故障目录诊断
  ├─ 组件适配策略更新
  └─ 知识沉淀到 SKILL.md + reference 文档
```

**技能进化（Skill Evolution）**：与自愈（修复已失效的脚本）不同，技能进化是**主动增长**——当用户提出新的测试需求、发现新的组件交互模式、或平台增加新功能时，流水线将该经验沉淀为 skill 的永久知识，使 skill 本身变得更强。

进化反馈闭环：

```
用户发现新模式/新需求 → 隔离调试验证 → 更新 SKILL.md 规则 → 更新 reference 文档
      ↓                                                          ↓
  下次遇到同类问题自动复用                             skill 知识库增长
```

#### 核心能力

| 阶段 | 产出 | 方法 |
|:---|:---|:---|
| **探索 (Explore)** | 页面结构化描述、组件交互陷阱、状态机分析、Page Manifest JSON | 自动: Vue Router 全量路由发现 + 菜单遍历 + Hermes browser 逐页深度探索（见 Phase 0） |
| **建模 (Manifest)** | `manifests/*.json`（字段/按钮/对话框/断言） | 按 schema 编写或从探索记录转换 |
| **生成 (Generate)** | 脚本骨架（Playwright function + 断言占位） | `manifest_generator.py` |
| **执行 (Execute)** | HTML 报告 + 断言结果 + JSON 输出 | 场景函数链 + `TestReport` |
| **自愈 (Self-Heal)** | 选择器降级、组件交互方案库、运行时重试 | 组件适配层 + 方案匹配 |
| **进化 (Evolve)** | SKILL.md 规则更新、reference 文档扩充、组件交互方案库扩展 | 用户反馈驱动 → 隔离调试 → 知识沉淀 |

#### 多平台支持

本流水线通过 **`platforms/{id}/` 目录隔离** 机制支持多个 Web 平台的独立测试上下文。当前已实现的参考实现：

| 平台 | ID | 状态 | 场景数 | 脚本位置 |
|:---|:---|:---:|:---:|:---|
| IoT 物联管理平台 | `iot` | 已验证通过 | 34 (9+3+7+5+8+2) | `platforms/iot/scripts/{atomic,e2e}/` |
| 总控应用集成系统 | `tckz` | 探索中 | — | `platforms/tckz/scripts/` (开发中) |

新增平台时，在 `platforms/` 下创建独立目录，参考物联网平台的实现模式填充。

以下内容基于 **IoT 物联管理平台** 的具体实现经验编写，方法论和规则通用，URL/DB/组件差异部分为平台特定。

---

### 〇.2 多平台数据隔离设计（Platform Profile）

> **架构状态：已落地（2026-06-08）**
> 原 `profiles/` 蓝图已重构为 `platforms/` 架构，root + core/ + platforms/{id}/ 三层隔离。
> 详见 SKILL.md §文件存储规范。

#### 实现方案：platforms/{id}/ 目录隔离

```
D:/AI/harmes agent/WEB平台自动化/
├── config.py              ← 动态路由器（根据 PLATFORM 环境变量转发）
├── run.py                 ← 统一入口
├── core/                  ← 通用核心代码
├── platforms/             ← 各平台独立上下文
│   ├── iot/
│   │   ├── config.py            ← 平台配置
│   │   ├── .env                 ← 平台连接信息
│   │   ├── scripts/{atomic,e2e}/ ← 脚本（按类型分目录）
│   │   ├── manifests/           ← 本平台探索产出
│   │   ├── docs/reports/        ← 测试报告
│   │   ├── docs/manuals/        ← 操作手册
│   │   └── recordings/          ← 录制脚本
│   └── tckz/
└── docs/media/            ← 全局媒体
```

#### 问题：为什么需要隔离？

当流水线服务于多个 Web 平台时，以下维度会发生交叉污染：

| 污染维度 | 当前 IoT 平台的单平台设计 | 多平台场景下的问题 |
|:---|:---|:---|
| 配置 | `config.py` 一个 `BASE_URL`、一个 `DB_HOST` | 平台 A 的 DB 密码覆盖平台 B 的 |
| 测试数据 | 清理 SQL `LIKE '自动化%'` 全局匹配 | 平台 A 的清理删掉平台 B 的数据 |
| 工作目录 | 脚本/报告/Manifest 混在同一目录 | 不同平台的输出文件互相覆盖 |
| 数据名称 | `TAG_NAME = "自动化测试-温度标签"` | 两个平台都叫"自动化测试-xxx"，无法区分 |

#### 方案：平台目录隔离

```
D:/AI/harmes agent/WEB平台自动化/
├── core/                                # 公共核心框架（所有平台共享）
│   ├── report_helper.py
│   ├── report_collector.py
│   ├── report_renderer.py
│   ├── json_renderer.py / junit_renderer.py
│   ├── component_strategies/
│   │   ├── base.py
│   │   └── element_ui.py
│   ├── manifest_generator.py
│   └── runner.py                        # 跨平台调度入口
│
├── platforms/                            # 各平台独立上下文
│   └── <platform_id>/                   # 如 iot, tckz
│       ├── .env                         # 本平台的 URL、DB 连接、代理
│       ├── config.py                    # 平台配置（读取 .env + 默认值）
│       ├── cleanup.sql                  # 本平台的数据清理策略
│       ├── scripts/{atomic,e2e}/        # 本平台的自动化测试脚本
│       ├── manifests/                   # 本平台的页面结构描述
│       ├── docs/reports/                # 测试报告
│       ├── docs/manuals/                # 操作手册
│       ├── recordings/                  # 录制脚本
│       └── references/                  # 本平台的交互记录、BUG 记录
│
└── docs/media/                           # 全局媒体文件
```

#### 隔离级别

| 维度 | 方案 | 实现方式 |
|:---|:---|:---|
| **配置文件** | 每个 platform 独立 `.env` + `config.py` | 根 `config.py` 动态路由，根据 `PLATFORM` 环境变量自动加载 `platforms/{id}/config.py` |
| **工作目录** | 每个 platform 独立 `scripts/`、`docs/reports/` | `run.py` 设置环境变量，`core/runner.py` 读 `config.SCRIPTS_DIR` 切换脚本目录 |
| **测试数据** | 数据名前缀 = `{platform_id}_auto_test_` | `config.DATA_PREFIX` 自动拼接到所有测试数据常量的开头 |
| **数据库** | 每个 platform 独立 DB 配置；或同一 DB 但不同 schema | `config.py` 读各自 `.env` 的 `DB_HOST/PORT/NAME/USER/PASSWORD` |
| **清理 SQL** | 按平台前缀精确匹配，不交叉污染 | 清理脚本读 `platform_id`，构造 `WHERE name LIKE 'iot_auto_test_%'` |
| **运行入口** | `python run.py --platform {id}` | `run.py` 设 `PLATFORM` → 根 `config.py` 路由 → 平台配置 |

#### 平台标识注入（关键实现）

所有测试数据常量统一加上平台前缀：

```python
# profiles/<id>/config.py
PLATFORM_ID = "iot"
DATA_PREFIX = f"{PLATFORM_ID}_auto_test"

# 所有测试数据自动带上前缀
TAG_NAME = f"{DATA_PREFIX}-温度标签"
TAG_CODE = f"{DATA_PREFIX}-tag-temp"
DEVICE_NAME = f"{DATA_PREFIX}-设备v1"
PV_NAME = f"{DATA_PREFIX}-PV"
```

#### 清理 SQL 自动携带平台 ID

```sql
-- 当前（单平台，全局污染风险）：
DELETE FROM device_tags WHERE tag_name LIKE '自动化测试%';

-- 改造后（按平台精确匹配）：
DELETE FROM device_tags WHERE tag_name LIKE 'iot_auto_test%';
-- 另一个平台运行时：
DELETE FROM device_tags WHERE tag_name LIKE 'bypass_admin_auto_test%';
```

#### 跨平台调度入口

```bash
# 运行 IoT 物联管理平台的全套测试
python run.py --platform iot

# 运行 IoT 无头模式
python run.py --platform iot --headless

# 查看 IoT 平台的所有脚本
python run.py --platform iot --list-scripts
```

#### 添加新平台步骤

1. 在 `platforms/` 下创建 `{id}/` 目录，复制 `iot/` 的目录骨架
2. 编写 `platforms/{id}/.env` 和 `platforms/{id}/config.py`
3. 设置 `PLATFORM_ID`、`SCRIPTS`、`ATOMIC_SCRIPTS`、`REPORT_DIR`
4. 运行 `python run.py --platform {id} --list-scripts` 验证路由
5. 按 `scene-design.md` 设计场景，在 `scripts/e2e/` 和 `scripts/atomic/` 下编写脚本

---

### 〇.3 Phase 0: 平台全量探索

> 从本 skill v2 起，平台探索作为流水线的内置第一阶段，不再依赖独立 skill。
> 以下内容吸收了原 `platform-explorer` skill 的核心方法论。

#### 适用场景

当你面对一个未知的 Web 管理平台，需要快速了解其全貌时使用。自动完成人工数天的工作量。

#### 核心流程

```
输入 URL + 可选认证 → 全量路由发现 → 逐个深度探索 → 分析数据依赖 → 生成 Page Manifest + HTML 报告
```

#### Step 0.1: 全量路由发现（优先使用 Vue Router）

**方法A（推荐）：Vue Router API**
读取 `document.querySelector('#app').__vue_app__.config.globalProperties.$router.getRoutes()` 获取所有注册路由。
过滤掉包含 `edit`、`detail`、`version`、`add`、`instrument`、`quick`、`subdevice`、`redirect`、`login`、`register` 的路径，只保留列表页和功能页。

**方法B（降级）：菜单遍历**
如果 Vue Router 不可用，通过侧边栏菜单逐级展开，收集所有可点击的菜单项和对应的URL。
- 用JS展开所有 `el-sub-menu`：`document.querySelectorAll('.el-sub-menu').forEach(el => el.classList.add('is-opened'))`
- 通过 `get_by_role("menuitem", name).first.click()` 逐一点击叶子菜单项并记录URL变化

#### Step 0.2: 逐个页面深度探索

对每个发现的页面执行：
- 截图
- 用 `browser_console` 收集所有输入框的 placeholder、type、required 属性
- 检测组件库类型（Element UI / Ant Design）
- 识别 el-input / el-autocomplete / el-select / el-cascader / el-transfer 等组件
- 自动点击"新增""编辑""版本详情"等操作按钮，记录深层表单
- 分析数据状态（有数据/空数据）

**超时处理**：每个页面最多等 15 秒加载，如果超时跳过该页继续。

#### Step 0.3: 交互方案验证

对每个识别出的组件类型，在浏览器中验证一套可行的自动化方案：

| 组件 | 验证项 | 记录内容 |
|:---|:---|:---|
| el-input | fill() 是否可用 | placeholder 值 |
| el-autocomplete | fill → 等待 → 点 popper 选项 | popper CSS, option selector, 等待时间 |
| el-select | force=True 打开 → 点 `.el-select-dropdown__item` | 是否 filterable |
| el-cascader | force=True 打开 → 点 checkbox | 多选/单选 |
| el-transfer | checkbox 勾选控制 | 按钮可用条件 |
| el-button | 按钮文本, force=True 需要 | 确认对话框文案 |

#### Step 0.4: DB 表结构探测

```sql
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
```

#### Step 0.5: 产出物（双重产出）

每次平台探索应同时产出两份产物：

1. **Page Manifest JSON** — 给机器用的，结构化的页面字段描述
   ```json
   {
     "platform": "设备综合管理系统",
     "base_url": "http://xxx:28080/jwsiot",
     "pages": [
       {
         "name": "设备-创建页",
         "url": "/controller/cDeviceEdit?type=create",
         "list_url": "/controller/cDeviceList",
         "fields": [
           {"placeholder": "请输入设备名称", "type": "input", "required": true},
           {"placeholder": "请输入设备模型名称搜索", "type": "el-autocomplete",
            "popper": ".el-autocomplete__popper", "option_selector": "li", "debounce_seconds": 2}
         ],
         "buttons": ["保存"],
         "assert_db": "device",
         "db_key_field": "device_name"
       }
     ]
   }
   ```
   - 格式定义详见 `references/page-manifest-schema.md`（schema）和 `references/page-manifest-format.md`（格式说明）

2. **HTML 分析报告** — 给人看的，包含截图画廊、页面导航树、数据热力图

#### 关键陷阱

⚠️ **placeholder vs 可访问性树标签**：`browser_snapshot` 显示的 `textbox` accessible name 是 form-item label 文本（如 `"* 标签名称"`），不是 input 的 HTML placeholder 属性（如 `"请输入标签名称"`）。用 `get_by_placeholder()` 定位时务必用 `browser_console` 确认真实的 placeholder 值。

⚠️ **输入框定位方式差异**：

| 来源 | 特征 | 定位方式 |
|:---|:---|:---|
| `placeholder` 属性 | 输入框内显示灰色提示文字 | `get_by_placeholder("文字")` |
| `<label>` 关联元素 | 输入框上方有 `LabelText` | `get_by_label("文字")` |
| `aria-label` 属性 | 输入框有 `aria-label` HTML 属性 | `locator("[aria-label*='...']")` |

---

## §一 核心原则

> 以下 13 条核心原则来自调试过程中的深刻教训，是 Web UI 自动化脚本质量的根本保证。

---

### 原则0: 场景间不重复导航 — 复用当前页面状态

**每个场景应利用前一个场景留下的页面状态，不需要重新导航+搜索。**

❌ **错误做法（之前的SN脚本）：**
```
场景1: 创建SN → 导航到列表 → 搜索SN → 验证 → DB
场景2: 重新导航到列表 → 重新搜索SN → 验证 → 跳出
场景3: 再重新导航到列表 → 再重新搜索SN → 操作
```

✅ **正确做法（优化后）：**
```
场景1: 创建SN → 导航到列表 → 搜索SN → 验证存在性+状态+分配按钮+DB（一页做完）
场景2: 从列表搜索直接进入操作（复用页面）
```

**规则：** 如果场景N已经打开了列表页并搜到了目标记录，场景N+1应该接着用这个状态，而不是重新导航。除非用户的 `--start-scene` 需要独立入口。

#### 场景衔接工具：ensure_on_page（必用模式）

**这是实现"场景间不重复导航"的工厂代码——每个场景启动时判断当前URL，已到达则跳过goto。**

```python
from urllib.parse import urlparse

def ensure_on_page(page, target_url, wait_seconds=3):
    """
    判断当前页面是否已在目标URL。
    如果页面已就位则跳过 goto，否则导航到目标页。
    这是实现"场景间不重复导航"的核心机制。
    """
    current = page.url
    cur_path = urlparse(current).path
    tgt_path = urlparse(target_url).path
    if cur_path == tgt_path:
        log(f"  ↪ 当前已在目标页面({cur_path})，跳过导航")
        return
    log(f"  ↪ 当前页面({cur_path}) ≠ 目标({tgt_path})，执行导航")
    page.goto(target_url, wait_until="domcontentloaded")
    time.sleep(wait_seconds)
```

**使用示例（Bypass 脚本场景2-5）：**
```python
# 场景1结束：保存后系统自动跳转到列表页 → 页面URL已是 LIST_URL
# 场景2开始时：
ensure_on_page(page, LIST_URL)  # → 当前已在目标页面(/pv/relation)，跳过导航

# 场景2结束：搜索停在列表页
# 场景3开始时：
ensure_on_page(page, LIST_URL)  # → 同样跳过导航
```

#### SPA 平台导航陷阱：page.goto 触发全量重载，Auth 状态丢失

**Hash-based SPA（如 Vue Router hash 模式）的核心问题：** `page.goto(url)` 触发**浏览器全量页面加载**，Vue 应用重新初始化，Pinia/Vuex 中的 auth 状态丢失，之后 SPA 会拦截导航并重定向到登录页。

##### 黄金法则：永远不要用 page.goto 导航 hash URL
对 hash-based SPA，使用 `page.evaluate("window.location.hash = '#/xxx'")` 而非 `page.goto`。JS hash 赋值只触发 Vue Router 的 hash 变更事件，**不触发全量页面重载**，auth 状态（localStorage/cookie）完整保留。

```python
# ❌ 错误：page.goto 触发全量重载 → auth 丢失 → 被重定向到登录页
page.goto(f"{BASE_URL}/#/maintenance/item", wait_until="domcontentloaded")

# ✅ 正确：JS hash 赋值，仅触发前端路由变更，auth 保留
page.evaluate("window.location.hash = '#/maintenance/item'")
```

##### ensure_on_page 正确实现（hash SPA 版）
```python
def ensure_on_page(page, target_url, wait_seconds=3):
    """导航到 hash SPA 目标页面（使用 JS hash 赋值，避免 goto 全量重载）"""
    cur_hash = urlparse(page.url).fragment
    tgt_hash = urlparse(target_url).fragment
    if cur_hash == tgt_hash:
        log(f"  ↪ 当前已在目标页面(#{cur_hash})，跳过导航")
        return True

    # 先确保登录
    if "login" in page.url:
        log("  ↪ 当前在登录页，先登录...")
        do_login(page)
        time.sleep(2)

    log(f"  ↪ 导航到 #{tgt_hash}（JS hash 方式）")
    page.evaluate(f"window.location.hash = '{tgt_hash}'")
    time.sleep(wait_seconds)

    # 兜底：如果 SPA 仍重定向到登录（极少见，如 token 过期）
    for _ in range(2):
        if "login" in page.url:
            do_login(page)
            time.sleep(2)
            page.evaluate(f"window.location.hash = '{tgt_hash}'")
            time.sleep(wait_seconds)
        else:
            break

    return urlparse(page.url).fragment == tgt_hash
```

#### SPA 登录流程：填充凭证 → 选择租户 → 导航到工作台

许多 SPA 平台（基于 RuoYi-Vue-Pro / Vben Admin）的登录包含**租户选择**步骤。注意租户选择后 URL 可能出现双 hash 问题（`#/workspace#/workspace`），需用 JS hash 重置：

```python
def do_login(page):
    page.goto(f"{BASE_URL}/#/auth/login", wait_until="domcontentloaded")
    page.get_by_placeholder("请输入用户名").fill(USERNAME)
    page.get_by_placeholder("请输入密码").fill(PASSWORD)
    page.locator("button.ant-btn").filter(has_text="登").click()
    time.sleep(3)
    ts = page.locator(".ant-select").first
    if ts.count() > 0 and "租户" in page.locator("body").inner_text():
        ts.click(); time.sleep(1)
        opt = page.locator(".ant-select-item-option").first
        if opt.count() > 0: opt.click(); time.sleep(2)

    # ★ 用 JS hash 而非 page.goto 导航到工作台（避免全量重载失去 auth）
    page.evaluate("window.location.hash = '#/workspace'")
    time.sleep(3)
```

#### 新平台表单结构验证：先跑 debug_form.py

**绝对不能**根据猜想的 placeholder/label 写脚本。首次接触新平台时：

```python
# 登录并导航到目标页面后，打印实际元素
print("=== BUTTONS ===")
for btn in page.locator("button").all():
    txt = btn.inner_text().strip()
    if txt: print(f"  '{txt}'")
print("=== INPUT PLACEHOLDERS ===")
for inp in page.locator("input").all():
    ph = inp.get_attribute("placeholder") or "(no placeholder)"
    print(f"  placeholder='{ph}'")
print("=== LABELS ===")
for lb in page.locator("label").all():
    txt = lb.inner_text().strip()
    if txt and len(txt) < 30: print(f"  '{txt}'")
```

**Ant Design (Vben Admin) vs Element Plus 差异：**
- **Element Plus 用 Modal 弹窗；Vben Admin 用 Inline 表单（非弹窗）** — 点击"新增"后表单直接渲染在页面内，不是 `.ant-modal`。检测方式：`document.querySelectorAll(".ant-modal").length === 0` 则为 inline 表单
- 按钮文本含空格：`确 认`、`取 消`、`重 置`、`搜 索`（Vben Admin 框架特征）。优先匹配 `确 认`，回退到 `确 定`
- 输入框可能**无 placeholder**（通过 `<label>` 标识字段），也可能有自定义 placeholder
- 部分选择字段（如设备选择、巡检项选择）**不是 a-select**，而是点击后打开独立 Dialog 从表格中选择
- **保存失败处理**：Inline 表单提交失败后需手动点"取消"关闭表单，否则 overlay (`<div data-dismissable-modal>`) 残留遮挡后续交互

**审计清单（写完脚本后逐项检查）:**
1. [ ] 列出每个场景结束时的页面URL
2. [ ] 列出每个场景开始时的页面需求URL
3. [ ] 如果场景N结束URL = 场景N+1开始URL → 场景N+1用 `ensure_on_page` 而非直接 `page.goto`
4. [ ] 特别留意"保存后自动跳转"的场景（确定→保存→自动跳转列表页），下一个场景一定不需要重新导航
5. [ ] 断点续跑 `--start-scene N` 时，场景N需要独立goto（因为浏览器是新打开的）—— `ensure_on_page` 的路径比较会自动处理：新浏览器URL为空 → 路径不同 → 执行导航
6. [ ] **新平台首次写脚本前**：运行 debug_form.py 验证实际 button 文本、input placeholder、label、select 选项、modal 结构
7. [ ] **SPA 平台**：ensure_on_page 必须使用 JS hash 赋值（`page.evaluate("window.location.hash='#/xxx'")`），不能用 `page.goto` 否则全量重载丢失 auth

---

### 原则0.1: 先研究现有脚本，再设计新场景

**当为一个已有测试脚本的模块开发新场景时，优先研究现有脚本的数据依赖链，而不是从零设计。**

这是最容易被忽略的步骤——凭猜测设计场景流程，结果跑不通才发现忽略了关键数据依赖。

```python
# ❌ 错误：不研究现有脚本，直接开始写
# 以为设备管理只需要 设备模型 → 设备 两步
# 实际依赖链是：PV → 元件模型 → 元件 → 设备模型 → 设备

# ✅ 正确：先通读 device_managent_test.py 的完整9场景
# 识别依赖链和数据流向 → 确认前置场景已执行
# 再基于正确的理解设计新场景
```

**审计清单：**
1. [ ] 通读现有脚本的**所有场景**，画出数据流向图
2. [ ] 标记每个场景的**输出表**和**输入依赖**
3. [ ] 确认新场景所需的前置数据在现有流程中已创建
4. [ ] 检查现有脚本中是否已包含类似逻辑（可直接复用而非重写）
5. [ ] 如果现有脚本已验证通过，关键步骤（如选项选择器、按钮定位）应直接拷贝，不要重新发明

---

### 原则1: 断言是灵魂 — 没有断言=无效自动化

**每个操作后必须有严格断言验证，不设软降级。**

```
三层断言金字塔：
┌──────────────┐
│   UI断言      │ ← 页面元素真实可见、状态正确
├──────────────┤
│   DB断言      │ ← 数据真正写入、字段值正确（最可靠）
├──────────────┤
│   异步轮询    │ ← 发布等操作等待最终状态收敛
└──────────────┘
```

**硬性规则：**
- ❌ 不允许"找不到就用DB验证"绕过 — 这会放掉"DB有数据但前端不显示"的BUG
- ❌ 不允许"可能UI结构不同"软降级 — 定位不到就 FAIL，如实记录
- ✅ 检查具体字段值（如 input.value），不只看元素存在
- ✅ DB断言先查 information_schema 确认字段名，不猜

---

### 原则2: 异步操作必须轮询，不能固定sleep

发布（元件/设备）后台有PV连通性检查，状态更新延迟。

**注意发布检测条件：**
- 列表页默认显示草稿状态的记录，状态列为**空**，操作列含"发布"按钮
- 发布成功后，状态列显示为"发布"（即 `td` 中 `has_text="发布"` 表示**已发布状态**）
- 检测时查行内 `td` 的文本，而非查按钮文本

```python
published = False
for wait_i in range(6):  # 最多等30秒
    time.sleep(5)
    page.goto(f"{LIST_URL}", wait_until="networkidle")
    time.sleep(1)
    row = page.locator("tr").filter(has_text=NAME)
    if row.count() > 0:
        # ✅ 正确：检查状态列 td 中是否包含"发布"文字（表示已发布状态）
        cells = row.locator("td").filter(has_text="发布")
        if cells.count() > 0:
            published = True
            break
    log(f"状态未变更（第{wait_i+1}次检查）", "⏳")
if not published:
    log("发布超时：前端未显示发布状态", "❌")
```

---

### 原则3: 每个自动化脚本必须附带HTML测试报告

**最终交付标准：** 自动化脚本调试通过后，必须集成 `TestReport` 生成自包含HTML报告，才能算"可复用脚本"。

```
测试脚本完成标准：
┌──────────────────────────────────────┐
│  1. 功能逻辑调试通过 ✅               │
│  2. 每个场景多层断言 ✅               │
│  3. ★ HTML测试报告输出 ★ ✅           │
│  4. 数据库清理（开头）+ 断点续跑 ✅   │
│  5. 依赖检查（消费型脚本） ✅          │
└──────────────────────────────────────┘
```

**集成方式（3行代码）：**
```python
from core.report_helper import TestReport
report = TestReport("脚本标题")
# ... 执行逻辑 ...
from datetime import datetime
_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
html_path = report.generate_html(filename=f"my_script_测试报告_{_ts}.html")
print(f"📋 报告已生成: {html_path}")
```

**报告必须记录的内容：**
- 每个场景的 **操作步骤**（含时间戳）
- **一步一截图策略**：填写表单后必须截图（`report.step("填写XXX", screenshot=page)`），展现填写后的页面状态。不要只在导航和保存时截图。每个表单操作（填写名称/编码/描述等）完成后立即截图，让阅读报告的人能看到每个表单填了什么。
- **关键导航截图**：导航到新页面、点击保存/提交后截图
- **断言结果内联展示**：断言显示在对应的操作步骤后面（不是单独分区），形成连续时间线：步骤→[截图]→断言→步骤→[截图]→断言...
- **★ 断言录制顺序至关重要：`report.step()` 必须在 `report.assertion()` 之前调用！** 因为断言自动关联到"最近记录的步骤"（`last_step_seq`），如果 assertion 在前 step 在后，断言会错误地绑定到上一个步骤。交换顺序后断言徽章才会正确显示在该步骤的标题行右侧。
- **进度条**：每个场景一段绿色（通过断言比例），**仅失败场景有红色段**（不能给0失败场景生成任何红色段）
- 场景通过/失败状态 + 耗时
- 顶部概览Banner（通过数/失败数/断言通过率/进度条）

**命名规范：**
- `TestReport("标题")` 和 `master_runner.py` 的 `SCRIPTS` 数组中的 `name` 字段必须使用**业务含义名称**（如"设备管理"、"SN全生命周期"），不要用技术文件名或版本号（如"端到端场景1-9"）
- 子报告文件名使用 `{script_id}_前缀 + 时间戳`（如 `bypass_lifecycle_测试报告_20260604_165857.html`），避免不同脚本报告互相覆盖
- 脚本通过 `generate_html(filename=f"{script_id}_测试报告_{ts}.html")` 传入自定义文件名
- JSON 结果文件同样加前缀（如 `bypass_lifecycle_test_results_20260604_165857.json`）
- 报告输出目录统一为 `platforms/{PLATFORM_ID}/docs/reports/`（由 `config.REPORT_DIR` 控制，环境变量 `IOT_REPORT_DIR` 可覆盖）

**硬性规则——不准隐藏失败：**
- 已知BUG也必须如实记录为 **断言失败**（`report.assertion("", False, "原因")`）
- `scene_end(True)` 但场景内有断言失败 → **`TestReport` 自动降级为失败状态**
- 不允许出现"明知断言失败，但场景标为通过"的情况
- 报告头部显示三态指示器：全部通过✅ / 全部失败❌ / 部分失败⚠️，失败数量标红、通过标绿

**总控调度：** 多个脚本串行执行时用 `run.py`（由 `core/runner.py` 调度）生成聚合总报告。
依赖关系在 `SCRIPTS` 数组中声明（`depends_on` 字段），调度器自动按序执行。

---

### 原则4: 调试阶段必须用有头模式

**工作流：** Hermes browser 探索 → 确认步骤 → 写脚本 → terminal background 运行（headed）→ 用户观察 → 修正

#### 浏览器窗口设置（关键——截图必须最大化）

脚本启动时必须最大化浏览器窗口，确保截图包含完整的页面信息：

```python
browser = p.chromium.launch(
    headless=False,
    args=["--start-maximized"]
)
context = browser.new_context(no_viewport=True)
page = context.new_page()
page.set_viewport_size({"width": 1920, "height": 1080})
```

- `--start-maximized` 让浏览器窗体最大化
- `no_viewport=True` 取消固定视口约束，使用真实窗口大小
- `set_viewport_size(1920x1080)` 作为兜底

**违反后果**：未最大化的浏览器截图会缺失页面右侧/底部内容，导致手册或报告信息不完整。

#### 关键规则：先隔离调试，确认可行，再整合脚本

当调试过程中发现某个组件交互不生效（如 el-select 下拉选不上、el-cascader 勾选不保存），且用户指出问题未解决时：

```
1. 不试图在主脚本中 inline 修复（会导致场景失败被跳过、断言混乱）
2. 创建独立的隔离调试脚本（如 *_debug.py），专门测试这个交互
3. 在隔离脚本中系统性尝试多种方案（force=True、evaluate、键盘操作等）
4. 用户现场见证隔离脚本通过，确认方案可靠
5. 再将已验证的方案移植到主脚本中
6. 运行完整主脚本确认无回归
```

**从本 session 得出的经验：** 用户指出"状态查询的问题不是还没有解决吗"后，直接创建隔离调试脚本 → 5 分钟内找到 force=True 方案 → 整合回主脚本 → 全场景通过。

---

### 原则5: 流程模拟人工操作，杜绝重复导航

**⚠️ 场景间页面状态复用（最常见的遗漏）：**
"场景N的断言阶段 goto 到列表页 → 场景N+1又以同样的 goto 开头" 是最容易遗漏的模式：
```python
# 场景2: 保存 → goto列表 → 搜索 → 断言 → 停在列表页
page.get_by_role("button", name="保存").click()
time.sleep(3)
page.goto(f"{URL}/elist", wait_until="networkidle")   # ✅ 需要（刚保存完）
page.get_by_placeholder("模型名称").fill(NAME)
page.get_by_role("button", name="搜索").click()
# 断言通过，页面停在 elist

# 场景3（错误）：又 goto 了一次同页面！
page.goto(f"{URL}/elist", wait_until="networkidle")    # ← ❌ 多余！
time.sleep(1.5)
page.get_by_placeholder("模型名称").fill(NAME)          # 直接搜即可
```
**审计清单：** 写完脚本后检查每个 `page.goto()` — 如果前一场景的断言/操作结束后页面就在该目标URL，删掉这个goto。断点续跑时该问题由 `--start-scene` 参数处理，无需在场景内做额外导航。

**自动化脚本的每个操作必须模拟人的真实行为：**

```python
# ❌ 错误：提交后系统已自动跳转到列表页，又手动导航一次
page.get_by_role("button", name="提交").click()
page.goto(f"{BASE_URL}/sn/list")   # 多余！
page.get_by_placeholder("SN号").fill(SN_CODE)

# ✅ 正确：利用系统跳转，直接在当前页面继续操作
page.get_by_role("button", name="提交").click()
# 此时系统已自动跳转到列表页 → 直接搜索
page.get_by_placeholder("SN号").fill(SN_CODE)
```

**三条铁律：**
1. **提交/保存后不导航** — 系统自带跳转，直接在结果页操作
2. **场景衔接不导航** — 上一个场景操作完在哪个页面，下一个场景就从哪里继续
3. **仅新模块才导航** — 只有需要进入不同功能模块时才调用 `page.goto()`

**判断是否该导航的标准：**"人现在在这个页面，他会怎么做？"如果人就在当前页面直接操作，脚本就不该 goto。

每步操作后验证：URL变化？网络请求发出？表单验证错误？列表页记录存在？
**保存后必须先导航到列表页确认记录是否存在**，不要因为页面空白就重复创建（用户原话：设备已创建成功，为什么一直重复创建）。

---

### 原则6: 断点续跑 + 数据清理前置

- `--start-scene N` 参数跳过已成功的场景
- `--no-cleanup` 保留数据供排查
- `--cleanup-only` 仅清理数据库

---

### 原则7: 数据清理前置 — 支持多脚本数据复用

**关键经验：清理放在脚本最开头（场景执行之前），不是结尾。**

```
e2e_full.py  ──── 开头清理旧数据 → 执行9场景 → 数据留在DB
                        ↓
sn_lifecycle.py ── 前置检查DB依赖 → 执行3场景SN → 数据留在DB
```

**为什么不在结尾清理？**
- 场景1-9产出的数据（PV、元件、设备等）需要被后续脚本（如SN全生命周期）复用
- 每次执行前清理旧数据确保幂等性，执行后保留数据供消费

**多脚本复用模式：**
```python
# 脚本B（消费者）的前置检查
def check_prerequisites():
    if not db_check_pv_exists():
        log("❌ PV数据不存在，请先执行 e2e_full.py", "❌")
        return False
    if not db_check_device_released():
        log("❌ 设备未发布，请先执行 e2e_full.py", "❌")
        return False
    return True
```

---

### 原则8: 前置数据依赖检查

消费型脚本（依赖其他脚本生成的数据）必须在开头做前置检查：
- DB直查确认基础数据存在（PV、模型、设备等）
- 不自动创建依赖数据（保持关注点分离）

#### 前置检查失败恢复策略（运行脚本时的操作指南）

当 `check_prerequisites()` 失败时（输出 `❌ 前置检查失败` 及 `None` 标记），说明依赖数据在 DB 中不存在。恢复步骤：

1. **确认缺失项**：查看脚本输出的缺失 ID 列表，`None` 对应的即为缺失数据
2. **DB 直查验证**：
   ```python
   from config import get_db_connection
   conn = get_db_connection()
   cur = conn.cursor()
   cur.execute("SELECT pv_code, id FROM pv_data_info WHERE pv_code = %s", ("目标PV名",))
   print(cur.fetchone())
   ```
3. **创建最小化记录**：如果缺失的只是简单的引用数据（如 PV 记录、测试标签），可以直接 INSERT 最小化字段：
   ```python
   cur.execute("""
       INSERT INTO pv_data_info (pv_code, pv_desc, is_delete)
       VALUES (%s, %s, false) ON CONFLICT DO NOTHING
   """, ("1111222333", "Auto test assoc PV 1"))
   conn.commit()
   ```
   - 仅填充 `NOT NULL` 约束的必要字段（通过 `information_schema.columns` 确认）
   - 使用 `ON CONFLICT DO NOTHING` 保证幂等性
4. **重新运行脚本**：`python xxx.py --headless`
5. **适用场景区分**：
   - ✅ **简单的引用数据**（PV、标签、字典项）→ 直接 INSERT 恢复
   - ❌ **复杂的依赖链**（完整模型-设备-元件链）→ 应运行上游脚本生成，而非手动 DB INSERT

---

### 原则9: 每个操作后必须校验——不允许"我以为它执行了"

**这是从标签场景中暴露出的最严重问题：** 脚本作者"以为"下拉框选上了、"以为"标签关联成功了，但断言没有校验，结果脚本报告通过但实际上操作并未生效。

**核心规则：每步操作后，必须通过观察页面状态来证明该操作确实执行了。**

```python
# ❌ 错误：点击下拉 → 搜索 → 只看搜索结果>0（未验证下拉是否选上）
page.get_by_role("combobox").click()
time.sleep(1)
page.locator("[role='option']").filter(has_text="草稿").first.click()
page.get_by_role("button", name="搜索").click()
assert page.locator("tr").count() > 0  # 即使下拉没选上，搜索也能出结果

# ✅ 正确：先验证下拉文本已改变，再搜索，再确认结果状态
page.get_by_role("combobox").click(force=True)
time.sleep(1.5)
page.locator(".el-select-dropdown__item").filter(has_text="草稿").first.click()
# 校验1：下拉文本已从"请选择"变为"草稿"
assert page.locator(".el-select").filter(has_text="请选择标签状态").count() == 0
page.get_by_role("button", name="搜索").click()
# 校验2：结果行的状态列确实是"草稿"
row = page.locator("tr").filter(has_text="草稿").first
status_cell = row.locator("td").nth(3).text_content()
assert "草稿" in status_cell
```

**对接原则：调试过程中，当某个交互方式经过多轮系统性尝试均失败后，应如实向用户汇报所有尝试方案及其结果，由用户判断是继续尝试、改用等价验证、还是暂时搁置。不要自动降级为等价验证而不告知用户。**

**设备关联的双重验证：**
保存后不能只看列表页的标签列（可能缓存），必须再次进入编辑页确认：
```python
page.get_by_role("button", name="保存").click()
# 回到列表 → 点编辑 → 确认标签在编辑页中
page.goto(list_url)
page.get_by_role("button", name="编辑").first.click()
body = page.locator("body").inner_text()
assert "已关联的标签名" in body  # 真正可靠的验证
```

**硬性规则：** 如果无法通过页面状态证明某操作已执行，则脚本存在缺陷。自动化脚本的每个断言必须在页面上有可见的证据支撑。

---

### 原则10: 关键操作后必须错误检测 + 即时截图 — 不截图等于盲操作

**这是本次会话最重要的教训。** 用户在点击保存后，页面出现了后端 NPE 红色报错横幅，但脚本没有截图保存，导致用户无法在报告中第一时间定位问题，误以为脚本本身有缺陷。

**核心规则：每次保存、发布、提交、确定等"写操作"后，必须立即执行错误检测函数并截图。**

#### 错误检测覆盖要求

错误提示有多种形态，不能只检测一种：

| 错误形态 | 选择器/检测方式 | 平台示例 |
|:---|:---|:---|
| Element UI 顶部 Message 错误 | `.el-message--error`, `.el-message--warning` | 通用 |
| Element Plus Notification 内容 | `.el-notification__content` | 通用 |
| Ant Design Message 错误 | `.ant-message-error`, `.ant-message-warning` | Vben Admin |
| Ant Design Notification | `.ant-notification-notice-description` | Vben Admin |
| 表单验证错误 | `.el-form-item__error`, `.ant-form-item-explain-error` | 通用 |
| Alert / Result 组件 | `.el-alert--error`, `.ant-alert-error` | 通用 |
| **页面内嵌红色横幅（非标准组件）** | **body 文本关键词匹配** | **IoT 平台 NPE** |
| URL 未变化 | `urlparse(page.url).path` 对比期望路径 | 保存失败信号 |

**关键教训：** IoT 平台的 NPE 报错 `Cannot invoke "ThingModelVersionPageVo.getId()" because "thingModelVersion" is null` 不是标准 `el-message` 组件，而是页面内嵌的自定义红色横幅，必须通过 **body 文本关键词匹配**（"Cannot invoke"/"is null"/"thingModelVersion"）才能捕获。

#### `check_page_errors` 标准实现（轮询版）

```python
def check_page_errors(page, report=None, step_name="保存后错误检查", expected_url_change=None):
    """
    检查页面是否有错误提示。发现任何错误则记录断言到报告。
    注意：报告中的 step 由调用方负责在调用此函数前记录（含截图），此函数只做断言。
    轮询检测：每 2 秒检查一次，共 4 次（最长等待 8 秒），捕捉异步延迟的后端错误。
    返回 (has_error, error_text)。
    """
    errors = []
    error_texts = []
    has_error = False

    # 轮询检测（后端 NPE 可能异步延迟返回）
    for check_round in range(4):
        time.sleep(2)
        round_errors = []

        # 1. Element UI / Element Plus 顶部 message 错误提示（仅 error/warning 级别，排除 success/info）
        for sel in [".el-message--error", ".el-message--warning",
                    ".ant-message-error", ".ant-message-warning"]:
            msgs = page.locator(sel).all()
            for msg in msgs:
                txt = msg.text_content().strip()
                if txt and len(txt) > 3 and txt not in error_texts:
                    round_errors.append(f"[Message:{sel}]{txt}")
                    error_texts.append(txt)

        # 2. Notification 通知（仅检测错误/警告内容）
        for sel in [".el-notification__content",
                    ".ant-notification-notice-description", ".ant-notification-notice-message"]:
            notifs = page.locator(sel).all()
            for n in notifs:
                txt = n.text_content().strip()
                if txt and len(txt) > 3 and txt not in error_texts:
                    round_errors.append(f"[Notification:{sel}]{txt}")
                    error_texts.append(txt)

        # 3. 表单验证错误
        form_errors = page.locator(".el-form-item__error, .ant-form-item-explain-error").all()
        for fe in form_errors:
            txt = fe.text_content().strip()
            if txt and txt not in error_texts:
                round_errors.append(f"[Form]{txt}")
                error_texts.append(txt)

        # 4. Alert / Result 组件
        for sel in [".el-alert--error", ".el-alert--warning", ".el-result__error",
                    ".ant-alert-error", ".ant-alert-warning"]:
            alerts = page.locator(sel).all()
            for a in alerts:
                txt = a.text_content().strip()
                if txt and len(txt) > 3 and txt not in error_texts:
                    round_errors.append(f"[Alert:{sel}]{txt}")
                    error_texts.append(txt)

        # 5. ★★★ 页面全局错误提示（body 文本关键词匹配——捕获非标准组件报错）
        body_text = page.locator("body").inner_text()
        backend_keywords = ["Cannot invoke", "NullPointerException", "exception",
                            "error", "失败", "系统繁忙", "请稍后重试",
                            "服务端异常", "500", "404", "操作失败", "保存失败",
                            "创建失败", "is null", "cannot be null"]
        for kw in backend_keywords:
            if kw.lower() in body_text.lower():
                if not any(kw.lower() in e.lower() for e in error_texts):
                    round_errors.append(f"[BodyKeyword]{kw}")
                    error_texts.append(kw)

        # 6. URL 变化检测（保存后 URL 未变 = 可能保存失败）
        if expected_url_change:
            from urllib.parse import urlparse
            cur_path = urlparse(page.url).path
            if expected_url_change not in cur_path:
                if not any("URL未变" in e for e in error_texts):
                    round_errors.append(f"[URL]保存后URL未变化: {cur_path}")
                    error_texts.append(f"URL未变: {cur_path}")

        if round_errors:
            errors.extend(round_errors)
            has_error = True
            # 第一次发现错误就跳出轮询，并截图
            break

        time.sleep(2)  # 只在没发现错误时才等——避免初始延迟漏掉瞬时表单验证错误
        print(f"  ⚠️  页面报错 detected: {full_error[:250]}")
        if report:
            report.assertion("页面无报错", False, full_error[:400])
    else:
        if report:
            report.assertion("页面无报错", True, "")

    return has_error, "; ".join(error_texts)
```

**使用方式（保存后调用，1 step）：**

```python
page.get_by_role("button", name="保存").click()
time.sleep(3)
# ★ 先截图记录步骤，再检查页面报错（1 step，统一放在此处）
report.step("保存元件模型", screenshot=page)
has_err, err_txt = check_page_errors(page, report, "保存元件模型后检查",
                                      expected_url_change="/elementType/elist")
if has_err:
    log(f"  保存时页面报错: {err_txt[:120]}", "❌")
    # 非关键失败（如PV关联）不阻断，让后续断言验证实际结果
```

#### Step 整合：保存/发布后只需 1 个 step

**原则：`check_page_errors` 只做断言，step 由调用方统一管理。** 每个保存/发布操作在报告中只有 1 个 step（含截图），而非旧方案的 3 个冗余 step。

**旧方案（3 step → 冗余）：**
```
check_page_errors: "保存后检查 (即时截图)"    ← step 1
check_page_errors: "保存后检查"                ← step 2（带 assertion）
调用方:           "保存xx"                     ← step 3（重复截图）
```

**新方案（1 step → 简洁）：**
```
调用方:  report.step("保存xx", screenshot=page)   ← step 1（含截图）
check_page_errors: report.assertion(...)           ← only assertion，无 step
```

**迁移步骤（所有场景统一模式）：**
1. 在 `check_page_errors` 函数中移除所有 `report.step()` 调用
2. 在每个调用点，将 `report.step(..., screenshot=page)` 移到 `check_page_errors()` 之前
3. 移除调用点的冗余 `report.step()`（原在 check_page_errors 之后）

**修改前（场景2）：**
```python
has_err, err_txt = check_page_errors(page, report, "保存元件模型后检查")
if has_err: return report
report.step("保存元件模型", screenshot=page)
```

**修改后（场景2）：**
```python
report.step("保存元件模型", screenshot=page)
has_err, err_txt = check_page_errors(page, report, "保存元件模型后检查")
if has_err: return report
```

#### 场景依赖中断（前置场景失败则跳过后续）

---
1. **保存/发布/提交/确定后必须调用 `check_page_errors`** — 这是区分"平台 BUG"和"脚本问题"的第一道防线
2. **即时截图 + 轮询检测** — 错误可能异步延迟出现，单次检测不可靠
3. **区分关键失败 vs 非关键失败** — 非关键失败不应阻断后续场景

⚠️ **常见陷阱：check_page_errors 选择器过宽导致假阳性**

> 此选择器列表中的 `.el-message` 和 `.ant-message` 会匹配**所有消息**，包括成功的绿色提示（如"发布成功"、"保存成功"）。如果将这些通用选择器加入列表，发布成功等操作会误判为场景失败，阻断后续所有依赖场景。
>
> **正确做法：只保留 error/warning 级别的具体选择器：**
> - ✅ `.el-message--error`, `.el-message--warning`
> - ✅ `.ant-message-error`, `.ant-message-warning`
> - ❌ `.el-message`（过宽，匹配所有类型）
> - ❌ `.ant-message`（过宽）
>
> **Notification 同理：**
> - ✅ `.el-notification__content`（内容区）
> - ❌ `.el-notification__title`（可能包含"操作成功"等标题）

#### 关键失败 vs 非关键失败

并非所有场景失败都应阻断后续流程。应根据场景间的数据依赖关系区分：

```python
def should_run(n):
    # 非阻塞场景：这些场景失败不会跳过后续场景
    # 场景4（新增元件+关联PV）：PV关联失败不影响元件创建
    # 场景5（发布元件）：发布失败不应阻断设备模型创建
    NON_BLOCKING = {4, 5}
    for scene in report.scenes:
        if scene.get("status") == "failed":
            import re
            m = re.search(r'\d+', str(scene.get("id", "")))
            scene_num = int(m.group()) if m else 0
            if scene_num not in NON_BLOCKING:
                return False
    return True
```

**规则：**
- **PV 创建、模型创建等基础场景失败** → 阻断（后续无数据可用）
- **PV 关联、发布等非核心操作失败** → 不阻断（主数据已创建）
- **保存后报错不立即 `return report`** → 让后续断言和 DB 验证判断实际结果。如果数据确实没创建，后续场景会自然失败

---

### 原则11: 编辑后二次确认（★★★）—— 保存后必须回查UI确认修改生效

**这是从Bypass编辑场景中暴露的关键缺失：** 编辑操作保存后，仅做DB断言不够——DB证实了数据层写入，但无法证实前端渲染正确。

```python
# ❌ 错误：保存后只做DB断言
page.get_by_role("button", name="确定").click()
time.sleep(3)
rels = db_check_relations(NAME)
report.assertion("DB: 关联已更新", len(rels) == 2, "")  # DB正确，但UI呢？

# ✅ 正确：保存后重新进入编辑页，UI验证数据
page.get_by_role("button", name="确定").click()
time.sleep(3)

# DB断言（第一层）
rels = db_check_relations(NAME)
report.assertion("DB: 关联已更新", len(rels) == 2, "")

# ★★★ 二次确认（第二层）：重新搜索→进入编辑页→验证UI
ensure_on_page(page, LIST_URL)
page.get_by_label("BypassPV名称").fill(BYPASS_PV)
page.get_by_role("button", name="搜索").click()
time.sleep(2)

edit_btn = page.get_by_role("button", name="编辑").first
edit_btn.click()
time.sleep(3)

# 验证编辑页中数据正确
edit_body = page.locator("body").inner_text()
report.assertion("UI确认: 编辑页含PV1", ASSOC_PV_1 in edit_body, "")
report.assertion("UI确认: 编辑页含PV2", ASSOC_PV_2 in edit_body, "")

# 验证计数等数字指标（比body文本更精确）
assoc_count = page.locator("text=已关联 PV").first.locator("xpath=./following-sibling::*[1]").inner_text()
report.assertion("UI确认: 已关联PV数=2", assoc_count.strip() == "2", "")

# 返回（不保存）
page.get_by_role("button", name="返回").click()
```

**三条铁律：**
1. **保存后必须有 DB 断言**（数据层）— 证明写入正确
2. **保存后必须有 UI 回查**（展示层）— 证明渲染正确
3. **UI 回查比全页面 body 更精确** — 验证计数、特定区域文本而非全页面。因为修改后的数据可能出现在其他区域（如从已关联区域移到可关联区域后，文本仍在页面中）

---

### 原则12: 转移组件(Transfer/穿梭框)的批操作陷阱——必须精细控制勾选框

**el-transfer 风格的双栏穿梭框（如Bypass管理的可关联PV/已关联PV）的「移除」操作常见陷阱：**

```python
# ❌ 错误：直接点"移除"按钮——默认全勾选=全部移除
page.get_by_role("button", name="移除").click()
# 结果：所有已关联条目都被移除，不是只移除目标

# ✅ 正确：先检查/控制勾选框状态，再点按钮
# 1. 进入编辑页时，已关联PV区域的checkbox默认全勾选
# 2. 需要对目标移除的条目保留勾选，其他条目取消勾选
# 3. 再点击"移除"——只移除勾选的条目

# ★ 定位方式：已关联PV区域的checkbox特征为：已勾选(is-checked)且未禁用
assoc_checked = page.locator(".el-checkbox.is-checked:not(.is-disabled)")
ac_count = assoc_checked.count()
log(f"已勾选checkbox数={ac_count}")
# 第0个=表头全选，第1个=行checkbox1，第2个=行checkbox2...
report.assertion("验证: 已关联PV默认勾选", ac_count >= 2, f"勾选数={ac_count}")

# 取消PV1行的勾选（保留），PV2行保持勾选（待移除）
assoc_checked.nth(1).click()  # 取消第一个PV行
time.sleep(0.5)

# ★ 验证：重新统计勾选数，确认只有目标PV仍勾选
still_checked = page.locator(".el-checkbox.is-checked:not(.is-disabled)")
report.assertion("验证: PV1已取消勾选(保留)", still_checked.count() == 1, "")

# 再点"移除"——仅移除仍勾选的PV2
remove_btn = page.get_by_role("button", name="移除").first
report.assertion("验证: 移除按钮可用", remove_btn.is_enabled(), "")
remove_btn.click()
```

**核心原则（一步一验证）：**
在执行任何"批量操作"（移除/关联/删除选中）前，**必须先验证勾选框的当前状态**，确认只有目标对象被勾选，再执行操作。不能在不确定勾选框状态的情况下直接点击操作按钮。

**硬性规则：**
- 任何时候点批量操作按钮（关联/移除/批量删除）前，必须先检查勾选框状态
- 写脚本时：点击按钮 → 立即断言结果，中间不隔其他操作
- 如果在移除后验证全页面body文本检查是否包含某个条目——该条目可能迁移到了另一个区域（例如从"已关联"移到"可关联"），导致body仍包含该条目的文本。此时应检查"已关联PV"的计数文本而非全页面body。更好的验证是检查该区域右侧的数字计数变化。

当遇到某个交互方式经多轮系统尝试均失败时（如 el-autocomplete 静默失败、PV绑定不持久化），遵循以下流程：

```
1. 系统性尝试: 列出所有可能方案并逐一记录结果（至少3-4种，含失败原因）
2. 透明汇报: 向用户展示完整方案表（方案/现象/失败原因），不自动降级
3. 用户决策: 由用户决定是继续尝试、改用等价验证、还是暂时搁置
4. 如需深度解决 → 多视角评审: 邀请不同专业背景（测试架构/框架/运维）输出结构化评审
5. 制定计划: 基于评审输出系统化改进方案，分优先级实施
6. 验证回归: 每个改动后运行现有脚本验证无回归
```

---

## 审计清单汇总

以下审计清单为所有原则的检查点汇总，请在每次完成脚本后逐项检查：

### 原则0（场景间不重复导航）
1. [ ] 列出每个场景结束时的页面URL
2. [ ] 列出每个场景开始时的页面需求URL
3. [ ] 如果场景N结束URL = 场景N+1开始URL → 场景N+1用 `ensure_on_page` 而非直接 `page.goto`
4. [ ] 特别留意"保存后自动跳转"的场景（确定→保存→自动跳转列表页），下一个场景一定不需要重新导航
5. [ ] 断点续跑 `--start-scene N` 时，场景N需要独立goto（因为浏览器是新打开的）
6. [ ] **新平台首次写脚本前**：运行 debug_form.py 验证实际 button 文本、input placeholder、label、select 选项、modal 结构
7. [ ] **SPA 平台**：ensure_on_page 必须使用 JS hash 赋值，不能用 `page.goto` 否则全量重载丢失 auth

### 原则0.1（先研究现有脚本）
1. [ ] 通读现有脚本的**所有场景**，画出数据流向图
2. [ ] 标记每个场景的**输出表**和**输入依赖**
3. [ ] 确认新场景所需的前置数据在现有流程中已创建
4. [ ] 检查现有脚本中是否已包含类似逻辑（可直接复用而非重写）
5. [ ] 如果现有脚本已验证通过，关键步骤应直接拷贝，不要重新发明

### 原则5（流程模拟人工操作）
- [ ] 写完脚本后检查每个 `page.goto()` — 如果前一场景的断言/操作结束后页面就在该目标URL，删掉这个goto

---

> 本文档由 `web-auto-pipeline` SKILL.md 的 §〇（前置背景）和 §一（核心原则）自动提取生成。
> 原文位于 `web-auto-pipeline` skill 的 SKILL.md。
> 生成日期：2026-06-08
