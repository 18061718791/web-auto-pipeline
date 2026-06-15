---
name: web-auto-pipeline
description: 通用 Web UI 自动化流水线 — 平台探索 → Page Manifest 生成 → 自动化脚本骨架生成 → 端到端场景执行与验证 → 脚本自愈（self-healing）→ 技能进化（skill evolution）。含多平台数据隔离、组件交互策略（el-select/el-cascader/el-autocomplete）、严格断言校验、HTML 报告系统、CI/CD 集成。基于 IoT 物联管理平台实现并验证。
triggers:
  - 自动化测试
  - web自动化
  - 端到端测试
  - 测试框架
  - 页面探索
  - 探索平台
  - 分析平台
  - 生成平台报告
  - 脚本生成
  - 自愈
  - 回归测试
  - 测试设计
  - 组件交互
  - el-select
  - el-tree
  - el-cascader
  - el-autocomplete
  - el-upload
  - 确认对话框
  - 文件上传
  - 文件导入
  - 导入
  - 批次导入
  - 多平台
  - 数据隔离
  - ant-design
  - shadcn-ui
  - radix-ui
  - nextjs
  - spa登录
  - 租户选择
  - ensure_on_page
  - check_page_errors
  - 场景设计
  - 自愈
  - healer
  - 运行时治愈
  - 保存自愈
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
tags: []
related_skills:
  - hermes-agent-skill-authoring
  - webwright  # webwright is the prototype precursor; web-auto-pipeline is its production-grade evolution with structured assertions, reports, runner, self-healing, and platform isolation
  - hybrid-web-autotester  # simplified 2-phase precursor; web-auto-pipeline is the full 5-phase production framework
---

# Web Auto Pipeline — 通用 Web UI 自动化流水线

> 从 Microsoft Webwright 原型演进而来。webwright 的 walk-one-step-verify-one-step 方法论和 Element Plus 交互经验在此沉淀为 MUST 规则和 references/ 知识库。相比 webwright 的「单次任务驱动」，本框架增加了三层断言金字塔、结构化报告体系、Runner 依赖链调度、运行时自愈和平台隔离架构。

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

| Phase | 状态 | 当前实现 |
|:---|:---:|:---|
| Phase 0 探索 | ✅ | `scripts/explorer_core.py` 可运行；完整4阶段方法论见 `references/platform-exploration-methodology.md`（含 Phase 2 自动化分析脚本模板 + Phase 3 表单字段提取 + Phase 4 数据依赖图） |
| Phase 1 骨架生成 | 🔶 骨架完成 | 手动编写 manifest 后生成脚本；`core/manifest_generator.py` |
| Phase 2 场景执行 | ✅ 已验证 (IoT) | `platforms/iot/scripts/{atomic,e2e}/` 有 15 个脚本（4 E2E + 11 基础功能） |
| | Phase 3 CI/CD 聚合 | ✅ 就绪（**2026-06-10 升级**） | `core/runner.py` 调度器 + `run.py` 入口；全量报告升级为 cyberpunk 设计（SVG 环形图/指标卡片/Modal iframe 弹窗/星云动画），子报告同步升级（in-iframe 检测/场景卡片强调色/断言徽章内联）。全量报告分两个模块（🚀 端到端场景 + 📦 基础功能），端到端展示数据流向图，基础功能因数据独立不展示 |
| Phase 4 自愈 | ✅ 事后诊断 + ✅ 运行时 | `self_heal.py` 故障目录 28 信号；`core/healer/` 6 模块运行时 Healer，13 个脚本已集成基础框架，3 个脚本启用运行时 Healer |

### 核心能力速查

| 阶段 | 产出 | 方法 |
|:---|:---|:---|
| **探索** | 页面结构化描述、组件交互陷阱、Page Manifest | 自动: Vue Router 全量路由发现 + 菜单遍历 + Hermes browser 逐页深度探索 |
| **建模** | `manifests/*.json`（字段/按钮/对话框/断言） | 按 schema 编写或从探索记录转换 |
| **生成** | 脚本骨架（Playwright function + 断言占位） | `manifest_generator.py`（参见 `references/manifest-system.md`） |
| **执行** | HTML 报告 + 断言结果 + JSON 输出 | 场景函数链 + `TestReport`（参见 `references/report-system.md`） |
| **自愈** | 选择器 5 级降级、组件交互运行时重试、保存三重确认、页面状态恢复 | 组件适配层 + `self_heal.py` 事后诊断 + `core/healer/` 运行时治愈（Selector/Component/Save/State/Assert/Recovery + HealingOrchestrator） |

---

## 11 条 MUST 级规则（含 1 条子规则，完整解释见 `references/core-principles.md`）

1. **场景间 / 场景内都不允许重复导航** — MUST 级，严格评审点。

   **原则**：脚本中每个场景的起始状态必须基于上一场景的结束状态。如果上一场景完成时已停留在目标页面（包括已执行过搜索/筛选），当前场景必须直接操作当前页面，**不得**重新 `page.goto`、`page.reload`、重新输入搜索条件再点搜索。

   **反例（被评审否决）**：
   ```python
   # 场景6：创建设备模型 → 保存 → 留在 controllerType/clist 列表页（搜索已完成）
   page.goto(f"{BASE_URL}/controllerType/clist", wait_until="networkidle")
   page.get_by_placeholder("模型名称").fill(MODEL_NAME)
   page.get_by_role("button", name="搜索").click()

   # 场景7：发布设备模型
   # ❌ 错误：场景6已经在此页面且搜索完成，不应重复 goto + 搜索
   page.goto(f"{BASE_URL}/controllerType/clist", wait_until="networkidle")
   page.get_by_placeholder("模型名称").fill(MODEL_NAME)
   page.get_by_role("button", name="搜索").click()
   row = page.locator("tr").filter(has_text=MODEL_NAME)
   row.locator("button").filter(has_text="版本详情").click()
   ```

   **正例（通过评审）**：
   ```python
   # 场景6：创建设备模型 → 保存 → 留在 controllerType/clist（搜索已完成）

   # 场景7：发布设备模型
   # ✅ 正确：直接在当前页面操作，无需重复导航/搜索
   row = page.locator("tr").filter(has_text=MODEL_NAME)
   assert row.count() > 0, f"断言失败: 模型'{MODEL_NAME}'不在列表中"
   row.locator("button").filter(has_text="版本详情").click()
   ```

   **场景内部同样适用**：如果一个操作（搜索/筛选/翻页）已经执行过，后续步骤不要重复执行。整个脚本的页面流动应该像一个连续的操作序列：

   ```
   场景A: goto(列表页) → search → click(详情) → verify → back(列表页)
   场景B: click(编辑) → edit → save → verify → 停留在列表页
   场景C: click(发布) → confirm → verify
   ```
   而不是：
   ```
   场景A: goto(列表页) → search → click(详情) → verify → goto(列表页) → search
   场景B: goto(列表页) → search → click(编辑) → edit → save → goto(列表页) → search
   场景C: goto(列表页) → search → click(发布)
   ```

   **⚠️ Vue SPA 同路由重导航陷阱（2026-06-10 实测）**：在 Vue SPA 中，通过菜单点击触发**与当前页面相同的路由**并非无操作——Vue Router 会执行完整的组件卸载→重新挂载→API 数据重请求的生命周期。在服务端响应较慢的环境下，这一过程可长达 15 秒+。

   **诊断方法**：在菜单导航前记录 URL，对比 `page.url` 与目标路由。如果已经在同一路由上，菜单点击触发的就是重导航而非新导航。

   **具体表现**：`page.goto(url)` 只花 0.2 秒，紧接着的 `navigate_to_device_list(page)`（菜单点击）也看似只花 1 秒（含 time.sleep），但后续的 `get_by_role("button").click()`（如"快速初始化"按钮）却花了 16 秒。原因是 Playwright 的 `click()` 内置 auto-wait 被 Vue 重渲染阻塞——组件在 15 秒后才就绪。

   **修复**：直接删除冗余的菜单导航调用。`page.goto` 已经初始化了 SPA 路由，无需再次触发重导航。从 page load 到按钮可点击的耗时从 ~18s 降到 ~3s。

   **实测数据（2026-06-10）**：
   ```
   修复前: page.goto(0.24s) → navigate_to_device_list(1.01s) → navigate_to_quick_init(16.14s) = ~18s
   修复后: page.goto(0.60s) → ← 跳过 → navigate_to_quick_init(1.17s) = ~3s
   ```
   16s 的瓶颈不在任何 `time.sleep` 中，而在 Playwright `click()` 的 auto-wait 被 Vue 重渲染阻塞。

   **边界情况处理**：如果场景A和B之间跨越了不同的数据对象（如场景A操作元件、场景B操作设备），且不在同一个页面下，才允许 `page.goto`。**判断标准**：是否同一张列表页 + 搜索条件相同。

   **例外**：仅在确认当前页面状态无法满足下一步需求时（如页面因保存操作自动跳转到空白页 `about:blank`），才允许重新导航。此时必须在 goto 前加注释说明原因。

   ### ✅ 推荐实现：左侧菜单直接点击跨场景切换（替代回首页重导航）

   对于有统一左侧菜单的 SPA 应用，场景间切换应直接点击左侧菜单项，而非回首页重新点菜单或使用顶部 tab 链接：

   ```python
   def click_menu_item(page, text):
       """直接点击左侧菜单项（不回首页，不用顶部tab）"""
       return page.evaluate("""(text) => {
           var items = document.querySelectorAll('.el-menu-item');
           for (var item of items) {
               var t = item.innerText.trim();
               if (t === text || t.includes(text)) {
                   item.click(); return true;
               }
           }
           return false;
       }""", text)

   # 使用：场景4 → 5 → 6 直接菜单切换
   click_menu_item(page, "全局视图")     # 从装置列表 → 全局视图
   click_menu_item(page, "系统视图")     # 从全局视图 → 系统视图
   # 返回装置列表需要展开子菜单再点击子项
   click_menu_item(page, "装置")         # 从系统视图 → 装置列表
   ```

   **⚠️ 菜单子项歧义处理**：当菜单项和子菜单标题文字相同（如"装置"既是子菜单标题又是子菜单项），需用 `closest('.el-sub-menu')` 区分：
   ```python
   page.evaluate("""() => {
       var subs = document.querySelectorAll('.el-sub-menu__title');
       for (var s of subs) {
           if (s.innerText.trim() === '装置') {
               var parent = s.closest('.el-sub-menu');
               if (parent && !parent.classList.contains('is-opened')) { s.click(); }
               break;
           }
       }
       setTimeout(function() {
           var items = document.querySelectorAll('.el-menu-item');
           for (var item of items) {
               var t = item.innerText.trim();
               if (t === '装置') {
                   var parentSub = item.closest('.el-sub-menu');
                   if (parentSub) { item.click(); return; }
               }
           }
       }, 500);
   }""")
   ```

   **首次进入**仍通过 goto 首页 + 左侧菜单导航（确保 SPA 状态正确初始化），后续跨场景全部用菜单直接点击。

   **不推荐顶部 tab 链接**：原因一是部分 SPA 页面的 tab 不会重新加载数据上下文，二是用户明确表达了此偏好。

   **同一场景内的操作链条必须紧凑**：不要在同一步骤之间插入无关的页面跳转或搜索。例如：新增保存后直接验证列表，列表验证完成后直接进行发布操作，不要在列表验证和发布之间重新 goto 列表页。

   ### ⚠️ 场景边界页面状态陷阱

   **最隐蔽的失败模式**：场景内的验证步骤（如点击"查看详情"）会改变页面状态，但下一场景假设列表页仍处于激活状态。

   **典型故障链**：
   ```
   场景4: goto(编辑页) → fill → save → goto(列表页) → search → 验证列表 ✓
          → click(查看详情)  ← 进入了详情页！
          → 验证详情页数据 ✓
          → scene_end()     ← 此时页面在详情页，不在列表页
   场景5: row = page.locator("tr").filter(has_text=NAME)  ← ❌ 无 tr
          → assert row.count() > 0  ← 断言失败
   ```

   **修复方案（推荐方案A）**：
   方案 A（多场景依赖链场景必选）：在场景结束前，明确返回列表页并恢复搜索状态。
   ```python
   # 场景4 末尾
   page.goto(f"{BASE_URL}/element/eDeviceList", wait_until="networkidle")
   time.sleep(1)
   page.get_by_placeholder("请输入元件名称").fill(EL_NAME)
   page.get_by_role("button", name="搜索").click()
   time.sleep(2)
   ```
   方案 B（独立启动的场景）：场景5启动时检测当前 URL 判断是否需导航。
   ```python
   if "eDeviceList" not in page.url:
       page.goto(f"{BASE_URL}/element/eDeviceList", ...)
   ```

   **判断标准**：依赖链中间环节用方案A，独立启动用方案B。

