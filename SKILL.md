---
name: web-auto-pipeline
description: Web UI 自动化流水线 — 平台探索 → 脚本生成 → 场景执行与验证 → 自愈与进化。支持多平台数据隔离、组件交互策略、三层断言+关联验证、HTML 报告、CI/CD 集成。
triggers:
  - web自动化
  - 端到端测试
  - 页面探索
  - 脚本生成
  - 自愈
  - 场景设计
  - 数据隔离
  - ensure_on_page
  - check_page_errors
  - save_and_verify
  - HealingOrchestrator
allowed-tools:
  - read
  - write
  - edit
  - glob
  - grep
  - question
  - bash
  - task
  - webfetch
  - browser_navigate
  - browser_snapshot
  - browser_click
  - browser_type
  - browser_console
tags:
  - testing
  - automation
  - playwright
  - self-healing
  - e2e
  - ui-testing
  - element-plus
  - shadcn-ui
related_skills:
  - webwright
  - hybrid-web-autotester
---

# Web Auto Pipeline — 通用 Web UI 自动化流水线

> 从 Microsoft Webwright 原型演进而来。增加了三层断言金字塔、结构化报告体系、Runner 依赖链调度、运行时自愈和平台隔离架构。

## 流水线总览

```text
Phase 0: 平台全量探索（自动）
  ├─ 路由发现 + 深度探索 + 组件识别 + DB 探测
  └─ 产出: Page Manifest JSON + HTML 分析报告
         ↓
Phase 1: 脚本骨架生成
  └─ manifest_generator.py 读取 Manifest → Playwright 脚本骨架
         ↓
Phase 2: 场景填充 → 执行验证
  ├─ 三层断言金字塔（UI → DB → 异步轮询）
  ├─ check_page_errors 检测
  └─ HTML 测试报告 + 截图
         ↓
Phase 3: 多脚本聚合 → CI/CD
  ├─ core/runner.py 依赖链调度
  ├─ JSON + JUnit XML 输出
  └─ 聚合总报告
         ↓
Phase 4: 自愈与技能进化（持续）
  ├─ 事后诊断：故障目录匹配（self_heal.py）
  ├─ 运行时治愈：6 模块 Healer（Selector/Component/Save/State/Assert/Recovery）
  ├─ 组件适配策略更新
  └─ 知识沉淀到 reference 文档
```

### 实现状态

| Phase | 状态 | 实现 |
|:---|:---:|:---|
| Phase 0 探索 | ✅ | `scripts/explorer_core.py`，方法论见 `references/platform-exploration-methodology.md` |
| Phase 1 骨架生成 | 🔶 | `core/manifest_generator.py`，详参 `references/manifest-system.md` |
| Phase 2 场景执行 | ✅ | 15 个已验证脚本（4 E2E + 11 基础功能） |
| Phase 3 CI/CD | ✅ | `core/runner.py` + `run.py`，cyberpunk 主题报告 |
| Phase 4 自愈 | ✅ | 事后诊断 + 运行时 Healer（`core/healer/` 6 模块） |

---

## 11 条 MUST 级规则（概要；完整示例+反例见 `references/core-principles.md`）

1. **场景间/内不允许重复导航** — 每个场景的起始状态基于上一场景结束状态。SPA 同路由重导航触发 Vue 完整重渲染（15s+）。用菜单直接点击替代回首页重导航。🆘 详见 → `references/SKILL_DETAIL.md §1`

2. **断言是灵魂 — 禁止静默跳过** — if/else 两个分支都必须有显式断言。`scene_end(True)` 的充要条件：所有 `report.assertion` 为 True + `check_page_errors` 无错误 + 无未捕获异常。🆘 详见 → `references/SKILL_DETAIL.md §2`

3. **异步操作必须轮询** — 发布等后台操作有延迟，循环检查状态列，最多等 30 秒。

4. **每个脚本附带 HTML 测试报告** — `TestReport("标题")` **必须传** `output_dir=get_script_report_dir('e2e|atomic', 'script_id')`。

5. **先隔离调试再整合** — 复杂交互创建独立 `*_debug.py` 验证后移植。有头模式 + 1920x1080 viewport。

