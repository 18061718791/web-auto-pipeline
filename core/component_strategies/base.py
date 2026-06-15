class ComponentAdapter:
    """Abstract base for UI framework component adapters"""

    def __init__(self, page=None):
        self.page = page

    @property
    def name(self) -> str:
        return "base"

    def locate_select(self, page, placeholder: str):
        raise NotImplementedError

    def locate_autocomplete(self, page, placeholder: str):
        raise NotImplementedError

    def select_option(self, page, select_locator, option_text: str):
        """Select an option from el-select/combobox - known to be problematic"""
        raise NotImplementedError

    def type_text(self, selector: str, text: str):
        """Type text into an input field"""
        raise NotImplementedError

    def click_button(self, text: str):
        """Click a button by its visible text"""
        raise NotImplementedError

    def get_table_rows(self, selector: str = None) -> list:
        """Get all table rows as list of cell text lists"""
        raise NotImplementedError

    def get_pagination_info(self) -> dict:
        """Get current pagination info (total, current page, etc.)"""
        raise NotImplementedError

    def open_modal(self):
        """Wait for and return the modal locator"""
        raise NotImplementedError

    def select_date(self, selector: str, date_str: str):
        """Select a date in a date-picker component"""
        raise NotImplementedError

    def check_table_has_text(self, text: str) -> bool:
        """Check if any table on the page contains the given text"""
        raise NotImplementedError

    @property
    def known_limitations(self) -> dict:
        return {}

    @property
    def autocomplete_debounce(self) -> float:
        return 2.0
