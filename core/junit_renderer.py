#!/usr/bin/env python3
"""
JUnit XML 测试报告渲染器 - 将 TestCollector 数据渲染为 JUnit XML 格式（CI/CD 集成）
"""
import os


class JUnitXmlRenderer:
    """将收集的测试数据渲染为 JUnit XML 格式（兼容 Jenkins/GitLab CI 等工具）"""

    @staticmethod
    def render(data: dict) -> str:
        """渲染为 JUnit XML 字符串"""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<testsuites name="测试报告">')

        for scene in data["scenes"]:
            scene_id = scene["id"]
            duration = scene.get("duration", 0) or 0
            assertions = scene.get("assertions", [])
            steps = scene.get("steps", [])

            # Group assertions by the step they follow
            assert_by_step = {}
            for a in assertions:
                step_seq = a.get("after_step", 0)
                assert_by_step.setdefault(step_seq, []).append(a)

            tests = len(assertions)
            failures = scene["assert_fail"]

            lines.append(f'  <testsuite name="{scene_id}" tests="{tests}" '
                         f'failures="{failures}" errors="0" time="{duration:.1f}">')

            # Process steps in order
            for step in steps:
                step_asserts = assert_by_step.pop(step["seq"], [])

                if step_asserts:
                    for a in step_asserts:
                        name = f"断言: {a['desc']}"
                        lines.append(f'    <testcase name="{JUnitXmlRenderer._escape(name)}" '
                                     f'classname="{scene_id}" time="0">')
                        if not a["passed"]:
                            detail = JUnitXmlRenderer._escape(str(a.get("detail", "")))
                            lines.append(f'      <failure message="断言失败">{detail}</failure>')
                        lines.append('    </testcase>')
                else:
                    # Step without assertions — informational testcase
                    name = f"步骤: {step['msg']}"
                    lines.append(f'    <testcase name="{JUnitXmlRenderer._escape(name)}" '
                                 f'classname="{scene_id}" time="0">')
                    lines.append('    </testcase>')

            # Any remaining assertions not linked to a step
            for step_seq, leftovers in assert_by_step.items():
                for a in leftovers:
                    name = f"断言: {a['desc']}"
                    lines.append(f'    <testcase name="{JUnitXmlRenderer._escape(name)}" '
                                 f'classname="{scene_id}" time="0">')
                    if not a["passed"]:
                        detail = JUnitXmlRenderer._escape(str(a.get("detail", "")))
                        lines.append(f'      <failure message="断言失败">{detail}</failure>')
                    lines.append('    </testcase>')

            lines.append('  </testsuite>')

        lines.append('</testsuites>')
        return '\n'.join(lines)

    @staticmethod
    def save(data: dict, output_dir=None, filename="junit_results.xml") -> str:
        """渲染并保存 JUnit XML 文件，返回文件路径"""
        xml = JUnitXmlRenderer.render(data)

        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(__file__))

        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"  📄 JUnit XML 报告已生成: {filepath}")
        return filepath

    @staticmethod
    def _escape(text: str) -> str:
        """转义 XML 特殊字符"""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")
        return text
