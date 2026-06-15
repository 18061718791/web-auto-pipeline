"""healer 包 — 运行时自愈模块

包含 6 个 Healer 模块和一个 HealingOrchestrator。
每个 Healer 可独立使用，也可通过 HealingOrchestrator 统一调度。

Usage:
    from core.healer import HealingOrchestrator
    h = HealingOrchestrator(page, report)
    h.fill("请输入PV名称", "test-PV")
    h.autocomplete_select("请输入模型名称", "model-A")
    h.save_and_verify("保存PV")
    print(h.summary())
"""

from core.healer.selector_healer import SelectorHealer
from core.healer.component_healer import ComponentHealer
from core.healer.save_healer import SaveHealer
from core.healer.state_healer import StateHealer
from core.healer.assert_healer import AssertHealer
from core.healer.orchestrator import HealingOrchestrator

__all__ = [
    "HealingOrchestrator",
    "SelectorHealer",
    "ComponentHealer",
    "SaveHealer",
    "StateHealer",
    "AssertHealer",
]
