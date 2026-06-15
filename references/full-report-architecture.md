# 全量测试报告架构

> 2026-06-09 重构：从单模块改为双模块展示。
> 2026-06-10 更新：基础功能移除数据流图；进度条条件渲染修复。

## 设计

全量报告由 `core/runner.py` 的 `generate_master_report(e2e_results, atomic_results)` 生成，接收两个参数而非原来的单一 `results`：

```python
master_path = generate_master_report(e2e_results, atomic_results, headless=True)
```

## 双模块结构

| 模块 | 标题 | 数据依赖 |
|:---|:---|:---|
| 🚀 **端到端场景** | 端到端脚本 + 各自场景 | E2E 脚本之间存在真实数据依赖（如 sn_lifecycle → device_management），按 `depends_on` 配置展示 |
| 📦 **基础功能** | 原子脚本 + 各自场景 | 基础功能脚本完全独立（无 `depends_on`），**不展示数据流图**（数据独立时箭头流无意义） |

## 模板变量变化

| 旧变量 | 新变量 | 原因 |
|:---|:---|:---|
| `results` | 拆分为 `e2e_results` + `atomic_results` | 双模块展示 |
| `results` (progress bar) | `all_results` (= `e2e_results + atomic_results`) | 进度条需统计全部脚本 |
| `results` (summary print) | `all_results` | 终端汇总输出 |

## 已知陷阱

### `NameError: name 'results' is not defined`

重构时容易遗漏模板字符串中的 `for r in results` 引用。搜索以下模式确保全部更新：

```python
# 搜索 patterns:
for r in results           # → all_results
for r in e2e_results: ...  # 正确
for r in atomic_results: ... # 正确
```

`generate_master_report` 中被引用的变量必须与函数形参匹配。

### NameError 触发条件
- 所有 14 个脚本执行完毕 → "生成聚合测试报告..." 打印成功 → 全量报告 HTML 已写入（46KB+）→ 但在最终汇总打印 `for r in results:` 时抛 NameError
- **exit code 仍然是 1**（因为异常未捕获），但报告文件已完整生成
- 修复路径：`results` → `all_results`（在 main() 的 final summary 和 progress bar 模板中各有 1 处）

### 进度条小红段（全部通过时仍有红色）

**问题**（2026-06-10 修复）：即使 `r["scene_stats"]["failed"] == 0`，原代码仍渲染 `<div class="progress-fail" style="flex:0.1">`，在进度条末端产生一条可见的小红段。

**修复**：`progress-fail` div 仅在 `failed > 0` 时才渲染，全部通过时进度条纯绿。

```python
# 修复前 — 始终渲染
f'<div class="progress-fail" style="flex:{r["scene_stats"]["failed"] or 0.1}"></div>'

# 修复后 — 条件渲染
(f'<div class="progress-fail" style="flex:{r["scene_stats"]["failed"]}"></div>'
 if r["scene_stats"]["failed"] > 0 else '')
```

**验证**：触发条件修复后，下次全量跑生成的报告即可验证。可通过 `grep progress-fail` 确认未带条件渲染的旧写法是否已消除。