2. **断言是灵魂 — 禁止静默跳过 / 结果诚实不可妥协** — MUST 级，严格评审点。

   **核心原则**：脚本中每个关键操作（下拉选择、模型关联、搜索、保存、字段填写）必须在**所有分支路径上都有显式断言**。`if ... else ...` 的两个分支都必须有断言，不存在"这里没找到应该不会发生"的假设。

   ### ⚠️ 静默跳过 = 虚假通过

   **反例（被评审否决）**：
   ```python
   # ❌ else 分支没有任何断言 — 即使关联失败，测试仍然标记为"通过"
   el_opt = page.locator("[role='option']").filter(has_text=EL_NAME).first
   if el_opt.count() > 0:
       el_opt.click()
       time.sleep(0.5)
   ```

   **正例（必须这样写）**：
   ```python
   el_opt = page.locator("[role='option']").filter(has_text=EL_NAME).first
   opt_found = el_opt.count() > 0
   if opt_found:
       el_opt.click()
       time.sleep(0.5)
       log(f"    ✅ 元件已关联: {EL_NAME}")
   else:
       log(f"    ❌ 元件下拉选项未出现: {EL_NAME}", "❌")
       page.evaluate("document.querySelector('.el-overlay')?.remove()")
   # ★ 无论 found 与否，都必须有断言
   report.assertion("关联已发布的元件", opt_found,
                    EL_NAME if opt_found else "下拉选项未出现")
   ```

   ### 断言覆盖检查清单

   - [ ] **下拉选择**：选项出现才点击 → else 分支必须有 `report.assertion(..., False, "选项未出现")`
   - [ ] **tab切换**：`tab.count() > 0` 的 false 分支必须有断言
   - [ ] **保存后**：`check_page_errors` + UI 列表 + DB + **关联关系验证**（详见关联验证）
   - [ ] **发布后**：UI 状态列 + DB 状态字段
   - [ ] **搜索后**：搜索结果行数 > 0

   ### "场景通过"的定义

   `scene_end(True)` 的充要条件：该场景内所有 `report.assertion` 均为 True + `check_page_errors` 无错误 + 无未捕获异常。如果某子操作因选项不存在而静默跳过，即使后续保存成功，**该场景也必须标记为失败** — 因为实际的业务操作未执行。

   ### ⚠️ DB 断言反模式：猜类型不查表

   写 SQL 断言前，必须先查 `information_schema.columns` 确认数据类型。猜错类型（如 boolean 当成 integer 比较）会导致断言永远静默失败。

   **反例（2026-06-09 标签脚本 scene7 调试已验证）：**
   `device_tags.is_delete` 是 `boolean` 类型，断言写成 `str(True) == "1"` → `"True" == "1"` → 永不通过。

   **正确做法**：
   ```python
   cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='device_tags' AND column_name='is_delete'")
   # data_type='boolean' → 用 db_row[0] is True
   # data_type='integer'  → 用 db_row[0] == 1
   ```

   ### ⚠️ UI 文本断言反模式：不查页面就写关键词匹配

   用 `body.inner_text()` 做 `"keyword" in text` 断言前，必须用 `browser` 截图或 `browser_snapshot` 确认页面实际渲染的文本。版本详情页的状态可能是徽章、图标或缩写，不一定是 "release" 或 "已发布"。

   **正确做法**：先截图（`report.step("页面截图", screenshot=page)`）保留现场，再根据实际渲染文本写断言。对不确定的文本，只截图不做文本断言。

   ### ⚠️ 删除测试场景设计：不准对已发布数据做删除操作

   IoT 平台上发布过的模型和设备不可删除。**不准通过 SQL 直接删版本记录来绕过业务限制**。

   **反例**（2026-06-09 元件模型 atomic scene6 已修复）：
   ```python
   # ❌ 通过删版本记录来绕过"已发布不可删除"的限制
   cur.execute("DELETE FROM thing_model_version WHERE ...")
   ```

   **正例**：场景6 应新建一个草稿状态的实体专门用于删除测试，用完清理。
   ```python
   # ✅ 创建一个草稿实体用于删除
   DEL_NAME = f"{DATA_PREFIX}_待删除"
   page.goto(CREATE_URL); fill_form(DEL_NAME); page.click("保存")
   # 搜索 → 删除 → 验证
   page.search(DEL_NAME); page.click("删除"); page.confirm()
   report.assertion("UI: 删除后不显示", rows == 0, ...)
   # DB 验证：软删除 is_delete = True
   db_row = find_thing_model(DEL_NAME)
   report.assertion("DB: 已软删除", db_row[-1] is True, ...)
   ```

   ### ⚠️ 软删除后 DOM 更新时序陷阱（2026-06-10 实测）

   软删除操作（点击确认弹窗后）通常不触发网络请求——前端 Vue 直接通过响应式过滤移除表格行。`page.wait_for_load_state("networkidle")` 在无网络请求时会立即返回，**此时 Vue 可能尚未完成 DOM 更新**，导致 `body.inner_text()` 断言提前执行。

   **修复模式**：
   ```python
   confirm_btn.click()
   page.wait_for_load_state("networkidle", timeout=5000)  # 等后端确认（如有请求）
   page.wait_for_timeout(1500)                             # 等 Vue 响应式更新 DOM

   # 重新搜索验证记录已移除
   name_input.fill(DEL_NAME)
   search_btn.click()
   page.wait_for_timeout(1500)
   page_text = page.locator("body").inner_text()
   report.assertion("删除后不在列表",
                    DEL_CODE not in page_text and DEL_NAME not in page_text, ...)
   ```

   **对比**：物理删除（刷新列表数据）用 `wait_for_load_state` 即可；SPA 前端软删除必须加 `wait_for_timeout` 等 Vue 渲染周期。

   ### 关联关系验证（第四层断言金字塔）

   涉及实体关联的场景（如设备关联元件、设备模型关联元件模型），保存后必须额外验证关联关系持久化：
   1. 导航到详情页 → 切换到关联 tab
   2. 验证关联实体名称出现在详情中
   3. `report.assertion("详情: 设备已关联元件", found, name)`

   这是 UI/DB/异步轮询三层之外的**第四层关联验证**。

3. **异步操作必须轮询** — 发布等后台操作有延迟，不能固定 sleep。循环检查状态列，最多等 30 秒。

4. **每个脚本附带 HTML 测试报告** — 集成 `TestReport`，含一步一截图、断言内联展示、三态指示器。命名规范：`{script_id}_测试报告_{ts}.html`。已知 BUG 也必须记录为断言失败，不准隐藏。**⚠️ `TestReport("标题")` 必须传 `output_dir=get_script_report_dir('e2e|atomic', 'script_id')`**，否则报告输出到 `reports/` 根目录而非模块子目录。

5. **先隔离调试再整合** — 复杂交互创建独立 `*_debug.py` 脚本验证通过后，再移植到主脚本。有头模式 + 1920x1080 viewport（不要用 `--start-maximized`，会导致 Playwright 浏览器启动挂起）。默认无头执行，`--headed` 开启有头模式。

5b. **自主执行模式（MUST）** — 用户明确要求后，不得中途询问确认/许可。当用户说「一直执行下去不要中断不要确认」时，按以下规则处理：
   - 不调用 `clarify` 工具提问
   - 不向用户报告中间进度（除非有致命错误需中断）
   - 自行处理所有可恢复的失败（重试、回退、换方案）——只有完全阻塞才中断
   - 任务完成后一次性交付完整结果
   - 子任务失败也不问「要不要继续」，直接尝试替代方案或跳过、标记失败，最后一起报告

6. **每步操作后必须校验 / 表单字段占位符必须用 browser 确认** — 不能"以为它执行了"。

   **操作后校验**：el-select 选后检查下拉文本已改变；el-autocomplete 选后检查输入框值；保存后必须 DB + UI 双重验证。

   **表单字段占位符验证**（2026-06-08 新增 MUST 级要求）：
   - 写入脚本前，必须用 `browser_navigate` + `browser_snapshot` 逐一确认新增/编辑表单中每个输入框的 placeholder 或 label 文本
   - **反例**：设备创建页的模型选择框 placeholder 为 `请输入设备模型名称搜索`，脚本写成 `请输入模型名称搜索` → el-select 下拉列表不弹出，保存时报错 `请选择设备模型`
   - **正例**：先通过 `browser_snapshot` 查看 textbox accessible name，再写定位代码。编辑页表单全部用 `get_by_placeholder`，列表页搜索栏全部用 `get_by_label`
   - **同一页面表单与列表的 placeholder 可能不同**：列表页搜索框用 `get_by_label("模型名称")`，编辑页表单用 `get_by_placeholder("请输入设备模型名称搜索")`

