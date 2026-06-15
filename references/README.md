# References 知识库索引

## standards/ — MUST 级规则与设计标准
| 文件 | 说明 |
|:-----|:------|
| `core-principles.md` | 11 条 MUST 级规则的完整解释 |
| `scene-design.md` | 测试分类原则（基础功能 vs 端到端） + 场景设计规范 |
| `framework-architecture.md` | 框架架构设计 |
| `full-report-architecture.md` | 报告系统架构 |
| `manifest-system.md` | Page Manifest 规范 |
| `report-system.md` | 报告系统设计 |
| `self-healing-v2-design.md` | 自愈 v2 设计文档 |
| `execution-pattern-template.md` | 执行模式模板 |
| `atomic-test-patterns.md` | 原子测试模式 |
| `assertion-extraction-pattern.md` | 断言提取模式 |
| `assertion-integrity.md` | 断言完整性规范 |
| `verify-save-pattern.md` | 保存验证模式 |
| `three-perspective-review.md` | 三视角评审规范 |
| `ui-fixture-pattern.md` | UI Fixture 模式 |
| `test-data-cleanup-strategy.md` | 数据清理策略 |
| `test-data-migration.md` | 数据迁移方案 |

## traps/ — 组件陷阱与调试
| 文件 | 说明 |
|:-----|:------|
| `el-autocomplete-trap.md` | el-autocomplete 陷阱 |
| `el-cascader-trap.md` | el-cascader 陷阱 |
| `element_ui_patterns.md` | Element Plus 交互模式 |
| `shadcn-ui-patterns.md` | Shadcn UI / Radix UI 交互模式 |
| `file-upload-technique.md` | 文件上传技术方案 |
| `fragility-audit-checklist.md` | 脆弱性审计清单 |
| `debugging-techniques.md` | 调试技术 |
| `debugging-workflow.md` | 调试工作流 |
| `failure-catalog.md` | 故障目录 |
| `file-storage-analysis.md` | 文件存储分析 |
| `ghost-file-cleanup-methodology.md` | Ghost 文件清理方法论 |
| `runner-cli-mismatch.md` | CLI 参数不匹配修复 |
| `runner-report-parsing-fix.md` | 报告解析修复 |
| `report-directory-migration.md` | 报告目录迁移 |
| `equipment-test-patterns.md` | 设备测试模式 |
| `example-device-atomic.md` | 设备原子测试示例 |
| `device-management-fixes-20260608.md` | 设备管理修复记录 |

## patterns/ — 设计模式与流程
| 文件 | 说明 |
|:-----|:------|
| `craft-cli-patterns.md` | CLI 设计模式 |
| `platform-exploration-methodology.md` | 平台探索方法论 |
| `platform-diff.md` | 跨平台差异 |
| `ppt-narrative-pattern.md` | PPT 叙事结构 |
| `skill-health-checklist.md` | Skill 健康检查清单 |

## 平台特定记录（应随 platforms 目录发布）
| 文件 | 所属平台 | 说明 |
|:-----|:---------|:------|
| `iot-device-records.md` | IoT | 设备管理记录 |
| `iot-full-coverage-plan.md` | IoT | 全量覆盖计划 |
| `iot-route-map.md` | IoT | 路由映射 |
| `tckz-records.md` | TCKZ | TCKZ 平台记录 |

> 平台特定文档建议迁移到对应的 platforms 仓库中管理，Skill 本身只保留通用知识。
