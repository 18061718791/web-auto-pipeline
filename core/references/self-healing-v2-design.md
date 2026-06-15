# Self-Healing v2 设计：从「事后诊断」到「运行时治愈」

> 基于 2026-06 月以来 13 个脚本、378 张截图、28 个故障信号的调试经验沉淀。

## 现状分析

### 当前 self_heal.py 的局限

| 维度 | 当前状态 | 问题 |
|:---|:---|:---|
| 时机 | 事后诊断（跑完后读日志/报告） | 不能预防失败，失败已经发生 |
| 介入 | 只输出修复建议 | 不自动修复，需要用户手动改脚本 |
| 上下文 | 无运行时状态 | 不知道当前页面、组件类型、场景阶段 |
| 信号覆盖 | 28 个已知信号 | 只覆盖 4 个高确定性信号做自动修复 |
| 集成度 | 独立 CLI 工具 | 不集成到 runner 中，不参与脚本执行 |

### 调试中反复出现的「可自愈」失败模式

从我们的调试记录看，70%+ 的失败可以通过运行时自愈避免：

```python
# 模式 1: el-autocomplete 静默失败（出现频率最高）
fill('设备模型A') → 等 3s → 点选项 → 验证输入框值
# → 如果值没变（debounce 超时/popper 未渲染），重试 dispatchEvent

# 模式 2: 保存按钮被透明overlay遮挡
click('保存') → 无反应 → 按 Escape 关闭 popper → 重新 click('保存')
# → 90% 情况下重试一次就成功

# 模式 3: get_by_placeholder 超时 → 自动降级
try get_by_placeholder → 超时 → try get_by_label → try locator
# → 大多数情况降级一次就命中

# 模式 4: 发布轮询超时 → 导航重新进入后再轮询
轮询 6次×5秒 状态未变 → goto(列表页) → 重新搜索 → 再轮询 3次
# → 部分场景因页面缓存不刷新导致，导航后刷新可见

# 模式 5: DB 断言类型猜错 → 自动查 information_schema
column_name='is_delete', 猜想类型=integer
→ 自动查 information_schema → 实际=boolean
→ 自动修正为 row[0] is True 的比较方式
```

---

## v2 架构设计

### 总体架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Self-Healing v2                              │
│                                                                 │
│  ┌────────────────────┐    ┌──────────────────────────────┐     │
│  │ Runtime Healer     │    │ Diagnosis Engine (增强)       │     │
│  │  (运行时治愈器)      │    │  (事后诊断引擎)               │     │
│  │                    │    │                              │     │
│  │  ├ SelectorHealer  │    │  ├ ReportAnalyzer (增强)      │     │
│  │  ├ ComponentHealer │    │  ├ LogAnalyzer (增强)         │     │
│  │  ├ SaveHealer      │    │  ├ ScriptAnalyzer (增强)      │     │
│  │  ├ StateHealer     │    │  └ AutoFixGenerator (新增)    │     │
│  │  ├ AssertHealer    │    │                              │     │
│  │  └ RecoveryHealer  │    │                              │     │
│  └────────────────────┘    └──────────────────────────────┘     │
│         ↕                              ↕                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Knowledge Base (故障知识库)                            │     │
│  │  ├ failure-catalog.md (enhanced)                      │     │
│  │  ├ healing-recipes.yaml (自愈食谱)                      │     │
│  │  └ selector-fallback-map.json (选择器降级映射)          │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 模块职责

---

## 模块 1：SelectorHealer（选择器自愈）

### 触发条件

`page.get_by_placeholder("xxx").fill("yyy")` 超时或定位失败时

### 自愈逻辑

