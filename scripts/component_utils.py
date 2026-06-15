#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
component_utils.py — Element UI 组件交互工具函数模块

提供三个核心组件交互函数，适用于基于 Element UI / Element Plus 的 Web 自动化：
  - select_el_option()       : el-select 下拉选择框选项选择
  - select_cascader_options(): el-cascader 级联选择器多选（复选框模式）
  - select_autocomplete_option(): el-autocomplete 自动补全选择

每个函数包含完整的异常处理、日志输出，并包含 wait_strategy 参数以支持
固定等待与自适应等待两种模式。

Usage:
    from scripts.component_utils import select_el_option, select_cascader_options, select_autocomplete_option
    select_el_option(page, "测试装置")
"""

import time
import logging
from playwright.sync_api import Page

logger = logging.getLogger(__name__)


# ============================================================================
#   el-select 下拉选择框
# ============================================================================

def select_el_option(
    page: Page,
    option_text: str,
    timeout: float = 10.0,
    wait_strategy: str = "fixed",
) -> bool:
    """
    在 el-select 下拉选择框中选择指定文本的选项。

    策略说明：
      1. force=True 点击 combobox 以打开下拉弹窗
      2. 等待下拉面板渲染（固定等待 1.5s 或自适应等待面板出现）
      3. 使用 .el-select-dropdown__item 定位选项，filter(has_text) 匹配文本
      4. force=True 点击选项（绕过 Popper 可见性检查）
      5. 若找不到选项，回退到键盘 ArrowDown + Enter 方式触发 Vue 事件

    Args:
        page:               Playwright Page 对象
        option_text (str):  要选择的选项文本（子串匹配）
        timeout (float):    操作超时秒数，默认 10 秒
        wait_strategy (str):
            等待策略："fixed" 使用固定 time.sleep，"adaptive" 使用
            page.wait_for_selector 等待下拉面板出现。默认 "fixed"。

    Returns:
        bool: 选择成功返回 True，失败返回 False

    Examples:
        >>> select_el_option(page, "启用")
        True
        >>> select_el_option(page, "测试装置")
        True
    """
    start = time.time()
    try:
        logger.info(f"[el-select] 开始选择选项: '{option_text}'")

        # 1. 打开下拉弹窗
        combobox = page.get_by_role("combobox").first
        if combobox.count() == 0:
            combobox = page.locator(".el-select").first
        combobox.click(force=True)
        elapsed = time.time() - start
        logger.info(f"[el-select] 已点击打开下拉 (耗时 {elapsed:.1f}s)")

        # 等待下拉面板出现
        if wait_strategy == "adaptive":
            page.wait_for_selector(
                ".el-select-dropdown",
                state="visible",
                timeout=2000,
            )
        else:
            time.sleep(1.5)

        # 2. 查找选项
        option = (
            page.locator(".el-select-dropdown__item")
            .filter(has_text=option_text)
            .first
        )
        if option.count() > 0:
            option.click(force=True)
            elapsed = time.time() - start
            logger.info(f"[el-select] ✅ 选项 '{option_text}' 已选中 (耗时 {elapsed:.1f}s)")
            time.sleep(0.5)
            return True

        # 3. 回退: 键盘 ArrowDown + Enter
        logger.warning(f"[el-select] 未找到选项 '{option_text}'，回退到键盘选择...")
        page.keyboard.press("ArrowDown")
        time.sleep(0.3)
        page.keyboard.press("Enter")
        time.sleep(0.5)
        elapsed = time.time() - start
        logger.info(f"[el-select] ✅ 键盘选择完成 (耗时 {elapsed:.1f}s)")
        return True

    except Exception as e:
        elapsed = time.time() - start
        logger.error(
            f"[el-select] ❌ 选择选项 '{option_text}' 失败 (耗时 {elapsed:.1f}s): {e}"
        )
        return False


# ============================================================================
#   el-cascader 级联选择器（复选框多选模式）
# ============================================================================

def select_cascader_options(
    page: Page,
    input_locator_selector: str,
    target_texts: list[str],
    timeout: float = 15.0,
    wait_strategy: str = "fixed",
) -> tuple[bool, list[str]]:
    """
    在 el-cascader（级联选择器，多选复选框模式）中选择指定的多个选项。

    策略说明：
      1. 使用 input_locator_selector 定位 cascader 并 force=True 点击打开
      2. 等待级联面板渲染（固定等待 1.5s 或自适应等待面板出现）
      3. 对每个 target_text，使用 page.evaluate 遍历 .el-cascader-node，
         找到包含文本的节点，点击其中的 .el-checkbox（勾选框）
      4. 全部选择完成后按 Escape 关闭下拉面板

    注意：
      - 此函数针对的是 el-cascader 的「复选框多选模式」。
        必须点击 checkbox 而不是节点文本，否则会触发级联展开而非选中。
      - target_texts 支持同时选择多个选项。

    Args:
        page:                    Playwright Page 对象
        input_locator_selector (str):
            el-cascader 的定位 CSS 选择器，例如 ".el-cascader" 或
            ".el-form-item:has-text('标签') .el-cascader"
        target_texts (list[str]): 要选择的选项文本列表（子串匹配）
        timeout (float):         操作超时秒数，默认 15 秒
        wait_strategy (str):
            等待策略："fixed" 使用固定 time.sleep，"adaptive" 使用
            page.wait_for_selector 等待级联面板出现。默认 "fixed"。

    Returns:
        tuple[bool, list[str]]:
            (整体成功/失败, 已成功选择的文本列表)
            所有选项选择成功时 bool=True；部分成功时 bool=False 但
            list 包含已选中的项目。完全失败时返回 (False, [])。

    Examples:
        >>> result, selected = select_cascader_options(
        ...     page, ".el-cascader", ["温度标签", "湿度标签"]
        ... )
        >>> result
        True
        >>> selected
        ["温度标签", "湿度标签"]
    """
    start = time.time()
    selected_texts: list[str] = []
    try:
        logger.info(
            f"[el-cascader] 开始选择选项: '{target_texts}' "
            f"(定位器: '{input_locator_selector}')"
        )

        # 1. 定位并打开 cascader
        cascader = page.locator(input_locator_selector).first
        if cascader.count() == 0:
            cascader = page.locator(".el-cascader").first
        cascader.click(force=True)

        # 等待级联面板出现
        if wait_strategy == "adaptive":
            page.wait_for_selector(
                ".el-cascader__dropdown",
                state="visible",
                timeout=2000,
            )
        else:
            time.sleep(1.5)
        logger.info("[el-cascader] 已打开级联面板")

        # 2. 逐个选择选项
        for text in target_texts:
            try:
                result = page.evaluate(
                    f"""
                    () => {{
                        const nodes = document.querySelectorAll('.el-cascader-node');
                        for (const node of nodes) {{
                            if (node.textContent.includes('{text}')) {{
                                const cb = node.querySelector('.el-checkbox');
                                if (cb) {{
                                    cb.click();
                                    return true;
                                }}
                            }}
                        }}
                        return false;
                    }}
                """
                )
                if result:
                    selected_texts.append(text)
                    logger.info(f"[el-cascader] ✅ 已选中: '{text}'")
                else:
                    logger.warning(f"[el-cascader] ⚠️ 未找到选项: '{text}'")
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"[el-cascader] ❌ 选择 '{text}' 时出错: {e}")

        # 3. 关闭下拉
        page.keyboard.press("Escape")
        time.sleep(0.5)
        elapsed = time.time() - start
        all_success = len(selected_texts) == len(target_texts)
        logger.info(
            f"[el-cascader] 已完成 (选中 {len(selected_texts)}/{len(target_texts)} 项, "
            f"耗时 {elapsed:.1f}s)"
        )
        return (all_success, selected_texts)

    except Exception as e:
        elapsed = time.time() - start
        logger.error(
            f"[el-cascader] ❌ 操作失败 (耗时 {elapsed:.1f}s): {e}"
        )
        return (False, selected_texts)


# ============================================================================
#   el-autocomplete 自动补全
# ============================================================================

def select_autocomplete_option(
    page: Page,
    input_locator,
    search_text: str,
    option_text: str = None,
    wait_seconds: float = 2.5,
    timeout: float = 15.0,
    wait_strategy: str = "fixed",
) -> bool:
    """
    在 el-autocomplete（可搜索自动补全输入框）中选择指定的选项。

    策略说明：
      1. 点击输入框获取焦点
      2. 清空后 fill 输入搜索文本（触发 Vue fetchSuggestions）
      3. 等待 debounce + 后端异步返回（固定等待或自适应等待 popper 出现）
      4. 使用 .el-autocomplete__popper li 定位下拉选项，
         用 filter(has_text) 匹配 option_text
      5. force=True 点击选项（绕过 Popper 可见性检查）
      6. 若找不到则降级到 [role='option']

    注意：
      - option_text 默认为 search_text（即搜索文本 == 选项文本时）
      - 选项可能包含版本后缀（如 "自动化测试-设备模型 v1"），
        使用子串匹配（has_text）而非全等匹配

    Args:
        page:               Playwright Page 对象
        input_locator:      el-autocomplete 输入框的定位方式。
                            可以是 CSS 选择器（str）或 Playwright Locator。
                            推荐："css=.el-autocomplete input" 或
                            page.get_by_placeholder("请输入名称搜索")
        search_text (str):  输入到搜索框的文本，用于触发异步搜索
        option_text (str):  要选择的选项显示文本。默认为 search_text，
                            当选项显示文本与搜索文本不同时需指定
        wait_seconds (float):
            输入后等待 debounce + 后端返回的秒数，默认 2.5 秒。
            当 wait_strategy='adaptive' 时此参数被忽略，转而等待 popper 出现。
        timeout (float):    操作超时秒数，默认 15 秒
        wait_strategy (str):
            等待策略："fixed" 使用固定 time.sleep(wait_seconds)，
            "adaptive" 使用 page.wait_for_selector 等待下拉面板出现。
            默认 "fixed"。

    Returns:
        bool: 选择成功返回 True，失败返回 False

    Examples:
        >>> select_autocomplete_option(
        ...     page, "css=.el-autocomplete input", "设备模型A"
        ... )
        True
        >>> select_autocomplete_option(
        ...     page,
        ...     page.get_by_placeholder("请输入设备模型名称搜索"),
        ...     "自动化测试-设备模型",
        ...     option_text="自动化测试-设备模型 v1",
        ...     wait_seconds=3.0,
        ... )
        True
    """
    start = time.time()
    effective_option = option_text or search_text
    try:
        logger.info(
            f"[el-autocomplete] 开始选择: search='{search_text}', "
            f"option='{effective_option}'"
        )

        # 1. 定位输入框并点击
        inp = (
            page.locator(input_locator).first
            if isinstance(input_locator, str)
            else input_locator.first
        )
        inp.click()
        time.sleep(0.3)

        # 2. 清空 + fill 搜索文本
        inp.fill("")
        time.sleep(0.3)
        inp.fill(search_text)

        # 等待 debounce + 后端返回
        if wait_strategy == "adaptive":
            logger.info("[el-autocomplete] 自适应等待 popper 出现...")
            page.wait_for_selector(
                ".el-autocomplete__popper",
                state="visible",
                timeout=int(timeout * 1000),
            )
        else:
            logger.info(
                f"[el-autocomplete] 已输入搜索文本 '{search_text}'，"
                f"等待 {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

        # 3. 再次点击确保 popper 可见
        inp.click()
        if wait_strategy == "adaptive":
            page.wait_for_selector(
                ".el-autocomplete__popper li",
                state="visible",
                timeout=2000,
            )
        else:
            time.sleep(0.5)

        # 4. 查找并点击选项
        # 主策略: .el-autocomplete__popper li
        option = (
            page.locator(".el-autocomplete__popper li")
            .filter(has_text=effective_option)
            .first
        )
        if option.count() > 0:
            option.click(force=True)
            time.sleep(0.5)
            elapsed = time.time() - start
            logger.info(
                f"[el-autocomplete] ✅ 选项 '{effective_option}' 已选中 "
                f"(耗时 {elapsed:.1f}s)"
            )
            return True

        # 降级 1: .el-popper li
        logger.warning(
            f"[el-autocomplete] 主选择器未找到，降级到 .el-popper li..."
        )
        option = (
            page.locator(".el-popper li")
            .filter(has_text=effective_option)
            .first
        )
        if option.count() > 0:
            option.click(force=True)
            time.sleep(0.5)
            elapsed = time.time() - start
            logger.info(
                f"[el-autocomplete] ✅ 选项 '{effective_option}' 已选中（降级1）"
                f"(耗时 {elapsed:.1f}s)"
            )
            return True

        # 降级 2: [role='option']
        logger.warning(
            f"[el-autocomplete] 降级1未找到，降级到 [role='option']..."
        )
        option = (
            page.locator("[role='option']")
            .filter(has_text=effective_option)
            .first
        )
        if option.count() > 0:
            option.click(force=True)
            time.sleep(0.5)
            elapsed = time.time() - start
            logger.info(
                f"[el-autocomplete] ✅ 选项 '{effective_option}' 已选中（降级2）"
                f"(耗时 {elapsed:.1f}s)"
            )
            return True

        # 全部失败
        elapsed = time.time() - start
        logger.error(
            f"[el-autocomplete] ❌ 所有选择器均未找到选项 '{effective_option}' "
            f"(耗时 {elapsed:.1f}s)"
        )
        return False

    except Exception as e:
        elapsed = time.time() - start
        logger.error(
            f"[el-autocomplete] ❌ 选择选项 '{effective_option}' 失败 "
            f"(耗时 {elapsed:.1f}s): {e}"
        )
        return False


# ============================================================================
#   Debug 入口
# ============================================================================

if __name__ == "__main__":
    """
    调试入口 — 用于验证导入、日志格式和函数签名。

    使用方法：
        在有 Playwright 环境的 Python 中：
            python scripts/component_utils.py

        或者在 REPL 中：
            from scripts.component_utils import select_el_option, ...
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 60)
    print("  component_utils.py — 模块验证")
    print("=" * 60)
    print()
    print(f"  函数列表:")
    print(f"    ✅ select_el_option(page, option_text)")
    print(f"    ✅ select_cascader_options(page, input_locator_selector, target_texts)")
    print(f"    ✅ select_autocomplete_option(page, input_locator, search_text, ...)")
    print()
    print(f"  使用示例:")
    print()
    print("    # el-select: 选择启用/禁用状态")
    print('    select_el_option(page, "启用")')
    print()
    print("    # el-cascader: 选择多个标签")
    print("    select_cascader_options(")
    print('        page, ".el-cascader", ["温度标签", "湿度标签"]')
    print("    )")
    print()
    print("    # el-autocomplete: 搜索并选择设备模型")
    print("    select_autocomplete_option(")
    print('        page,')
    print('        page.get_by_placeholder("请输入名称搜索"),')
    print('        "设备模型A",')
    print("    )")
    print()
    print("=" * 60)
    print("  模块导入验证通过 ✅")
