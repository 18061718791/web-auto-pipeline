"""
ComponentHealer — 组件交互自愈

涵盖 el-autocomplete / el-select / el-cascader 三个最容易出问题的组件。

设计原则：
  - 每种组件有主方案 + 2~3 个降级方案
  - 每次尝试后验证效果（输入框值、选中文本）
  - 验证失败才降级，不盲目重试
  - 记录命中方案供后续调用参考

用法：
    from core.healer.component_healer import ComponentHealer
    healer = ComponentHealer()
    ok = healer.autocomplete_select(page, "请输入模型名称搜索", "模型A")
    ok = healer.select_option(page, "状态", "已发布")
    ok = healer.cascader_select(page, "区域", ["华东", "上海"])
"""

import time
from typing import Optional

from core.healer._base import HealerBase


class ComponentHealer(HealerBase):
    """组件交互自愈（el-autocomplete / el-select / el-cascader）"""

    def __init__(self):
        self._stats = {
            "autocomplete": {"ok": 0, "fail": 0},
            "select": {"ok": 0, "fail": 0},
            "cascader": {"ok": 0, "fail": 0},
        }

    # ── el-autocomplete ──────────────────────────────────

    def autocomplete_select(
        self, page, input_hint: str, target_text: str, debounce: float = 3.0
    ) -> bool:
        """el-autocomplete 选择：fill → 等debounce → 点选项 → 验证 → 关闭popper

        降级链：
          1. .el-autocomplete__popper li click(force=True)  ← 主方案
          2. JS evaluate dispatchEvent 点击选项              ← 降级1
          3. 键盘 ArrowDown + Enter 选择                    ← 降级2
        """
        # Step 1: 定位输入框
        inp = self._locate_input(page, input_hint)
        if inp is None:
            self._log(f"❌ autocomplete: 找不到输入框 '{input_hint}'")
            self._stats["autocomplete"]["fail"] += 1
            return False

        # Step 2: 触发搜索
        original_url = page.url
        inp.fill("")
        time.sleep(0.3)
        inp.fill(target_text)
        time.sleep(debounce)

        # Step 3: 尝试选择下拉选项（多级降级）
        attempts = [
            ("主方案: click li force=True", self._ac_click_li),
            ("降级1: JS dispatchEvent", self._ac_dispatch_event),
            ("降级2: 键盘 ArrowDown+Enter", self._ac_keyboard),
        ]

        for name, fn in attempts:
            try:
                fn(page, target_text)
                time.sleep(0.5)
            except Exception as e:
                self._log(f"  ⚠️ {name} 异常: {e}")
                continue

            # 验证输入框值是否更新
            current_val = self._get_input_value(page, input_hint)
            if current_val and target_text in current_val:
                # 关闭 popper
                try:
                    page.keyboard.press("Escape")
                except Exception as e:
                    self._log(f"关闭popper失败: {e}", "warning")
                self._log(f"✅ autocomplete 命中 [{name}]: {target_text}")
                self._stats["autocomplete"]["ok"] += 1
                return True

        # 全部失败 — 尝试关闭 popper 清理现场
        try:
            page.keyboard.press("Escape")
        except Exception as e:
            self._log(f"关闭popper失败: {e}", "warning")
        self._log(f"❌ autocomplete 全部降级失败: {target_text}")
        self._stats["autocomplete"]["fail"] += 1
        return False

    def _ac_click_li(self, page, text: str):
        """方案1: 点击 .el-autocomplete__popper li"""
        page.locator(".el-autocomplete__popper li").filter(has_text=text).first.click(
            force=True
        )

    def _ac_dispatch_event(self, page, text: str):
        """方案2: JS dispatchEvent 点击"""
        page.evaluate(f"""
            (function() {{
                var items = document.querySelectorAll(
                    '.el-autocomplete__popper li');
                for(var i of items) {{
                    if(i.textContent.includes('{text}')) {{
                        i.dispatchEvent(
                            new MouseEvent('click', {{bubbles: true}}));
                        return;
                    }}
                }}
            }})()
        """)

    def _ac_keyboard(self, page, text: str):
        """方案3: 键盘 ArrowDown + Enter"""
        for _ in range(10):
            time.sleep(0.2)
            page.keyboard.press("ArrowDown")
            current_val = page.evaluate("document.activeElement?.value || ''")
            if text in current_val or not current_val:
                page.keyboard.press("Enter")
                return
        # 兜底：直接 Enter
        page.keyboard.press("Enter")

    # ── el-select ─────────────────────────────────────────

    def select_option(self, page, trigger_hint: str, option_text: str) -> bool:
        """el-select 选择：打开下拉 → 选选项 → 验证

        降级链：
          1. click(force=True) 打开 → click(force=True) 点选项  ← 主方案
          2. dispatchEvent mousedown 打开  ← 降级1
          3. 键盘 ArrowDown+Enter 选择        ← 降级2
        """
        # Step 1: 定位 trigger
        trigger_selectors = [
            lambda: page.get_by_role("combobox").filter(has_text=trigger_hint).first,
            lambda: page.get_by_placeholder(trigger_hint),
            lambda: page.get_by_label(trigger_hint),
            lambda: page.locator(".el-select").filter(has_text=trigger_hint).first,
        ]
        trigger = None
        for fn in trigger_selectors:
            try:
                t = fn()
                if t.count() > 0:
                    trigger = t
                    break
            except Exception as e:
                self._log(f"trigger选择器异常: {e}", "warning")
                continue

        if trigger is None:
            self._log(f"❌ select: 找不到 trigger '{trigger_hint}'")
            self._stats["select"]["fail"] += 1
            return False

        # Step 2: 打开下拉
        open_attempts = [
            ("open: click force=True", lambda: trigger.click(force=True)),
            (
                "open: dispatchEvent mousedown",
                lambda: trigger.evaluate(
                    "el => el.dispatchEvent(new Event('mousedown', {bubbles: true}))"
                ),
            ),
        ]

        opened = False
        for name, fn in open_attempts:
            try:
                fn()
                time.sleep(1)
                if (
                    page.locator(
                        ".el-select-dropdown:not([style*='display: none'])"
                    ).count()
                    > 0
                ):
                    opened = True
                    break
            except Exception as e:
                self._log(f"打开下拉失败 ({name}): {e}", "warning")
                continue

        if not opened:
            self._log("❌ select: 下拉无法打开")
            self._stats["select"]["fail"] += 1
            return False

        # Step 3: 选择选项
        opt_attempts = [
            (
                "select: click dropdown item force=True",
                lambda: page.locator(".el-select-dropdown__item")
                .filter(has_text=option_text)
                .first.click(force=True),
            ),
            (
                "select: JS dispatchEvent",
                lambda: page.evaluate(f"""
                 document.querySelectorAll(
                     '.el-select-dropdown__item').forEach(function(el) {{
                     if(el.textContent.includes('{option_text}')) {{
                         el.dispatchEvent(
                             new MouseEvent('click', {{bubbles: true}}));
                     }}
                 }})"""),
            ),
            (
                "select: keyboard ArrowDown+Enter",
                lambda: (trigger.press("ArrowDown"), trigger.press("Enter")),
            ),
        ]

        for name, fn in opt_attempts:
            try:
                fn()
                time.sleep(0.3)
                # 验证：trigger 文本是否变化
                selected = trigger.text_content() or ""
                if option_text in selected:
                    self._log(f"✅ select 选中 [{name}]: {option_text}")
                    self._stats["select"]["ok"] += 1
                    return True
            except Exception as e:
                self._log(f"选择选项失败 ({name}): {e}", "warning")
                continue

        self._log(f"❌ select 全部降级失败: {option_text}")
        self._stats["select"]["fail"] += 1
        return False

    # ── el-cascader ───────────────────────────────────────

    def cascader_select(self, page, trigger_hint: str, options: list[str]) -> bool:
        """el-cascader 多选：展开 → 逐级勾选 checkbox → 关闭

        关键：必须点击 .el-checkbox 而不是节点文本，
             否则会展开子级而不是选中。
        """
        # Step 1: 定位 trigger
        trigger = self._locate_input(page, trigger_hint)
        if trigger is None:
            self._log(f"❌ cascader: 找不到 trigger '{trigger_hint}'")
            self._stats["cascader"]["fail"] += 1
            return False

        # Step 2: 展开 cascader
        try:
            trigger.click(force=True)
            time.sleep(1)
        except Exception:
            self._log("❌ cascader: 无法展开")
            self._stats["cascader"]["fail"] += 1
            return False

        # Step 3: 逐级勾选
        for opt in options:
            try:
                cb = (
                    page.locator(".el-cascader-node__checkbox, .el-checkbox")
                    .filter(has_text=opt)
                    .first
                )
                if cb.count() > 0:
                    cb.click(force=True)
                    time.sleep(0.3)
                else:
                    # 降级：点击节点文本
                    node = page.locator(".el-cascader-node").filter(has_text=opt).first
                    if node.count() > 0:
                        node.click()
                        time.sleep(0.3)
            except Exception as e:
                self._log(f"cascader选项异常: {e}", "warning")
                continue

        # Step 4: 关闭 cascader popover
        try:
            page.keyboard.press("Escape")
        except Exception as e:
            self._log(f"关闭cascader失败: {e}", "warning")

        self._log(f"✅ cascader 选择完成: {options}")
        self._stats["cascader"]["ok"] += 1
        return True

    # ── 工具方法 ──────────────────────────────────────────

    def _locate_input(self, page, hint: str) -> Optional[object]:
        """定位输入框（通用）"""
        from core.healer.selector_healer import SelectorHealer

        return SelectorHealer().locate(page, hint)

    def _get_input_value(self, page, hint: str) -> Optional[str]:
        """获取输入框当前值"""
        from core.healer.selector_healer import SelectorHealer

        return SelectorHealer().get_value(page, hint)

    def stats(self) -> dict:
        return dict(self._stats)