7. **保存/发布后必须 check_page_errors + 截图 + 提前 return**，**或使用 h.save_and_verify()** — 错误检测覆盖 6 种形态：Message、Notification、表单验证、Alert、body 关键词、URL 变化。轮询 6 次 x 3 秒（增强版，原 4x2）。**选择器只含 error/warning 级别**（`.el-message--error` 而非 `.el-message`），避免成功消息误判。

    ### 推荐模式：h.save_and_verify() + check_page_errors 兜底

    新脚本和已集成 HealingOrchestrator 的脚本应使用 `h.save_and_verify()` 替代裸 `click + sleep`，它在点击保存前会主动关闭 popper、检查表单错误，并通过 API/URL/DB/toast 四路信号确认保存结果。`check_page_errors` 作为兜底验证保留。

    ```python
    # ✅ 推荐：h.save_and_verify() + check_page_errors 兜底
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

    ### 传统模式（仍有效，但无自愈）：

    `check_page_errors()` 用 `report.assertion()` 记录失败后**必须检查返回值并提前返回**，否则脚本会继续执行后续的 DB 断言和截图，产生「页面上有错误但数据正确」的矛盾报告。

    **反例（2026-06-09 element/device/sn atomic 已修复）**：
    ```python
    # ❌ check_page_errors 记录失败后继续执行 → DB 断言可能通过 → 报告矛盾
    check_page_errors(page, report)
    row = db_check(EL_NAME)
    report.assertion("DB: 元件已创建", row is not None, ...)
    report.scene_end(True)  # 页面有错误但场景标记为通过
    ```

    **正例（所有 atomic 脚本已统一应用）**：
    ```python
    has_err = check_page_errors(page, report)
    if has_err:
        report.scene_end(False)
        return report  # ← 提前返回，不继续执行
    row = db_check(EL_NAME)
    report.assertion(...)
    report.scene_end(True)
    ```

    **检查清单**：脚本中所有 `check_page_errors()` 调用（场景1保存、场景3保存、场景4发布、场景6删除）**都必须**使用 `has_err = ... ; if has_err: return report` 模式。

8. **编辑后二次确认** — 保存后重新进入编辑页验证 UI 数据正确，不仅依赖 DB 断言。验证计数、特定区域文本而非全页面 body。

9. **数据清理前置 + 依赖检查** — 清理放在脚本开头（非结尾），支持多脚本数据复用。消费型脚本执行前检查 DB 依赖数据是否存在。

    ### ⚠️ 自动清理铁律：所有测试数据必须可追溯、可清除

    **两条 MUST 级原则（2026-06-10 用户明确要求）：**
    
    1. **命名前缀**：所有脚本生成的测试数据必须有 `AUTO_` 前缀（如有平台限制如只允许输入数字则加备注说明）。
    2. **强制清理**：脚本跑完后（无论成功还是失败），必须清理所有由自动化产生的测试数据，包括：
       - 脚本直接创建的（通过 UI 或 DB）
       - **UI 交互触发后端自动创建的侧效应数据**（如勾选复选框→后端自动 INSERT 记录）
       - 不得影响存量非测试数据

    #### ⚠️ 后端侧效应数据清理模式（2026-06-10 编入）

    当 UI 操作（如勾选复选框、选择下拉选项）触发后端 API 自动创建记录，且后端无"if not exists"幂等判断时，这些记录**没有 `AUTO_` 前缀、无法通过 LIKE 匹配**，必须使用**基线保留法**清理：

    ```python
    # 清理后端侧效应记录：保留每个名称最早的一条基线数据，删除后代重复
    cur.execute("""
        DELETE FROM thing_model WHERE thing_type='SEGMENT'
        AND id NOT IN (
            SELECT MIN(id) FROM thing_model
            WHERE thing_type='SEGMENT' GROUP BY thing_name
        )
    """)
    seg_n = cur.rowcount
    # 同步清理关联表（级联）
    if seg_n:
        cur.execute("DELETE FROM thing_model_version WHERE thing_model_id NOT IN (SELECT id FROM thing_model)")
    ```

    **适用条件**：侧效应记录名称固定（如 HEBT/LBHL/MEBT 等预定义名称），多次运行后每个名称存在多条。`MIN(id)` 保证保留最初系统自带的那条。

    **不适用**：名称不固定的侧效应记录。此时改用时间窗口清理（记录执行开始时间，删除创建时间大于该时间的非 AUTO_ 记录）。

    **2026-06-10 实测案例**：`composite_device_test.py` 勾选段复选框（HEBT/LBHL/MEBT）时，后端无幂等判断，每次自动创建 3 条 `thing_model type='SEGMENT'` 记录。运行 22 次后累积 70 条。清理后保留 6 条基线。侧效应清理代码已集成到 `delete_device_data()`。

    ### ⚠️ 数据清理反模式：时间戳前缀 + 不清理旧数据

    原子脚本使用 `AUTO_{MODULE}_{TIMESTAMP}` 时间戳前缀命名测试数据，每次运行创建不同名字。**仅按当前名字清理不会触及上一次运行的数据**——这是垃圾数据产生的核心原因。

    **反例（2026-06-09 调试验证：DB 残留大量 AUTO_ 数据）：**
    ```python
    existing = find_thing_model(DEV_MODEL_NAME)
    if existing:
        delete_thing_model(DEV_MODEL_NAME)  # 只删当前名字
    ```

    **正例：在 finally 块追加 LIKE 模式清理**
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

    #### ⚠️ 清理必须按模块匹配正确表（反例：2026-06-10 SN 原子脚本）

    **陷阱**：不同模块的测试数据存于不同表。SN 模块的数据在 `device_sn` 表，不在 `thing_model` 表。如果不按模块选择正确表，清理操作完全无效，导致数据残留最终在下一次运行时触发静默保存失败：

    ```
    AUTO_SN_* 数据存于 device_sn          ← 需要用 device_sn LIKE 清理
    AUTO_THING_* 数据存于 thing_model     ← 需要用 thing_model LIKE 清理
    ```

    **反例（2026-06-10 已修复）**：sn_atomic_test.py 的 finally 块删的是 thing_model 表：
    ```python
    # ❌ 错误：SN 数据在 device_sn，删 thing_model 毫无效果
    cu.execute("DELETE FROM thing_model WHERE thing_name LIKE 'AUTO_SN_%'")
    ```

    **正例**：
    ```python
    # ✅ 正确：按模块匹配正确表
    cu.execute("DELETE FROM device_sn WHERE sn LIKE %s", (f"{DATA_PREFIX}%",))
    ```

    **判断标准**：写 finally 清理前，先查 `information_schema.columns` 确认数据存在哪个表。SN 模块 → `device_sn`，模型模块 → `thing_model` + `thing_model_version` + `thing_model_relation_ship`，设备 → `device`，标签 → `device_tags`。

    **覆盖表**：`thing_model`、`thing_model_version`、`thing_model_relation_ship`、`device`、`device_sn`、`device_tags`、`pv_data_info`、`pv_data_relation`、`facility_info`。注意删除顺序：先删版本/关联表，再删主表。

    **批量清理工具**：`python _cleanup.py` 提供按 `LIKE 'AUTO_%'` 模式扫描所有表（dry-run/execute/force 三种模式）。创建于 2026-06-09，支持增量预览 + 实际执行。项目根目录调用，无需指定任何参数。

10. **转移组件(Transfer)的批操作必先检查勾选框状态** — 进入编辑页时 checkbox 默认全勾选。必须逐行控制勾选后再点击操作按钮。一步一验证。

11. **每条路由必须在浏览器中实际验证后再写入脚本** — MUST 级，严格评审点。绝不要从 URL 模式推断路由。`/controller/cModelEdit` 和 `/controllerType/cEdit` 结构相似但完全不同，前者是 404 后者才是正确路由。

    **反例（被评审否决）**：
    ```python
    # ❌ 凭感觉写的路由，从未验证 — 导致 404
    page.goto(f"{BASE_URL}/controller/cModelEdit?type=create")
    ```

    **正确做法**：
    ```python
    # 1. 先验证：browser_navigate(BASE_URL + "/controllerType/cEdit?type=create")
    # 2. 确认页面非 404
    # 3. 再写入
    page.goto(f"{BASE_URL}/controllerType/cEdit?type=create")
    ```

    **编写脚本前的必做步骤**：
    - 加载本 skill 并检查 `references/platform-diff.md` 获取已知路由映射
    - 目标平台的所有路由节点，先操作左侧菜单实际到达，记录 URL，再写入脚本
    - 对比同类模块的路由模式（如元件模型=`elementType/e*`、设备模型=`controllerType/c*`），但仅作参考，仍需逐一验证
    - 带参数路由（`?type=create`、`?type=edit&id=N`）需验证参数也能正常加载

---

## 11. 测试分类原则（与 §10 同等 MUST 级 — 详见 `references/scene-design.md` §八）

### 11.0 测试分类定义

平台自动化分为两个类别，**必须严格区分，数据完全隔离**：

#### 基础功能

按 **功能菜单维度** 编写的独立自动化测试脚本。每个菜单覆盖其下的全部操作：

**增 / 删 / 改 / 查 / 发布 / 导入 / 关联 / 按钮操作**

| 操作类型 | 说明 | 示例 |
|:---|:---|:---|
| 增 (Create) | 新增一条记录 | 新增PV、新增设备 |
| 删 (Delete) | 删除/软删除一条记录 | 删除PV、注销标签 |
| 改 (Update) | 编辑修改记录字段 | 编辑PV描述、修改设备名称 |
| 查 (Read) | 查看详情/搜索列表 | PV详情、搜索设备 |
| 发布 (Publish) | 状态变更操作 | 发布模型、发布设备 |
| 导入 (Import) | 文件批量导入 | PV批次导入 |
| 关联 (Associate) | 模块间关联/取消关联 | 设备关联元件、标签关联设备 |
| 按钮操作 (Button) | 功能性按钮 | 连通性测试 |

**设计原则：**

| 特性 | 说明 |
|:---|:---|
| **维度** | 一个菜单一个脚本（如 `pv_atomic_test.py` 只测 PV 管理） |
| **数据** | 自造数据、自清理，不依赖任何其他脚本 |
| **独立性** | 不与端到端脚本共享数据；即使同一操作在两端都有，也必须各自独立执行 |
| **命名** | `{menu}_atomic_test.py`（如 `pv_atomic_test.py`） |

#### 端到端业务场景

由 **多个功能模块组合** 而成的完整业务流。

| 特性 | 说明 |
|:---|:---|
| **维度** | 一个业务流一个脚本（如 `device_management_test.py` 覆盖 PV→模型→元件→设备→发布） |
| **数据** | 在脚本内按依赖链依次创建，消费型脚本可直接查询依赖数据 |
| **独立性** | 不依赖基础功能脚本的数据 |
| **命名** | `{business_flow}_test.py` 或 `{business_flow}_lifecycle.py` |

### 11.0a 核心规则

1. **基础功能脚本完全自包含** — 每个菜单的基础功能脚本自己造数据、自己清理。即使某操作在端到端脚本中已覆盖，基础功能脚本仍要独立执行一次（如新增PV仍在基础功能脚本中执行）。
2. **数据隔离** — 基础功能脚本用 `AUTO_{MENU}_{TIMESTAMP}` 前缀标识数据，清理时精确匹配此前缀。端到端脚本用不同的前缀。
3. **不允许共享数据** — 基础功能脚本不依赖端到端脚本的数据，端到端脚本也不
   依赖基础功能脚本的数据。两类脚本各自维护完整的数据链。
4. **用户提供的 mock 数据可自由操作** — 不要对用户标注为 mock 的数据加"不可修改/删除"的限制。连通性测试、编辑、搜索、删除等操作都应基于该 mock 数据正常执行。
5. **清理原则** — 只清理脚本自身创建的自动化数据（通过前缀匹配），不动存量数据。双条件查重（如 PV名称+IP）用于脚本开头清理旧数据。

### 11.0b 端到端脚本的数据依赖链 MUST 级要求

**写入端到端脚本前必须先画出完整的数据依赖链。** 每个实体不仅有"创建→发布"的生命周期，实体之间还有关联关系。遗漏任何一环都导致下游场景失败。

**反例（2026-06-08 实际发生的失败链）**：

```
PV → 元件模型(创建→发布) → 元件(创建→关联PV→发布) → 设备模型(创建→发布) → 设备(创建→关联元件→发布)
                                                                              ↑
                                                                        设备模型未关联元件模型→无法关联
```

设备模型创建页面有 **"元件模型"** 区域 + **"添加元件模型"** 按钮，用于将已发布的元件模型绑定到设备模型。不执行此关联步骤，设备创建时"元件"tab 内空无一物。

**正例（必须包含关联步骤）**：

```
PV → 元件模型(创建→发布) → 元件(创建→关联PV→发布)
          ↓
    设备模型(创建→添加属性→添加元件模型→发布)
          ↓
    设备(创建→选择设备模型→关联元件→发布)
```

**编写前的必做步骤**：

1. 画出完整的数据依赖有向图（有箭头）。确定每个实体创建时需要哪些前置资源（如设备模型需要已发布的元件模型）
2. 标注每个实体的必须字段和可选字段（通过 `browser_snapshot` 逐字段确认）
3. 标注每个表单页面中**需要关联其他实体**的位置（如设备模型页的"添加元件模型"按钮和搜索框）
4. 验证关联交互的完整流程：按钮点击→搜索框输入→下拉选项点击→确认关联生效
5. 检查目标实体必须处于"已发布"状态才能被关联
6. 隐藏的 tab 页内容必须点开后通过 `browser_snapshot` 验证

**IoT 物联管理平台参考依赖链（2026-06-08 验证）**：

```
┌─────┐    ┌────────────┐    ┌──────┐    ┌────────────┐    ┌──────┐
│ PV  │───→│ 元件模型    │───→│ 元件  │    │ 设备模型    │───→│ 设备  │
│     │    │ (element    │    │      │    │ (controller │    │      │
│     │    │  Type)      │    │      │    │  Type)      │    │      │
│新增 │    │ 新增        │    │新增  │    │ 新增        │    │新增  │
│     │    │ 发布        │    │关联PV│    │ 添加属性    │    │选模型│
│     │    │             │    │ 发布 │    │ 添加元件模型 │    │关联   │
│     │    │             │    │      │    │ 发布        │    │元件   │
└─────┘    └────────────┘    └──────┘    └────────────┘    └──────┘
```

**关键关联步骤的 Playwright 实现（设备模型 → 元件模型 关联）**：

```python
# 1. 点击"添加元件模型"按钮
page.locator("button").filter(has_text="添加元件模型").click()
time.sleep(1.5)

# 2. 在表格行中搜索元件模型
el_model_inp = page.get_by_placeholder("请输入模型名称搜索")
el_model_inp.click()
el_model_inp.fill(EL_MODEL_NAME)
time.sleep(2)

# 3. 从下拉列表中选择已发布的元件模型
el_model_opt = page.locator("[role='option']").filter(has_text=EL_MODEL_NAME).first
el_model_opt.click()  # 选中后版本列自动填充为"v1"
time.sleep(0.5)
```

### 11.1 定位方式模式总结（2026-06-09 更新）

#### 表单字段定位：Model 页 vs Instance 页

IoT 平台的 Element Plus 表单字段有两种定位模式，**取决于页面是「模型定义」还是「实例管理」**：

| 页面类型 | 正确定位方式 | 示例 | 原因 |
|:---|:---|:---|:---|
| **模型新增/编辑页**（如元件模型、设备模型、装置模型、段模型） | `page.get_by_label("字段名")` | `get_by_label("模型名称")` | 表单有 `<label for="el-id-xx">模型名称</label>`，accessible name 来自 label |
| **实例新增/编辑页**（如元件、设备、SN） | `page.get_by_placeholder("请输入XXX")` | `get_by_placeholder("请输入元件名称")` | 表单无 label，placeholder 直接暴露文本 |
| **列表页搜索栏** | `page.get_by_label("字段名")` 或 `page.get_by_placeholder()` | 需逐页确认 | 部分用 label(`模型名称`) 部分用 placeholder(`请输入设备名称`) |

**核心原则**：不要猜测定位方式。先跑 FIELD_SCAN 代码，再写定位代码。

#### FIELD_SCAN：字段定位诊断代码

```python
# 在目标页面执行此代码，一次性提取所有输入框的完整定位信息
inputs = page.locator('input:visible, textarea:visible, .el-input__inner:visible').all()
for inp in inputs:
    pid = inp.get_attribute('id') or ''
    ph = inp.get_attribute('placeholder') or ''
    label_el = page.locator(f'label[for="{pid}"]').first
    label_text = label_el.inner_text().strip() if label_el.count() > 0 else ''
    aria = inp.get_attribute('aria-label') or ''
    print(f"  placeholder='{ph}' label='{label_text}' aria='{aria}'")
