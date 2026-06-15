# IoT Platform Tester — 三方评审报告

> 日期: 2026-06-03
> 目标: 将 `iot-platform-tester` 从平台特定脚本集合升级为通用 Web UI 自动化测试框架
> 评审团队: 测试架构师 / 框架工程师 / DevOps & 安全工程师

---

## 一、评审 1: 测试架构视角

### 1. 测试原则

**亮点:**
- 三层断言金字塔（UI + DB + 异步轮询）定义清晰，硬性规定不软降级
- `--start-scene N` 断点续跑设计合理
- 数据清理前置而非结尾，架构上正确支持生产者-消费者模式

**缺口与建议:**

| 问题 | 严重度 | 建议 |
|:---|---:|:---|
| 缺少负面断言模式 | HIGH | 增加"元素不应存在/按钮应禁用"等反向断言模式 |
| 没有异常捕获断言模式 | HIGH | `try/except → report.assertion(..., False, str(e)) → scene_end(False)` 标准化 |
| 断言无严重等级 | MEDIUM | 增加 `severity="blocker"|"critical"|"info"` 字段 |
| 清理只有 SQL，无 UI 清理 | MEDIUM | 增加 UI 驱动的清理模式作为 SQL 的 fallback |
| `--start-scene` 不恢复页面状态 | MEDIUM | 文档化场景首部应加导航守卫 |

### 2. 测试设计方法论

**亮点:**
- 状态机分析显式文档化（states/transitions/state_actions）
- CRUD + 状态转换检查清单实用
- "只增不改"反模式被明确禁止

**缺口与建议:**

| 问题 | 严重度 | 建议 |
|:---|---:|:---|
| 缺少等价类划分 | HIGH | 增加字段级 `equivalence_classes: {valid, boundary, invalid}` 表 |
| 缺少边界值分析 | HIGH | 空字符串、最大长度、特殊字符、SQL注入等模式 |
| 没有逆向场景 | HIGH | 必填字段为空、重复名称、非法状态转换 |
| 状态机仅文档化未强制执行 | MEDIUM | 增加场景验证器检查每个状态/转换都有测试覆盖 |
| 无数据驱动/参数化模式 | MEDIUM | `@pytest.mark.parametrize` 或简单 dict 驱动循环 |
| 主 E2E 缺少 DELETE/UPDATE | MEDIUM | "只增不改"原则应在主脚本中强制 |

### 3. 生命周期管理

| 问题 | 严重度 | 建议 |
|:---|---:|:---|
| 无并行执行支持 | HIGH | `--parallel N` + 依赖图调度 + 数据命名空间隔离 |
| 无数据隔离/命名空间 | HIGH | `TEST_RUN_ID` 时间戳前缀 |
| 无 fixture/setup-teardown 模式 | MEDIUM | `SceneContext` 类管理设置/执行/断言/清理 |
| 无 teardown 模式 | MEDIUM | 异常时关闭浏览器、重置状态、清除 cookie |
| 浏览器会话管理 ad-hoc | MEDIUM | `BrowserSession` 上下文管理器 + 超时重认证 |
| 无重试/flaky 容错 | LOW | `--retry N` 场景级重试 |

### 4. 报告系统

**亮点:** 自包含 HTML、三态指示器、自动降级、step-assertion 绑定

**缺口:**

| 问题 | 严重度 | 建议 |
|:---|---:|:---|
| 无结构化输出（JUnit/Allure） | HIGH | `generate_junit_xml()` + `--format junit\|html\|allure` |
| 无测试时间粒度 | MEDIUM | `time.time()` 获取场景/步骤耗时 |
| 无失败分类 | MEDIUM | assertion_failure vs timeout vs page_error |
| 截图大小不可控 | LOW | 可选 `viewport_only=True` + 压缩配置 |
| 无趋势对比 | LOW | 跨运行结果累加到 SQLite/JSON |

---

## 二、评审 2: 框架工程视角

### 1. Manifest JSON Schema — 5/10

**亮点:** 字段级粒度好、`known_bugs` 优秀模式、`post_save_behavior` 实用

**严重问题:**
- 无 schema 版本号 → 无法迁移
- `test_value` 嵌入环境特定数据 → 应运行时注入
- DB 断言引用特定表名 → 应可配置
- 无 `base_url` 环境抽象
- Element UI 选择器硬编码
- `scenes.json` type 字段缺失

### 2. manifest_generator.py — 4/10

**亮点:** 组件到 Playwright 的映射合理、`--compose` 模式有前瞻性

**严重问题:**
- 字符串拼接生成代码 → 无法验证语法、无法单元测试
- DB 凭证嵌入生成代码 → 安全风险
- 无错误处理脚手架
- 不生成 `--start-scene` CLI 参数
- 不生成 `report.step/assertion` 调用
- 断言代码是在 Python f-string 中嵌入 JavaScript 字符串 → 不可维护

