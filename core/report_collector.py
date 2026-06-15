#!/usr/bin/env python3
"""
测试数据收集器 - 独立于呈现格式的场景/步骤/断言生命周期管理
"""
import time


class TestCollector:
    """收集测试执行数据，不关心输出格式"""

    def __init__(self, title="测试报告", output_dir=None):
        self.title = title
        self.output_dir = output_dir
        self.start_time = time.time()
        self.scenes = []
        self.current_scene = None
        self._exception = None

    # ── 场景生命周期 ──

    def scene_start(self, scene_id, description=""):
        """开始一个新场景"""
        if self.current_scene:
            self._finalize_scene()
        self.current_scene = {
            "id": scene_id,
            "desc": description,
            "start": time.time(),
            "end": None,
            "steps": [],
            "assertions": [],
            "status": "running",
            "step_count": 0,
            "last_step_seq": 0,
            "assert_count": 0,
            "assert_pass": 0,
            "assert_fail": 0,
        }
        print(f"▶ {scene_id}: {description}")

    def scene_end(self, success=True):
        """结束当前场景"""
        if not self.current_scene:
            return
        self.current_scene["end"] = time.time()

        # ★ 有断言失败则状态必为失败
        has_failed = self.current_scene["assert_fail"] > 0
        if has_failed:
            success = False

        self.current_scene["status"] = "passed" if success else "failed"
        self.current_scene["duration"] = self.current_scene["end"] - self.current_scene["start"]
        elapsed = self.current_scene["duration"]
        icon = "✅" if success else "❌"
        print(f"{icon} {self.current_scene['id']}: {'通过' if success else '失败'} ({elapsed:.1f}s)")
        if has_failed:
            print(f"    ⚠️  原因：{self.current_scene['assert_fail']} 个断言未通过")
        self._finalize_scene()

    def scene_skip(self, scene_id, description=""):
        """记录跳过的场景"""
        self.scenes.append({
            "id": scene_id,
            "desc": description,
            "start": None, "end": None,
            "steps": [],
            "assertions": [],
            "status": "skipped",
            "step_count": 0,
            "assert_pass": 0,
            "assert_fail": 0,
            "duration": 0,
        })

    # ── 步骤与断言 ──

    def step(self, msg, screenshot_bytes=None):
        """记录一个操作步骤，screenshot_bytes 为 PNG bytes 或 None"""
        if not self.current_scene:
            return None
        self.current_scene["step_count"] += 1
        self.current_scene["last_step_seq"] = self.current_scene["step_count"]
        entry = {
            "seq": self.current_scene["step_count"],
            "msg": msg,
            "ts": time.strftime("%H:%M:%S"),
            "screenshot": self._encode_screenshot(screenshot_bytes),
            "type": "step",
        }
        self.current_scene["steps"].append(entry)
        print(f"  [{entry['ts']}] {msg}")
        return entry["seq"]

    def assertion(self, desc, passed, detail=""):
        """记录一个断言结果"""
        if not self.current_scene:
            return
        self.current_scene["assert_count"] += 1
        entry = {
            "desc": desc,
            "passed": passed,
            "detail": detail,
            "ts": time.strftime("%H:%M:%S"),
            "seq": self.current_scene["assert_count"],
            "after_step": self.current_scene["last_step_seq"],
            "type": "assertion",
        }
        self.current_scene["assertions"].append(entry)
        self.current_scene["assert_pass"] += 1 if passed else 0
        self.current_scene["assert_fail"] += 0 if passed else 1
        icon = "✅" if passed else "❌"
        print(f"    {icon} {desc}: {detail[:60] if detail else ''}")

    def record_exception(self, exc):
        """记录未捕获异常到当前场景"""
        import traceback
        tb = traceback.format_exc()
        self._exception = (exc, tb)
        if self.current_scene:
            self.current_scene.setdefault("exception", str(exc))
            self.current_scene.setdefault("traceback", tb)

    # ── 数据导出 ──

    def get_data(self):
        """返回完整数据字典供渲染器消费"""
        self._finalize_scene()
        total_elapsed = time.time() - self.start_time
        total = len(self.scenes)
        passed = sum(1 for s in self.scenes if s["status"] == "passed")
        failed = sum(1 for s in self.scenes if s["status"] == "failed")
        skipped = sum(1 for s in self.scenes if s["status"] == "skipped")
        total_assert = sum(s["assert_pass"] + s["assert_fail"] for s in self.scenes)
        assert_pass = sum(s["assert_pass"] for s in self.scenes)
        assert_fail = sum(s["assert_fail"] for s in self.scenes)

        # ★ 打印断言汇总到 stdout，供 runner.py 提取
        print(f"📊 断言: 通过{assert_pass} 失败{assert_fail}")

        return {
            "title": self.title,
            "output_dir": self.output_dir,
            "start_time": self.start_time,
            "total_elapsed": total_elapsed,
            "scenes": self.scenes,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total_assert": total_assert,
            "assert_pass": assert_pass,
            "assert_fail": assert_fail,
        }

    # ── 内部 ──

    def _finalize_scene(self):
        if self.current_scene and self.current_scene not in self.scenes:
            self.scenes.append(self.current_scene)
        self.current_scene = None

    @staticmethod
    def _encode_screenshot(screenshot_bytes):
        """将 PNG bytes 转为 data URI"""
        if screenshot_bytes is None:
            return None
        try:
            import base64
            b64 = base64.b64encode(screenshot_bytes).decode()
            return f"data:image/png;base64,{b64}"
        except Exception:
            return None