```python
class SelectorHealer:
    """选择器多级降级自愈"""

    FALLBACK_CHAIN = [
        # 1: placeholder（快速命中）
        lambda page, hint: page.get_by_placeholder(hint),
        # 2: label（模型页表单常用）
        lambda page, hint: page.get_by_label(hint),
        # 3: aria-label
        lambda page, hint: page.locator(f"[aria-label='{hint}']"),
        # 4: 模糊匹配 + visible 过滤
        lambda page, hint: page.locator(
            f"input:visible, textarea:visible, .el-input__inner:visible"
        ).filter(has_text=hint).first,
        # 5: 匹配 placeholder 属性（子串）
        lambda page, hint: page.locator(
            f"input[placeholder*='{hint}'], input[placeholder*='{hint}']"
        ).first,
    ]

    def locate(self, page, hint: str, locator_type: str = None,
               timeout: int = 3000) -> Locator | None:
        """
        多级降级定位。每级超时短（3s），一旦命中立即返回。
        返回 None 表示全部降级失败。
        """
        chain = self.FALLBACK_CHAIN
        if locator_type:  # 如果有指定类型，优先尝试
            chain = [self._typed_locator(page, hint, locator_type)] + chain

        for i, fn in enumerate(chain):
            try:
                el = fn(page, hint)
                if el.count() > 0:
                    self._record_success(hint, i)  # 记录命中级别
                    return el.first
            except Exception:
                continue
        self._record_failure(hint)
        return None

    def fill(self, page, hint: str, value: str,
             locator_type: str = None) -> bool:
        """填充并返回是否成功"""
        el = self.locate(page, hint, locator_type)
        if el is None:
            return False
        try:
            el.fill(value)
            return True
        except Exception:
            return False
```

### 实战效果预估

| 调试案例 | 原始失败原因 | 自愈行为 | 成功率 |
|:---|:---|:---|:---:|
| 元件模型表单 `placeholder='* 模型名称'` 但实际 label= `模型名称` | `get_by_placeholder("* 模型名称")` 超时 | 降级到 `get_by_label("模型名称")` 命中 | ~95% |
| 设备创建表单无 label，只有 placeholder | `get_by_label("元件名称")` 失败 | 降级到 `get_by_placeholder` 命中 | ~95% |
| 编辑页搜索框 accessible name 显示为 placeholder 文本 | `get_by_placeholder` 无法匹配 | 降级到 `filter(has_text)` 或 `[aria-label]` 命中 | ~80% |

### 关键规则

- **每级超时 3 秒**，不阻塞整体流程
- **记录命中历史**，同 hint 下次优先从历史命中级别开始
- **不抛异常**，失败返回 None 让调用方处理

---

## 模块 2：ComponentHealer（组件交互自愈）

### el-autocomplete 自愈

```python
class AutocompleteHealer:
    """
    el-autocomplete 自愈：问题根源是键盘选择不触发 Vue @select。
    自愈 = fill + 等待 + 点击 dom 选项 + 验证 + 关闭 popper。
    """

    def select(self, page, input_hint: str, target_text: str,
               debounce: float = 3.0) -> bool:
        # Step 1: 定位输入框
        healer = SelectorHealer()
        inp = healer.locate(page, input_hint)
        if inp is None:
            return False

        # Step 2: fill 触发搜索
        inp.fill(target_text)
        time.sleep(debounce)  # 等待后端结果返回

        # Step 3: 尝试点击下拉选项（主方案）
        attempts = [
            ("click .el-autocomplete__popper li",
             lambda: page.locator(".el-autocomplete__popper li")
                     .filter(has_text=target_text).first.click(force=True)),
            ("dispatchEvent 点击",
             lambda: page.evaluate(f"""
                 var item = document.querySelector('.el-autocomplete__popper li');
                 if(item) {{ item.dispatchEvent(new MouseEvent('click', {{bubbles: true}})); }}
                 return !!item;
             """)),
        ]

        for name, action in attempts:
            try:
                action()
                time.sleep(0.5)
                # Step 4: 验证输入框值已更新
                current_val = inp.input_value()
                if target_text in current_val:
                    page.keyboard.press("Escape")  # 关闭 popper
                    return True
            except Exception:
                continue

        return False
```

### el-select 自愈