### 3. TestReport 架构 — 6/10

**亮点:** API 简洁、自动降级防止假通过、三态指示器、step-assertion 绑定

**严重问题:**
- God class: 数据收集和 HTML 渲染纠缠在一起
- `generate_html()` 是 270 行 f-string 单体 → 样式修改风险大、无法本地化
- 无序列化/导出 → 执行崩溃则数据全丢
- `screenshot=page` 紧耦合 Playwright
- 无 `record_exception()` 方法
- `_log()` 仅 `print()`，无等级控制

### 4. master_runner.py 依赖链 — 4/10

**亮点:** 简单可理解、依赖跳过逻辑存在、聚合报告质量好

**严重问题:**
- stdout 正则解析脆弱 — 格式变更即断裂
- 600 秒固定超时不可配置
- 无重试机制
- 无并行执行
- 路径硬编码 (Windows-specific)
- `--skip-sn` 是脚本特定 hack
- 依赖跳过有 bug: `continue` 只跳过内层循环，脚本仍执行

### 5. 框架通用性 — 2/10

需要完全重构为：
```
web_ui_tester/
├── core/          config, collector, runner
├── renderer/      html, junit, json
├── adapter/       base.py, element_ui.py
├── manifest/      schema, generator, scenes
└── assertions/    ui, db, api
```

关键抽象: `ComponentAdapter` ABC、`AssertionBackend` ABC、`BrowserAdapter` ABC

---

## 三、评审 3: DevOps & 安全视角

### 1. CI/CD 集成 — 状态: 不可集成

| 要求 | 状态 |
|:---|---:|
| JUnit XML | ❌ 缺失 |
| Allure 格式 | ❌ 缺失 |
| 结构化输出 | ❌ 缺失 |
| Exit code 传播 | ⚠️ 部分（master_runner 不 exit 1） |
| 选择性执行 | ⚠️ 部分（--start-scene 但有 script 特定参数） |

### 2. 安全隐患 — 严重度: CRITICAL

| 问题 | 严重度 | 位置 |
|:---|---:|:---|
| 硬编码 DB 凭证 | CRITICAL | 14 个 .py 文件 (postgres/123456) |
| 硬编码内网 IP | HIGH | 每个脚本 BASE_URL |
| 明文密码 | CRITICAL | "123456" 出现在 13+ 文件 |
| 无 HTTPS | MEDIUM | 凭证和会话 cleartext 传输 |
| 使用 DB 超级用户 | CRITICAL | 应为只读角色 |
| 截图含敏感数据 | HIGH | HTML 报告无访问控制 |
| 生成器产生凭证 | CRITICAL | manifest_generator.py 内置凭证到生成代码 |

### 3. 环境配置 — 状态: 缺失

- 无配置层
- 无法切换 dev/staging/prod
- Windows 硬编码路径
- 无 `.env` 文件支持

### 4. 可复现性

**优势:** 脚本开头清理、--start-scene、--no-cleanup、自动降级防止假通过

**劣势:** 硬编码数据名不能并行运行、`time.sleep()` 约 30+ 处、bare `except`、无 requirements.txt

### 5. 缺失的 DevOps 实践

| 实践 | 优先级 |
|:---|---:|
| requirements.txt | P0 |
| .gitignore | P0 |
| Exit code 传播 | P0 |
| JUnit XML | P1 |
| 重试机制 | P1 |
| 并行执行 | P1 |
| 唯一运行 ID 数据隔离 | P1 |
| logging 替代 print | P1 |
| Docker 支持 | P2 |
| CI 流水线定义 | P2 |

---

## 四、重构计划概要

完整计划见 `.hermes/plans/20260603_refactor-universal-skill.md`

**5 阶段，20+ 任务:**

| 阶段 | 内容 | 优先级 |
|:---|---|:---:|
| Phase 0 | config.py + .env + .gitignore + requirements.txt + 14 脚本凭证外置 | P0 |
| Phase 1 | report_helper 分拆、master_runner bug 修复、generator 模板化 | P1 |
| Phase 2 | 组件适配层、多环境配置 | P1 |
| Phase 3 | JUnit XML、exit code、JSON 结果文件 | P1 |
| Phase 4 | 场景定义规范化、等价类/边界值、逆向场景 | P2 |
| Phase 5 | 配置验证、三个核心脚本回归、runner/generator 回归 | P0 |

**验收标准（7 条）:**
1. 全仓库 `grep "password.*123456"` = 0 匹配
2. 3 个主力脚本全部通过，无回归失败
3. `master_runner.py` exit code 1 当有失败
4. JUnit XML 输出可被 CI 解析
5. `ComponentAdapter` 接口 + Element UI 实现
6. 等价类/边界值/逆向场景方法论文档
7. `pip install -r requirements.txt` 可运行