```

label 有值 → 用 `get_by_label()`；label 无值但 placeholder 有值 → 用 `get_by_placeholder()`

#### 常见陷阱

| 陷阱 | 表现 | 正确做法 |
|:---|:---|:---|
| label 带星号 `* 模型名称` | `get_by_label("* 模型名称")` 失败 | label 是 `模型名称`，星号是 CSS 伪元素 `::before` |
| 误以为所有表单都用 label | 实例页用 `get_by_label("元件名称")` 超时 | 实例页用 `get_by_placeholder("请输入元件名称")` |
| 误以为所有表单都用 placeholder | 模型页用 `get_by_placeholder("请输入模型名称")` 可用 | 模型页**也**可用，但 label 更语义化 |
| label 带星号 `* 装置模型名称` | `get_by_placeholder("* 装置模型名称")` 超时等待 30s | 星号是 CSS 伪元素 `::before`，label 实际是 `装置模型名称`，用 `get_by_label("装置模型名称")` |
| 同一页面 label 和 placeholder 混合 | 部分字段识别错误 | 一律用 FIELD_SCAN 代码确认后再写 |
| **`page.locator("input").first` 定到 el-select readonly 输入框** | `fill()` 超时：`element is not editable` | 用 `get_by_label("装置名称")` 或 `get_by_role("textbox", name=...)`。el-select 的输入框 `role=combobox` 且 `readonly`，不会被 `input[type='text']` 排除，必须用 label 精确匹配 |

#### 诊断方法

用 `browser_snapshot` 查看 textbox 的 accessible name：
- `textbox "PV名称"` → 用 `get_by_label("PV名称")`
- `textbox "请输入PV名称"` → 用 `get_by_placeholder("请输入PV名称")`
- 对不确定的字段，用 FIELD_SCAN 代码提取完整信息

### 11.2 表格行选择器

不同 Element Plus 版本/配置下表格的 HTML 结构不同：

| 结构 | 示例 | 正确选择器 |
|:---|:---|:---|
| **标准嵌套** | 一个 `<table>` 包含表头和行 | `tr.el-table__row` 或 `table tr` |
| **兄弟表格**（常见） | 两个 `<table>` 并列：表头 + 数据体 | `table[class] >> nth=1 tr` 或 `table[class] tr[class]` |

> **注意**：`table table tr` 仅在表格<strong>嵌套</strong>时有效。对于<strong>兄弟表格</strong>（PV 列表页即此结构），该选择器不匹配任何行。

**策略：** 先用 `browser_snapshot` 确认表格结构（多个 `<table>` 是兄弟还是父子），再选择正确的选择器。

---

## 静默保存失败诊断流程（5 步排查） + verify_save()

当保存按钮 `click()` 后出现**无网络请求、无错误提示、无表单验证错误、DB 无数据**的情况时，按以下顺序排查：

1. **el-autocomplete popper 未关闭**（最常见）— `page.keyboard.press("Escape")` 确保 popper 关闭
2. **按钮 disabled** — 检查 `.el-form-item__error` 确认表单验证错误的根因
3. **表单验证错误** — 保存后立即检查 `.el-form-item__error` 文本内容（IP格式校验、MAC格式校验）
4. **网络请求未发出** — `performance.getEntriesByType('resource').length` 对比前后
5. **JS Console 错误** — `performance.getEntriesByType('resource').filter(e => e.responseStatus >= 400)`
6. **API 确认（进阶）** — `page.on("response")` 监听保存 API 返回 200 但 DB 无数据 → 后端唯一约束冲突（如设备IP与已有PV IP重复）
7. **Playwright click() auto-wait 阻塞诊断（2026-06-10 编入）** — 当 `click()` 耗时远超预期（如 16 秒），不要先怀疑 time.sleep 设置。Playwright 的 `click()` 内置 auto-wait 会等待元素 visible+stable+enabled。用 tic() 时间标记定位真实瓶颈：

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

    **实测案例（2026-06-10，装置设备脚本场景1）**：
    ```
    page.goto(domcontentloaded):             0.24s
    已登录(含Vue挂载):                         0.42s
    navigate_to_device_list(菜单点击):         1.01s
    navigate_to_quick_init(按钮):             16.14s  ← 瓶颈在这里！
    ```

    **诊断结论**：16 秒不在任何 `time.sleep` 中，而是冗余的菜单导航触发了 Vue SPA 同路由完整重渲染（组件卸载→挂载→API 重请求），`click()` 的 auto-wait 被阻塞了 15 秒。修复：删除冗余导航后 `navigate_to_quick_init` 降至 **1.17s**。

    **修复方法见 §1 Vue SPA 同路由重导航陷阱**。不要在定位前先调 `time.sleep` 参数——先加 tic() 找到瓶颈，再对症修复。

### 系统性解决方案：`verify_save()` → `h.save_and_verify()`

在 E2E 脚本中，每次保存操作应替换 `click -> sleep -> check_page_errors` 模式为 `h.save_and_verify()`（Healer v2 方案）或 `verify_save()`（旧方案），后者通过 API 响应监控 + URL 变化 + 成功 toast + DB 直查四路信号轮询确认保存结果。

**推荐方案（新脚本）**：使用 `h.save_and_verify()`（位于 `core/healer/save_healer.py`），它是 `HealingOrchestrator` 的一部分，提供：

- 保存前自动关闭 el-autocomplete popper（#1 静默失败根因）
- 检查 `.el-form-item__error` 确认表单验证错误
- API 响应监听（匹配 save/add/insert/edit/update）
- URL 变化检测 + 成功 toast 检测 + DB 直查轮询
- 15 秒超时，失败自动重试 2 次
- IP/MAC 格式校验错误自动修正

```python
# 旧模式（脆弱）：click -> sleep -> check_page_errors
page.get_by_role("button", name="保存").click()
time.sleep(4)
has_err, _ = check_page_errors(page, report)
if has_err: return report

# 新模式（推荐）：h.save_and_verify() — 自愈 + 三重确认
ok = h.save_and_verify("步骤名",
    db_verify_fn=find_pv_by_code,       # DB 验证函数
    db_args=[PV_CODE],                  # 验证参数
    expected_url="List")                # 期望跳转 URL
if not ok:
    report.scene_end(False)
    return report

# 旧方案（兼容）：verify_save() — 无自愈的三重确认
page.get_by_role("button", name="保存").click()
save_ok = verify_save(page, report, "步骤名",
                      db_check_fn, [arg1, arg2],
                      expected_url_segment="List")
if not save_ok:
    report.scene_end(False)
    return report
has_err, _ = check_page_errors(page, report)
```

**实现参考：** `platforms/iot/scripts/e2e/device_management_test.py`（已升级到 `h.save_and_verify()`）
**详细文档：** `references/verify-save-pattern.md` + `core/healer/save_healer.py`

### check_page_errors 增强轮询

当前所有脚本的 check_page_errors() 统一使用 6 次 x 3 秒轮询（原 4x2），给后端更长的处理窗口。

---

## 文件上传 / 导入操作自动化

### el-upload（Element Plus）文件上传 — 标准方案

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=HEADLESS)
    page = browser.new_page()
    page.goto(list_url)

    # ★ 核心：通过 expect_file_chooser 拦截OS文件对话框
    upload_wrapper = page.locator(".el-upload").filter(has_text="导入").first
    # 或定位到特定按钮：page.locator("button").filter(has_text="PV导入")
    with page.expect_file_chooser() as fc_info:
        upload_wrapper.click(force=True)  # 必须点击 .el-upload 包装器
        time.sleep(2)                     # 给文件选择器初始化时间
    file_chooser = fc_info.value
    file_chooser.set_files(r"E:\path\to\template.xlsx")
```

### ⚠️ 用户偏好：文件上传必须模拟人为操作

**此用户不接受 `expect_file_chooser` 后台拦截**，要求点击按钮后 OS 对话框真实弹出 → 通过键盘模拟粘贴路径 → Enter 确认。

2026-06-08 对 Windows 10 + Chrome 调研了 4 种方案：

| 方案 | 效果 |
|:---|:---:|
| `expect_file_chooser` (Playwright 标准) | ✅ 可靠，但用户不接受 |
| `pywin32` WM_SETTEXT + BM_CLICK | ⚠️ 路径写入成功，BM_CLICK 不生效（Common Item Dialog 不响应） |
| `pyautogui` / `SendInput` 键盘模拟 | ❌ 键盘事件发到错误窗口（焦点问题） |
| 手动暂停模式：click + `input("请选文件...")` | ✅ 用户看到OS对话框，手动选文件 |

**根因**：Chrome 在 Win10+ 使用 IFileOpenDialog (COM 新式对话框)，不响应传统 Win32 消息。

**决策**：CI/自动化回归用 `expect_file_chooser`；需要演示/调试时用「手动暂停模式」。见 `references/file-upload-technique.md`。不要拿"行业标准"当借口不做调研。

**关键规则：**

1. **点击 `.el-upload` 包装器而非内部 button** — Element UI 在 `.el-upload` 上绑定了点击监听，直接点击内部 button 可能不触发文件选择
2. **降级方案**：若 `expect_file_chooser` 失败（常见于 headless 模式超时），用 `page.locator("input.el-upload__input").set_input_files(path)` 直接操作隐藏 input
3. **文件格式要求** — 模板文件的 sheet 名和列名必须与后端接口匹配。本平台要求：sheet=`pv数据导入`，col=(`PV名称`, `PV描述`)
4. **测试数据唯一性** — 避免重复导入导致 `successCount=0`。每次运行生成唯一 PV 名（如带时间戳）或使用纯净模板（不从已有模板复制）

### 导入结果验证（三层策略）

| 层级 | 方法 | 代码 | 可靠性 |
|:---|:---|:---|:---:|
| **API** | `page.on("response")` 监听导入接口 | 解析 JSON 中 `successCount` | ★★★ 最直接 |
| **DB** | 导入前后对比记录数 | `SELECT COUNT(*) FROM table` | ★★★ 最可靠 |
| **UI** | 刷新列表后搜索导入记录 | `page.get_by_label("名称").fill(name)` | ★★ 确认渲染 |

**推荐策略：API + DB 双重验证，UI 作为补充确认。**

```python
import_response = {}

def on_response(response):
    if "importPvDataFromExcel" in response.url:  # 替换为实际API路径
        try:
            data = response.json()
            import_response.clear()
            import_response.update(data)
            sc = data.get("data", {}).get("successCount", 0)
            fc = data.get("data", {}).get("failureCount", 0)
            report.assertion("API: 导入结果", sc > 0, f"成功{sc}条, 失败{fc}条")
        except Exception:
            pass

page.on("response", on_response)
```

### 测试模板生成（openpyxl）

```python
import openpyxl
from datetime import datetime

ts = datetime.now().strftime("%H%M%S")
test_pv_name = f"AUTO_IMPORT_{ts}_PV_001"

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "pv数据导入"          # 与后端接口要求的sheet名一致
ws.append(("PV名称", "PV描述"))  # 列名必须匹配
ws.append((test_pv_name, "测试描述"))
wb.save("模板_测试.xlsx")
```

### 已知陷阱

- **`expect_file_chooser` timeout 30s** — 在 headless 模式下偶发。降级到 `set_input_files()` 可绕过
- **`set_input_files()` 不触发上传** — 若 `auto-upload=true` 有效，否则需手动触发。本平台 `auto-upload=true`，两种方案均通过验证
- **API 响应延迟** — 导入接口需要 20-30 秒处理（后端解析 Excel + 逐行写入），偶见 60-90 秒。轮询超时应设为 90 秒。`page.on("response")` 必须在导航前注册
- **重复导入** — 模板中已有的 PV 名会失败（`failureCount` 递增），务必使用纯净模板或唯一测试名
- **导入结果弹窗必须手动关闭** — 导入成功后会弹出"导入结果"模态对话框。必须通过 `page.get_by_role("button", name=re.compile(r"确[认定]|知道了")).click()` 关闭，否则弹窗会阻塞后续所有页面点击操作。不要依赖自动消失。
- **pv_import_test.py 完整参考** — 见 `platforms/iot/scripts/atomic/pv_import_test.py`

---

## 组件交互方案速查

| 组件 | 方案 | 代码 | 详细参考 |
|:---|:---|:---|:---|
| **Radix UI DropdownMenu / Combobox** (Shadcn UI) | Playwright 原生 click() 有效（2026-06-11 验证），不需手动 dispatchEvent | `page.locator('button').filter(has_text='用户名').first.click()` | `references/shadcn-ui-patterns.md` |
| **Shadcn UI 文件上传** | 隐藏 `input[type="file"]` + dropzone div | `locator('input[type="file"]').set_input_files(path)` | `references/shadcn-ui-patterns.md` |
| **Radix UI Dialog / AlertDialog** | Portal 渲染到 body，按钮/确认弹窗均用原生 click() | `page.get_by_role('button', name='确认退出').click()` | `references/shadcn-ui-patterns.md` |
| **SPA 登录 (Next.js)** | 登录后 URL 不变（仍为 /auth/signin），需检查 body 内容而非 URL | `assert '退出' in page.locator('body').inner_text()` | `references/shadcn-ui-patterns.md` |\n| **el-select** (Element Plus) | `force=True` 打开 → `.el-select-dropdown__item` + `force=True` 点击选项 | `select_el_option()` | `references/element_ui_patterns.md` |
| **el-cascader** (多选) | `force=True` 打开 → 点**checkbox**（非节点文本） → Escape 关闭 | `select_cascader_options()` | `references/el-cascader-trap.md` |
| **el-autocomplete**（标准） | fill → 等 3s → `.el-autocomplete__popper li` + `force=True` 点击选项 → Escape 关闭 popper | 见 `references/el-autocomplete-trap.md` | `references/el-autocomplete-trap.md` |
| **ComponentHealer** (运行时自愈) | `core/healer/component_healer.py` — fill → 3s → 3级降级方案 → Escape | `h.autocomplete_select(hint, text)` | `core/healer/` 入口通过 `HealingOrchestrator` 统一调度。|
| **el-autocomplete**（设备模型→添加元件模型） | 设备模型创建页的搜索弹窗。前置元素模型**必须通过 UI 创建并发布**（DB 直插数据不会出现在下拉中）。创建完毕后 autocomplete 自然命中，无需特殊选择器 | 见 `device_model_atomic_test.py` UI 前置场景 |
| **el-upload** (Element Plus) | `.el-upload` 包装器 → `expect_file_chooser()` 拦截OS对话框 → `set_files(path)` | 见 §文件上传 | `references/file-upload-technique.md` |
| **el-tree** (详情页关联数据) | 关联数据用 `<div class="el-tree">` 渲染，非 `<tr>` 表格。使用 `.inner_text()` 或 `.node-actions` 定位 | `page.locator(".el-tree").inner_text()` | `references/fragility-audit-checklist.md` |
| **确认对话框(确定按钮)** | 统一作用域限定，防止误点页面其他"确定"按钮 | `page.locator(".el-message-box__btns button, .el-dialog button, .el-message-box button").filter(has_text="确定")` | — |
| **Ant Design Select** | `.ant-select-item-option` 定位；按钮文本含空格（`确 认`） | `force=True` 点击 | `references/element_ui_patterns.md` |
| **SPA 列表页（需菜单过滤）** | 部分 SPA 页面（如装置模型 `/system/device`）直接 `page.goto()` 无法触发类型过滤（FACILITY），页面显示空列表或概览模式。**必须通过左侧菜单点击导航**，使用 `navigate_to_facility_list()` 辅助函数模式：先 goto 首页 → 用 `page.evaluate` 点击菜单项 → 触发 Vue Router 正确过滤 | `composite_device_model_atomic_test.py` 中的 `navigate_to_facility_list()` 函数 |
| **el-checkbox in el-table（Vue v-model）** | Element Plus 的 el-table 内嵌 el-checkbox 时，直接 `checkbox.check()` 或 `checkbox.click()` 无法触发 Vue 的 v-model 绑定。必须点击该行**第一列**的 `<label>` 元素。用 `page.evaluate` 找到文本行 → 取 `td:first-child label` → `label.click()`。 | `page.evaluate("""(s) => { const rows = document.querySelectorAll('.el-table__body tr'); for (let row of rows) { const cells = row.querySelectorAll('td'); for (let cell of cells) { if (cell.innerText.trim() === s) { const fc = row.querySelector('td:first-child'); if (fc) { const lbl = fc.querySelector('label'); if (lbl) { lbl.click(); return true; } } } } } return false; }""", text)` | `composite_device_test.py` 的 checkbox 选中逻辑（已验证） |
| **表单页 URL 依赖 SPA 状态（非路由过滤）** | 部分表单页面（如装置快速初始化 `eqcDeviceQuickInit`）直接 `page.goto()` 会导致**表单内的下拉表格数据为空**（"暂无数据"）——不是路由过滤问题，而是表单依赖 SPA 的前置状态/数据加载。必须通过菜单→列表页→按钮的方式进入。 | `composite_device_test.py` 的 `navigate_to_device_list()` + 快速初始化按钮 |

