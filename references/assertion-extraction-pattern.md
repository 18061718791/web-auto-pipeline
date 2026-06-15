# Assertion-Extraction Pattern: Child Script → Parent Runner 断言汇总通信

## 问题

`runner.py` 的聚合报告显示某些脚本的断言为 0（如 `断言0/0`），但脚本中实际执行了大量 `report.assertion()` 调用。

## 根因

`runner.py` 提取断言统计的方式是 **解析子脚本 stdout** 中的特定格式行：

```python
m = re.search(r'📊\s*断言:\s*通过(\d+)\s*失败(\d+)', line)
# or
m2 = re.search(r'(\d+)/(\d+)\s*断言通过', line)
```

如果子脚本从未向 stdout 输出断言汇总行，则 `assert_stats` 始终为 `{0, 0}`。

## 修复（2026-06-10）

在 `TestCollector.get_data()` 中集中打印断言汇总（一次修改覆盖所有使用 TestReport 的脚本）：

```python
def get_data(self):
    ...
    assert_pass = sum(s["assert_pass"] for s in self.scenes)
    assert_fail = sum(s["assert_fail"] for s in self.scenes)

    print(f"📊 断言: 通过{assert_pass} 失败{assert_fail}")
    ...
```

`get_data()` 由 `report.generate_html()` 调用，每个脚本在测试结束时调用一次 `generate_html()`，因此汇总行出现在脚本 stdout 末尾。

## 设计原则

| 原则 | 说明 |
|:---|:---|
| **集中汇总** | 在 `TestCollector.get_data()` 统一打印，而非每个脚本各自打印。单点修改覆盖所有脚本 |
| **stdout 通信** | 子脚本通过 stdout 向父进程 `runner.py` 传递统计，这是无需额外 IPC 机制的最轻量方式 |
| **regex 提取** | `runner.py` 的 `run_script()` 中循环扫描 stdout 所有行，取最后匹配项 |
| **格式约定** | `📊 断言: 通过X 失败Y` — 既含 emoji 前缀用于标识，又用可解析的结构化格式 |

## 适用范围

此模式适用于 `runner.py` 的下述提取变量：

| 变量 | stdout 匹配行 | 正则模式 |
|:---|:---|:---|
| `scene_stats` | `📊 场景: 通过9 失败0 跳过0` | 3 种兼容格式 |
| `assert_stats` | `📊 断言: 通过25 失败0` | `📊\s*断言:\s*通过(\d+)\s*失败(\d+)` |
| `report_path` | `📋 测试报告: /path/to/file.html` | `📋\s*(?:测试报告\|报告已生成\|报告):\s*(.+)` |
