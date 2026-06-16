# Agent 故障排查决策树

> Agent 遇到问题时，按此决策树快速定位和解决。

```
脚本执行失败？
│
├─ 页面操作类
│  ├─ 元素定位超时？
│  │  ├─ 字段输入失败 → 检查是 Model 页还是 Instance 页
│  │  │  ├─ Model 页 → get_by_label("字段名")
│  │  │  └─ Instance 页 → get_by_placeholder("请输入XXX")
│  │  ├─ 下拉选择失败 → 见 references/element_ui_patterns.md
│  │  ├─ el-autocomplete 失败 → 见 references/el-autocomplete-trap.md
│  │  └─ 通用 → 先跑 FIELD_SCAN 确认定位方式
│  │
│  ├─ 保存后无反应？（静默保存失败）
│  │  ├─ 1. el-autocomplete popper 未关闭 → Escape 关闭后重试
│  │  ├─ 2. 表单验证错误 → 检查 .el-form-item__error
│  │  ├─ 3. 按钮 disabled → 检查前置条件
│  │  └─ 详细流程 → references/SKILL_DETAIL.md §3
│  │
│  ├─ 场景间导航失败？
│  │  ├─ SPA 同路由重导航 → 删除冗余 goto/菜单点击
│  │  ├─ 场景间状态丢失 → 场景末尾恢复列表页+搜索状态
│  │  └─ 详见 → SKILL.md §1 + references/SKILL_DETAIL.md §1
│  │
│  └─ 组件交互异常？
│     ├─ el-select → force=True + .el-select-dropdown__item
│     ├─ el-cascader → force=True + 点 checkbox + Escape
│     ├─ el-upload → .el-upload 包装器 + expect_file_chooser
│     ├─ el-tree → .inner_text() 或 .node-actions
│     └─ Shadcn/Radix → Playwright 原生 click()
│
├─ 断言失败类
│  ├─ UI 断言失败
│  │  ├─ 文本不匹配 → browser_snapshot 确认实际渲染文本
│  │  ├─ 元素找不到 → 检查表格结构（兄弟 vs 嵌套）
│  │  └─ 状态不对 → 软删除时查 is_delete 字段
│  │
│  ├─ DB 断言失败
│  │  ├─ 类型不匹配 → 先查 information_schema.columns 确认 data_type
│  │  │  ├─ boolean → row[0] is True
│  │  │  └─ integer → row[0] == 1
│  │  └─ 记录不存在 → 检查清理是否误删（LIKE 模式 vs 精确匹配）
│  │
│  └─ 静默跳过（最危险）
│     ├─ else 分支无断言 → 必须加 report.assertion(..., False, msg)
│     └─ check_page_errors 未检查返回值 → has_err = ...; if has_err: return
│
├─ 数据类
│  ├─ 数据残留 → finally 块加 LIKE 模式清理
│  ├─ 清理删错表 → 按模块匹配正确表（SN→device_sn，模型→thing_model）
│  ├─ 依赖缺失 → 自动创建前置数据（ensure_prerequisites）
│  └─ 侧效应数据 → 基线保留法清理
│
└─ 报告/框架类
   ├─ 报告输出到根目录 → 缺少 output_dir=get_script_report_dir()
   ├─ runner 参数错误 → runner 只有 --headless/--exclude/--only/--list
   ├─ import 路径错误 → 确保项目根目录在 sys.path
   └─ Healer 集成陷阱 → h=HealingOrchestrator 必须在 page 创建之后
```

## Agent 步骤清单

编写新脚本时，按此清单逐项确认：

### 脚本前准备
- [ ] 确认脚本类型（基础功能 vs 端到端）
- [ ] 确认数据依赖链（端到端必须画有向图）
- [ ] 确认平台 UI 框架（Element Plus / Shadcn UI / 其他）
- [ ] 查阅 `references/platform-diff.md` 获取已知路由映射

### 编写脚本
- [ ] 添加项目根目录到 sys.path（4 层 `..` 相对路径）
- [ ] 设置 script_id 并注册到 config.py
- [ ] TestReport 传 output_dir=get_script_report_dir()
- [ ] 所有表单字段先 browser_snapshot 确认定位方式
- [ ] 场景间不重复导航（用菜单直接点击）
- [ ] 每个保存操作后 check_page_errors + 提前 return
- [ ] 所有 if/else 分支都有显式断言
- [ ] 发等异步操作用轮询（最多 30 秒）
- [ ] 数据清理用 AUTO_ 前缀 + like 模式匹配

### Healer 集成（推荐）
- [ ] import HealingOrchestrator
- [ ] h = HealingOrchestrator(page, report, db_connection_fn=get_db_connection)
- [ ] 表单 fill → h.fill()（7 级降级）
- [ ] 保存 → h.save_and_verify()（API/URL/toast/DB 四路检测）
- [ ] DB 断言 → h.assert_db()（自动查类型）
- [ ] h.print_summary() 放在 try 块内部

### 脚本后验证
- [ ] run.py --only <script_id> 执行
- [ ] 报告输出到正确子目录（非根目录）
- [ ] finally 块数据清理生效（DB 中无残留 AUTO_ 数据）
- [ ] 所有断言通过或失败原因明确

## 自检清单（提交前必过）

| 维度 | 检查项 |
|:---|:---|
| **导航** | 场景间无重复 goto/搜索？SPA 同路由无重导航？ |
| **断言** | 所有 if/else 分支有断言？check_page_errors 返回值已检查？ |
| **数据** | AUTO_ 前缀？finally 块 LIKE 清理？按模块匹配正确表？ |
| **报告** | output_dir 参数？命名 `{script_id}_测试报告_{ts}.html`？ |
| **定位** | FIELD_SCAN 已确认？Model 页用 label / Instance 页用 placeholder？ |
| **Healer** | h 放在 page 创建之后？print_summary() 在 try 内？ |
| **配置** | script_id 注册到 config.py？sys.path 包含项目根？ |