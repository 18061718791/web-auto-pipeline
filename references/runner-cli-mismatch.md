# Runner CLI 参数不匹配 — 发现与修复全记录

## 发现问题

2026-06-08 执行全量测试时发现：运行 `PLATFORM=iot python -m core.runner --headless` 后，子脚本全部失败且无可见输出。

## 症状

```
开始执行: 设备管理
命令: D:\Program Files\Python313\python.exe -u ...device_management_test.py --headless

❌ 依赖 'device_management' 执行失败，跳过 'sn_lifecycle'
```

Runner 捕获了 stdout/stderr 但不打印到终端，只有 `依赖执行失败` 提示。子进程实际上因参数错误中途退出。

## 根因

| 组件 | 参数定义 | 语义 |
|:---|:---|:---|
| `core/runner.py` 旧代码第 62 行 | `cmd.append("--headless")` | 通知脚本以无头模式运行 |
| 各类 `*_test.py` argparse | `add_argument("--headed")` | `--headed` 开启有头，默认无头 |

`runner.py` 在无头模式下给脚本传递 `--headless`，但脚本只认 `--headed`。`--headless` 未被识别，argparse 报错退出。

## 代码修复（2026-06-08 执行）

**修改 `core/runner.py` 的 `run_script()` 函数**：

```python
# 旧代码（有 bug）：
def run_script(script_info, headless=False):
    script_path = os.path.join(SCRIPTS_DIR, script_info["file"])
    cmd = [PYTHON, "-u", script_path]
    if headless:
        cmd.append("--headless")   # ← 脚本不认识 --headless

# 修复后（2026-06-08）：
def resolve_script_path(file):
    """同时支持 E2E 和原子脚本目录"""
    e2e_path = os.path.join(SCRIPTS_DIR, file)
    if os.path.isfile(e2e_path):
        return e2e_path, "e2e"
    atomic_path = os.path.join(ATOMIC_SCRIPTS_DIR, file)
    if os.path.isfile(atomic_path):
        return atomic_path, "atomic"
    raise FileNotFoundError(...)

def run_script(script_info, headless=False):
    script_path, script_type = resolve_script_path(script_info["file"])
    cmd = [PYTHON, "-u", script_path]
    # ★ 修复：不向子脚本传 --headless（脚本默认无头）
    # 仅在需要有头模式时传 --headed
    if not headless:
        cmd.append("--headed")
```

## 确认命令

```bash
# ❌ 修复前：直接跑脚本 + --headless → 报错
$ PLATFORM=iot python platforms/iot/scripts/e2e/device_management_test.py --headless
usage: device_management_test.py [-h] [--headed] [--start-scene START_SCENE] [--no-cleanup]
device_management_test.py: error: unrecognized arguments: --headless

# ✅ 修复后：runner 不传 --headless，脚本默认无头，正常执行
$ PLATFORM=iot python -m core.runner
```

## 补充修复：Runner 解析正则优化

在同一提交中修复了 runner 的 3 个 regex 解析点，使其兼容 E2E 和原子脚本的不同输出格式。详见 `references/runner-report-parsing-fix.md`。

## 补充修复：Runner 纳入原子脚本

在同一提交中将 `scripts_to_run` 从 `SCRIPTS[:]` 扩展为 `SCRIPTS[:] + ATOMIC_SCRIPTS[:]`，runner 现在可一键全量执行。

```python
# 修复前：只跑 E2E 4 个脚本
scripts_to_run = SCRIPTS[:]

# 修复后：跑 E2E + Atomic 共 6 个脚本
scripts_to_run = SCRIPTS[:] + ATOMIC_SCRIPTS[:]
```
