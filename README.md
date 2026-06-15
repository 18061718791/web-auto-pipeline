# Web Auto Pipeline — 通用 Web UI 自动化流水线

基于 Playwright 的 Web UI 全流程自动化框架，支持平台探索、脚本生成、端到端执行、自愈（Self-Healing）和技能进化。已在 IoT 物联管理平台和 TCKZ 平台验证。

## 流水线总览

```
Phase 0: 平台全量探索
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
  └─ 聚合总报告（Cyberpunk 风格）
         ↓
Phase 4: 自愈与技能进化（持续）
  ├─ 事后诊断：28 种故障模式匹配
  ├─ 运行时治愈：6 模块 Healer（Selector/Component/Save/State/Assert/Recovery）
  ├─ 组件适配策略更新
  └─ 知识沉淀到 reference 文档
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 执行测试（IoT 平台，有头模式）
python run.py

# 无头模式
python run.py --headless

# 列出可用脚本
python run.py --list-scripts

# 仅执行指定脚本
python run.py --only device_management

# 排除指定脚本
python run.py --exclude sn_lifecycle
```

## 项目结构

```
├── run.py                          # 统一入口
├── config.py                       # 平台配置路由器（自动按 PLATFORM 环境变量切换）
├── requirements.txt                # 依赖：playwright, psycopg2-binary
│
├── core/
│   ├── runner.py                   # 核心运行器，依赖链调度 + 聚合报告
│   ├── manifest_generator.py       # Page Manifest → 脚本骨架生成
│   ├── report_collector.py         # 测试报告收集
│   ├── report_helper.py            # 报告辅助工具
│   ├── report_renderer.py          # HTML 报告渲染（Cyberpunk 风格）
│   ├── json_renderer.py            # JSON 输出
│   ├── junit_renderer.py           # JUnit XML 输出
│   ├── component_strategies/       # 组件交互策略（antd, element-ui）
│   ├── healer/                     # 运行时自愈系统（6 模块）
│   │   ├── orchestrator.py         # HealingOrchestrator 总调度
│   │   ├── selector_healer.py      # 选择器 5 级降级
│   │   ├── component_healer.py     # 组件交互重试
│   │   ├── save_healer.py          # 保存三重确认
│   │   ├── state_healer.py         # 页面状态恢复
│   │   ├── assert_healer.py        # 断言自愈
│   │   └── save_healer.py          # 保存自愈
│   └── templates/
│       └── page_script.j2          # 脚本生成模板
│
├── scripts/
│   ├── explorer_core.py            # Phase 0：平台探索引擎
│   ├── self_heal.py                # 事后自愈诊断（28 故障信号）
│   ├── component_utils.py          # 组件工具
│   └── metrics_collector.py        # 指标收集
│
├── docs/
│   ├── doc_recorder.py             # 文档录制
│   ├── html_renderer.py            # HTML 文档渲染
│   ├── pdf_renderer.py             # PDF 文档生成
│   └── replay_render.py            # 回放渲染
│
├── templates/                      # 用户输入模板
├── tests/                          # 测试
└── references/                     # 42 份知识文档（MUST 规则、故障目录、平台差异等）
```

## 核心特性

### 三层断言金字塔

1. **UI 断言** — `report.assertion()` 嵌入每一步，check_page_errors 覆盖 6 种错误形态
2. **DB 断言** — 通过 `information_schema.columns` 确认数据类型后写 SQL 断言
3. **异步轮询断言** — 发布等后台操作轮询最多 30 秒
4. **关联验证（第四层）** — 实体关联关系持久化验证

### 运行时自愈系统（Healer v2）

| 模块 | 功能 |
|:---|:---|
| SelectorHealer | 选择器 5 级降级（标准 → 文本 → 索引 → CSS → XPath） |
| ComponentHealer | 组件交互重试（el-select/el-cascader/el-autocomplete） |
| SaveHealer | 保存三重确认（API + URL + DB 轮询） |
| StateHealer | 页面状态恢复 |
| AssertHealer | 断言软化/重试 |
| HealingOrchestrator | 总调度 |

### 报告系统

- 单脚本 HTML 报告（一步一截图、断言内联展示、三态指示器）
- 聚合总报告（Cyberpunk 设计：SVG 环形图、指标卡片、Modal iframe 弹窗、星云动画）
- JSON + JUnit XML 输出（CI/CD 集成）

## 11 条 MUST 级规则

1. 场景间/场景内不允许重复导航
2. 断言是灵魂 — 禁止静默跳过
3. 异步操作必须轮询
4. 每个脚本附带 HTML 测试报告
5. 先隔离调试再整合
6. 每步操作后必须校验
7. 保存后必须 check_page_errors
8. 编辑后二次确认
9. 数据清理前置 + 依赖检查
10. 转移组件批操作必先检查勾选框
11. 每条路由必须实际验证后再写入

详见 `SKILL.md` 和 `references/core-principles.md`。

## 环境要求

- Python 3.9+
- Playwright + Chromium
- PostgreSQL（被测平台使用）
- Windows / Linux

## 许可

内部使用