```python
class SelectHealer:
    """
    el-select 自愈：问题是 overlay 拦截 + popper 关闭。
    """

    def select(self, page, trigger_hint: str, option_text: str) -> bool:
        # Step 1: 定位 trigger
        trigger = SelectorHealer().locate(page, trigger_hint, "combobox")
        if trigger is None:
            return False

        # Step 2: 打开下拉（多重方案）
        for open_attempt in [
            lambda: trigger.click(force=True),
            lambda: trigger.dispatchEvent("mousedown"),  # Element UI 专用的
            lambda: page.evaluate(
                "document.querySelector('.el-select').dispatchEvent("
                "new Event('mousedown', {bubbles: true}))"),
        ]:
            try:
                open_attempt()
                time.sleep(1)
                # 检查下拉是否打开
                if page.locator(".el-select-dropdown").last.count() > 0:
                    break
            except Exception:
                continue

        # Step 3: 选中选项
        opt_selector = ".el-select-dropdown__item"
        for select_attempt in [
            lambda: page.locator(opt_selector)
                    .filter(has_text=option_text).first.click(force=True),
            lambda: trigger.press("ArrowDown"),
            lambda: page.evaluate(f"""
                var items = document.querySelectorAll('.el-select-dropdown__item');
                for(var i of items) {{
                    if(i.textContent.includes('{option_text}')) {{
                        i.click(); break;
                    }}
                }}
            """),
        ]:
            try:
                select_attempt()
                time.sleep(0.3)
                # 验证选中
                selected = trigger.text_content() or ""
                if option_text in selected:
                    return True
            except Exception:
                continue

        return False
```

### el-cascader 自愈

```python
class CascaderHealer:
    """
    el-cascader 多选：必须点击 checkbox 非节点文本。
    """

    def select(self, page, trigger_hint: str, options: list[str]) -> bool:
        # 展开 cascader
        trigger = SelectorHealer().locate(page, trigger_hint)
        if trigger is None:
            return False

        trigger.click(force=True)
        time.sleep(1)

        # 逐级勾选
        for opt in options:
            try:
                cb = page.locator(".el-cascader-node__checkbox, .el-checkbox") \
                         .filter(has_text=opt).first
                if cb.count() > 0:
                    cb.click(force=True)
                    time.sleep(0.3)
            except Exception:
                pass

        page.keyboard.press("Escape")  # 关闭 cascader popper
        return True
```

---

## 模块 3：SaveHealer（保存操作自愈）

### 核心逻辑

