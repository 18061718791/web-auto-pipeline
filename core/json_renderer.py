#!/usr/bin/env python3
"""
JSON 测试报告渲染器 - 将 TestCollector 数据渲染为结构化 JSON（CI/CD 集成）
"""
import os
import json
from datetime import datetime


class JsonRenderer:
    """将收集的测试数据渲染为 JSON 格式（供 CI/CD pipeline 消费）"""

    @staticmethod
    def render(data: dict) -> dict:
        """返回 JSON-serializable 字典，screenshot 被截断以减小体积"""
        ts = datetime.fromtimestamp(
            data["start_time"]
        ).isoformat() if data.get("start_time") else datetime.now().isoformat()

        scenes_out = []
        for sc in data["scenes"]:
            assertions_out = []
            for a in sc.get("assertions", []):
                assertions_out.append({
                    "desc": a["desc"],
                    "passed": a["passed"],
                    "detail": a.get("detail", ""),
                })

            scenes_out.append({
                "id": sc["id"],
                "description": sc.get("desc", ""),
                "status": sc["status"],
                "duration": sc.get("duration", 0) or 0,
                "assertions": assertions_out,
            })

        result = {
            "title": data["title"],
            "timestamp": ts,
            "total_elapsed": round(data["total_elapsed"], 1),
            "total_scenes": data["total"],
            "passed": data["passed"],
            "failed": data["failed"],
            "skipped": data["skipped"],
            "total_assertions": data["total_assert"],
            "assertions_passed": data["assert_pass"],
            "scenes": scenes_out,
        }
        return result

    @staticmethod
    def save(data: dict, output_dir=None, filename="test_results.json") -> str:
        """JSON 报告已弃用，仅生成 HTML。返回 None。"""
        return None