通用原则：页面定位方式取决于页面类型，参见 §11.1「搜索框定位方式」。**不要默认假设 get_by_placeholder 优先于 get_by_label** — 先用 `browser_snapshot` 检查 textbox 的 accessible name，再选正确的定位方式。

### 断言增强：从「非空检查」升级为「语义内容检查」

`assert_ui()` 仅检查元素内容非空，但无法验证具体语义。对状态列、版本信息等关键字段，应使用显式断言：

> **注意**：`assert_ui()` 不是 `core/` 中的全局函数——每个脚本按需定义自己的版本（参考 `references/scene-design.md` L600），不同平台的验证逻辑不同。

```python
# ✅ 版本信息 — 检查是否包含"发布:1"
ver_cell = page.locator("tr").filter(has_text=name).locator("td").nth(4).first
if ver_cell.count() > 0:
    ver_text = ver_cell.text_content(timeout=5000) or ""
    is_published = "发布:1" in ver_text
    report.assertion("UI: 版本信息含发布标记", is_published, ver_text[:80])
else:
    report.assertion("UI: 版本信息含发布标记", False, "未找到版本信息列")

# ✅ 发布状态 — 检查是否包含"发布"
status_cell = page.locator("tr").filter(has_text=name).locator("td").nth(4).first
if status_cell.count() > 0:
    status_text = status_cell.text_content(timeout=5000) or ""
    is_released = "发布" in status_text
    report.assertion("UI: 设备已发布", is_released, status_text[:40])
else:
    report.assertion("UI: 设备已发布", False, "未找到状态列")
```

列索引需预先用 `browser` 工具确认（参见 `references/fragility-audit-checklist.md` 维度1）。

### el-select 下拉选项等待优化

避免用 `time.sleep()` + `count()` 检查下拉选项，应使用显式等待：

```python
# ❌ 脆弱：固定sleep + count检查
rw_sel.click()
time.sleep(0.5)
ro = page.locator("[role='option']").filter(has_text="读写").first
if ro.count() > 0: ro.click()

# ✅ 健壮：显式等待选项可见后再点击
rw_sel.click()
rw_opt = page.locator("[role='option']").filter(has_text="读写").first
rw_opt.wait_for(state="visible", timeout=3000)
rw_opt.click()
```

此模式适用于所有 `el-select` 下拉选择、`el-autocomplete` 建议列表等动态渲染的选项。

### ⚠️ 关键陷阱：Playwright helper 函数必须用 sync API，不用 async

**此用户的所有 Playwright 脚本使用同步 (sync) API。** 编写 `scripts/component_utils.py` 等工具函数时：

```python
# ✅ 正确：playwright.sync_api
from playwright.sync_api import Page

def select_el_option(page: Page, ...) -> bool:
    page.get_by_role("combobox").click(force=True)    # 无 await
    ...

# ❌ 错误：playwright.async_api 会导致 ImportError
from playwright.async_api import Page  # 用户环境无此模块

async def select_el_option(page: Page, ...) -> bool:
    await page.get_by_role("combobox").click(force=True)  # 语法错误
    ...
```

用户的所有现有脚本（在 `D:/AI/harmes agent/WEB平台自动化/` 下）均使用同步 Playwright API，`scripts/component_utils.py` 中新增的函数必须与之保持一致。使用 async API 会导致 agent 生成的 helper 被用户拒绝并重写。第一次编写时就使用 sync API 可避免返工。

---

---

## 用户输入模板规范

> 本 skill 的标准用户接口。用户填写此模板后交给 AI Agent，即可启动 Phase 0-4 全流程。
>
> 所有菜单结构、URL 路由、组件类型、定位方式均由 Phase 0 自动探索，用户只需提供工具无法获知的信息。

### 标准模板位置

`templates/user-input-template.md` — 用户填写此文件即可启动全流程。

`references/example-device-atomic.md` — 完整参考示例（设备管理·基础功能，6 场景）。

### 模板 4 部分

| 部分 | 内容 | 工具能做什么 |
|:---|:---|:---|
| 一：平台连接 | URL、账号密码、前端框架、组件库 | 连接、登录、Phase 0 探索 |
| 二：数据库 | 类型、主机、库名、账号密码 | 信息_schema 自动检测字段类型 |
| 三：场景描述 | 自然语言操作步骤 + 每步校验 | 解析操作、生成脚本、执行、断言 |
| 四：已知数据（可选） | 存量 mock 数据清单 | 优先复用而非自建 |

### 场景描述标注语法

#### 字段约束（跟在字段名后的括号内）

| 标注 | 含义 |
|:---|:---|
| `（必填）` | 字段不能为空，保存后检测表单验证错误 |
| `（最长N字符）` | 长度上限，超长自动截断或用短值 |
| `（不可重复）` | 唯一约束，冲突时自动追加时间戳后缀重试 |
| `（字母开头+数字）` | 格式约束，校验并自动修正 |
| `（0-255格式）` | IP 地址格式校验 |
| `（下划线连接大写）` | MAC 地址格式校验 |
| `（从下拉搜索选择已发布的XXX）` | el-autocomplete/el-select 关联搜索+选择 |

#### 状态与操作标注

| 标注 | 含义 |
|:---|:---|
| `注意：已发布不可编辑` | 特定状态下按钮不可用，不在已发布数据上执行此操作 |
| `注意：已发布不可删除` | 同上 |
| `注意：软删除` | DB 断言查 is_delete 标志而非查记录是否存在 |
| `预期失败：XXX` | 断言错误提示出现而非等待超时 |
| `最多等待 N 秒` | 异步操作最大轮询时间 |
| `依赖声明：本脚本依赖「XXX」已发布` | 前置数据依赖，缺失则自动创建 |

#### 校验关键词（工具自动处理）

| 你写的 | 工具自动做 |
|:---|:---|
| 页面无错误提示 | 检测 el-message、el-notification、表单验证错误、NPE 等 6 种形态 |
| 数据库 XXX 表有记录 | 自动查 information_schema 确认字段类型，正确断言，截图留证 |
| 状态变为 XXX | 自动轮询等待（最多 30 秒 6 次） |
| 列表显示 XXX | 自动搜索、检查表格行、截图 |
| 关联了 XXX | 进入详情页验证关联关系 |

### 设计原则

1. **工具能自动发现的，不要用户填** — 菜单结构、路由、组件类型、定位方式均由 Phase 0 探索
2. **字段约束和状态限制是成功率瓶颈** — 字段格式、唯一约束、已发布不可编辑等业务规则，必须在场景描述中标注
3. **数据依赖链必须在场景开头声明** — 遗漏依赖是 E2E 脚本失败的第一大原因
4. **无需理解 skill 内部规则** — 11 条 MUST 规则、三层断言金字塔、场景衔接策略、Healer 降级链均由工具自动应用

---

## 文件索引

### 引用文件（`references/`）

| 文件 | 内容 | 行数 |
|:---|:---|:---:|
| `core-principles.md` | 13 条核心原则完整版（含代码示例、反例、审计清单） | 1166 |
| `scene-design.md` | 场景设计规范（状态机、CRUD、检查清单、scenes.json 模板、覆盖率分析、后续场景规划） | 1011 |
| `manifest-system.md` | Page Manifest 系统：格式说明 + JSON Schema + 脚本生成流水线 | 458 |
| `example-device-atomic.md` | **2026-06-15 新增** — 用户输入模板完整示例（设备管理·基础功能6场景）。用户参照此示例格式编写自己的场景描述 |
| `iot-device-records.md` | IoT 设备模块调试记录（创建/模型/生命周期/管理） | 371 |
| `element_ui_patterns.md` | Element UI 全组件交互方案 + Ant Design Vben Admin 特有模式 | 681 |
| `failure-catalog.md` | 故障目录（26 条故障信号 + 诊断流程 + 静默失败诊断 5 步法） | 356 |
| `platform-diff.md` | IoT 平台特定：URL 映射、placeholder 表、组件区分表、BUG 表、DB 字段 | 283 |
| `report-system.md` | **2026-06-10 更新** cyberpunk 设计（子报告：in-iframe 检测/星云动画/断言内联；全量报告：SVG 环形图/Modal iframe 弹窗/指标卡片）+ f-string JS 模板字面量陷阱 + Runner stdout 解析（断言汇总提取/`_log_class` 汇总行优先级/PLATFORM_NAME 动态标题） |
| `debugging-techniques.md` | 静默保存失败诊断 + 操作后错误检测技术 | 235 |
| `three-perspective-review.md` | 三方评审报告（测试架构/框架/DevOps） | 216 |
| `debugging-workflow.md` | **2026-06-09 新增** — 脚本调试工作流程（先分析再修复/DB字段类型确认/UI文本确认/el-autocomplete统一模式） |
| `tckz-records.md` | TCKZ 总控平台调试记录 + 表单结构 | 170 |
| `iot-route-map.md` | **2026-06-09 编入** — IoT 平台路由全映射（24 条验证路由 + DB schema 对照） | 107 |
| `framework-architecture.md` | **2026-06-09 编入** — 框架架构参考（组件分层设计 + 架构重构记录） | 213 |
| `device-management-fixes-20260608.md` | **2026-06-09 编入** — 设备管理端到端修复合并记录（路由/表单/关联/断言） | 175 |
| 其他（6 个） | 组件交互陷阱（el-autocomplete/el-cascader/文件上传）、Runner 修复记录、报告迁移 | — |
| `assertion-integrity.md` | **2026-06-08 新增** — 断言完整性强制要求（禁止静默跳过/双分支断言/关联验证/断言覆盖检查清单） |
| `verify-save-pattern.md` | **2026-06-09 新增** — 防静默保存失败模式：API 监听 + URL 变化 + DB 直查三重确认 `verify_save()` 函数实现 |
| `self-healing-v2-design.md` | **2026-06-10 新增** — 自愈 v2 设计：6 个运行时 Healer 模块（Selector/Component/Save/State/Assert/Recovery）+ 三步集成路径。设计文档位于项目 `core/references/self-healing-v2-design.md`，实现位于 `core/healer/` |
| `ppt-narrative-pattern.md` | **2026-06-09 新增** — 技术体系介绍 PPT 叙事结构模式（痛点→方案→演进→能力→实践） |
| `atomic-test-patterns.md` | **2026-06-08 新增** — 原子测试脚本构建规范（自包含/数据隔离/清理规范/标准6场景结构/通用交互模式） |
| `fragility-audit-checklist.md` | **2026-06-08 新增** — 脚本脆弱性审计指南：5维度审计清单（选择器/等待策略/断言语义/数据依赖/异常恢复） |
| `iot-full-coverage-plan.md` | **2026-06-08 新增** — IoT 平台全量脚本覆盖计划：12+ 待实现原子功能 + 6 E2E 场景 + 5 并行工作流 |
| `execution-pattern-template.md` | **2026-06-09 新增** — 标准场景执行模式模板（Navigate→Interact→SS→Verify→Log），3种常用模式（列表/表单/异步轮询）+ 工具函数速查 |
| `full-report-architecture.md` | **2026-06-09 新增** — 全量测试报告双模块架构（端到端场景 + 基础功能分离、数据依赖图独立、Runner 签名变化、NameError 陷阱） |
| `craft-cli-patterns.md` | **2026-06-09 新增** — Craft CLI 模式规范（参数化脚本工程：4组件骨架/工具函数模板/执行模式/验证协议/runner兼容） |
| `ui-fixture-pattern.md` | **2026-06-09 新增** — UI 前置数据创建规范（代替 DB 直插，端到端模拟用户创建+发布流程） |
| `platform-exploration-methodology.md` | **2026-06-09 新增** — 4阶段平台探索方法论（Phase 1-4 标准化流程 + 自动化分析脚本模板 + 数据依赖图） |
| `ghost-file-cleanup-methodology.md` | **2026-06-09 新增** — Ghost 文件清理方法论（3步审计→分类→同步流程 + 合并安全模式 + 验证清单） |
| `skill-health-checklist.md` | **2026-06-09 新增** — Skill 健康分析检查清单（交叉引用/选择器一致性/幽灵文件/结构完整性 6 维度） |
| `assertion-extraction-pattern.md` | **2026-06-10 新增** — 断言汇总提取模式：子脚本 stdout → runner.py 的正则提取机制（`TestCollector.get_data()` 集中打印 + runner.py regex 解析） |
| `equipment-test-patterns.md` | **2026-06-10 更新** — 装置模块测试模式（无草稿/发布态/编辑删除禁用/全局+系统视图拓扑验证/快速初始化模式）。**v2 修正**：DB表更正为 `device` 非 `facility_info`，复选框交互改 `label.click()`，导航方式改菜单进入，段/系统关联改 `device_relation_ship` 表。 | 重写 ~200 |\n| `shadcn-ui-patterns.md` | **2026-06-11 新增** — Shadcn UI / Radix UI 组件交互参考（PointerEvent 事件链、Portal 渲染、隐藏文件上传 input、Next.js 平台探索流程）。适用于非 Element-Plus 的 React 平台。 | ~250 |\n| `test-data-migration.md` | **2026-06-10 新增** — 测试环境前置数据填充：dev→test DB 迁移流程、IoT 业务字典完整参考数据（defaultSystem 15 项 + defaultSegment 6 项） |
| `platforms/hlxinzhi/references/platform-exploration.md` | **2026-06-11 新增** — 惠联新质平台探索记录（路由映射、Shadcn UI 组件结构、分类选项、知识管理/萃取/问答页面结构） | ~120 |

