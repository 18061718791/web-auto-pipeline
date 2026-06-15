from .base import ComponentAdapter


class ElementUIVue3Adapter(ComponentAdapter):
    @property
    def name(self):
        return "element-ui-vue3"

    def locate_select(self, page, placeholder: str):
        return page.get_by_role("combobox", name=placeholder)

    def locate_autocomplete(self, page, placeholder: str):
        return page.locator(f"input[placeholder*='{placeholder}']")

    def select_option(self, page, select_locator, option_text: str):
        # Known limitation: el-select popper is not visible to Playwright
        # Use force=True to bypass span overlay
        select_locator.click(force=True)
        import time
        time.sleep(1)
        page.keyboard.press("ArrowDown")
        time.sleep(1)
        page.keyboard.press("Enter")
        time.sleep(0.5)

    @property
    def known_limitations(self):
        return {
            "select_option_visible": False,
            "autocomplete_needs_popper_click": True,
            "autocomplete_debounce": 2.5,
            "description": "el-select popper not visible to Playwright; autocomplete needs popper li click",
        }

    @property
    def autocomplete_debounce(self):
        return 2.5
