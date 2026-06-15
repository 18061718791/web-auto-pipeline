# 执行模式模板（Execution Pattern Template）

> 标准场景执行模式：**Navigate → Interact → Screenshot → Verify → Log**
> 适用于所有端到端和原子测试脚本，确保步骤一致性和可维护性。

## 标准场景循环

```python
def run_scene(page, report, scene_num, name, headless=True):
    """标准场景执行模板"""
    report.scene_begin(f"场景{scene_num}: {name}")
    log(f"\n{'='*50}")
    log(f"场景{scene_num}: {name}")
    log(f"{'='*50}")

    try:
        # ====== Navigate ======
        log(f"[操作] 导航到列表页")
        page.goto(f"{BASE_URL}/controllerType/clist", wait_until="domcontentloaded")
        time.sleep(2)
        ss(page, f"{scene_num:02d}_01_list_page")

        # ====== Interact ======
        log(f"[操作] 搜索目标数据")
        search_input = page.get_by_placeholder("请输入名称搜索")
        search_input.fill(TEST_NAME)
        page.get_by_role("button", name="搜索").click()
        time.sleep(2)
        ss(page, f"{scene_num:02d}_02_search_result")

        # ====== Verify ======
        row_count = page.locator("tr").filter(has_text=TEST_NAME).count()
        report.assertion(f"搜索结果包含{TEST_NAME}", row_count > 0, f"行数={row_count}")

        # ====== Log ======
        log(f"✅ 场景{scene_num} 通过")
        report.scene_end(True)

    except Exception as e:
        log(f"❌ 场景{scene_num} 失败: {e}", "❌")
        report.scene_end(False, str(e))
        import traceback
        traceback.print_exc()
```

## 3 种常用模式

### 模式 A: 简单导航→操作→验证（列表页操作）

```python
# Navigate
ensure_on_page(page, LIST_URL)
# 如果已在目标页则跳过 goto

# Interact
page.get_by_placeholder("请输入名称").fill(NAME)
page.get_by_role("button", name="搜索").click()
time.sleep(2)

# Screenshot
ss(page, "scene_search")

# Verify
found = page.locator("tr").filter(has_text=NAME).count() > 0
report.assertion(f"列表中存在{NAME}", found, "")

# Log
log(f"{'✅' if found else '❌'} 搜索结果: {NAME}")
```

### 模式 B: 创建/编辑表单操作（保存后验证）

```python
# Navigate
page.goto(f"{BASE_URL}/someEdit?type=create", wait_until="domcontentloaded")
time.sleep(2)
ss(page, "form_page")

# Interact (fill form)
page.get_by_placeholder("请输入名称").fill(TEST_NAME)
page.get_by_label("编码").fill(TEST_CODE)
# ... 其他字段 ...

# Screenshot before save
ss(page, "form_filled")

# Save
page.locator("button").filter(has_text="保存").first.click()
time.sleep(2)

# Verify: check_page_errors + DB
has_err, err_txt = check_page_errors(page, report, "保存后检查")
ss(page, "after_save")
report.assertion("保存无报错", not has_err, err_txt or "")

if not has_err:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM some_table WHERE name=%s", (TEST_NAME,))
    count = cur.fetchone()[0]
    report.assertion("DB: 记录已写入", count > 0, f"count={count}")
    cur.close(); conn.close()

# Log
log(f"{'✅' if count > 0 else '❌'} 创建{TEST_NAME}")
```

### 模式 C: 发布/状态变更（异步轮询）

```python
# Navigate (从上一场景直接复用)
row = page.locator("tr").filter(has_text=TEST_NAME)
report.assertion("列表中有目标记录", row.count() > 0, "")

# Click publish button
row.locator("button").filter(has_text="发布").first.click()
time.sleep(1)

# Confirm dialog (if any)
confirm_btn = page.locator(".el-message-box__btns button, .el-dialog button").filter(has_text="确定")
if confirm_btn.count() > 0:
    confirm_btn.click()
    log("确认发布对话框")

ss(page, "after_publish")
time.sleep(2)

# Async polling: 最多等 30 秒
published = False
for attempt in range(6):
    page.locator("button").filter(has_text="搜索").first.click()
    time.sleep(2)

    row_text = page.locator("tr").filter(has_text=TEST_NAME).inner_text()
    if "发布" in row_text or "已发布" in row_text:
        published = True
        log(f"✅ 发布成功（轮询 {attempt+1} 次）")
        break
    log(f"轮询 {attempt+1}/6: 未发布，等待...")
    report.step(f"发布轮询 {attempt+1}", screenshot=page)

report.assertion(f"{TEST_NAME} 发布成功", published, f"轮询{6 if not published else ''}次")
```

---

## 工具函数速查

| 函数 | 用途 | 代码 |
|:---|:---|:---|
| `ss(page, name)` | 截图（自动 step 前缀） | `page.screenshot(path=SCREENSHOTS / f"step{step[0]:02d}_{name}.png")` |
| `log(msg)` | 日志（自动步数递增） | `print(f"[{step[0]:02d}] {msg}")`  |
| `fill(page, loc, val, desc)` | 填充+等待 | `loc.wait_for(state="visible"); loc.fill(val); time.sleep(0.3)` |
| `ensure_on_page(page, url)` | 仅当不在目标页时才 goto | `if url not in page.url: page.goto(url)` |
| `check_page_errors(page, ...)` | 页面错误检测 | 6 种错误形态 + body 关键词 + URL 变化 |
| `report.assertion(name, cond, detail)` | 断言记录 | 自动统计通过/失败/总计 |

---

## 脚本启动模板

```python
import sys, os, time, json, argparse, re
from datetime import datetime
from pathlib import Path

# 确保项目根在 sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import BASE_URL, get_db_connection, get_script_report_dir
from core.report_helper import TestReport
from scripts.component_utils import select_el_option

SCRIPT_ID = "script_id"
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
SCREENSHOTS_DIR = Path(get_script_report_dir("e2e", SCRIPT_ID)) / f"screenshots_{ts}"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

step = [0]
def log(msg: str): step[0] += 1; print(f"[{step[0]:02d}] {msg}")
def ss(page, name: str): page.screenshot(path=str(SCREENSHOTS_DIR / f"step{step[0]:02d}_{name}.png"))
```

---

## 验证检查清单

- [ ] 每个保存/发布/删除操作后: `check_page_errors` + 截图
- [ ] 每个搜索/过滤操作后: 断言行数 > 0
- [ ] el-select / el-autocomplete 操作后: 检查值已设置
- [ ] 异步操作: 轮询（非固定 sleep）
- [ ] if/else 双分支都有断言（无静默跳过）
- [ ] 场景间不重复导航（用 `ensure_on_page` 控制）
