# Craft CLI 模式（参数化脚本工程规范）

> 从 Webwright 的 Craft 模式适配，为 `web-auto-pipeline` 脚本提供可复用 CLI 工具的构建规范。
> 适用场景：需要参数化执行（如 `--model-name`, `--headless`）和 CI 集成的测试脚本。

## 适用判断

| 条件 | 使用 Default 模式 | 使用 Craft 模式 |
|:---|:---|:---|
| 一次性调试/探索 | ✅ | — |
| 平台回归测试 | — | ✅ |
| CI 流水线调用 | — | ✅ |
| 参数化执行 | — | ✅ |
| 多环境切换（dev/staging/prod） | — | ✅ |

---

## 1. 脚本骨架规范

每个 Craft 模式脚本必须包含以下 4 个组件（按顺序）：

### 1.1 主执行函数（同步，与 web-auto-pipeline sync API 一致）

**注意**：该框架使用 Playwright **sync** API。函数必须定义为同步（非 `async def`），使用 `sync_playwright` 而非 `asyncio.run`。

```python
def _run(model_name: str = "默认模型", headless: bool = True) -> dict:
    """
    脚本功能的一句话描述。

    Args:
        model_name: 设备模型名称。Default: "默认模型"。
        headless: 是否无头模式。Default: True。

    Returns:
        dict with keys: result (bool), scenes_total (int), scenes_passed (int)
    """
    from playwright.sync_api import sync_playwright
    from config import BASE_URL, get_db_connection, get_script_report_dir
    from core.report_helper import TestReport

    report = TestReport("测试标题", output_dir=get_script_report_dir("e2e", "script_id"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        try:
            # 场景实现...
            pass
        finally:
            browser.close()

    report.generate_html(filename=f"script_id_测试报告_{ts}.html")
    return {
        "result": report.all_assertions_passed(),
        "scenes_total": len(report.scenes),
        "scenes_passed": sum(1 for s in report.scenes if s.get("status") == "passed")
    }
```

### 1.2 Argparse CLI 包装

```python
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description=_run.__doc__.splitlines()[0] if _run.__doc__ else "脚本描述"
    )
    parser.add_argument("--model-name", dest="model_name", type=str,
                        default="默认模型",
                        help="设备模型名称")
    parser.add_argument("--headed", action="store_true", default=False,
                        help="有头模式（默认无头）")
    parser.add_argument("--headless", action="store_true", dest="headless_",
                        help="无头模式（显式指定，兼容 runner 调用）")

    args = parser.parse_args()
    is_headless = args.headless_ or not args.headed
    result = _run(
        model_name=args.model_name,
        headless=is_headless
    )
    sys.exit(0 if result.get("result") else 1)
```

### 1.3 `if __name__` 守卫

```python
if __name__ == "__main__":
    main()
```

### 1.4 必须的顶层 import

```python
import sys
import re
import json
import time
from datetime import datetime
from pathlib import Path
```

**重要**：所有 import 放在模块顶层，禁止放在 `if __name__` 或函数体内。

---

## 2. 工具函数模板

```python
step_counter = [0]

def log(msg: str, icon: str = None):
    """
    统一日志：自动递增步数。

    兼容性警告：当前 IoT 平台实际脚本（如 device_management_test.py）中的
    log() 定义仅接受 msg 参数（单参数）。此模板提供 icon=None 是为了向前
    兼容。在生成新脚本时，应优先使用单参数形式 log(msg)；双参数 log(msg, icon)
    仅当目标脚本确实定义了 icon 参数时才可安全使用。
    """
    step_counter[0] += 1
    prefix = f"[{step_counter[0]:02d}]"
    if icon:
        line = f"{prefix} {icon} {msg}"
    else:
        line = f"{prefix}   {msg}"
    print(line)

def ss(page, name: str):
    """截图：保存到测试报告输出的 screenshots 子目录"""
    page.screenshot(path=str(SCREENSHOTS_DIR / f"step{step_counter[0]:02d}_{name}.png"))

def fill(page, locator, value: str, desc: str):
    """输入框填充 + 日志"""
    locator.wait_for(state="visible", timeout=5000)
    locator.fill(value)
    time.sleep(0.3)
    log(f"填写 {desc} = '{value}'")
```

---

## 3. 执行模式

### Navigate → Interact → Screenshot → Verify → Log

```python
# Phase N: 描述
step_name = "创建设备"
log(f"Phase: {step_name}")

# Navigate
page.goto(f"{BASE_URL}/controller/cDeviceEdit?type=create", wait_until="domcontentloaded")
time.sleep(2)
ss(page, "01_create_page")

# Interact
page.get_by_placeholder("请输入设备名称").fill(DEVICE_NAME)
page.get_by_placeholder("请输入设备编码").fill(DEVICE_CODE)
# ... 更多交互 ...

# Screenshot (before save)
ss(page, "02_before_save")

# Click save
page.locator("button").filter(has_text="保存").first.click()
time.sleep(2)

# Verify
has_err, err_txt = check_page_errors(page, report, f"保存后检查")
ss(page, "03_after_save")
report.assertion(f"{step_name}: 保存成功", not has_err, err_txt or "无错误")
log(f"✅ {step_name} 完成")
```

---

## 4. 最终报告格式

```python
# 脚本末尾汇总
summary = {
    "result": report.all_assertions_passed(),
    "scenes_total": len(report.scenes),
    "scenes_passed": sum(1 for s in report.scenes if s.get("status") == "passed"),
    "scenes_failed": sum(1 for s in report.scenes if s.get("status") == "failed"),
    "assertions": report.total_assertions,
    "passed": report.passed_assertions
}

# 输出到 stdout 供 runner 解析
print(json.dumps(summary, ensure_ascii=False))
```

---

## 5. 验证协议（3 项检查）

脚本编写完成后，必须通过以下 3 项验证：

### 检查 1: 无参数可重现

```bash
cd platforms/iot/scripts/e2e/
python script_id.py --headless
# 必须能以默认参数正常运行，不依赖外部环境变量
```

### 检查 2: Import 安全性

```bash
# 从任意目录执行 import，不得有副作用（不能启动浏览器、不能写文件）
python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('script',
    'platforms/iot/scripts/e2e/script_id.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print([n for n in dir(m) if not n.startswith('_')])
"
# 预期输出：包含 _run, main, log, ss 等名称，不应有启动浏览器或写入文件的行为
```

### 检查 3: `--help` 参数文档

```bash
python platforms/iot/scripts/e2e/script_id.py --help
# 必须输出有意义的参数说明（不是 argparse 默认的 "show this help message"）
```

---

## 6. 兼容 `core/runner.py`

Craft 模式脚本必须同时支持 `--headed` 和 `--headless` 两种参数：

```python
parser.add_argument("--headed", action="store_true", default=False,
                    help="有头模式（默认无头）")
parser.add_argument("--headless", action="store_true", dest="headless_",
                    help="无头模式（显式指定，兼容 runner 调用）")

args = parser.parse_args()
is_headless = args.headless_ or not args.headed
```

这样 runner 传 `--headless` 时能正常工作，用户手动跑传 `--headed` 也能工作。

---

## Craft 模式 vs Default 模式对照

| 维度 | Default 模式 | Craft 模式 |
|:---|:---|:---|
| 参数 | 硬编码 | argparse CLI |
| 导入安全 | — | 强制 `if __name__` 守卫 |
| 验证 | 用户目视 | 3 项检查（reproduce/import/help） |
| CI 集成 | 需手动包装 | `sys.exit(0/1)` 开箱即用 |
| 适用脚本 | 调试/探索/一次性 | 回归/CI/多环境 |
