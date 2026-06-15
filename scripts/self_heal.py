#!/usr/bin/env python3
"""
self_heal.py — Phase 4 自愈诊断引擎

读取当前失败日志/报告 JSON，根据故障目录（failure-catalog.md）匹配已知信号模式，
输出诊断结论和恢复建议。

Usage:
    python self_heal.py --report path/to/test_results.json
    python self_heal.py --log path/to/runner_output.log
    python self_heal.py --analyze-script path/to/script.py

故障诊断基于 references/ 中的故障目录知识。
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import Optional


# ── 故障信号库 ──────────────────────────────────────────────

FAILURE_SIGNATURES = [
    {
        "id": "S001",
        "name": "指针事件拦截 (intercepts pointer events)",
        "signal_pattern": r"intercepts pointer events",
        "confidence": "high",
        "root_cause": "Element UI 的 <span> overlay 遮挡目标元素",
        "fix": "使用 force=True 或 JS 原生点击（dispatchEvent）绕过 overlay 拦截",
        "severity": "error",
    },
    {
        "id": "S002",
        "name": "严格模式违规 (strict mode violation)",
        "signal_pattern": r"strict mode violation",
        "confidence": "high",
        "root_cause": "选择器匹配到多个元素，Playwright 无法确定目标",
        "fix": "使用 .first 或 .nth(i) 精确定位，或增加更具体的过滤条件",
        "severity": "error",
    },
    {
        "id": "S003",
        "name": "超时 (Timeout 30000ms)",
        "signal_pattern": r"Timeout \d+ms exceeded",
        "confidence": "medium",
        "root_cause": "元素未在指定时间内出现在 DOM 中",
        "fix": "检查 URL 是否正确、前置操作是否完成、增加等待时间；详见 fix_detail",
        "fix_common": "检查 URL 是否正确、前置操作是否完成、增加等待时间",
        "fix_detail": [
            "get_by_placeholder 超时：输入框可能由 <label> 标记而非 placeholder，降级用 get_by_label()",
            "get_by_role(\"button\") 超时：按钮可能不是原生 button（如 <a> 标签），改用 locator 定位",
            "get_by_role(\"option\") 超时：el-select 选项无 role='option'，用 .el-select-dropdown__item",
        ],
        "severity": "error",
    },
    {
        "id": "S004",
        "name": "下拉选项无法选中 (无法点击/click不生效)",
        "signal_pattern": r"el-select|下拉|dropdown.*item|combobox",
        "confidence": "low",
        "root_cause": "el-select 的 teleport 渲染到 <body> 末尾，Playwright 可见性检查失败",
        "fix": "click(force=True) 打开下拉 → 等待 1.5s → click(force=True) 点击 .el-select-dropdown__item",
        "severity": "warning",
    },
    {
        "id": "S005",
        "name": "el-autocomplete 静默失败 (v-model 未更新)",
        "signal_pattern": r"el-autocomplete|autocomplete",
        "confidence": "medium",
        "root_cause": "键盘选择（ArrowDown+Enter）不会触发 Vue @select 事件",
        "fix": "fill 输入 → 等待 2.5s → 用 dispatchEvent('click') 点击 `.el-autocomplete__popper li` 选项",
        "severity": "error",
    },
    {
        "id": "S006",
        "name": "保存后无数据写入 (UI + DB 均为空)",
        "signal_pattern": r"保存.*无数据|保存.*失败|写入.*空",
        "confidence": "medium",
        "root_cause": "表单验证静默失败或 el-autocomplete popper overlay 遮挡",
        "fix": [
            "1. 点击保存前执行 page.keyboard.press('Escape') 关闭 popper",
            "2. 检查 .el-form-item__error 确认有验证错误",
            "3. 监听 page.on('request') 确认是否有网络请求发出",
            "4. 可靠的验证方式：DB 直查",
        ],
        "severity": "error",
    },
    {
        "id": "S007",
        "name": "保存后 URL 未变化 (无跳转)",
        "signal_pattern": r"URL|url.*未变|path.*未变",
        "confidence": "medium",
        "root_cause": "部分平台的创建表单保存后不跳转、不弹消息（平台设计如此）",
        "fix": "不要靠 URL 或消息判断保存成功；可靠的验证方式只有 DB 直查",
        "severity": "info",
    },
    {
        "id": "S008",
        "name": "DB 唯一约束冲突 (XXX 已被使用)",
        "signal_pattern": r"已被使用|唯一|duplicate|unique",
        "confidence": "high",
        "root_cause": "数据库唯一约束冲突（MAC 地址、编码等字段重复）",
        "fix": "给每次运行生成唯一值：f'00:1A:2B:{hash(name) % 65536:04x}'",
        "severity": "error",
    },
    {
        "id": "S009",
        "name": "Tab 切换后保存按钮无效",
        "signal_pattern": r"tab|切换.*保存|保存.*tab",
        "confidence": "low",
        "root_cause": "Vue SPA tab 切换导致表单组件卸载/重建，部分 v-model 绑定丢失",
        "fix": "如果目标 Tab 无内容（显示'暂无数据'），不要切换过去——直接在当前 Tab 保存即可",
        "severity": "warning",
    },
    {
        "id": "S010",
        "name": "发布状态未变更",
        "signal_pattern": r"发布.*超时|发布.*未变|published.*not|状态.*未变",
        "confidence": "high",
        "root_cause": "后端 PV 连通性检查延迟",
        "fix": "循环轮询 6 次 × 5 秒，检查行内状态列的 td 文本是否为'发布'",
        "severity": "warning",
    },
    {
        "id": "S011",
        "name": "NPE / NullPointerException",
        "signal_pattern": r"NullPointerException|Cannot invoke.*null|thingModelVersion.*null",
        "confidence": "high",
        "root_cause": "IoT 平台后端 BUG：ThingModelVersion.getId() 返回 null。可能因缺少版本记录",
        "fix": "确认前置场景已执行（创建模型→发布→版本生成）。如已确认操作无误，则报告平台 BUG",
        "severity": "error",
    },
    {
        "id": "S012",
        "name": "el-select 选项在 aria tree 中无 role='option'",
        "signal_pattern": r"get_by_role.*option|role.*option.*not found",
        "confidence": "high",
        "root_cause": "Element Plus 的 el-select 选项 DOM 没有 role='option' 属性",
        "fix": "用 locator('.el-select-dropdown__item') 替代 get_by_role('option')",
        "severity": "error",
    },
    {
        "id": "S013",
        "name": "按钮有头模式失败/无头通过",
        "signal_pattern": r"headed.*fail|headless.*pass|有头.*失败|无头.*通过",
        "confidence": "low",
        "root_cause": "有头模式渲染速度差异或浏览器焦点/窗口层级问题",
        "fix": "优先用 force=True；增加等待时间；用 page.locator 替换 get_by_role",
        "severity": "warning",
    },
    {
        "id": "S014",
        "name": "页面空白 (about:blank)",
        "signal_pattern": r"about:blank|空白页",
        "confidence": "high",
        "root_cause": "Session 过期或导航异常",
        "fix": "导航到列表页（不要重复创建），从列表页搜索继续",
        "severity": "error",
    },
]

# ── 诊断引擎 ────────────────────────────────────────────────

def load_report(report_path: str) -> Optional[dict]:
    """加载 test_results.json 报告文件"""
    path = Path(report_path)
    if not path.exists():
        print(f"[SELF_HEAL] 报告文件不存在: {report_path}")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[SELF_HEAL] JSON 解析失败: {e}")
        return None


def analyze_log(log_path: str) -> list[dict]:
    """分析运行日志，匹配故障信号"""
    path = Path(log_path)
    if not path.exists():
        print(f"[SELF_HEAL] 日志文件不存在: {log_path}")
        return []

    log_text = path.read_text(encoding="utf-8", errors="replace")
    matches = []

    for sig in FAILURE_SIGNATURES:
        try:
            if re.search(sig["signal_pattern"], log_text, re.IGNORECASE):
                matches.append({**sig, "matched_text": "日志中匹配到关键词"})
        except re.error:
            pass  # 跳过无效正则

    return matches


def analyze_report(report_data: dict) -> list[dict]:
    """分析 test_results.json，检查失败场景"""
    matches = []
    scenes = report_data.get("scenes", [])

    for scene in scenes:
        if scene.get("status") != "failed":
            continue
        scene_text = json.dumps(scene, ensure_ascii=False)

        for sig in FAILURE_SIGNATURES:
            try:
                if re.search(sig["signal_pattern"], scene_text, re.IGNORECASE):
                    matches.append({
                        **sig,
                        "matched_scene": scene.get("name", scene.get("id", "?")),
                        "matched_text": scene.get("detail", "无详情")[:200],
                    })
            except re.error:
                pass

    return matches


# ── 自动修复命令生成（--apply 模式） ────────────────────────────

AUTO_FIX_COMMANDS = {
    "S001": {
        "command": 'click(force=True)',
        "description": "将 .click() 替换为 .click(force=True) 以绕过 overlay 拦截",
    },
    "S012": {
        "command": "locator('.el-select-dropdown__item')",
        "description": "将 get_by_role('option') 替换为 locator('.el-select-dropdown__item')",
    },
    "S008": {
        "command": "f'00:1A:2B:{hash(name) % 65536:04x}'",
        "description": "使用唯一值生成代码片段避免唯一约束冲突",
    },
    "S011": {
        "command": "🤖 平台 BUG — 用例失败非自动化脚本问题",
        "description": "向 IoT 平台提交 BUG 报告，路径: 平台 BUG 报告系统",
    },
}


def render_auto_fix(matches: list[dict]):
    """输出 --apply 模式的自动修复建议"""
    print(f"\n{'='*60}")
    print(f"  📋 --apply 自动修复模式")
    print(f"{'='*60}")

    high_conf_signals = [m for m in matches if m.get("confidence") == "high"]
    if not high_conf_signals:
        print(f"\n  当前匹配信号中无高确定性（high confidence）信号，跳过自动修复。")
        return

    for m in high_conf_signals:
        sig_id = m["id"]
        cmd_info = AUTO_FIX_COMMANDS.get(sig_id)
        if cmd_info:
            print(f"\n  [AUTO-FIX] {sig_id}: {cmd_info['description']}")
            print(f"  {' ' * (12 + len(sig_id))}命令: {cmd_info['command']}")
            if m.get("matched_scene"):
                print(f"  {' ' * (12 + len(sig_id))}场景: {m['matched_scene']}")
        else:
            print(f"\n  [AUTO-FIX] {sig_id}: {m.get('fix', '未知')}")

    print(f"\n{'='*60}")


def render_report(matches: list[dict], source: str, apply: bool = False):
    """格式化输出诊断报告

    Args:
        matches: 匹配的故障信号列表
        source: 分析来源描述
        apply: 是否启用自动修复模式（对高确定性信号输出修复命令代码）
    """
    if not matches:
        print(f"\n{'='*60}")
        print(f"[SELF_HEAL] {source} — 未检测到已知故障信号 ✅")
        if apply:
            print(f"  --apply 模式已启用，但无信号需要修复。")
        print(f"{'='*60}")
        return

    print(f"\n{'='*60}")
    print(f"[SELF_HEAL] {source} — 检测到 {len(matches)} 个已知故障信号")
    print(f"{'='*60}")

    for i, m in enumerate(matches, 1):
        emoji = {"error": "🔴", "warning": "🟡", "info": "ℹ️"}.get(m.get("severity", "info"), "ℹ️")
        print(f"\n{emoji} [{i}] {m['id']}: {m['name']}")
        print(f"    severity: {m.get('severity', '?')}")
        print(f"    confidence: {m.get('confidence', '?')}")
        print(f"    root_cause: {m.get('root_cause', '?')}")
        if m.get("matched_scene"):
            print(f"    matched_scene: {m['matched_scene']}")
        if m.get("matched_text"):
            print(f"    matched_text: {m['matched_text'][:100]}")

        fix = m.get("fix")
        if isinstance(fix, list):
            for line in fix:
                print(f"    → {line}")
        elif fix:
            print(f"    → {fix}")

        if m.get("fix_detail"):
            for detail in m["fix_detail"]:
                print(f"    → {detail}")

    print(f"\n{'='*60}")

    # --apply 模式：对高确定性信号输出自动修复建议
    if apply:
        render_auto_fix(matches)


def analyze_script_file(script_path: str, platform: str = "element_ui") -> list[dict]:
    """分析测试脚本源码中的潜在问题模式

    Args:
        script_path: 脚本文件路径
        platform: 目标 UI 平台，可选 "element_ui" 或 "antd"
    """
    path = Path(script_path)
    if not path.exists():
        print(f"[SELF_HEAL] 脚本文件不存在: {script_path}")
        return []

    script_text = path.read_text(encoding="utf-8", errors="replace")
    issues = []

    # 检查：使用 get_by_role("option")
    if re.search(r'get_by_role\([\"\\\']option[\"\\\']', script_text):
        issues.append({
            "id": "L001",
            "name": "使用 get_by_role('option') — 不兼容 Element Plus",
            "severity": "error",
            "fix": "替换为 locator('.el-select-dropdown__item') 或 locator('[role=\"option\"]')（仅兼容 Ant Design）",
            "line_snippet": "get_by_role('option')",
        })

    # 检查：page.goto 用于 SPA hash URL
    goto_matches = re.findall(r'page\.goto\([\"\\\']([^\"\\\']+)[\"\\\']', script_text)
    for goto_url in goto_matches:
        if "#" in goto_url:
            issues.append({
                "id": "L002",
                "name": f"page.goto('{goto_url}') — SPA hash URL 不应使用 goto",
                "severity": "warning",
                "fix": "使用 page.evaluate(\"window.location.hash = '#{fragment}'\") 替代",
            })

    # 检查：使用 get_by_role("button") 而非 filter(has_text)
    if re.search(r'get_by_role\([\"\\\']button[\"\\\'][^)]*name=[\"\\\'](?![^\"\\\']*确认|保存|确定|发布)', script_text):
        issues.append({
            "id": "L003",
            "name": "get_by_role('button', name=...) — Ant Design 按钮文本含空格",
            "severity": "info",
            "fix": "使用 locator('button').filter(has_text='确 认') 以应对 Vben Admin 空格",
        })

    # 检查：el-cascader 点击节点文本而非 checkbox（仅 Element UI 相关）
    if platform == "element_ui" and re.search(r'get_by_role\([\"\\\']treeitem[\"\\\']', script_text):
        issues.append({
            "id": "L004",
            "name": "el-cascader 用 get_by_role('treeitem') — 应点击 checkbox 而非节点文本",
            "severity": "error",
            "fix": "使用 evaluate() 点击节点内的 .el-checkbox，点击节点文本会展开子级",
        })

    # 检查：固定 sleep 而非轮询
    if re.search(r'time\.sleep\([1-9][0-9]\)', script_text):
        issues.append({
            "id": "L005",
            "name": "长固定 sleep 可能应改为轮询",
            "severity": "info",
            "fix": "用 for+time.sleep+break 模式替代单次长 sleep，控制最大等待时间",
        })

    return issues


# ── CLI 入口 ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 4 自愈诊断引擎")
    parser.add_argument("--report", help="test_results.json 文件路径")
    parser.add_argument("--log", help="运行日志文件路径")
    parser.add_argument("--analyze-script", help="分析测试脚本源码中的潜在问题")
    parser.add_argument("--platform", default="element_ui", choices=["element_ui", "antd"],
                        help="目标 UI 平台（默认 element_ui），影响 L004 等平台相关规则")
    parser.add_argument("--list-signals", action="store_true", help="列出所有已知故障信号")
    parser.add_argument("--apply", action="store_true", help="自动修复模式：对高确定性信号输出修复命令代码")
    args = parser.parse_args()

    if args.list_signals:
        print(f"\n{'='*60}")
        print(f"  已知故障信号库 ({len(FAILURE_SIGNATURES)} 条)")
        print(f"{'='*60}")
        for sig in FAILURE_SIGNATURES:
            emoji = {"error": "🔴", "warning": "🟡", "info": "ℹ️"}.get(sig.get("severity", "info"), "ℹ️")
            print(f"  {emoji} {sig['id']:5s} [{sig['confidence']:6s}] {sig['name']}")
        print()
        return

    any_action = False

    if args.report:
        any_action = True
        data = load_report(args.report)
        if data:
            matches = analyze_report(data)
            render_report(matches, f"报告分析: {args.report}", apply=args.apply)

    if args.log:
        any_action = True
        matches = analyze_log(args.log)
        render_report(matches, f"日志分析: {args.log}", apply=args.apply)

    if args.analyze_script:
        any_action = True
        issues = analyze_script_file(args.analyze_script, platform=args.platform)
        script_path = Path(args.analyze_script)
        if issues:
            print(f"\n{'='*60}")
            print(f"[SELF_HEAL] 脚本分析: {script_path.name} — 发现 {len(issues)} 个潜在问题")
            print(f"{'='*60}")
            for i, iss in enumerate(issues, 1):
                emoji = {"error": "🔴", "warning": "🟡", "info": "ℹ️"}.get(iss.get("severity"), "ℹ️")
                print(f"\n{emoji} [{i}] {iss['name']}")
                print(f"    → {iss['fix']}")
        else:
            print(f"\n[SELF_HEAL] 脚本分析: {script_path.name} — 未发现已知问题模式 ✅")

    if not any_action:
        parser.print_help()


if __name__ == "__main__":
    main()
