"""
SelectorHealer — 5级选择器降级自愈

触发条件：get_by_placeholder / get_by_label 等定位失败时自动降级。

降级链：
  0. 指定的定位方式（如 get_by_placeholder）
  1. get_by_label（模型页表单常用）
  2. [aria-label] 属性
  3. visible 过滤 + 子串匹配
  4. placeholder 属性子串匹配

用法：
    from core.healer.selector_healer import SelectorHealer
    healer = SelectorHealer()
    el = healer.locate(page, "请输入PV名称")
    if el: el.fill("test-PV")
"""

import time
import re
from typing import Optional


class SelectorHealer:
    """选择器多级降级自愈"""

    # 降级链：每个级别一个 (名称, 定位函数)
    FALLBACK_CHAIN = [
        ("placeholder", lambda page, hint: page.get_by_placeholder(hint)),
        ("label", lambda page, hint: page.get_by_label(hint)),
        ("aria-label", lambda page, hint:
            page.locator(f"[aria-label='{hint}']")),
        ("visible+substring", lambda page, hint:
            page.locator(
                "input:visible, textarea:visible, "
                ".el-input__inner:visible"
            ).filter(has_text=hint).first),
        ("placeholder-substring", lambda page, hint:
            page.locator(
                f"input[placeholder*='{hint}'], "
                f"textarea[placeholder*='{hint}']"
            ).first),
        ("input-any", lambda page, hint:
            page.locator(
                "input, textarea, .el-input__inner, "
                ".el-textarea__inner"
            ).filter(has_text=hint).first),
    ]

    def __init__(self):
        # 命中统计：{hint: best_level}
        self._hit_stats = {}
        # 历史可用选择器缓存：{hint: (level, locator_type)}
        self._hint_cache = {}

    def locate(self, page, hint: str,
               preferred_type: str = None,
               timeout: int = 3000) -> Optional[object]:
        """多级降级定位元素

        Args:
            page: Playwright Page 对象
            hint: 定位提示（placeholder 文本、label 文本等）
            preferred_type: 优先尝试的定位方式（'placeholder','label'等）
            timeout: 每级超时（毫秒）

        Returns:
            Locator 或 None
        """
        chain = list(self.FALLBACK_CHAIN)

        # 如果有历史命中级，排到前面
        if hint in self._hint_cache:
            cached_level, cached_type = self._hint_cache[hint]
            chain.insert(0, chain.pop(cached_level))

        # 如果有优先类型，放到最前
        if preferred_type:
            for i, (name, _) in enumerate(chain):
                if name == preferred_type and i > 0:
                    chain.insert(0, chain.pop(i))
                    break

        for level, (name, fn) in enumerate(chain):
            try:
                el = fn(page, hint)
                if el.count() > 0:
                    self._hit_stats[hint] = level
                    self._hint_cache[hint] = (level, name)
                    self._log(f"✅ 选择器命中 [level={level} {name}]: {hint}")
                    return el.first
            except Exception:
                continue

        self._log(f"❌ 选择器全部降级失败: {hint}")
        return None

    def fill(self, page, hint: str, value: str,
             preferred_type: str = None) -> bool:
        """定位并填充，返回是否成功"""
        el = self.locate(page, hint, preferred_type)
        if el is None:
            return False
        try:
            # 先清除再填充
            el.click()
            el.fill("")
            el.fill(value)
            return True
        except Exception as e:
            self._log(f"⚠️ 填充失败: {hint} value={value} err={e}")
            return False

    def click(self, page, hint: str,
              preferred_type: str = None,
              force: bool = True) -> bool:
        """定位并点击，返回是否成功"""
        el = self.locate(page, hint, preferred_type)
        if el is None:
            return False
        try:
            el.click(force=force)
            return True
        except Exception as e:
            self._log(f"⚠️ 点击失败: {hint} err={e}")
            return False

    def get_value(self, page, hint: str,
                  preferred_type: str = None) -> Optional[str]:
        """定位并获取值，返回 None 表示失败"""
        el = self.locate(page, hint, preferred_type)
        if el is None:
            return None
        try:
            return el.input_value()
        except Exception:
            try:
                return el.text_content()
            except Exception:
                return None

    def _log(self, msg: str):
        print(f"  [SelectorHealer] {msg}")

    def stats(self) -> dict:
        """返回命中统计"""
        return {
            "hits": len(self._hit_stats),
            "by_level": {
                level: sum(1 for v in self._hit_stats.values() if v == level)
                for level in range(len(self.FALLBACK_CHAIN))
            },
        }