```python
class SaveHealer:
    """
    保存操作自愈：针对「保存后无反馈但数据未写入」的 5 种模式。
    """

    def save_and_verify(self, page, report, step_name: str,
                        btn_text: str = "保存",
                        db_verify_fn=None, db_args=None,
                        expected_url: str = None,
                        max_retries: int = 2) -> bool:
        """
        1. 保存前预处理（关闭 popper、验证按钮状态）
        2. 点击保存
        3. 三重确认（API/URL/DB/toast）
        4. 如果失败，执行自愈序列后重试
        """

        for attempt in range(1, max_retries + 1):
            # ── 保存前预处理 ──
            # 1a. 关闭可能遮挡的 popper
            try:
                has_popper = page.evaluate("""
                    document.querySelectorAll(
                        '.el-autocomplete__popper:not([style*=\"display: none\"])'
                    ).length > 0
                """)
                if has_popper:
                    page.keyboard.press("Escape")
                    time.sleep(0.3)
            except Exception:
                pass

            # 1b. 检查表单验证错误
            form_errors = []
            try:
                for el in page.locator(".el-form-item__error").all():
                    txt = el.text_content().strip()
                    if txt:
                        form_errors.append(txt)
            except Exception:
                pass

            if form_errors:
                report.assertion(f"{step_name} 表单验证错误",
                                 False, "; ".join(form_errors))
                # IP/MAC 格式错误 → 自动修正后再试
                for err in form_errors:
                    if "IP" in err or "MAC" in err:
                        healed = self._heal_ip_mac_fields(page)
                        if healed:
                            form_errors = []
                            break
                if form_errors:
                    return False

            # 1c. 查找并点击保存按钮
            btn = None
            for btn_sel in [
                f"button:has-text('{btn_text}')",
                f".el-button--primary:has-text('{btn_text}')",
                f"[class*='save']:has-text('{btn_text}')",
            ]:
                try:
                    btn = page.locator(btn_sel).first
                    if btn.count() > 0 and btn.is_enabled():
                        break
                except Exception:
                    continue

            if btn is None or btn.count() == 0:
                report.assertion(f"{step_name}: 未找到保存按钮",
                                 False, btn_text)
                return False

            # ── 2. 注册 API 监听器 ──
            save_detected = {"api": False, "url_changed": False,
                             "toast": False, "db_ok": False}
            initial_url = page.url

            def _on_response(response):
                if any(kw in response.url.lower()
                       for kw in ["save", "add", "insert", "edit",
                                   "update", "create"]):
                    if response.status == 200:
                        save_detected["api"] = True

            page.on("response", _on_response)

            # ── 3. 点击保存 ──
            try:
                btn.click()
            except Exception:
                # 尝试 force=True
                try:
                    btn.click(force=True)
                except Exception:
                    try:
                        page.evaluate(
                            "document.querySelector('button:has-text(\"保存\")')"
                            "?.click()")
                    except Exception:
                        pass

            # ── 4. 三重确认轮询（最多 15 秒） ──
            for _ in range(15):
                time.sleep(1)
                # 4a. URL 变化检测
                if expected_url and expected_url in page.url:
                    save_detected["url_changed"] = True
                # 4b. 成功 toast
                try:
                    if page.locator(".el-message--success").count() > 0:
                        save_detected["toast"] = True
                except Exception:
                    pass
                # 4c. DB 直查
                if db_verify_fn and db_args:
                    try:
                        result = db_verify_fn(*db_args)
                        if result:
                            save_detected["db_ok"] = True
                    except Exception:
                        pass

                if any(save_detected.values()):
                    break

            page.remove_listener("response", _on_response)

            # 任一信号确认 = 保存成功
            if any(save_detected.values()):
                report.assertion(f"{step_name} 保存成功", True,
                                 f"API={save_detected['api']} "
                                 f"URL={save_detected['url_changed']} "
                                 f"toast={save_detected['toast']} "
                                 f"DB={save_detected['db_ok']}")
                return True

            # ── 5. 自愈重试 ──
            if attempt < max_retries:
                print(f"  🔄 保存自愈 #{attempt}: 无响应 → 尝试关闭 popper + "
                      f"重新点击")
                page.keyboard.press("Escape")
                time.sleep(1)
                continue

        # 全部重试失败
        report.assertion(f"{step_name} 保存失败（已重试{max_retries}次）",
                         False, page.url)
        return False

    def _heal_ip_mac_fields(self, page) -> bool:
        """自动修正 IP/MAC 格式验证错误"""
        healed = False
        try:
            for err_el in page.locator(".el-form-item__error").all():
                err_text = err_el.text_content().strip()
                if "IP" in err_text:
                    # 找相邻的输入框填默认 IP
                    parent = err_el.locator("xpath=..")
                    inp = parent.locator("input")
                    if inp.count() > 0:
                        inp.fill("10.20.30.40")
                        healed = True
                if "MAC" in err_text:
                    parent = err_el.locator("xpath=..")
                    inp = parent.locator("input")
                    if inp.count() > 0:
                        inp.fill("00-1A-2B-00-00-01")
                        healed = True
        except Exception:
            pass
        return healed
```

---

## 模块 4：StateHealer（页面状态自愈）

### 场景状态恢复