### 脚本（`scripts/`）

| 文件 | 用途 |
|:---|:---|
| `explorer_core.py` | Phase 0 核心探索引擎 |
| `component_utils.py` | 组件交互工具函数（select_el_option / select_cascader_options / select_autocomplete_option） |
| `self_heal.py` | Phase 4 故障诊断脚本（`--list-signals` 查询、`--report` 分析报告、`--apply` 修复命令输出） |
| `healer/` 模块包 | **2026-06-10 新增** — 运行时自愈 6 模块：`SelectorHealer`（5级选择器降级链）、`ComponentHealer`（el-autocomplete/select/cascader 自愈）、`SaveHealer`（保存三重确认+重试）、`StateHealer`（页面状态恢复）、`AssertHealer`（DB 字段类型自动检测）、`HealingOrchestrator`（统一调度器）。位于 `core/healer/` |
| `metrics_collector.py` | 成功率追踪（`record`, `trend --days 7`, `summary`）|

### 测试（`tests/`）

| 文件 | 用途 |
|:---|:---|
| `test_self_heal.py` | self_heal 引擎的 40 个 pytest 用例（信号模式匹配/SCHEMA验证/日志分析/脚本分析/自动修复） |

### 模板（`templates/`）

| 文件 | 用途 |
|:---|:---|
| `user-input-template.md` | **2026-06-15 新增** — 标准用户输入模板（4部分：平台连接/数据库/场景描述+字段约束标注/已知数据）。用户只需填写此模板，无需了解 skill 内部规则即可启动全流程。菜单/路由/组件由 Phase 0 自动探索 |
| `master_runner_template.py` | 多脚本聚合调度器模板 |
| `e2e_full.py` | **指向占位** — 实际参考已验证脚本 `platforms/iot/scripts/e2e/` 和 `core/templates/` J2 模板 |
| `generate_ppt_template.py` | **2026-06-10 新增** — 程序化 PPT 生成脚本模板（python-pptx，深色主题，13页标准叙事结构） |

### 外部已验证脚本（IoT 平台）

所有脚本位于 `platforms/iot/scripts/` 下，按类型分 `e2e/`（端到端业务场景）和 `atomic/`（基础功能测试）：

| 脚本 | 场景数 | 分类 | script_id | 报告子目录 |
|:---|:---:|:---:|---:|:---|
| `e2e/device_management_test.py` | 9 | 端到端 — 设备全生命周期 | `device_management` | `e2e/device-management/` |
| `e2e/sn_lifecycle.py` | 3 | 端到端 — SN全生命周期 | `sn_lifecycle` | `e2e/sn-management/` |
| `e2e/tag_lifecycle_test.py` | 7 | 端到端 — 标签全生命周期 | `tag_lifecycle` | `e2e/tag-management/` |
| `e2e/bypass_lifecycle_test.py` | 5 | 端到端 — Bypass管理 | `bypass_lifecycle` | `e2e/bypass-management/` |
| `atomic/pv_atomic_test.py` | 8 | 基础功能 — PV管理 | `pv_atomic` | `atomic/pv-management/` |
| `atomic/pv_import_test.py` | 2 | 基础功能 — PV导入 | `pv_import` | `atomic/pv-management/` |
| `atomic/element_model_atomic_test.py` | 6 | 基础功能 — 元件模型 | `element_model_atomic` | `atomic/element-model/` |
| `atomic/device_model_atomic_test.py` | 6 | 基础功能 — 设备模型 | `device_model_atomic` | `atomic/device-model/` |
| `atomic/composite_device_model_atomic_test.py` | 6 | 基础功能 — 装置模型 | `composite_device_model_atomic` | `atomic/composite-device-model/` |
| `atomic/element_atomic_test.py` | 6 | 基础功能 — 元件 | `element_atomic` | `atomic/element/` |
| `atomic/device_atomic_test.py` | 6 | 基础功能 — 设备 | `device_atomic` | `atomic/device/` |
| `atomic/segment_atomic_test.py` | 6 | 基础功能 — 段模型 | `segment_atomic` | `atomic/segment-model/` |
| `atomic/sn_atomic_test.py` | 6 | 基础功能 — SN | `sn_atomic` | `atomic/sn-management/` |
| `atomic/composite_device_test.py` | 6 | 基础功能 — 装置设备 | `composite_device_test` | `atomic/composite-device/` |
| `atomic/segment_entity_atomic_test.py` | 6 | 基础功能 — 段 | `segment_entity_atomic` | `atomic/segment-entity/` |

> **注意**：`device_managent_test.py` 的 script_id 已从 `device_managent` 修正为 `device_management`（修复 typo）。旧报告文件名 `device_managent_测试报告_*.html` 将在清理周期中移入 `_archive/`。

### 新平台探索（hlxinzhi — 惠联新质·电厂AI管家）

| 脚本 | 场景数 | 分类 | 说明 |
|:---|:---:|:---|:---|
| `platforms/hlxinzhi/scripts/e2e/knowledge_management_lifecycle.py` | 8 | 端到端 — 知识管理全生命周期 | 覆盖 luxiao2 上传→admin 审批→知识萃取→知识问答→清理。验证 Next.js + Shadcn UI (Radix UI) 交互模式 |

**交互特性**：Radix UI 组件使用 Playwright 原生 click() 即可驱动（2026-06-11 验证），文件上传通过隐藏 `input[type="file"]`。详见 `references/shadcn-ui-patterns.md`。

---

## 报告命名标准与清理机制

### 报告命名铁律

- **必须使用** `{script_id}_测试报告_{ts}.html` — 禁止裸 `测试报告_{ts}.html`
- ~~`{script_id}_results_{ts}.json`~~ **⚠️ JSON 报告已于 2026-06-10 弃用** — `JsonRenderer.save()` 现在为 no-op，不生成文件。
- script_id 使用**英文小写+下划线**，如 `device_management`、`sn_lifecycle`
- script_id 一旦确定不可随意更改（否则聚合报告依赖链断裂）

### 报告清理（`config.cleanup_old_reports`）

`run.py` / `core/runner.py` 启动时自动调用 `cleanup_old_reports()`，执行以下策略：

| 条件 | 动作 |
|:---|:---|
| `e2e/{module-subdir}/` 或 `atomic/{module-subdir}/` 中报告 > 7 天 | 移入 `_archive/` |
| 兼容旧格式：`e2e/` 或 `atomic/` 根目录下也有报告文件 | 同样移入 `_archive/` |
| `_archive/` 中报告 > 30 天 | 自动删除 |
| 根级全量测试报告 | 永久保留（不归档） |

环境变量控制：`IOT_REPORT_RETENTION_DAYS=14`、`IOT_ARCHIVE_MAX_DAYS=60`

### 输出目录规范

| 内容 | 位置 |
|:---|:---|
| 端到端测试报告 | `platforms/{id}/docs/reports/e2e/{module-subdir}/{script_id}_测试报告_{ts}.html` |
| 原子功能测试报告 | `platforms/{id}/docs/reports/atomic/{module-subdir}/{script_id}_测试报告_{ts}.html` |
| ~~JSON 结果~~ | **⚠️ 已于 2026-06-10 弃用** |
| 聚合报告 | `platforms/{id}/docs/reports/全量测试报告_{ts}.html` |
| 操作手册 | `platforms/{id}/docs/manuals/` |
| 录制脚本 | `platforms/{id}/recordings/` |
| 全局媒体 | `docs/media/` |
| 探索产出 | `platforms/{id}/manifests/` + `docs/output/{id}/explore_{ts}/` |

**模块子目录映射**（定义在 `platforms/{id}/config.py` 的 `SCRIPT_REPORT_SUBDIRS` 字典）：

| 脚本 ID | 模块子目录 | 类型 |
|:---|:---|:---:|
| `device_management` | `device-management/` | E2E |
| `sn_lifecycle` | `sn-management/` | E2E |
| `bypass_lifecycle` | `bypass-management/` | E2E |
| `tag_lifecycle` | `tag-management/` | E2E |
| `pv_atomic` / `pv_import` | `pv-management/` | 原子 |
| `element_model_atomic` | `element-model/` | 原子 |
| `device_model_atomic` | `device-model/` | 原子 |
| `composite_device_model_atomic` | `composite-device-model/` | 原子 |
| `element_atomic` | `element/` | 原子 |
| `device_atomic` | `device/` | 原子 |
| `segment_atomic` | `segment-model/` | 原子 |
| `sn_atomic` | `sn-management/` | 原子 |
| `composite_device_test` | `composite-device/` | 原子 |

示例：设备管理 E2E 报告 -> `.../reports/e2e/device-management/device_management_测试报告_20260609_120000.html`

### 添加新脚本时的 checklist

- [ ] 确定类型：原子功能（`atomic/`）还是端到端场景（`e2e/`）
- [ ] 设置 script_id（`platforms/{id}/config.py` 的 `SCRIPTS` 或 `ATOMIC_SCRIPTS` 数组）
- [ ] 添加项目根目录到 `sys.path`（顶部 6 行模板代码）
- [ ] import 中加入 `get_script_report_dir`（`from config import BASE_URL, get_db_connection, E2E_REPORT_DIR, get_script_report_dir`）
- [ ] **`TestReport("标题")` 必须传 `output_dir=get_script_report_dir('e2e|atomic', 'script_id')`** — ⚠️ 漏掉此参数报告会输出到 `reports/` 根目录而非模块子目录。已有多个脚本踩过此坑。
- [ ] `generate_html(filename=f"{script_id}_测试报告_{_ts}.html")`
- [ ] 注册到 `platforms/{id}/config.py` 的脚本数组中

---

## 文件存储规范

> **2026-06-08 结构性重构**：从扁平 root 结构重构为 `platforms/{id}/scripts/{atomic,e2e}/` 架构。
> 根目录只保留配置 + 入口，核心代码归 `core/`，平台内容按维度隔离。

### 当前目录结构

```
D:/AI/harmes agent/WEB平台自动化/
├── run.py               ← 统一入口 (python run.py --platform iot --headless)
├── config.py            ← 平台路由器（动态转发到 platforms.{PLATFORM}.config）
├── .env                 ← 全局配置
├── _cleanup.py          ← AUTO_ 前缀测试数据批量清理工具（dry-run/execute/force）
| `core/` | 通用核心代码（所有平台共享） |
| ├── `runner.py` | 调度器（原 master_runner.py） |
| ├── `report_helper.py` | 报告框架 |
| ├── `report_collector.py` | |
| ├── `report_renderer.py` | HTML 报告渲染器（**2026-06-10 更新：浅色主题**） |
| ├── `json_renderer.py` | ~~JSON 报告（2026-06-10 弃用，`save()` 为 no-op）~~ |
│   ├── manifest_generator.py
│   ├── component_strategies/   组件交互策略
│   ├── healer/                 运行时自愈模块（2026-06-10 新增）
│   └── templates/              J2 模板
│
└── platforms/            ← 各平台独立上下文
    ├── __init__.py
    ├── iot/              ← IoT 物联管理平台
    │   ├── config.py           平台配置（读自身 .env）
    │   ├── .env
    │   ├── scripts/
    │   │   ├── e2e/            端到端业务场景
    │   │   └── atomic/         基础功能测试
    │   ├── manifests/          本平台探索产出（15 JSON）
    │   ├── docs/reports/       测试报告（含 _archive/）
    │   ├── docs/manuals/       操作手册
    │   ├── recordings/         录制脚本
    │   └── references/         本平台调试记录
    │
    └── tckz/             ← 总控平台（开发中）
        ├── config.py
        ├── .env
        ├── scripts/
        ├── manifests/
        └── references/
```

### 核心规范

| 维度 | 规范 |
|:---|:---|
| **根目录** | 只允许 `run.py`（入口）、`config.py`（路由器）、`.env`、`requirements.txt` |
| **核心代码** | 全部在 `core/` 下，以包形式组织（含 `__init__.py`） |
| **平台代码** | 全部在 `platforms/{id}/` 下，按平台维度隔离 |
| **脚本分类** | `e2e/` = 跨模块业务流，`atomic/` = 单菜单基础功能操作 |
| **报告输出 (E2E)** | `platforms/{id}/docs/reports/e2e/{module-subdir}/`（按模块归类） |
| **报告输出 (原子)** | `platforms/{id}/docs/reports/atomic/{module-subdir}/`（按模块归类） |
| **聚合报告** | `platforms/{id}/docs/reports/全量测试报告_{ts}.html` |
| **探索产出** | `platforms/{id}/manifests/` + `docs/output/{id}/explore_{ts}/` |
| **操作手册** | `platforms/{id}/docs/manuals/` |
| **录制脚本** | `platforms/{id}/recordings/` |
| **全局媒体** | `docs/media/` |

