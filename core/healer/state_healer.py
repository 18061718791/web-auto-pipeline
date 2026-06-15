"""
StateHealer — 页面状态自愈

检测页面状态（列表页/编辑页/详情页/空白页/登录页），
在与预期状态不一致时自动导航恢复。

典型场景：
  - 场景A结束在详情页，场景B期望从列表页开始 → 自动导航 → 恢复搜索
  - about:blank → 导航到目标URL
  - Session过期被踢到登录页 → 导航回目标
  - 404 页面 → 导航回列表页

用法：
    from core.healer.state_healer import StateHealer
    healer = StateHealer()
    healer.ensure_state(page, PV_LIST_URL)
    healer.heal_between_scenes(page, report, PV_LIST_URL)
"""

import time


class StateHealer:
    """页面状态检测与恢复"""

    STATE_PATTERNS = {
        "list":    ["List", "list", "clist", "elist",
                    "alist", "deviceList", "tag/list",
                    "eDeviceList", "cDeviceList"],
        "create":  ["Edit?type=create", "?type=create",
                    "type=create"],
        "edit":    ["Edit?type=edit", "?type=edit",
                    "type=edit"],
        "detail":  ["Detail", "detail", "View", "view"],
        "blank":   ["about:blank"],
        "login":   ["login", "Login", "#/login"],
        "404":     ["404", "notfound", "not_found"],
    }

    def __init__(self):
        self._stats = {"healed": 0, "no_action": 0}

    def detect_state(self, page) -> str:
        """检测当前页面状态类型"""
        url = page.url
        for state, keywords in self.STATE_PATTERNS.items():
            for kw in keywords:
                if kw in url:
                    return state

        # 检查页面标题
        try:
            title = page.title().lower()
            if "404" in title or "not found" in title:
                return "404"
        except Exception:
            pass

        return "unknown"

    def ensure_state(self, page, target_url: str,
                     max_retries: int = 3) -> bool:
        """确保页面处于目标状态，偏差时自愈

        Args:
            page: Playwright Page
            target_url: 期望的 URL（包含主机部分）
            max_retries: 最大导航重试次数

        Returns:
            True=页面已处于期望状态或已恢复
        """
        for attempt in range(max_retries):
            current_state = self.detect_state(page)
            state_info = (
                f"[state={current_state}] "
                f"url={page.url[:80]}...")

            # 检查是否已匹配
            if target_url in page.url:
                self._stats["no_action"] += 1
                return True

            # 需要恢复的情况
            needs_nav = False
            reason = ""

            if current_state == "blank":
                reason = "空白页(about:blank)"
                needs_nav = True
            elif current_state == "login":
                reason = "session过期(登录页)"
                needs_nav = True
            elif current_state == "404":
                reason = "404页面"
                needs_nav = True
            elif current_state == "unknown":
                # 可能页面加载异常
                reason = f"未知页面状态 {state_info}"
                needs_nav = True

            if needs_nav:
                self._log(f"🔄 状态自愈 #{attempt+1}: {reason}")
                try:
                    page.goto(target_url,
                              wait_until="domcontentloaded",
                              timeout=15000)
                    time.sleep(2)
                    self._stats["healed"] += 1
                    # 导航后重新检测
                    if target_url in page.url:
                        return True
                except Exception as e:
                    self._log(f"  ⚠️ 导航失败: {e}")
                    continue
            else:
                # 在某个已知页面但和目标不匹配
                self._log(
                    f"ℹ️ 当前状态={current_state}, "
                    f"非目标, 导航中...")
                try:
                    page.goto(target_url,
                              wait_until="domcontentloaded",
                              timeout=15000)
                    time.sleep(2)
                    if target_url in page.url:
                        return True
                except Exception:
                    continue

        return target_url in page.url

    def heal_between_scenes(self, page, report,
                            expected_url: str,
                            scene_name: str = "") -> bool:
        """场景衔接自愈

        场景A结束时可能停在详情页/编辑页，
        场景B期望从列表页开始。
        此函数检测偏差并自动导航恢复。
        """
        if expected_url in page.url:
            self._stats["no_action"] += 1
            return True

        current_state = self.detect_state(page)
        self._log(
            f"🔄 场景'{scene_name}'衔接自愈: "
            f"当前={current_state}({page.url[:60]}...), "
            f"期望={expected_url[:60]}...")

        # 强行导航到目标
        try:
            page.goto(expected_url,
                      wait_until="domcontentloaded")
            time.sleep(2)

            if expected_url in page.url:
                self._log("  ✅ 场景衔接恢复成功")
                self._stats["healed"] += 1
                return True
            else:
                # 可能被重定向了
                self._log(
                    f"  ⚠️ 导航后URL不匹配: "
                    f"{page.url[:60]}...")
                return False
        except Exception as e:
            self._log(f"  ❌ 场景衔接恢复失败: {e}")
            return False

    def _log(self, msg: str):
        print(f"  [StateHealer] {msg}")

    def stats(self) -> dict:
        return dict(self._stats)
