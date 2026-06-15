#!/usr/bin/env python3
"""
报告组件兼容层 — TestReport API 不变，内部委托给 TestCollector + HtmlRenderer

v2 更新：
  - 新增 _global_doc_recorder 类变量：设置后自动同步 step/scene → 操作手册录制
  - 测试脚本无需任何改动，只需在导入前设置 TestReport._global_doc_recorder = doc
"""
import os
from core.report_collector import TestCollector
from core.report_renderer import HtmlRenderer


class TestReport:
    """测试报告收集器（兼容层）"""

    _global_doc_recorder = None    # 全局操作手册录制器，设置后自动同步
    _current_module_title = None   # 当前测试脚本对应的手册模块标题

    def __init__(self, title="测试报告", output_dir=None):
        if output_dir is None:
            from config import REPORT_DIR
            output_dir = REPORT_DIR
        self._collector = TestCollector(title, output_dir)
        self._renderer = HtmlRenderer()

        self.title = title
        self.output_dir = self._collector.output_dir
        self.start_time = self._collector.start_time
        self.scenes = self._collector.scenes
        self.current_scene = self._collector.current_scene
        self.html_path = None

        self._doc = TestReport._global_doc_recorder
        self._module_started = False

    @classmethod
    def set_doc_recorder(cls, doc, module_title=None):
        """设置全局操作手册录制器（在导入测试脚本前调用）"""
        cls._global_doc_recorder = doc
        cls._current_module_title = module_title

    @classmethod
    def clear_doc_recorder(cls):
        """清除全局录制器"""
        cls._global_doc_recorder = None
        cls._current_module_title = None

    def _ensure_module_started(self, scene_desc=""):
        """确保手册中的当前模块已开始录制"""
        if not self._doc or self._module_started:
            return
        module_title = TestReport._current_module_title or self.title
        self._doc.module(module_title)
        self._module_started = True

    def scene_start(self, scene_id, description=""):
        self._collector.scene_start(scene_id, description)
        self.scenes = self._collector.scenes
        self.current_scene = self._collector.current_scene

        if self._doc:
            self._ensure_module_started()
            self._doc.sub_heading(description or scene_id)

    def scene_end(self, success=True):
        self._collector.scene_end(success)
        self.scenes = self._collector.scenes
        self.current_scene = self._collector.current_scene

    def scene_skip(self, scene_id, description=""):
        self._collector.scene_skip(scene_id, description)
        self.scenes = self._collector.scenes

    def step(self, msg, screenshot=None):
        screenshot_bytes = None
        screenshot_page = None

        if screenshot is not None:
            if hasattr(screenshot, "screenshot") and callable(getattr(screenshot, "screenshot", None)):
                try:
                    screenshot_bytes = screenshot.screenshot(full_page=True)
                    screenshot_page = screenshot
                except Exception:
                    if isinstance(screenshot, (bytes, bytearray)):
                        screenshot_bytes = screenshot
            elif isinstance(screenshot, (bytes, bytearray)):
                screenshot_bytes = screenshot
            else:
                try:
                    import base64
                    if isinstance(screenshot, str) and screenshot.startswith("data:image"):
                        screenshot_bytes = base64.b64decode(screenshot.split(",")[1])
                except Exception:
                    pass

        self._collector.step(msg, screenshot_bytes)
        self.current_scene = self._collector.current_scene

        if self._doc and screenshot_page:
            try:
                self._doc.step(msg, screenshot_page=screenshot_page)
            except Exception:
                self._doc.step(msg)

    def assertion(self, desc, passed, detail=""):
        self._collector.assertion(desc, passed, detail)
        self.current_scene = self._collector.current_scene

    def generate_html(self, filename=None):
        data = self._collector.get_data()
        self.html_path = self._renderer.save(data, self._collector.output_dir, filename)
        return self.html_path

    def record_exception(self, exc):
        self._collector.record_exception(exc)

    def get_data(self):
        return self._collector.get_data()


__all__ = ["TestReport", "TestCollector", "HtmlRenderer"]