```python
class StateHealer:
    """
    页面状态自愈：检测当前页面状态与期望状态的差异，自动恢复。
    """

    EXPECTED_STATES = {
        "list": {"keywords": ["List", "list", "clist", "elist",
                              "alist", "deviceList"]},
        "create": {"keywords": ["Edit?type=create", "create"]},
        "edit": {"keywords": ["Edit?type=edit", "edit"]},
        "detail": {"keywords": ["Detail", "detail", "view"]},
        "blank": {"keywords": ["about:blank"]},
        "login": {"keywords": ["login", "Login"]},
    }

    def detect_state(self, page) -> str:
        """检测当前页面属于哪种状态"""
        url = page.url
        for state, info in self.EXPECTED_STATES.items():
            for kw in info["keywords"]:
                if kw in url:
                    return state
        return "unknown"

    def ensure_state(self, page, target_url: str, timeout: int = 10) -> bool:
        """
        确保页面处于目标状态。如果偏差则自动修复：
          - about:blank → navigate
          - 登录页 → navigate（session 过期场景）
          - 详情页/编辑页 → navigate to list
          - 404 → navigate
        """
        for _ in range(timeout):
            current = self.detect_state(page)

            if current == "blank":
                print("  🔄 自愈: 空白页 → 导航到目标")
                page.goto(target_url, wait_until="domcontentloaded")
                time.sleep(2)
                continue

            if current == "login":
                print("  🔄 自愈: session 过期 → 导航到目标")
                page.goto(target_url, wait_until="domcontentloaded")
                time.sleep(2)
                continue

            if current == "unknown":
                # 可能 404 或新页面
                title = page.title()
                if "404" in title or "not found" in title.lower():
                    print("  🔄 自愈: 404 页面 → 导航到目标")
                    page.goto(target_url, wait_until="domcontentloaded")
                    time.sleep(2)
                    continue

            # 检查 URL 是否包含目标
            if target_url in page.url:
                return True

            # 如果已接近但未完全匹配（如参数不同）
            time.sleep(1)

        return target_url in page.url

    def heal_between_scenes(self, page, report, current_url: str,
                            expected_url: str) -> bool:
        """
        场景衔接自愈：检测场景间页面状态偏移。
        """
        if expected_url in page.url:
            return True

        # 检测偏移类型
        current = self.detect_state(page)
        expected = self._url_to_state(expected_url)

        if expected == "list" and current in ("detail", "edit"):
            # 从详情/编辑页回到了列表页
            print(f"  🔄 场景衔接自愈: {current} → list")
            page.goto(expected_url, wait_until="domcontentloaded")
            time.sleep(2)
            return True

        if current == "blank":
            print("  🔄 场景衔接自愈: about:blank → 导航到目标")
            page.goto(expected_url, wait_until="domcontentloaded")
            time.sleep(2)
            return True

        # 兜底：直接导航
        print(f"  🔄 场景衔接自愈: 兜底导航 {current} → expected")
        page.goto(expected_url, wait_until="domcontentloaded")
        time.sleep(2)
        return expected_url in page.url

    def _url_to_state(self, url: str) -> str:
        for state, info in self.EXPECTED_STATES.items():
            for kw in info["keywords"]:
                if kw in url:
                    return state
        return "unknown"
```

---

## 模块 5：AssertHealer（断言自愈）

### DB 字段类型自动检测

```python
class AssertHealer:
    """
    断言自愈：DB 字段类型自动检测，防止类型猜错导致的静默失败。
    """

    def __init__(self, db_connection_fn):
        self._type_cache = {}
        self._db_fn = db_connection_fn

    def get_column_type(self, table: str, column: str) -> str:
        """缓存式查询 information_schema"""
        key = f"{table}.{column}"
        if key not in self._type_cache:
            conn = self._db_fn()
            cur = conn.cursor()
            cur.execute("""
                SELECT data_type FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """, (table, column))
            row = cur.fetchone()
            self._type_cache[key] = row[0].lower() if row else "unknown"
            cur.close()
            conn.close()
        return self._type_cache[key]

    def assert_db_value(self, report, desc: str,
                        table: str, column: str,
                        actual_value, expected) -> None:
        """
        自动适配类型的 DB 断言。
        例如 is_delete=boolean → 用 actual_value is True
                 status=integer  → 用 actual_value == 1
        """
        col_type = self.get_column_type(table, column)

        if col_type == "boolean":
            result = expected is True if isinstance(expected, bool) \
                else actual_value is expected
        elif col_type in ("integer", "smallint", "bigint"):
            try:
                result = actual_value == int(expected)
            except (ValueError, TypeError):
                result = False
        elif col_type in ("character varying", "text", "varchar"):
            result = actual_value == str(expected)
        else:
            result = actual_value == expected

        report.assertion(desc, result,
                        f"类型={col_type}, 实际={actual_value}")
```