5b. **自主执行模式** — 用户说「一直执行下去不要中断」时，不提问、不确认、自行处理可恢复失败、最后一次性交付。

6. **每步操作后必须校验** — el-select 选后检查下拉文本；保存后 DB + UI 双重验证。表单字段占位符必须用 `browser_snapshot` 确认。🆘 详见 → `references/SKILL_DETAIL.md §1`

7. **保存/发布后必须 check_page_errors + 截图 + 提前 return** — 或使用 `h.save_and_verify()`。`check_page_errors()` 返回值必须检查，有错误则 `scene_end(False); return`。

8. **编辑后二次确认** — 保存后重新进入编辑页验证 UI 数据正确。

9. **数据清理前置 + 依赖检查** — 清理放在脚本开头。所有测试数据用 `AUTO_` 前缀。🆘 详见 → `references/SKILL_DETAIL.md §5`

10. **转移组件批操作必先检查勾选框状态** — 逐行控制勾选后再点操作按钮。

11. **每条路由必须浏览器验证后写入脚本** — 绝不从 URL 模式推断。先查 `references/platform-diff.md`，再实际验证。

---

## 测试分类原则（概要；详见 `references/scene-design.md`）

| 分类 | 维度 | 数据 | 命名 |
|:---|:---|:---|:---|
| **基础功能** | 一个菜单一个脚本 | 自造自清理 | `{menu}_atomic_test.py` |
| **端到端** | 一个业务流一个脚本 | 脚本内按依赖链创建 | `{flow}_test.py` |

**核心规则**：基础功能脚本完全自包含，数据隔离，不与端到端脚本共享数据。端到端脚本必须先画出数据依赖有向图。

---

## 组件交互方案速查

| 组件 | 方案 | 详细参考 |
|:---|:---|:---|
| el-select | `force=True` 打开 → `.el-select-dropdown__item` + `force=True` 点击 | `references/element_ui_patterns.md` |
| el-cascader | `force=True` 打开 → 点 checkbox → Escape 关闭 | `references/el-cascader-trap.md` |
| el-autocomplete | fill → 等 3s → 选项列表 + `force=True` 点击 → Escape | `references/el-autocomplete-trap.md` |
| ComponentHealer | `h.autocomplete_select(hint, text)` 三级降级 | `references/self-healing-v2-design.md` |
| el-upload | `.el-upload` 包装器 → `expect_file_chooser()` → `set_files(path)` | `references/file-upload-technique.md` |
| el-tree | `.inner_text()` 或 `.node-actions` 定位 | `references/fragility-audit-checklist.md` |
| Radix/Shadcn UI | Playwright 原生 click()，隐藏 `input[type="file"]` | `references/shadcn-ui-patterns.md` |
| SPA 列表页（菜单过滤） | 必须通过左侧菜单点击导航，不能直达 URL | 见平台特定路由映射 |

> **定位规则**：不要猜测。先跑 FIELD_SCAN 代码确认 label/placeholder，再写定位代码。🆘 完整定位模式 → `references/SKILL_DETAIL.md §1`

---

## HealingOrchestrator 快速集成

```python
from core.healer import HealingOrchestrator
h = HealingOrchestrator(page, report, db_connection_fn=get_db_connection)

h.fill("请输入PV名称", "test-PV")                        # 7 级选择器降级
h.save_and_verify("保存PV", db_verify_fn=find_pv, ...)  # API/URL/toast/DB 四路检测
h.assert_db("DB: 已软删除", "table", "col", row[0], True) # 自动查类型
h.heal_between_scenes(expected_url=PV_LIST_URL)         # 场景衔接自愈
h.print_summary()
```

🆘 完整文档+集成陷阱 → `references/SKILL_DETAIL.md §6`

---

## 文件索引

### 引用文件（`references/`）

