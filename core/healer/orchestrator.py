"""
HealingOrchestrator — 自愈总调度器

集成所有 Healer 模块，提供统一 API。
嵌入到 test script 的 run() 函数中，替换裸 Playwright 操作。

使用方式（三选一）：

A) 全量使用（推荐新脚本）：
    from core.healer import HealingOrchestrator
    h = HealingOrchestrator(page, report, db_connection_fn)
    h.fill("请输入PV名称", "test-PV")       # 选择器降级
    h.save_and_verify("保存PV", db_verify_fn=fn, db_args=[x])
    print(h.summary())

B) 选择性使用（引入现有脚本）：
    from core.healer.save_healer import SaveHealer
    healer = SaveHealer()
    ok = healer.save_and_verify(page, report, "保存")

C) 单项使用（最小入侵）：
    from core.healer.selector_healer import SelectorHealer
    el = SelectorHealer().locate(page, "请输入PV名称")
    if el: el.fill("test-PV")
"""

from typing import Callable, Optional, Any

from core.healer._base import HealerBase
from core.healer.selector_healer import SelectorHealer
from core.healer.component_healer import ComponentHealer
from core.healer.save_healer import SaveHealer
from core.healer.state_healer import StateHealer
from core.healer.assert_healer import AssertHealer


class HealingOrchestrator(HealerBase):
    """自愈总调度器"""

    def __init__(self, page, report, db_connection_fn: Callable = None):
        """
        Args:
            page: Playwright Page
            report: TestReport 实例
            db_connection_fn: get_db_connection 函数（用于 AssertHealer）
        """
        self.page = page
        self.report = report
        self.selector = SelectorHealer()
        self.component = ComponentHealer()
        self.save = SaveHealer()
        self.state = StateHealer()
        self.assertion = AssertHealer(db_connection_fn) if db_connection_fn else None

        self._all_healers = [
            self.selector,
            self.component,
            self.save,
            self.state,
        ]
        if self.assertion:
            self._all_healers.append(self.assertion)

    # ── 选择器 ──

    def fill(self, hint: str, value: str, preferred_type: str = None) -> bool:
        """填充输入框（带选择器降级）"""
        return self.selector.fill(self.page, hint, value, preferred_type)

    def locate(self, hint: str, preferred_type: str = None) -> Optional[object]:
        """定位元素（带选择器降级）"""
        return self.selector.locate(self.page, hint, preferred_type)

    def click(self, hint: str, preferred_type: str = None) -> bool:
        """点击元素（带选择器降级）"""
        return self.selector.click(self.page, hint, preferred_type)

    def get_value(self, hint: str) -> Optional[str]:
        """获取输入框值（带选择器降级）"""
        return self.selector.get_value(self.page, hint)

    # ── 组件交互 ──

    def autocomplete_select(
        self, input_hint: str, target_text: str, debounce: float = 3.0
    ) -> bool:
        """el-autocomplete 选择"""
        return self.component.autocomplete_select(
            self.page, input_hint, target_text, debounce
        )

    def select_option(self, trigger_hint: str, option_text: str) -> bool:
        """el-select 选择"""
        return self.component.select_option(self.page, trigger_hint, option_text)

    def cascader_select(self, trigger_hint: str, options: list[str]) -> bool:
        """el-cascader 选择"""
        return self.component.cascader_select(self.page, trigger_hint, options)

    # ── 保存 ──

    def save_and_verify(
        self,
        step_name: str,
        btn_text: str = "保存",
        db_verify_fn: Callable = None,
        db_args: list = None,
        expected_url: str = None,
        max_retries: int = 2,
        timeout: int = 15,
    ) -> bool:
        """保存 + 三重确认 + 自愈重试"""
        return self.save.save_and_verify(
            self.page,
            self.report,
            step_name,
            btn_text=btn_text,
            db_verify_fn=db_verify_fn,
            db_args=db_args,
            expected_url=expected_url,
            max_retries=max_retries,
            timeout=timeout,
        )

    # ── 页面状态 ──

    def ensure_state(self, target_url: str) -> bool:
        """确保页面状态正确"""
        return self.state.ensure_state(self.page, target_url)

    def heal_between_scenes(self, expected_url: str, scene_name: str = "") -> bool:
        """场景衔接自愈"""
        return self.state.heal_between_scenes(
            self.page, self.report, expected_url, scene_name
        )

    # ── DB 断言 ──

    def assert_db(
        self, desc: str, table: str, column: str, actual_value: Any, expected: Any
    ) -> bool:
        """带类型适配的 DB 断言"""
        if self.assertion:
            return self.assertion.assert_db_value(
                self.report, desc, table, column, actual_value, expected
            )
        self.report.assertion(
            desc, actual_value == expected, f"无类型适配, actual={actual_value}"
        )
        return actual_value == expected

    def probe_table(self, table: str) -> list[dict]:
        """探测表结构"""
        if self.assertion:
            return self.assertion.probe_table(table)
        return []

    # ── 统计 ──

    def summary(self) -> dict:
        """返回所有 Healer 的自愈统计"""
        result = {}
        for healer in self._all_healers:
            name = healer.__class__.__name__
            try:
                result[name] = healer.stats()
            except Exception as e:
                self._log(f"获取{name}统计异常: {e}", "warning")
                result[name] = {}
        return result

    def print_summary(self):
        """打印自愈统计"""
        s = self.summary()
        print(f"\n{'=' * 50}")
        print("  📊 Healing Summary")
        print(f"{'=' * 50}")
        for healer_name, stats in s.items():
            if isinstance(stats, dict):
                items = ", ".join(f"{k}={v}" for k, v in stats.items())
                print(f"  {healer_name:25s} | {items}")
            else:
                print(f"  {healer_name:25s} | {stats}")
        print(f"{'=' * 50}")
