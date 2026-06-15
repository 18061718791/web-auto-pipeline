# 文件存储规范与已知问题分析

> 2026-06-08 全面审计 + 一次优化执行完成。
> 本文档定义了流水线生成文件（报告/manifest/探索产出）的存放规则，
> 问题分析（10 个），以及 2026-06-08 已执行的 Plan A 修复方案。

---

## 当前实际目录结构（2026-06-08 清理后）

```
D:/AI/harmes agent/WEB平台自动化/     ← 工作根目录（所有脚本在此运行）
├── config.py, .env                   ← 平台配置（含 cleanup_old_reports()）
├── device_managent_test.py           ← 端到端脚本（9 场景，script_id=device_management）
├── sn_lifecycle.py                   ← 端到端脚本（3 场景）
├── tag_lifecycle_test.py             ← 端到端脚本（7 场景）
├── bypass_lifecycle_test.py          ← 端到端脚本（5 场景）
├── pv_atomic_test.py                 ← 原子脚本（8 场景）
├── pv_import_test.py                 ← 原子脚本（2 场景）
├── master_runner.py                  ← 多脚本聚合调度器（含 cleanup_old_reports 调用）
├── report_helper.py / report_collector.py / report_renderer.py  ← 报告框架
├── manifests/                        ← Page Manifest JSON（15 个，唯一权威位置）
├── profiles/
│   ├── iot/
│   │   ├── .env / config.py          ← 平台配置（未来 profile_loader 使用）
│   │   └── scripts/                  ← 仅保留与根目录完全一致的文件副本
│   └── tckz/                         ← 空壳状态
├── docs/
│   ├── output/iot/                   ← 测试报告输出
│   │   ├── {script_id}_测试报告_{ts}.html
│   │   ├── {script_id}_results_{ts}.json
│   │   ├── 全量测试报告_{ts}.html     ← master_runner 产出
│   │   └── _archive/                 ← 自动归档（>7 天报告）
│   ├── manuals/iot/                  ← 操作手册（HTML+PDF）
│   └── media/                        ← 视频产出
├── core/                              ← 公共框架（report_collector/renderer 等）
├── templates/                         ← 脚本模板
└── references/                        ← 全局参考文档
```

### 关键矛盾（已标记，未解决）

| SKILL.md 描述的架构 | 实际运行中的架构 | 状态 |
|---|---|---|
| `profiles/<id>/scripts/` 为唯一脚本位置 | 根目录为主脚本位置 | 已清理过期副本，标记为蓝图为"未实现" |
| `profiles/<id>/manifests/` 唯一位置 | `manifests/` 根目录为活跃位置 | 已删除 profiles/ 副本 |
| 通过 `runner.py --profile <id>` 调用 | 直接 `master_runner.py` 调用 | 待实现 |
| `docs/output/<id>/` 为各平台报告 | 仅 iot 有产出 | 一致 |

---

## 报告输出规范

### 命名铁律（MUST）

- 子报告：`{script_id}_测试报告_{ts}.html`
- JSON 结果：`{script_id}_results_{ts}.json`
- 禁止裸 `测试报告_{ts}.html`（会导致多脚本互相覆盖）
- `script_id` 英文小写+下划线，如 `device_management`

### 输出目录分布

| 内容 | 路径 | 管理方式 |
|:---|:---|:---:|
| 测试报告 + JSON | `docs/output/{PLATFORM_ID}/` | 自动清理（7 天 → _archive/，30 天删除） |
| 聚合报告 | `docs/output/{PLATFORM_ID}/全量测试报告_{ts}.html` | 永久保留 |
| 操作手册 | `docs/manuals/{PLATFORM_ID}/` | 手动管理 |
| 视频/媒体 | `docs/media/` | 手动管理 |
| 探索产出 | `docs/output/{PLATFORM_ID}/explore_{ts}/` | 通过 `--platform-id` 参数控制 |

### 脚本 script_id 对照表

| 脚本 | script_id | 报告文件名前缀 |
|:---|:---|---:|
| `device_managent_test.py` | `device_management` | `device_management_测试报告_` |
| `sn_lifecycle.py` | `sn_lifecycle` | `sn_lifecycle_测试报告_` |
| `tag_lifecycle_test.py` | `tag_lifecycle` | `tag_lifecycle_测试报告_` |
| `bypass_lifecycle_test.py` | `bypass_lifecycle` | `bypass_lifecycle_测试报告_` |
| `pv_atomic_test.py` | `pv_atomic` | `pv_atomic_测试报告_` |
| `pv_import_test.py` | `pv_import` | `pv_import_测试报告_` |

---

## 10 个已知问题 — 修复状态（2026-06-08）

| # | 问题 | 严重度 | 修复状态 | 修复动作 |
|---|:---|:---:|:---:|:---|
| P1 | Manifests 双份（root vs profiles/iot） | 中 | ✅ 已修复 | 删除 profiles/iot/manifests/，root 为权威 |
| P2 | 脚本在三处重复 | 中 | ✅ 已修复 | 删除 profiles/iot/scripts/ 中 7 个过期副本 |
| P3 | 无前缀报告互相覆盖 | 高 | ✅ 已修复（代码）+ ⏳ 历史遗留 | 修复 generate_html 命名，cleanup 自动归档旧报告 |
| P4 | 报告无自动清理 | 高 | ✅ 已修复 | config.py 新增 cleanup_old_reports() + master_runner 调用 |
| P5 | Explorer 产出混乱 | 中 | ✅ 已修复 | explorer_core.py 新增 `--platform-id`，默认 `docs/output/{id}/explore_{ts}/` |
| P6 | 报告漏到 profiles/iot/scripts/ | 中 | ✅ 已修复 | 删除 3 个陈旧文件 |
| P7 | tckz/reports/ 与约定不一致 | 低 | ✅ 已修复 | 删除空目录 |
| P8 | script_id 命名不一致 | 低 | ✅ 已修复 | `device_managent` → `device_management`，`hybrid_9scenes` → `device_test_hybrid` |
| P9 | 调试文件污染 | 低 | ✅ 已修复 | 删除 18 个一次性调试脚本 |
| P10 | 非报告文件混入 | 低 | ✅ 已修复 | 手册 → docs/manuals/iot/，视频 → docs/media/ |

### 待办项

- [ ] 18 个裸 `测试报告_*.html` 是历史遗留，下次运行 `master_runner.py` 时 `cleanup_old_reports()` 会自动归档
- [ ] `docs/output/iot/images/` 是操作手册截图的残留，由操作手册工具管理
- [ ] profiles/ 架构完全落地（含 `runner.py --profile`）仍待实现

---

## 外部工具输出分类

| 产出类型 | 生成工具 | 存放位置 |
|:---|:---|:---|
| 测试报告 | `TestReport.generate_html()` | `docs/output/{PLATFORM_ID}/` |
| 操作手册 | `doc_recorder.py` | `docs/manuals/{PLATFORM_ID}/` |
| 视频 | `make_video.py` | `docs/media/` |
| 平台探索 | `explorer_core.py` | `docs/output/{PLATFORM_ID}/explore_{ts}/` |

---

## 维护原则

1. **预览征求同意** — 涉及 rm -rf、mv、批量删除文件时，先列出受影响文件清单
2. **只清理自己的数据** — 只删除自动化测试数据和临时产出，不动存量用户数据
3. **profiles/ 是未来架构** — 保持目录结构但删除过期副本，标记为"蓝图"
4. **不遗留调试文件** — `*_debug.py` 等调试文件验证通过后立即删除