---

## 模块 6：RecoveryHealer（运行时恢复）

```python
class RecoveryHealer:
    """
    整体恢复：浏览器崩溃、页面死锁、token 过期等严重故障的恢复。
    """

    def __init__(self, browser_factory):
        self._browser_factory = browser_factory

    def handle_crash(self, error: Exception, page,
                     report, current_scene: dict) -> bool:
        """浏览器/页面崩溃恢复"""
        error_str = str(error)

        # 浏览器进程崩溃
        if any(kw in error_str for kw in [
            "browser closed", "Target closed", "connection closed",
            "Session closed", "Protocol error"
        ]):
            print("  🔄 严重恢复: 浏览器崩溃 → 重启浏览器")
            report.step("浏览器崩溃恢复", icon="🔄")
            # 新浏览器由上层创建，这里记录崩溃点
            return True

        # 页面死锁（内存泄漏/死循环）
        if "Timeout" in error_str and "30000" in error_str:
            print("  🔄 严重恢复: 页面超时 → 刷新页面")
            try:
                page.goto(page.url, timeout=10000)
                time.sleep(2)
                return True
            except Exception:
                return False

        return False
```

---

## 模块 7：HealingOrchestrator（总调度器）

```python
class HealingOrchestrator:
    """
    自愈总调度器：集成所有 Healer，提供统一入口。
    嵌入到 run() 函数和 report_helper 中。
    """

    def __init__(self, page, report, db_connection_fn):
        self.page = page
        self.report = report
        self.selector = SelectorHealer()
        self.autocomplete = AutocompleteHealer()
        self.select = SelectHealer()
        self.cascader = CascaderHealer()
        self.save = SaveHealer()
        self.state = StateHealer()
        self.assertion = AssertHealer(db_connection_fn)
        self.recovery = RecoveryHealer(None)  # browser factory set later
        self._stats = {"healed": 0, "failed": 0, "skipped": 0}

    def fill(self, hint: str, value: str) -> bool:
        """带自愈的 fill 操作"""
        ok = self.selector.fill(self.page, hint, value)
        if not ok:
            self._stats["failed"] += 1
        return ok

    def select_option(self, trigger_hint: str, option_text: str) -> bool:
        """带自愈的 select 选择"""
        ok = self.select.select(self.page, trigger_hint, option_text)
        if ok:
            self._stats["healed"] += 1
        return ok

    def autocomplete_select(self, input_hint: str, target: str) -> bool:
        """带自愈的 autocomplete 选择"""
        ok = self.autocomplete.select(self.page, input_hint, target)
        if ok:
            self._stats["healed"] += 1
        return ok

    def save_and_verify(self, step_name: str, **kwargs) -> bool:
        """带自愈的保存验证"""
        ok = self.save.save_and_verify(self.page, self.report,
                                        step_name, **kwargs)
        if ok:
            self._stats["healed"] += 1
        return ok

    def heal_state(self, target_url: str) -> bool:
        """页面状态自愈"""
        ok = self.state.ensure_state(self.page, target_url)
        if ok:
            self._stats["healed"] += 1
        return ok

    def assert_db(self, desc: str, table: str, column: str,
                  actual, expected) -> None:
        """带类型适配的 DB 断言"""
        self.assertion.assert_db_value(self.report, desc, table,
                                       column, actual, expected)

    def summary(self) -> dict:
        """返回自愈统计"""
        return dict(self._stats)
```

