# 框架架构参考 — 重构后组件分层

## 包结构

```
WEB平台自动化/
├── config.py                     # 统一配置层（环境变量 + .env + 默认值）
├── .env.example                  # 环境变量模板
├── .gitignore                    # 忽略规则
├── requirements.txt              # 依赖声明

├── report_collector.py           # 数据采集器（场景/步骤/断言生命周期）
├── report_renderer.py            # HTML 渲染器（从 data dict 渲染）
├── report_helper.py              # 兼容层（保持 TestReport API 不变）
├── junit_renderer.py             # JUnit XML 输出（CI 集成）
├── json_renderer.py              # 结构化 JSON 输出

├── component_strategies/
│   ├── __init__.py               # 导出 get_adapter() 工厂函数
│   ├── base.py                   # ComponentAdapter 抽象基类
│   └── element_ui_vue3.py        # Element UI / Vue 3 实现

├── master_runner.py              # 多脚本调度器（依赖链 + 失败传播）
├── manifests/*.json              # 页面结构化描述
├── templates/page_script.j2      # Jinja2 代码生成模板

├── e2e_full.py                   # 9 场景端到端（核心）
├── sn_lifecycle.py               # SN 全生命周期
├── tag_lifecycle_test.py         # 标签全生命周期
└── references/                   # 知识库文档
```

## 分层设计

```
┌──────────────────────────────────────────────┐
│              测试脚本层                        │
│  e2e_full.py / sn_lifecycle.py / ...          │
├──────────────────────────────────────────────┤
│             报告系统层                         │
│  collector.py → renderer (HTML/JUnit/JSON)    │
├──────────────────────────────────────────────┤
│           配置层 + 适配层                      │
│  config.py + component_strategies/*.py        │
├──────────────────────────────────────────────┤
│           基础设施层                           │
│  requirements.txt / .gitignore / .env         │
└──────────────────────────────────────────────┘
```

## 各组件职责

### config.py — 配置层

读取优先级：环境变量 > `.env` 文件 > 默认值。

**关键特性：**
- `.env` 文件自动加载（`os.path.isfile` 检测 + 手动解析，不依赖 `python-dotenv`）
- 环境变量优先（已设置的 env 不会被 `.env` 覆盖）
- `get_db_connection()` 统一管理数据库连接
- `RUN_ID` 提供测试数据隔离前缀

**扩展新环境：** 创建 `.env` 文件覆盖默认值即可，无需修改 `config.py`

### report_collector.py + report_renderer.py — 报告系统分离

**设计原则：** 数据采集与呈现分离（Separated Presentation）。

**TestCollector** 管理场景生命周期（scene_start/end/skip）、步骤记录（step）、断言记录（assertion）。输出 `get_data()` 返回标准 dict。

**HtmlRenderer** 接收 Dict 数据，渲染为自包含 HTML。不存储状态，可多次调用。

**JUnitXmlRenderer / JsonRenderer** 同样接收 Dict 数据，输出不同格式。

**兼容层：** `report_helper.TestReport` 保持旧 API（`step(screenshot=page)` 自动检测 Playwright Page 对象并截图），内部委托给 Collector + Renderer。

### component_strategies/ — 组件适配层

**设计原则：** 抽象 UI 框架差异。

```python
from component_strategies import get_adapter
adapter = get_adapter("element-ui-vue3")  # 默认

# 统一接口
adapter.locate_select(page, "标签状态")       # → locator
adapter.locate_autocomplete(page, "元件模型") # → locator
adapter.select_option(page, locator, "草稿")  # → 选择操作

# 已知平台限制
adapter.known_limitations  # → {"select_option_visible": False, ...}
```

新增框架支持：创建新的 `Adapter` 子类实现 `ComponentAdapter` 接口即可。

### master_runner.py — 增强后特性

- **依赖跳过修复：** `dep_failed` 标记机制，正确跳过失败的依赖脚本
- **通用过滤：** `--exclude sn_lifecycle,some_script` 和 `--only e2e_full`
- **失败传播：** `sys.exit(1)` 当任何脚本失败
- **路径自适应：** `WORK_DIR` 使用 `__file__` 相对路径，`PYTHON` 使用 `sys.executable`

## 验证新组件的标准流程