### 配置路由机制

根 `config.py` 是动态路由器：

```python
_PLATFORM = os.environ.get('PLATFORM', 'iot')
_mod = importlib.import_module(f'platforms.{_PLATFORM}.config')
for _attr in dir(_mod):
    if not _attr.startswith('_'):
        globals()[_attr] = getattr(_mod, _attr)
```

- 脚本中 `from config import BASE_URL` 自动路由到当前平台
- 设 `PLATFORM=tckz` 即切到 TCKZ 配置
- 环境变量由 `run.py` 根据 `--platform` 参数自动设置

### Python import 路径

所有脚本需确保项目根目录在 `sys.path` 中。`run.py` 自动处理。独立运行时每条脚本顶部添加：

```python
import sys, os
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
```

然后使用绝对导入：`from core.report_helper import TestReport`、`from config import BASE_URL`。

---

## 10. 工作方式纪律

1. **未知领域先调研再执行** — 当用户指出某个技术方向（如 OS 级对话框自动化）存在成熟方案而你用了简单绕路方案时，先系统性列出所有可能方案、逐一验证、报告结果，再给出推荐。不要用"行业标准"为借口不深入。
2. **结论先说，细节后补** — 优先给出 A/B 选择或是否判断，用户追问再展开。
3. **调试脚本后清理** — `*_debug.py`、`*_test.png` 等临时文件在验证通过后删除，不污染工作目录。
4. **破坏性文件操作必须预览征求同意** — 涉及 rm -rf、mv、批量删除文件时，必须先列出受影响的文件清单，征求用户确认后再执行。不得在未确认的情况下执行批量删除/移动。

5. **先定义结构再执行** — 涉及目录结构变更、文件移动、报告输出路径等影响整体布局的操作时，必须先与用户确认结构定义，待用户批准后再执行。不要跳过定义阶段直接执行。

6. **修改 reference 文件后必须维护交叉引用一致性** — 当新增或修改任何 `references/` 下的文件时，必须同步执行以下检查（警告：未执行此流程会导致规则与实现矛盾，如 `.el-message--success` 被误判为错误，或 el-select 被错误地判定为"不可自动化"）。

7. **决策场景只给最优方案，不给选择题** — 当用户询问问题诊断方案、架构选择、文件处置策略等决策性问题时，直接给出一个专业推荐方案并附带理由，不给"方案A/B/C 你选哪个"的多选项选择题。用户偏好是：**"请从专业角度，给出最靠谱的解决方案"**。多个选项仅在用户主动追问"还有什么备选吗"时才展开。

8. **一次性执行完整计划，不递进式询问** — 涉及多步骤优化、修复、清理的任务时，制定完整的执行计划后一次性完成所有步骤，不在执行中途停下来问用户"下一步要做什么"或"先确认删不删除"。用户偏好是：**"你自己制定一个完整的计划，一次性完成优化"**。

9. **不提交需要进一步讨论的建议作为 todo** — 任何需要用户决策才能推进的任务，要么直接替用户做决策并执行（适用于可逆操作），要么明确标记为"暂停/需确认"且暂时搁置不推进。不要在 active todo 列表中保留未决策项。如果必须等待用户决策，在汇报中明确列出并请求一次性批复。

9. **PPT 介绍稿必须有叙事逻辑** — 当需要制作本 skill 的介绍 PPT 时，遵循 `references/ppt-narrative-pattern.md` 的叙事结构（痛点→方案→演进→能力→实践）。不要平铺菜单式罗列功能。所有页面使用统一深色配色，附真实截图作为证据。\n\n   ### 交叉引用一致性检查清单

   - [ ] **SKILL.md 文件索引更新**：新增文件必须加入索引表并标注行数；行数变化超过 10 行的已有文件必须更新索引行数
   - [ ] **SKILL.md 规则一致性检查**：检查新文件中的规则/断言/选择器是否与 SKILL.md MUST 级规则冲突（例如 `check_page_errors` 的选择器范围不能扩大至 `.el-message` bare，否则违反规则 7）
   - [ ] **跨文件函数签名一致性检查**：所有文件中 `log()`、`check_page_errors()`、`fill()`、`ss()` 等工具函数的参数和返回值签名必须完全一致（特别警惕：`log(msg, icon)` vs `log(msg)` 在子 agent 委托中已多次造成 TypeError）
   - [ ] **幽灵文件标记**：如果文件属于"历史记录"性质（如记录被推翻的结论、已过时的调试记录），必须在文件开头添加醒目的 `> **⚠️ 已过时**` 标记，并用一句话说明当前应参考哪个文件。禁止仅标记"已过时"而不给出替代路径。
   - [ ] **Ghost 文件清理**：参见 `references/ghost-file-cleanup-methodology.md` 的三步法（审计列表 → 分类处置 → 索引同步更新）。核心原则：合并前用 `+=` 分步拼接，不要用条件表达式单行拼接。

### 常用工具陷阱

#### read_file + write_file 截断与格式污染

`read_file` 默认限制 500 行（`limit=500`）。当用 `execute_code` 的 `read_file()` + `write_file()` 组合时存在两个问题：

1. **截断**：如果源文件超过 500 行，`write_file` 会写回截断版本，导致文件后半段数据永久丢失。
2. **格式污染**：`read_file` 返回的 `result["content"]` 包含行号前缀 `NN|`。用 `write_file` 写回后，每行都变成 `1|#!/usr/bin/env python3` 格式，破坏 Python 语法。

**解决方案**：
- 始终指定 `limit=2000`：`read_file(path, limit=2000)`，或逐段读取
- 优先用 `terminal` 工具配合 Python 脚本读取和写入（`python -c "..."`）
- 文件变换优先用 `patch` 工具，而非 `read_file`+`write_file` 组合
- 如需用 `execute_code` 读写，用 `terminal()` 替代 `read_file()` + `write_file()`

#### ⚠️ Python 条件表达式优先级陷阱：`a + b if cond else c` ≠ `a + (b if cond else c)`

用 `execute_code` 或 `terminal python` 做内容合并时，条件表达式的绑定优先级会导致非预期的截断，**这是本 skill 历史数据丢失事故的根因**。

```python
# ❌ 陷阱：a + b + c if cond else d
# 实际解析为：(a + b + c) if cond else d
# 当 cond=False 时，整个 a + b + c 被丢弃，只返回 d
pem_updated = pem + "\n...appendix..." + content.split('---', 1)[-1] if '---' in content else "\n...appendix..." + content
# 如果 content 不包含 '---'，pem 被完全丢弃！
```

```python
# ✅ 正确：用括号明确条件作用的范围
pem_updated = pem + "\n...appendix..." + (content.split('---', 1)[-1] if '---' in content else content)
# 括号确保条件只作用在 split/raw 选择上，pem 总是被保留
```

**核心原则**：在混合 `+` 和 `if/else` 的表达式里，**始终用括号包围条件部分**。Python 的 `if/else` 条件表达式优先级低于所有算术/字符串拼接运算符，这违反了大多数人的直觉。

**合并操作的标准安全模式**（已验证，零丢失风险）：
```python
# 方案 A：用 += 分步拼接（最清晰）
result = target_file
result += "\n\n---\n\n## 附录\n\n"
result += source_content
open(path, 'w').write(result)

# 方案 B：如果必须单表达式，加括号
result = target_file + "\n\n---\n\n## 附录\n\n" + (source_content if cond else fallback)
```

#### ⚠️ DB 字段类型验证：`information_schema` 不能只看列名

`SELECT column_name FROM information_schema.columns` 只能确认「列存在」，不能确认「类型是什么」。SQL 断言中列类型假设错误会导致断言永远静默失败：

```python
# ❌ 错误：假设 is_delete 为 integer
cur.execute("SELECT is_delete FROM device_tags WHERE tag_code=%s", (code,))
row = cur.fetchone()
report.assertion("DB: 已删除", str(row[0]) == "1", ...)
# str(True) == "1" → "True" == "1" → 永远 False！

# ✅ 正确：先查类型再比较
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name='device_tags' AND column_name='is_delete'
""")
# data_type = 'boolean' → 用 row[0] is True
# data_type = 'integer'  → 用 row[0] == 1
```

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



```python
# ❌ 陷阱：a + b + c if cond else d
# 实际解析为：(a + b + c) if cond else d
# 当 cond=False 时，整个 a + b + c 被丢弃，只返回 d
pem_updated = pem + "\n...appendix..." + content.split('---', 1)[-1] if '---' in content else "\n...appendix..." + content
# 如果 content 不包含 '---'，pem 被完全丢弃！
```

```python
# ✅ 正确：用括号明确条件作用的范围
pem_updated = pem + "\n...appendix..." + (content.split('---', 1)[-1] if '---' in content else content)
# 括号确保条件只作用在 split/raw 选择上，pem 总是被保留
```

**核心原则**：在混合 `+` 和 `if/else` 的表达式里，**始终用括号包围条件部分**。Python 的 `if/else` 条件表达式优先级低于所有算术/字符串拼接运算符，这违反了大多数人的直觉。

**合并操作的标准安全模式**（已验证，零丢失风险）：
```python
# 方案 A：用 += 分步拼接（最清晰）
result = target_file
result += "\n\n---\n\n## 附录\n\n"
result += source_content
open(path, 'w').write(result)

# 方案 B：如果必须单表达式，加括号
result = target_file + "\n\n---\n\n## 附录\n\n" + (source_content if cond else fallback)
```

#### ⚠️ terminal `python -c` 反斜杠转义陷阱（Windows bash）

通过 git-bash 的 `terminal` 工具运行 `python -c "..."` 时，shell 会先处理反斜杠转义序列，导致 Python 收到的字符串与预期不同。

**症状**：`python -c "s = 'hello\\nworld'"` 中 `\\n` 被 bash 解释为 `\n`（换行符），而非 Python 期望的 `\n`（反斜杠+n）。文件写入后实际包含换行符而非转义序列，导致语法错误。

```bash
# ❌ 问题：通过 python -c 的 \\\\n 被 bash 吃掉一层
python -c "s = 'hello\\\\nworld'; print(repr(s))"
# 实际输出：'hello\\nworld'  → 两个反斜杠
# 期望输出：'hello\\nworld'   → 一个反斜杠+n
```

**解决方案**：不要用 `python -c` + 内联代码做文件修改。改用 `write_file` 工具写一个独立的 `.py` 脚本文件，然后通过 `terminal` 执行该脚本：

```python
# ✅ 正确：用 write_file 写 fix 脚本，然后 python fix_script.py 执行
write_file("fix_script.py", "修复逻辑的 Python 代码")
terminal("python fix_script.py")
```

**特别警告**：`execute_code` 的 `read_file()` + `write_file()` 组合会带回行号前缀 `NN|`，污染文件。文件变换优先用 `patch` 工具或独立 Python 脚本。

用 `sed` 做 Python import/函数调用的全局替换极易误伤。例如 `s/")$/", output_dir=X)/` 会匹配文件中所有以 `)` 结尾的行，损坏大量正常代码行（包括 assert、append、print、f-string 等）。

**正确方案**：

```python
import re
with open('file.py', encoding='utf-8') as f:
    content = f.read()
# 精确替换，只影响目标行
content = re.sub(r'TestReport\("([^"]+)"\)', r'TestReport("\1", output_dir=E2E_REPORT_DIR)', content)
with open('file.py', 'w', encoding='utf-8') as f:
    f.write(content)
```

始终用 Python 脚本（`terminal` 或 `execute_code`）做代码级文本变换，不要用 `sed`。

#### 脚本标准模板（argparse 与默认值）

端到端脚本和原子脚本必须使用以下标准参数模板（2026-06-08 更新：增加 `--headless` 兼容 runner）：

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

- `headless` 默认 `True`（无头），`--headed` 改为有头，`--headless` 显式指定无头
- `run()` 函数签名：`def run(start_scene=1, headless=True, cleanup=True)`
- 兼容 runner: runner 统一传 `--headless`，脚本同时接受此参数

#### ⚠️ terminal 后台模式输出缓冲（Windows）

`terminal(background=True)` 在 Windows bash 环境下**不会捕获 stdout**——进程运行但 `process(action='log')` 返回空输出。根因是 Python 子进程在非 TTY 模式下启用全缓冲。

**症状**：进程 uptime 持续增长但 `output_preview` 为空，`log` 无内容。

**解决方案**：
- 方案 A：`terminal("... > output.txt 2>&1", background=True)` 重定向到文件，然后用 `read_file` 轮询文件
- 方案 B：`terminal(foreground=True, timeout=N)` 前台执行，长任务需配合长 timeout
- 方案 C：子进程使用 `python -u`（unbuffered）或设置 `PYTHONUNBUFFERED=1`

**验证过的安全模式（本 session）**：

```bash
# 启动全量测试（后台，无超时限制）
cd "D:/AI/harmes agent/WEB平台自动化"
python -u run.py > /tmp/full_test_run.log 2>&1
# 注意：run.py 内部 subprocess.run 使用 capture_output=True，
# 所以 log 文件只在每个子脚本完成时刷新一次，不是实时流
# 适合监控的是：wc -l 增量 + 最终结果而非中间过程

# 检查进度（每 60-120 秒轮询一次）
wc -l /tmp/full_test_run.log           # 看行数是否增加
tail -10 /tmp/full_test_run.log        # 看当前在跑哪个脚本
grep "开始执行" /tmp/full_test_run.log | wc -l  # 已启动脚本数

# 跑完后提取结果
grep -E "(通过|失败|🎉|⚠️|总耗时)" /tmp/full_test_run.log
```