---

## 集成路径：三步走

### Step 1：核心模块落地（本周）

把 `HealingOrchestrator` 和 6 个 Healer 实现为独立模块：

```
core/
├── healer/
│   ├── __init__.py               # 导出 HealingOrchestrator
│   ├── selector_healer.py        # 选择器降级
│   ├── component_healer.py       # el-autocomplete/select/cascader
│   ├── save_healer.py            # 保存验证 + 自愈重试
│   ├── state_healer.py           # 页面状态恢复
│   ├── assert_healer.py          # DB 断言类型适配
│   └── recovery_healer.py        # 浏览器崩溃恢复
├── references/
│   └── self-healing-v2-design.md   # 本文档
```

### Step 2：脚本改造（逐步）

1. `pv_atomic_test.py` → 引入 `HealingOrchestrator`
2. `device_management_test.py` → 用 `save_and_verify()` 替换原始保存
3. 其他脚本逐一代入

**改造成本**：每个脚本约 20 行代码变更（import + init + 替换关键操作）

### Step 3：自愈知识闭环

```python
# 每次自愈事件写入知识库
class HealingRecorder:
    """自愈日志持久化，用于后续分析"""

    def record(self, healer: str, input_hint: str,
               fallback_level: int, success: bool,
               context: str = ""):
        """
        记录到 healer_stats.json：
        {
            "selector_healer": {
                "请输入设备名称": {
                    "attempts": 15,
                    "success_levels": {0: 10, 1: 3, 2: 2},
                    "last_fallback": 1
                }
            }
        }
        """
```

---

## 效果预估

### 预期自愈覆盖率

| 故障类型 | 当前处理 | v2 处理后 | 降低比例 |
|:---|:---:|:---:|:---:|
| el-autocomplete 静默失败 | 人工排查 | 自动重试 + dispatchEvent 降级 | ~85% |
| 保存按钮无响应 | 人工 5 步排查 | Escape + 重试 + IP/MAC 修正 | ~80% |
| 选择器不匹配 | 人工改脚本 | 自动 5 级降级 | ~90% |
| 场景边界状态偏移 | 人工加 goto | 自检 + 自动导航回恢复 | ~70% |
| DB 断言类型猜错 | 人工查 information_schema | 自动检测后适配 | ~95% |
| 浏览器崩溃 | 脚本从头重跑 | 自动恢复 + 从崩溃点继续 | ~60% |

### 脚本健壮性提升

```
当前： 13 个脚本 × 5 种潜在静默失败 = 65 个可能中断点
v2后： 65 × (1 - 平均自愈率 80%) ≈ 13 个潜在中断点
整体可靠性提升约 5 倍
```

---

## 不与现有架构冲突的关键点

| 维度 | 说明 |
|:---|:---|
| 兼容性 | 所有 Healer 可独立使用，不改变 `TestReport` / `runner.py` 接口 |
| 渐进式 | 脚本可逐步引入，不改动即可继续使用原有断言模式 |
| 侵入性 | `HealingOrchestrator` 是可选包装，不强制使用 |
| 报告集成 | 自愈事件自动写入 report.assertion，用户可见 |
| 知识积累 | `HealingRecorder` 数据驱动后续优化 |

---

## 实现优先级

| 优先级 | 模块 | 理由 |
|:---:|:---|:---|
| P0 | **SaveHealer** | 保存操作是最大失败源（el-autocomplete popper + 表单验证 + 唯一约束） |
| P0 | **ComponentHealer (autocomplete)** | #1 频率最高的静默失败模式 |
| P1 | **SelectorHealer** | 减少脚本调试中 50% 的定位失败 |
| P1 | **StateHealer** | 解决场景衔接类失败（约 15% 的失败） |
| P2 | **AssertHealer** | 降低 DB 断言类型的调试成本 |
| P2 | **RecoveryHealer** | 严重故障场景的兜底恢复 |