| 文件 | 内容 |
|:---|:---|
| `core-principles.md` | 11 条 MUST 规则完整版（代码示例、反例、审计清单） |
| `scene-design.md` | 场景设计规范（状态机、CRUD、检查清单、scenes.json） |
| `manifest-system.md` | Page Manifest 系统 + JSON Schema |
| `SKILL_DETAIL.md` | **运营详细指南**（定位模式、断言增强、数据清理、Healer 完整文档等） |
| `example-device-atomic.md` | 用户输入模板完整示例 |
| `element_ui_patterns.md` | Element Plus 全组件交互方案 |
| `shadcn-ui-patterns.md` | Shadcn UI / Radix UI 交互参考 |
| `self-healing-v2-design.md` | 自愈 v2 设计文档 |
| `failure-catalog.md` | 26 条故障信号 + 诊断流程 |
| `verify-save-pattern.md` | 防静默保存失败模式 |
| `assertion-integrity.md` | 断言完整性强制要求 |
| `platform-diff.md` | IoT 平台特定（URL映射、placeholder、BUG、DB字段） |
| `debugging-workflow.md` | 脚本调试工作流 |
| `ppt-narrative-pattern.md` | PPT 叙事结构模式 |

> 完整索引见 `references/README.md`

### 核心代码（`core/`）

| 文件 | 用途 |
|:---|:---|
| `runner.py` | 调度器（含 argparse、依赖链、报告聚合） |
| `report_helper.py` | TestReport 报告框架 |
| `report_renderer.py` | HTML 报告渲染器 |
| `manifest_generator.py` | Page Manifest → 脚本骨架 |
| `healer/` | 运行时自愈 6 模块 + HealingOrchestrator |
| `component_strategies/` | 组件交互策略 |

### 脚本与模板

| 位置 | 用途 |
|:---|:---|
| `scripts/explorer_core.py` | Phase 0 探索引擎 |
| `scripts/component_utils.py` | 组件交互工具函数 |
| `scripts/self_heal.py` | Phase 4 故障诊断 |
| `templates/user-input-template.md` | 标准用户输入模板 |
| `platforms/iot/scripts/` | 15 个已验证脚本 |

---

## 快速参考

### 报告命名铁律

- **必须** `{script_id}_测试报告_{ts}.html`，禁止裸 `测试报告_{ts}.html`
- `TestReport("标题")` **必须** 传 `output_dir=get_script_report_dir('e2e|atomic', 'script_id')`

### 数据清理铁律

- 所有测试数据用 `AUTO_` 前缀
- 脚本跑完后必须清理（finally 块 + LIKE 模式）
- 按模块匹配正确表（SN→`device_sn`，模型→`thing_model`）
- 🆘 详见 → `references/SKILL_DETAIL.md §5`

### Runner 调用

```bash
python run.py --platform iot --headless        # 全量执行
python run.py --platform iot --only device_management  # 单脚本
python run.py --platform iot --list-scripts      # 列出可用脚本
```

> **不要** 向 runner 传递 `--platform`，runner 只有 `--headless/--exclude/--only/--list`。

---

## 添加新平台步骤

1. 在 `platforms/` 下创建新目录，复制 `iot/` 骨架
2. 编写 `.env` 和 `config.py`（设置 `PLATFORM_ID`/`SCRIPTS`/`ATOMIC_SCRIPTS`/`SCRIPT_REPORT_SUBDIRS`）
3. 运行 `python run.py --platform <id> --list-scripts` 验证
4. 确认 UI 框架类型：Element Plus → `references/element_ui_patterns.md`，Shadcn/Radix → `references/shadcn-ui-patterns.md`
5. 编写脚本（参考已验证 IoT 脚本模式）
6. 验证：`python run.py --platform <id> --only <script_id>`

---

## 工作方式纪律

1. **未知领域先调研再执行** — 系统性列出所有可能方案、逐一验证
2. **结论先说，细节后补** — 优先给出判断
3. **破坏性操作必须预览征求同意** — 先列受影响文件
4. **决策场景只给最优方案** — 不给选择题
5. **一次性执行完整计划** — 不递进式询问
6. **修改 reference 后必须维护交叉引用一致性** — 同步更新 SKILL.md 索引和规则
7. **不提交需讨论的 todo** — 直接决策或标记暂停

🆘 常用工具陷阱、Python 陷阱、脚本模板 → `references/SKILL_DETAIL.md §11-13`