#### ⚠️ runner.py 独立 argparse 隔离

`core/runner.py` 的 `main()` 有自己独立的 `argparse.ArgumentParser`（只接受 `--headless`、`--exclude`、`--only`、`--list`）。**不要向 runner 传递 `--platform` 参数**——正确方式是通过 `run.py` 入口调用，或先设置 `os.environ['PLATFORM'] = 'iot'` 再 `from core.runner import main; main()`。

```bash
# ✅ 正确：通过 run.py 入口
python run.py --headless

# ✅ 正确：环境变量 + 直接调用 runner
PLATFORM=iot python -u -m core.runner

# ❌ 错误：runner 不认识 --platform
python run.py --platform iot --headless  # 如果 runner.main() 被调用时会先 parse_args()
```

### Runner 使用速查

Runner 相关的问题和配置细节已迁移到独立 reference 文件：

| 问题 | 参考文件 |
|:---|:---|
| CLI 参数不匹配（--headless vs --headed） | `references/runner-cli-mismatch.md` |
| 报告解析 regex 兼容（3 种输出格式） | `references/runner-report-parsing-fix.md` |
| 全量执行（E2E+Atomic）、依赖跳过恢复、config 配置、模板变量 NameError 陷阱 | `references/runner-cli-mismatch.md` + `core/runner.py` 源码；重构 `generate_master_report` 时所有模板中的 `for r in results` 必须改为 `all_results`（2处：progress bar + 终端汇总） |

---

### 运行时依赖自愈（Self-Healing Prerequisites）

**2026-06-08 新增**：端到端脚本（如 `bypass_lifecycle_test.py`）依赖的外部数据（如 PV）缺失时，应**自动创建缺失数据**而非直接退出。模式：

#### 标准实现模板

```python
# 消费型脚本前置自愈
from config import get_db_connection

def create_entity_if_missing(name, **fields):
    """自愈：如果实体不存在则自动创建"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM table WHERE code=%s", (name,))
        row = cur.fetchone()
        if row:
            cur.close(); conn.close()
            return row[0]

        # 不存在 → 自动创建（必须补齐使实体在UI中可搜索的关键字段）
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

def ensure_prerequisites():
    """自愈式前置检查：缺什么就创建什么"""
    ids = []
    for entity in [ENTITY_A, ENTITY_B]:
        pid = create_entity_if_missing(entity, code=entity, ...)
        ids.append(pid)
    all_ok = all(ids)
    print(f"{'✅' if all_ok else '❌'} 前置检查: {'全部通过' if all_ok else f'部分失败 {ids}'}")
    return all_ok
```

#### 规则

| 规则 | 说明 |
|:---|:---|
| **必须在 `run()` 中调用** | 场景执行前检查，失败时 `sys.exit(1)` |
| **只创建纯数据** | 不创建依赖于其他脚本完整业务流的数据（如设备需要模型已发布） |
| **DB 列名 + 类型必须用 `information_schema` 确认** | 列名正确但类型猜错（如 boolean 当成 integer）会导致断言永远失败。示例：`SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='device_tags'` 查出 `is_delete=boolean` 后断言应写 `row3[0] is True` 而非 `str(row3[0]) == "1"` |
| **日志必须清晰** | `🔧 自愈: 已创建PV 'xxx' (id=N)` 让用户知道自动补了数据 |
| **不覆盖已有数据 + 修复不完整实体** | 如果实体已存在但缺少使 UI 可搜索的关键字段（如 `acq_mode`、`device_id`、`is_delete`），执行 UPDATE 修复而非跳过 |

#### 适用范围

| 脚本 | 前置数据 | 自愈方式 |
|:---|:---|:---|
| `bypass_lifecycle_test.py` | ASSOC_PV_1, ASSOC_PV_2 | `create_pv_if_missing()` 直接 INSERT/UPDATE 到 `pv_data_info` |

#### 关键陷阱

- 仅 INSERT 到 DB 不保证 UI 搜索可见 — 可能还需 `acq_mode`、`device_id`、`is_delete=false` 等附加字段
- 先查 `information_schema.columns` 确认真实列名再写 SQL

---

### HealingOrchestrator：运行时自愈统一入口（v2）

**2026-06-10 新增**：`core/healer/` 提供 5 个运行时自愈模块 + 1 个调度器，替代裸 Playwright 操作。

#### 快速集成（3 行代码）

```python
# 在 run() 中创建页面后初始化
from core.healer import HealingOrchestrator
h = HealingOrchestrator(page, report, db_connection_fn=get_db_connection)

# 带选择器降级的 fill
h.fill("请输入PV名称", "test-PV")          # 自动 7 级降级

# 带自愈的 el-autocomplete
h.autocomplete_select("请输入模型名称搜索", "model-A")  # 3 级降级

# 带三重确认的自愈保存
h.save_and_verify("保存PV",                 # API/URL/toast/DB 四路检测
    db_verify_fn=find_pv_by_code,           # DB 验证函数
    db_args=[PV_CODE],                      # 验证参数
    expected_url="pv/list")                 # 期望跳转 URL

# 带类型适配的 DB 断言（自动查 information_schema）
h.assert_db("DB: 已软删除", "device_tags", "is_delete", row[0], True)

# 场景衔接自愈
h.heal_between_scenes(expected_url=PV_LIST_URL, scene_name="场景2")

# 测试结束时输出自愈统计
h.print_summary()
```

#### 设计原则

| 原则 | 说明 |
|:---|:---|
| **可独立使用** | 每个 Healer 可单独 import，不强制用 Orchestrator |
| **结果可见** | 自愈事件自动写入 `report.assertion`，不隐瞒失败 |
| **安全降级** | 全部降级失败返回 `False`，不抛异常，不影响流程 |
| **渐进集成** | 脚本可逐步引入，不改动即可继续使用原有断言模式 |

详见 `core/references/self-healing-v2-design.md`。已集成脚本：13 个脚本中的 13 个已完成基础集成（import + init + print_summary），其中 `pv_atomic_test.py` 启用了 SelectorHealer+SaveHealer，`device_model_atomic_test.py` 和 `element_atomic_test.py` 启用了 ComponentHealer。

#### ⚠️ 批量集成陷阱

当将 HealingOrchestrator 集成到现有脚本时，以下问题必须注意：

| 陷阱 | 表现 | 正确做法 |
|:---|:---|:---|
| **Viewport 创建模式差异** | 部分脚本用 `page.set_viewport_size()`，部分用 `browser.new_context(viewport=...)` | `h = HealingOrchestrator(...)` 必须放在 `page = ctx.new_page()` **之后**，无论 viewport 是如何设置的 |
| **try-except 缩进破坏** | 在 `try:` 和 `except` 之间插入代码时，`except` 丢失 8 空格缩进 | `h.print_summary()` 必须放在 **`try` 块内部**（12 空格缩进），与场景代码相同的缩进级别 |
| **get_by_label fill 不应替换** | 批量替换把所有 `get_by_placeholder().fill()` 转为 `h.fill()`，但 `get_by_label().fill()` 用于搜索栏，不属于定位不明的情况 | 只替换表单字段的 placeholder fill，搜索栏的 label fill 保持原样 |
| **E2E 大脚本谨慎操作** | `device_management_test.py`（1079 行，9 场景）的 save+check_page_errors 模式复杂 | 对 E2E 脚本优先只添加 import+init，逐步替换关键操作 |

---

### 报告通知

全量跑完成后，可通过 `send_message` 工具发送测试结果到微信：

```python
# 查看可用的消息目标
send_message(action="list")

# 发送测试结果
send_message(
    action="send",
    target="weixin:<user_id>@im.wechat",  # 从 list 结果获取
    message="测试报告摘要文本"
)
```

**文件发送**：`send_message` 的 `message` 字段支持 `MEDIA:<本地绝对路径>` 前缀，可直接发送 HTML 报告文件到微信、Telegram 等平台：

```python
send_message(action="send", target="weixin",
    message="MEDIA:D:/path/to/全量测试报告_20260610_200130.html")
```

发送成功返回 `"success": true`。平台文件大小限制：微信约 20MB。

**文本概要**：对于大文件或需要快速查看的内容，仍保留文本摘要发送方式。
```python
send_message(action="send", target="weixin",
    message=f"✅ 全量测试通过\n脚本: {n}/{total} | 场景: {n_scene} | 断言: {n_pass}/{n_total}")
```

---

### delegate_task 超时陷阱：浏览器操作密集型任务

`delegate_task` 默认 600 秒超时。含大量 `browser_navigate` + `browser_click` 等浏览器操作的任务（如编写新测试脚本时反复打开页面探索路由），**不应通过子 agent 并行执行**，原因：

| 问题 | 说明 |
|:---|:---|
| **浏览器操作慢** | 每个 `page.goto()` + `time.sleep()` 约 3-5 秒，批量验证 20+ 路由需 60-100 秒 |
| **页面渲染阻塞** | SPA 应用的页面切换可能触发异步数据加载，进一步拉长等待时间 |
| **子agent 无法恢复** | 600s 超时后子 agent 被杀死，中间产出（已写的脚本、已做的配置修改）可能丢失 |
| **无进度可见性** | 子 agent 的中间日志不回流，直到超时或完成才返回摘要 |

**推荐做法**：
- 脚本编写任务按模块**独立串行**而非并行，或在主 agent 中直接编写
- 如果必须并行，设置 `timeout=900`（需在 `config.yaml` 的 `delegation` 段调整 `max_agent_timeout`）
- 仅将**无需浏览器**的任务（如数据分析、脚本重构、正则替换）委托给子 agent

#### 子agent编写测试脚本的已知陷阱

当使用 `delegate_task` 让子 agent 编写 Playwright 测试脚本时，以下问题是高频复现的，需要在委托 context 中明确约束：

| 陷阱 | 表现 | 约束 |
|:---|:---|:---|
| **标签定位选择错误** | 子agent 用 `get_by_placeholder("* 模型名称")`，实际 label 是 `模型名称` | 强制要求先 `browser_navigate` + 字段诊断代码确认 label/placeholder，再写定位代码 |
| **log() 签名不匹配** | 子agent 脚本中 `log("msg", "icon")` 但实际 runtime 脚本只定义 `log(msg)` | 委托 context 中写明：`log(msg)` 只接受 1 个参数（**注意**：`craft-cli-patterns.md` 模板定义了 `log(msg, icon=None)` 但实际脚本未统一升级，使用双参数前必须确认目标脚本的定义） |
| **点击不可见的菜单项** | 子agent 用 `page.get_by_text("设备模型").click()` 但菜单在 sidebar 底部不可见 | 委托 context 中说明**菜单项用 JS evaluate 点击**或直接 `page.goto(list_page_url)` |
| **忽略已有脚本模板** | 子agent 自创一套脚本结构，与现有 `pv_atomic_test.py` 风格不一致 | 委托 context 中**必须附上一个已验证的参考脚本 URL**（如 `pv_atomic_test.py`），要求严格遵循其结构和风格 |
| **数据隔离前缀不一致** | 清理逻辑用不同前缀导致遗留数据 | 委托 context 中明确规定 `DATA_PREFIX = f'AUTO_{MODULE}_{RUN_ID}'` |
| **断言双分支遗漏** | if 分支有断言但 else 分支没有，导致静默跳过 | 委托 context 中重申 else 分支必须有 `report.assertion(..., False, ...)` |

---

## 添加新平台步骤

1. 在 `platforms/` 下创建新目录（如 `platforms/abc/`），复制 `iot/` 的目录骨架
2. 编写 `platforms/abc/.env`（平台 URL、DB 连接等）和 `platforms/abc/config.py`（继承框架配置规范）
3. 设置 `PLATFORM_ID`、`SCRIPTS`（e2e 脚本数组）和 `ATOMIC_SCRIPTS`（原子脚本数组）
4. **在 `config.py` 中添加 `SCRIPT_REPORT_SUBDIRS` 字典**，为每个脚本定义模块子目录（参考 IoT 的映射），确保报告按模块归类而非平铺
5. 运行 `python run.py --platform abc --list-scripts` 验证配置路由
6. 按照 `scene-design.md` 的检查清单设计场景
7. **确认平台 UI 框架类型**：若为 Shadcn UI / Radix UI（Next.js React），参考 `references/shadcn-ui-patterns.md` 中的 PointerEvent 交互模式和组件定位方式；若为 Element Plus（Vue），参考 `references/element_ui_patterns.md`
8. 在 `scripts/e2e/` 或 `scripts/atomic/` 下编写脚本，参考已验证的 IoT 脚本模式，使用 **`get_script_report_dir(script_type, script_id)`** 而非裸 `E2E_REPORT_DIR` / `ATOMIC_REPORT_DIR`
9. 使用 `from core.report_helper import TestReport`、`from config import BASE_URL, get_script_report_dir` 等核心导入
10. 验证：`python run.py --platform abc --only <script_id>`

### 迁移现有平铺报告到模块子目录（适用场景：从旧有 flat 结构升级）

当已有平台（如 tckz）的报告文件平铺在 `e2e/` 和 `atomic/` 根目录下，需要迁移到模块子目录时，可以编写一次性 Python 脚本完成迁移。核心逻辑：按 `script_id` 前缀匹配文件名 → 查找 `SCRIPT_REPORT_SUBDIRS` 映射 → 移入对应子目录。参考 `references/report-directory-migration.md`。
