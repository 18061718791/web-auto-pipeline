#!/usr/bin/env python3
"""
DocRecorder — 物联管理平台操作手册录制器
=========================================
非测试框架，纯录制。用于为平台操作人员生成可交付的操作手册。

v7 更新：
  - 新增 goal/prerequisites/time_estimate 三要素方法（教学模式升级）
  - 新增 faq 方法（FAQ 章节支持）
  - 新增 task/task_step 方法（常见任务引导）
  - 支持 screenshot_selector 仅截内容区（消除无关信息）
"""
import os
import time
import json
import copy
from datetime import datetime


class DocRecorder:
    """操作手册录制器"""

    def __init__(self, title, platform_id="iot", version="V1.0", output_dir=None,
                 screenshot_format="jpeg", screenshot_quality=85,
                 screenshot_selector=None):
        self.title = title
        self.platform_id = platform_id
        self.version = version
        self.screenshot_format = screenshot_format
        self.screenshot_quality = screenshot_quality
        self.screenshot_selector = screenshot_selector
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "output", platform_id
        )
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "images"), exist_ok=True)

        self.data = {
            "title": title,
            "version": version,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "sections": [],
            "current_module": None,
            "current_step": None,
        }

        self._page = None
        self.screenshot_counter = 0

    # ═══════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════

    def record_start(self, page):
        self._page = page
        page.set_viewport_size({"width": 1920, "height": 1080})
        return self

    def record_end(self):
        return self

    # ═══════════════════════════════════════
    # 文档元素
    # ═══════════════════════════════════════

    def module(self, title, description=""):
        module = {
            "type": "module",
            "id": self._make_id(title),
            "title": title,
            "description": description,
            "children": [],
        }
        self.data["sections"].append(module)
        self.data["current_module"] = module
        self.data["current_step"] = None
        print(f"\n📦 模块: {title}")
        return self

    def goal(self, text):
        """设置本模块的学习目标（三要素之一）"""
        item = {"type": "goal", "text": text}
        self._append(item)
        print(f"  🎯 目标: {text[:50]}{'...' if len(text) > 50 else ''}")
        return self

    def prerequisites(self, *items):
        """设置前置条件列表（三要素之一）"""
        item = {"type": "prerequisites", "items": list(items)}
        self._append(item)
        print(f"  📋 前置条件: {', '.join(items)}")
        return self

    def time_estimate(self, minutes):
        """设置预计学习时间（三要素之一）"""
        item = {"type": "time_estimate", "minutes": minutes}
        self._append(item)
        return self

    def concept(self, title, text):
        item = {"type": "concept", "title": title, "text": text}
        self._append(item)
        print(f"  📖 概念: {title}")
        return self

    def page_description(self, title, fields=None, buttons=None):
        item = {
            "type": "page_desc",
            "title": title,
            "fields": fields or [],
            "buttons": buttons or [],
        }
        self._append(item)
        print(f"  📄 页面: {title}")
        return self

    def step(self, description, screenshot_page=None):
        page = screenshot_page or self._page
        item = {
            "type": "step",
            "description": description,
            "highlight_selector": None,
            "screenshot_path": None,
        }

        if page:
            try:
                time.sleep(0.5)
                self.screenshot_counter += 1
                counter = self.screenshot_counter
                timestamp = datetime.now().strftime("%H%M%S")
                ext = "jpg" if self.screenshot_format == "jpeg" else "png"
                filename = f"step_{counter:02d}_{timestamp}.{ext}"
                filepath = os.path.join(self.output_dir, "images", filename)

                if self.screenshot_selector:
                    el = page.locator(self.screenshot_selector)
                    if el.count() > 0:
                        kwargs = {"path": filepath}
                        if self.screenshot_format == "jpeg":
                            kwargs["type"] = "jpeg"
                            kwargs["quality"] = self.screenshot_quality
                        el.first.screenshot(**kwargs)
                    else:
                        kwargs = {"path": filepath, "full_page": True}
                        if self.screenshot_format == "jpeg":
                            kwargs["type"] = "jpeg"
                            kwargs["quality"] = self.screenshot_quality
                        page.screenshot(**kwargs)
                else:
                    kwargs = {"path": filepath, "full_page": True}
                    if self.screenshot_format == "jpeg":
                        kwargs["type"] = "jpeg"
                        kwargs["quality"] = self.screenshot_quality
                    page.screenshot(**kwargs)

                item["screenshot_path"] = filename
            except Exception as e:
                print(f"    ⚠️  截图失败: {e}")
                item["screenshot_path"] = None

        self._append(item)
        self.data["current_step"] = item
        print(f"  📸 步骤: {description[:60]}{'...' if len(description) > 60 else ''}")
        return self

    def expected(self, text):
        if self.data.get("current_step"):
            self.data["current_step"]["expected"] = text
        return self

    def field_table(self, title, fields):
        item = {"type": "field_table", "title": title, "fields": fields}
        self._append(item)
        return self

    def note(self, text, level="info"):
        item = {"type": "note", "text": text, "level": level}
        self._append(item)
        print(f"  💡 提示: {text[:50]}{'...' if len(text) > 50 else ''}")
        return self

    def sub_heading(self, title):
        item = {"type": "sub_heading", "title": title}
        self._append(item)
        return self

    def dependency(self, depends_on, note=""):
        """标注前置依赖模块"""
        item = {"type": "dependency", "depends_on": depends_on, "note": note}
        self._append(item)
        return self

    def faq(self, question, answer):
        """添加 FAQ 条目"""
        item = {"type": "faq", "question": question, "answer": answer}
        self._append(item)
        return self

    def task(self, title, steps, goal=""):
        """添加常见任务引导卡片"""
        item = {"type": "task", "title": title, "steps": steps, "goal": goal}
        self._append(item)
        return self

    def overview(self, title, content):
        """添加平台总览章节"""
        item = {"type": "overview", "title": title, "content": content}
        self._append(item)
        return self

    # ═══════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════

    def _append(self, item):
        if self.data.get("current_module") is None:
            self.module("未分类", "")
        self.data["current_module"]["children"].append(item)

    @staticmethod
    def _make_id(title):
        import re
        aid = re.sub(r'[^\w\u4e00-\u9fff]+', '-', title)
        return aid.strip('-').lower() or "section"

    # ═══════════════════════════════════════
    # 导出
    # ═══════════════════════════════════════

    def to_dict(self):
        return copy.deepcopy(self.data)

    def export_json(self, filename=None):
        if not filename:
            filename = f"物联管理平台操作手册_V{self.version}_{self.platform_id}.json"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON 数据已导出: {filepath}")
        return filepath

    def export_html(self, filename=None, embed_images=False):
        from docs.html_renderer import render_html
        if not filename:
            filename = f"物联管理平台操作手册_V{self.version}_{self.platform_id}.html"
        filepath = os.path.join(self.output_dir, filename)
        html = render_html(self.data, self.output_dir, embed_images=embed_images)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n✅ HTML 已生成: {filepath}")
        return filepath

    def export_pdf(self, filename=None, html_path=None):
        from docs.pdf_renderer import render_pdf
        if not filename:
            filename = f"物联管理平台操作手册_V{self.version}_{self.platform_id}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        html_file = html_path or self.export_html(embed_images=True)
        render_pdf(html_file, filepath, title=self.title, version=self.version)
        print(f"✅ PDF 已生成: {filepath}")
        return filepath
