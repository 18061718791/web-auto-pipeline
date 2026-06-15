"""Ant Design (Vue 3) 组件适配器

适用于总控应用集成系统 (RuoYi-Vue-Pro + Ant Design Vue 3) 的自动化操作。
"""
from .base import ComponentAdapter


class AntDesignAdapter(ComponentAdapter):
    """Ant Design (Vue 3) 组件适配器

    支持 Ant Design Vue 3 常用组件的自动化交互:
    - a-select 下拉选择器
    - a-input 输入框
    - a-button / button.ant-btn 按钮
    - a-table 表格
    - a-pagination 分页
    - a-modal 模态框
    - a-date-picker 日期选择器
    - a-switch 开关
    - a-tabs 标签页
    """

    def __init__(self, page):
        self.page = page

    @property
    def name(self):
        return "antd"

    # ── 基础组件交互 ──────────────────────────────────────────

    def locate_select(self, page, placeholder: str):
        """定位 a-select 下拉选择器（按 placeholder 文本）"""
        return page.locator(
            f".ant-select:has(.ant-select-selection-placeholder:text-is(\"{placeholder}\")),"
            f".ant-select:has(.ant-select-selection-item[title]),"
            f".ant-select[style*='width']"
        ).first

    def locate_autocomplete(self, page, placeholder: str):
        """定位 autocomplete 输入框（按 placeholder）"""
        return page.locator(f"input.ant-input[placeholder*='{placeholder}']")

    def select_option(self, page, select_locator, option_text: str):
        """从 a-select 下拉中选择选项

        交互方案:
        1. 点击展开 a-select
        2. 等待 .ant-select-dropdown 出现
        3. 在 .ant-select-item 中查找匹配文本的选项
        4. 点击该选项
        """
        select_locator.click()
        page.locator(".ant-select-dropdown:visible").wait_for(timeout=5000)
        option = page.locator(
            ".ant-select-dropdown:visible .ant-select-item",
            has_text=option_text,
        ).first
        option.click(timeout=3000)

    def type_text(self, selector: str, text: str):
        """在 a-input 输入框中输入文本"""
        locator = self.page.locator(selector)
        locator.click()
        locator.fill(text)

    def click_button(self, text: str):
        """点击包含指定文本的按钮 (button.ant-btn)"""
        self.page.locator("button.ant-btn", has_text=text).click()

    # ── 表格操作 ────────────────────────────────────────────

    def get_table_rows(self, selector: str = None):
        """获取表格所有行数据，每行为各列文本列表

        Args:
            selector: 可选的表格选择器，默认查找 .ant-table-tbody

        Returns:
            list[list[str]]: 每行各列文本内容
        """
        tbody = selector or ".ant-table-tbody"
        rows = self.page.locator(f"{tbody} tr").all()
        result = []
        for row in rows:
            cells = row.locator("td").all_text_contents()
            # 跳过全空行（ant-table 可能渲染空占位行）
            cells = [c.strip() for c in cells if c.strip()]
            if cells:
                result.append(cells)
        return result

    def check_table_has_text(self, text: str) -> bool:
        """检查页面上任意 Ant Design 表格中是否包含指定文本"""
        return self.page.locator(".ant-table-tbody").locator(f"text={text}").count() > 0

    # ── 分页 ────────────────────────────────────────────────

    def get_pagination_info(self) -> dict:
        """获取 ant-pagination 分页信息

        Returns:
            dict 包含 total（总条数）、current（当前页）、
                 page_size（每页条数，如有）
        """
        pagination = self.page.locator(".ant-pagination")
        total_text = pagination.locator(".ant-pagination-total-text").text_content()
        # 格式: "共 XX 条" 或 "1-10 of 100"
        import re
        total = None
        if total_text:
            match = re.search(r'(\d+)', total_text)
            if match:
                total = int(match.group(1))

        current_item = pagination.locator(
            ".ant-pagination-item-active"
        ).get_attribute("title")
        current = int(current_item) if current_item and current_item.isdigit() else None

        return {
            "total": total,
            "current": current,
        }

    # ── 模态框 ──────────────────────────────────────────────

    def open_modal(self):
        """等待并返回 ant-modal 模态框定位器

        Returns:
            Locator: .ant-modal 定位器（已等待可见）
        """
        modal = self.page.locator(".ant-modal")
        modal.wait_for(state="visible", timeout=10000)
        return modal

    # ── 日期选择器 ──────────────────────────────────────────

    def select_date(self, selector: str, date_str: str):
        """在 a-date-picker 中选择日期

        Args:
            selector: a-date-picker 的选择器
            date_str: 日期字符串，支持格式 '2026-06-15' 或 '06-15'
        """
        parts = date_str.split("-")
        day = parts[-1]  # 取最后一段作为日期数字

        self.page.locator(selector).click()
        # 等待日期面板弹出
        self.page.locator(".ant-picker-dropdown:visible").wait_for(timeout=5000)
        # 点击对应的日期单元格（排除禁用状态）
        self.page.locator(
            ".ant-picker-dropdown:visible "
            ".ant-picker-cell:not(.ant-picker-cell-disabled) "
            f".ant-picker-cell-inner:text-is(\"{int(day)}\")"
        ).click()

    # ── 辅助方法 ────────────────────────────────────────────

    def select_simple(self, selector: str, option_text: str):
        """简洁版下拉选择：传入 CSS 选择器字符串直接选择

        这是 select_option 的便捷 wrapper，用于 adapter.select_option('.ant-select', '在线') 模式
        """
        self.page.locator(selector).click()
        self.page.locator(
            ".ant-select-dropdown:visible .ant-select-item",
            has_text=option_text,
        ).first.click()

    @property
    def known_limitations(self):
        return {
            "select_option_visible_dropdown": True,
            "description": (
                "Ant Design a-select 需要点击展开后才可见下拉选项；"
                "select_date 暂不支持范围选择器 (a-range-picker)"
            ),
        }

    @property
    def autocomplete_debounce(self):
        # Ant Design autocomplete 默认 debounce 较短
        return 0.5
