#!/usr/bin/env python3
"""pytest tests for self_heal.py — Phase 4 自愈诊断引擎"""

import os
import re
import sys
import json
import tempfile
from pathlib import Path

import pytest

# Add script directory to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from self_heal import (
    FAILURE_SIGNATURES,
    load_report,
    analyze_log,
    analyze_report,
    analyze_script_file,
    render_report,
    render_auto_fix,
    AUTO_FIX_COMMANDS,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def sample_error_log():
    """Create a temporary log file containing known failure signals."""
    content = """
[ERROR] 2024-01-01 10:00:00 - Action failed: intercepts pointer events
[ERROR] 2024-01-01 10:00:01 - strict mode violation
[ERROR] 2024-01-01 10:00:02 - Timeout 30000ms exceeded
[WARN]  Some el-select dropdown issue with combobox
[ERROR]  NullPointerException at line 42
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmppath = f.name
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture
def sample_report():
    """Return a sample test_results.json dict."""
    return {
        "scenes": [
            {
                "name": "测试_创建设备",
                "status": "failed",
                "detail": "保存后无数据写入，页面空白页",
            },
            {
                "name": "测试_删除设备",
                "status": "passed",
                "detail": "ok",
            },
            {
                "name": "测试_发布",
                "status": "failed",
                "detail": "thingModelVersion null, NullPointerException",
            },
        ]
    }


@pytest.fixture
def script_with_l001():
    """Script that triggers L001 (get_by_role('option'))."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write('page.get_by_role("option").click()\n')
        tmppath = f.name
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture
def script_with_l002():
    """Script that triggers L002 (hash URL goto)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write('page.goto("http://example.com/#/list")\n')
        tmppath = f.name
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture
def script_with_l003():
    """Script that triggers L003 (button with name)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write('page.get_by_role("button", name="提交").click()\n')
        tmppath = f.name
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture
def script_with_l004():
    """Script that triggers L004 (get_by_role('treeitem'))."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write('page.get_by_role("treeitem").click()\n')
        tmppath = f.name
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture
def script_with_l005():
    """Script that triggers L005 (long sleep)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write("import time\ntime.sleep(30)\n")
        tmppath = f.name
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture
def script_clean():
    """Clean script that triggers no issues."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write('page.locator(".btn").click()\n')
        tmppath = f.name
    yield tmppath
    os.unlink(tmppath)


# ── 1. FAILURE_SIGNATURES 模式匹配验证 ─────────────────────


class TestFailureSignaturesPatternMatch:
    """每条信号的 signal_pattern 能在对应的示例文本中匹配。"""

    def test_s001_intercepts_pointer_events(self):
        sig = self._find("S001")
        assert re.search(sig["signal_pattern"], "intercepts pointer events", re.IGNORECASE)

    def test_s002_strict_mode_violation(self):
        sig = self._find("S002")
        assert re.search(sig["signal_pattern"], "strict mode violation", re.IGNORECASE)

    def test_s003_timeout_exceeded(self):
        sig = self._find("S003")
        assert re.search(sig["signal_pattern"], "Timeout 30000ms exceeded", re.IGNORECASE)

    def test_s004_el_select(self):
        sig = self._find("S004")
        assert re.search(
            sig["signal_pattern"],
            "Failed to click el-select dropdown item",
            re.IGNORECASE,
        )

    def test_s005_el_autocomplete(self):
        sig = self._find("S005")
        assert re.search(sig["signal_pattern"], "el-autocomplete issue", re.IGNORECASE)

    def test_s006_save_no_data(self):
        sig = self._find("S006")
        assert re.search(sig["signal_pattern"], "保存后无数据写入", re.IGNORECASE)

    def test_s007_url_unchanged(self):
        sig = self._find("S007")
        assert re.search(
            sig["signal_pattern"], "保存后 url 未变化", re.IGNORECASE
        )

    def test_s008_unique_constraint(self):
        sig = self._find("S008")
        assert re.search(
            sig["signal_pattern"], "MAC 地址已被使用", re.IGNORECASE
        )

    def test_s009_tab_switch(self):
        sig = self._find("S009")
        assert re.search(sig["signal_pattern"], "切换tab后保存无效", re.IGNORECASE)

    def test_s010_publish_not_changed(self):
        sig = self._find("S010")
        assert re.search(
            sig["signal_pattern"], "发布超时状态未变", re.IGNORECASE
        )

    def test_s011_npe(self):
        sig = self._find("S011")
        assert re.search(sig["signal_pattern"], "NullPointerException", re.IGNORECASE)

    def test_s012_option_role(self):
        sig = self._find("S012")
        assert re.search(
            sig["signal_pattern"],
            "get_by_role('option') not found",
            re.IGNORECASE,
        )

    def test_s013_headed_issue(self):
        sig = self._find("S013")
        assert re.search(
            sig["signal_pattern"], "headed mode fail", re.IGNORECASE
        )

    def test_s014_about_blank(self):
        sig = self._find("S014")
        assert re.search(sig["signal_pattern"], "about:blank", re.IGNORECASE)

    def _find(self, sig_id: str):
        for sig in FAILURE_SIGNATURES:
            if sig["id"] == sig_id:
                return sig
        raise KeyError(f"Signal {sig_id} not found in FAILURE_SIGNATURES")


# ── 2. Schema 完整性验证 ────────────────────────────────────


class TestSchemaComplete:
    """每条信号的 schema 完整（id, name, signal_pattern, confidence, fix, severity）。"""

    REQUIRED_KEYS = {"id", "name", "signal_pattern", "confidence", "fix", "severity"}

    def test_all_signals_have_required_keys(self):
        for sig in FAILURE_SIGNATURES:
            missing = self.REQUIRED_KEYS - set(sig.keys())
            assert not missing, (
                f"Signal {sig.get('id', '?')} missing keys: {missing}"
            )


# ── 3. Confidence 值合法性 ──────────────────────────────────


class TestConfidenceValid:
    """验证 confidence 值合法（仅 high/medium/low）。"""

    VALID_CONFIDENCE = {"high", "medium", "low"}

    def test_all_confidence_values_valid(self):
        for sig in FAILURE_SIGNATURES:
            assert sig["confidence"] in self.VALID_CONFIDENCE, (
                f"Signal {sig['id']} has invalid confidence: {sig['confidence']}"
            )


# ── 4. Severity 值合法性 ────────────────────────────────────


class TestSeverityValid:
    """验证 severity 值合法（仅 error/warning/info）。"""

    VALID_SEVERITY = {"error", "warning", "info"}

    def test_all_severity_values_valid(self):
        for sig in FAILURE_SIGNATURES:
            assert sig["severity"] in self.VALID_SEVERITY, (
                f"Signal {sig['id']} has invalid severity: {sig['severity']}"
            )


# ── 5. analyze_log 测试 ─────────────────────────────────────


class TestAnalyzeLog:
    """测试 analyze_log 对已知错误日志的匹配。"""

    def test_matches_known_signals(self, sample_error_log):
        matches = analyze_log(sample_error_log)
        matched_ids = {m["id"] for m in matches}
        assert "S001" in matched_ids, "Should match intercepts pointer events"
        assert "S002" in matched_ids, "Should match strict mode violation"
        assert "S003" in matched_ids, "Should match timeout"
        assert "S004" in matched_ids, "Should match el-select/combobox"
        assert "S011" in matched_ids, "Should match NullPointerException"

    def test_non_existent_log(self):
        matches = analyze_log("/tmp/nonexistent_log_xyz.log")
        assert matches == [], "Should return empty list for non-existent file"

    def test_empty_log(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            tmppath = f.name
        try:
            matches = analyze_log(tmppath)
            assert matches == []
        finally:
            os.unlink(tmppath)


# ── 6. analyze_report 测试 ──────────────────────────────────


class TestAnalyzeReport:
    """测试 analyze_report 对已知失败信号的匹配。"""

    def test_matches_failed_scenes(self, sample_report):
        matches = analyze_report(sample_report)
        matched_ids = {m["id"] for m in matches}
        assert "S006" in matched_ids, "Should match '保存后无数据'"
        assert "S011" in matched_ids, "Should match NullPointerException"
        assert "S014" in matched_ids, "Should match about:blank/空白页"

    def test_empty_report(self):
        matches = analyze_report({"scenes": []})
        assert matches == []

    def test_all_passed_report(self):
        matches = analyze_report(
            {"scenes": [{"name": "t1", "status": "passed", "detail": "ok"}]}
        )
        assert matches == []


# ── 7. analyze_script_file 测试 ─────────────────────────────


class TestAnalyzeScriptFile:
    """测试 analyze_script_file 对已知问题模式的检测。"""

    def test_l001_option_role(self, script_with_l001):
        issues = analyze_script_file(script_with_l001)
        assert any(i["id"] == "L001" for i in issues)

    def test_l002_hash_goto(self, script_with_l002):
        issues = analyze_script_file(script_with_l002)
        assert any(i["id"] == "L002" for i in issues)

    def test_l003_button_name(self, script_with_l003):
        issues = analyze_script_file(script_with_l003)
        assert any(i["id"] == "L003" for i in issues)

    def test_l004_treeitem_element_ui(self, script_with_l004):
        """L004 should trigger with platform='element_ui' (default)."""
        issues = analyze_script_file(script_with_l004, platform="element_ui")
        assert any(i["id"] == "L004" for i in issues)

    def test_l004_treeitem_antd_skipped(self, script_with_l004):
        """L004 should be skipped with platform='antd'."""
        issues = analyze_script_file(script_with_l004, platform="antd")
        assert not any(i["id"] == "L004" for i in issues), (
            "L004 should not trigger on antd platform"
        )

    def test_l004_treeitem_default(self, script_with_l004):
        """L004 should trigger with default platform (element_ui)."""
        issues = analyze_script_file(script_with_l004)
        assert any(i["id"] == "L004" for i in issues)

    def test_l005_long_sleep(self, script_with_l005):
        issues = analyze_script_file(script_with_l005)
        assert any(i["id"] == "L005" for i in issues)

    def test_clean_script_no_issues(self, script_clean):
        issues = analyze_script_file(script_clean)
        assert issues == []

    def test_non_existent_script(self):
        issues = analyze_script_file("/tmp/nonexistent_script_xyz.py")
        assert issues == []


# ── 8. --apply 模式测试 ─────────────────────────────────────


class TestAutoFix:
    """测试 --apply 模式的修复命令输出。"""

    def test_auto_fix_commands_exist(self):
        """Verify all high-confidence signals have fix commands."""
        high_sigs = {s["id"] for s in FAILURE_SIGNATURES if s["confidence"] == "high"}
        for sig_id in high_sigs:
            if sig_id == "S001":
                assert "S001" in AUTO_FIX_COMMANDS
            if sig_id == "S012":
                assert "S012" in AUTO_FIX_COMMANDS

    def test_auto_fix_high_confidence_only(self, capsys):
        """render_auto_fix should only output for high confidence."""
        matches = [
            {"id": "S001", "confidence": "high", "fix": "Use force=True"},
            {"id": "S004", "confidence": "low", "fix": "Some fix"},
        ]
        render_auto_fix(matches)
        captured = capsys.readouterr()
        # S001 (high) should appear
        assert "S001" in captured.out
        # S004 (low) should NOT appear
        assert "S004" not in captured.out

    def test_auto_fix_no_high_confidence(self, capsys):
        """render_auto_fix should skip when no high confidence signals."""
        matches = [
            {"id": "S004", "confidence": "low"},
        ]
        render_auto_fix(matches)
        captured = capsys.readouterr()
        assert "跳过自动修复" in captured.out

    def test_auto_fix_command_content(self, capsys):
        """Verify fix command output contains expected content."""
        sig = next(s for s in FAILURE_SIGNATURES if s["id"] == "S001")
        render_auto_fix([sig])
        captured = capsys.readouterr()
        assert "force=True" in captured.out


# ── 9. Platform CLI Argument ────────────────────────────────


class TestPlatformCli:
    """Test that --platform CLI argument flows through correctly."""

    def test_cli_platform_antd_suppresses_l004(self):
        """Simulating CLI: platform=antd should suppress L004."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write('page.get_by_role("treeitem").click()\n')
            tmppath = f.name
        try:
            el_issues = analyze_script_file(tmppath, platform="element_ui")
            antd_issues = analyze_script_file(tmppath, platform="antd")
            assert any(i["id"] == "L004" for i in el_issues)
            assert not any(i["id"] == "L004" for i in antd_issues)
        finally:
            os.unlink(tmppath)


# ── 10. render_report (载) ──────────────────────────────────


class TestRenderReport:
    """Basic smoke tests for render_report."""

    def test_no_matches(self, capsys):
        render_report([], source="测试来源")
        captured = capsys.readouterr()
        assert "未检测到已知故障信号" in captured.out

    def test_with_matches(self, capsys):
        sig = FAILURE_SIGNATURES[0]
        render_report([sig], source="测试来源")
        captured = capsys.readouterr()
        assert sig["id"] in captured.out
        assert sig["name"] in captured.out

    def test_apply_mode_renders_auto_fix(self, capsys):
        sig = next(s for s in FAILURE_SIGNATURES if s["id"] == "S001")
        render_report([sig], source="测试", apply=True)
        captured = capsys.readouterr()
        assert "force=True" in captured.out