```python
# 验证 collector + renderer
from report_helper import TestReport
r = TestReport("验证")
r.scene_start("S1", desc)
r.step("step1")
r.assertion("assert1", True, "ok")
r.scene_end(True)
r.generate_html()  # → 测试报告_{ts}.html

# 验证 JUnit 输出
from junit_renderer import JUnitXmlRenderer
data = r.get_data()
xml = JUnitXmlRenderer.render(data)

# 验证 JSON 输出
from json_renderer import JsonRenderer
j = JsonRenderer.render(data)

# 验证组件适配器
from component_strategies import get_adapter
adapter = get_adapter()
assert adapter.name == "element-ui-vue3"
assert adapter.autocomplete_debounce == 2.5
```


---

## 附录：架构重构记录（2026-06-08）

# 项目架构重构记录（2026-06-08）

> 全量端到端结构性重构：从扁平 root 结构重构为 `platforms/{id}/` 按平台维度隔离的架构。

## 目标结构

```
D:/AI/harmes agent/WEB平台自动化/
├── run.py              ← 统一入口 (python run.py --platform iot --headless)
├── config.py           ← 平台路由器（动态转发到 platforms.{PLATFORM}.config）
├── .env                ← 全局配置
│
├── core/               ← 通用核心代码（所有平台共享）
│   ├── runner.py                调度器（原 master_runner.py）
│   ├── report_helper.py         报告框架
│   ├── report_collector.py
│   ├── report_renderer.py
│   ├── json_renderer.py / junit_renderer.py
│   ├── manifest_generator.py
│   ├── component_strategies/    组件交互策略
│   └── templates/               J2 模板
│
└── platforms/           ← 各平台独立上下文
    ├── iot/             ← IoT 物联管理平台
    │   ├── config.py            平台配置（读自身 .env）
    │   ├── .env
    │   ├── scripts/
    │   │   ├── e2e/             端到端业务场景
    │   │   └── atomic/          原子功能测试
    │   ├── manifests/           本平台探索产出（15 JSON）
    │   ├── docs/reports/        测试报告（含 e2e/ 和 atomic/ 子目录）
    │   ├── docs/manuals/        操作手册
    │   ├── recordings/          录制脚本
    │   └── references/          本平台调试记录
    │
    └── tckz/            ← 总控平台（开发中）
```

## 核心设计决策

### 配置路由机制
- 根 `config.py` 是动态路由器，根据 `PLATFORM` 环境变量动态转发到对应的 `platforms.{id}.config`
- 脚本中 `from config import BASE_URL` 自动路由到当前平台
- `run.py` 通过 `--platform` 参数设置 `PLATFORM` 环境变量

### 报告输出
- 子报告（各脚本产出）：`platforms/{id}/docs/reports/e2e/` 或 `atomic/`
- 聚合报告（master runner）：`platforms/{id}/docs/reports/全量测试报告_{ts}.html`
- 每个脚本必须指定 `output_dir`：`TestReport("标题", output_dir=E2E_REPORT_DIR)`
- 文件名必须带 script_id 前缀：`generate_html(filename=f"{script_id}_测试报告_{_ts}.html")`

### 脚本分类
- `scripts/e2e/`：端到端业务场景（跨模块组合测试）
- `scripts/atomic/`：原子功能测试（单菜单全操作覆盖）
- 两类脚本数据完全隔离，使用不同的数据前缀

### 报告输出结构
- `docs/reports/e2e/`：端到端场景报告（每个 `e2e/` 脚本对应此处）
- `docs/reports/atomic/`：原子功能报告（每个 `atomic/` 脚本对应此处）
- `docs/reports/_archive/`：超过 7 天的旧报告自动归档
- `docs/reports/全量测试报告_{ts}.html`：聚合总报告（根级保留，不归档）
- `cleanup_old_reports()` 按 e2e/ → _archive/ 逐级清理，非直接删除

### script_id 修正记录
- `device_managent` → `device_management`（修复 typo，6/8 重构时一并完成）
- 旧报告文件 `device_managent_测试报告_*.html` 已移入 `_archive/`
- 对应 SCRIPTS 数组中的 `id` 和 `depends_on` 引用同步更新

## 清理操作记录
- 删除了 17 个一次性调试脚本（fix_*.py, debug_*.py, headed_*.py）
- 删除了 profiles/ 目录（内容已迁移到 platforms/）
- 删除了 root manifests/（迁移到 platforms/iot/manifests/）
- 删除了 explore 输出目录（中文名 + typo + URL编码）
- 删除了 node_modules/（7.5MB，单次 PPT 生成工具依赖）
- 删除了 generate_ppt.js, make_video.py 等单次工具
- 清理了 profiles/iot/scripts/ 下的陈旧副本
- 清理了 TCKZ 的 18 个调试文件
