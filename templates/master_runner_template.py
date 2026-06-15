#!/usr/bin/env python3
"""
设备综合管理系统 - 全量端到端测试调度器（模板）
==========================================
按依赖顺序执行多个自动化脚本，生成聚合HTML总报告。

用法:
  python master_runner.py                    # 完整执行
  python master_runner.py --headless         # 无头模式
  python master_runner.py --skip-<script>    # 跳过指定脚本

添加新脚本：
  1. 给新脚本集成 TestReport
  2. 在 SCRIPTS 数组加一条记录（id, name, file, depends_on）
  3. 运行 python master_runner.py

⚠️ 注意：本模板可能落后于实际使用的 `master_runner.py`。
最新完整版请参考项目目录下的 `master_runner.py`（含三态状态指示器、
横向数据流向展示、部分失败黄色支持等优化）。
"""
import sys, os, re, subprocess, time
from datetime import datetime

# ===== 在此添加/修改脚本列表 =====
SCRIPTS = [
    {
        "id": "e2e_full",
        "name": "设备管理",
        "file": "e2e_full.py",
        "description": "PV创建 → 元件模型(添加/发布) → 元件(PV绑定/发布) → 设备模型(添加/发布) → 设备(关联元件/发布)",
        "depends_on": [],
    },
    {
        "id": "sn_lifecycle",
        "name": "SN全生命周期",
        "file": "sn_lifecycle.py",
        "description": "新增SN → 分配SN → 设备详情验证",
        "depends_on": ["e2e_full"],
    },
]


def run_script(script_info, work_dir, python_exe, headless=False):
    """
    [中] 执行单个自动化脚本，收集输出、报告路径、场景/断言统计等结果
        - script_info : 脚本配置字典（须含 id, name, file）
        - work_dir    : 脚本所在工作目录
        - python_exe  : Python 解释器路径
        - headless    : 是否以无头模式运行
        返回包含执行结果的字典。

    [EN] Execute a single automation script and collect stdout, report path,
        scene/assertion stats.
        - script_info : script config dict (must have id, name, file)
        - work_dir    : working directory for the script
        - python_exe  : path to Python interpreter
        - headless    : run in headless mode flag
        Returns a dict with execution results.
    """
    script_path = os.path.join(work_dir, script_info["file"])
    cmd = [python_exe, "-u", script_path]
    if headless:
        cmd.append("--headless")

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir, timeout=600)
    elapsed = time.time() - start

    output = result.stdout
    if result.stderr:
        output += "\n[STDERR]\n" + result.stderr

    # 提取报告路径 / Extract report path
    report_path = None
    for line in output.split("\n"):
        m = re.search(r'📋.*报告已生成:\s*(.+)', line)
        if m:
            report_path = m.group(1).strip()

    # 提取场景统计 / Extract scene stats
    scene_stats = {"passed": 0, "failed": 0, "skipped": 0}
    for line in output.split("\n"):
        m = re.search(r'📊\s*场景:\s*通过(\d+)\s*失败(\d+)\s*跳过(\d+)', line)
        if m:
            scene_stats = {"passed": int(m.group(1)), "failed": int(m.group(2)), "skipped": int(m.group(3))}

    # 提取断言统计 / Extract assertion stats
    assert_stats = {"passed": 0, "failed": 0}
    for line in output.split("\n"):
        m = re.search(r'📊\s*断言:\s*通过(\d+)\s*失败(\d+)', line)
        if m:
            assert_stats = {"passed": int(m.group(1)), "failed": int(m.group(2))}

    return {
        "script_id": script_info["id"],
        "name": script_info["name"],
        "description": script_info["description"],
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "elapsed": elapsed,
        "report_path": report_path,
        "scene_stats": scene_stats,
        "assert_stats": assert_stats,
        "output_lines": output.split("\n"),
    }


def generate_master_report(results, work_dir, headless=False):
    """
    [中] 根据所有脚本执行结果生成聚合 HTML 总报告
        - results  : run_script 返回的结果字典列表
        - work_dir : 输出报告的目标目录
        - headless : 无头模式标记（当前仅用于接口一致性）
        返回生成的 HTML 文件绝对路径。

    [EN] Generate an aggregated HTML master report from all script results.
        - results  : list of result dicts from run_script()
        - work_dir : target directory for the report file
        - headless : headless flag (kept for interface consistency)
        Returns absolute path to the generated HTML file.
    """
    total_elapsed = sum(r["elapsed"] for r in results)

    total_scripts = len(results)
    passed_scripts = sum(1 for r in results if r["success"])
    total_scene_pass = sum(r["scene_stats"]["passed"] for r in results)
    total_scene_fail = sum(r["scene_stats"]["failed"] for r in results)
    total_assert_pass = sum(r["assert_stats"]["passed"] for r in results)
    total_assert_fail = sum(r["assert_stats"]["failed"] for r in results)

    scripts_cards = ""
    for i, r in enumerate(results):
        status_icon = "✅" if r["success"] else "❌"
        card_class = "passed" if r["success"] else "failed"
        elapsed_str = f"{r['elapsed']:.0f}秒"
        report_link = (f'<a href="{os.path.relpath(r["report_path"], work_dir)}" target="_blank" '
                       f'class="report-link">📄 查看详细报告</a>') if r["report_path"] else ""

        key_lines = [l for l in r["output_lines"]
                     if any(kw in l for kw in ["📊", "✅ 场景", "❌ 场景", "▶ 场景", "HTML报告", "断言统计"])]
        log_html = "<div class='log-block'>" + "".join(
            f"<div class='log-line log-{'ok' if '✅' in l else 'err' if '❌' in l else 'info'}'>{l}</div>"
            for l in (key_lines or r["output_lines"][-15:])
        ) + "</div>"

        badges = f'''<span class="badge badge-pass">✅ 场景通过 {r["scene_stats"]["passed"]}</span>'''
        if r["scene_stats"]["failed"] > 0:
            badges += f'<span class="badge badge-fail">❌ 场景失败 {r["scene_stats"]["failed"]}</span>'
        if r["scene_stats"]["skipped"] > 0:
            badges += f'<span class="badge badge-skip">⏭️ 跳过 {r["scene_stats"]["skipped"]}</span>'
        badges += f'''<span class="badge badge-assert">✅ 断言 {r["assert_stats"]["passed"]}/{r["assert_stats"]["passed"]+r["assert_stats"]["failed"]}</span>
            <span class="badge badge-time">⏱️ {elapsed_str}</span>'''

        scripts_cards += f'''<div class="script-card {card_class}">
            <div class="script-header" onclick="this.classList.toggle('active');this.nextElementSibling.classList.toggle('active')">
                <span class="script-num">#{i+1}</span>
                <span class="script-status">{status_icon}</span>
                <span class="script-name">{r["name"]}</span>
                <span class="script-meta">{r["scene_stats"]["passed"]}场景通过 | {badges} {report_link}</span>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="script-body">
                <div class="script-desc">{r["description"]}</div>
                <div class="scene-badges">{badges}</div>
                {log_html}
            </div>
        </div>'''

    dep_html = ""
    for i, r in enumerate(results):
        dep_html += f"<div class='dep-node dep-{'pass' if r['success'] else 'fail'}'>{r['name']}</div>"
        if i < len(results) - 1:
            dep_html += "<div class='dep-arrow'>⬇ 依赖</div>"

    total_pct = round(total_assert_pass / (total_assert_pass + total_assert_fail) * 100) if (total_assert_pass + total_assert_fail) > 0 else 100
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>全量端到端测试报告</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
.container{{max-width:1200px;margin:0 auto}}
.report-title{{font-size:28px;font-weight:700;color:#f0f6fc;margin-bottom:4px}}
.report-time{{color:#484f58;font-size:13px;margin-bottom:24px}}
.summary-banner{{background:linear-gradient(135deg,#161b22,#0d1117);border:1px solid #30363d;border-radius:12px;padding:28px;display:flex;align-items:center;gap:36px;flex-wrap:wrap;margin-bottom:24px}}
.summary-stat{{text-align:center;min-width:60px}}
.summary-stat .num{{font-size:34px;font-weight:700}}
.summary-stat .label{{font-size:12px;color:#8b949e;margin-top:2px}}
.stat-scene .num{{color:#3fb950}}
.stat-fail .num{{color:#f85149}}
.stat-assert .num{{color:#58a6ff}}
.stat-script .num{{color:#bc8cff}}
.stat-time .num{{color:#d29922;font-size:24px}}
.progress-area{{flex:1;min-width:200px}}
.progress-track{{height:10px;background:#21262d;border-radius:5px;overflow:hidden;display:flex}}
.progress-pass{{background:#3fb950}}
.progress-fail{{background:#f85149}}
.progress-labels{{display:flex;justify-content:space-between;font-size:12px;color:#8b949e;margin-top:4px}}
.dep-chain{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px;display:flex;align-items:center;gap:12px;justify-content:center;flex-wrap:wrap}}
.dep-node{{padding:8px 20px;border-radius:6px;font-weight:600;font-size:14px}}
.dep-pass{{background:#0d4429;color:#3fb950;border:1px solid #3fb95044}}
.dep-fail{{background:#3d1416;color:#f85149;border:1px solid #f8514944}}
.dep-arrow{{color:#484f58;font-size:20px}}
.script-card{{background:#161b22;border:1px solid #30363d;border-radius:8px;margin-bottom:12px;overflow:hidden}}
.script-card.failed{{border-color:#f8514966}}
.script-header{{display:flex;align-items:center;gap:12px;padding:14px 18px;cursor:pointer;user-select:none;flex-wrap:wrap}}
.script-header:hover{{background:#1c2128}}
.script-num{{color:#484f58;font-weight:700;font-size:13px}}
.script-status{{font-size:20px}}
.script-name{{font-weight:600;color:#f0f6fc}}
.script-meta{{color:#8b949e;font-size:13px;margin-left:auto;display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.report-link{{color:#58a6ff;text-decoration:none;font-size:13px;padding:3px 10px;border:1px solid #58a6ff44;border-radius:4px}}
.toggle-icon{{color:#8b949e;font-size:12px;transition:transform .2s}}
.script-header.active .toggle-icon{{transform:rotate(180deg)}}
.script-body{{display:none;padding:0 18px 18px}}
.script-body.active{{display:block}}
.script-desc{{color:#8b949e;font-size:13px;margin-bottom:12px;padding:8px 12px;background:#0d1117;border-radius:6px}}
.scene-badges{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
.badge{{padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600}}
.badge-pass{{background:#0d442944;color:#3fb950}}
.badge-fail{{background:#3d141644;color:#f85149}}
.badge-skip{{background:#3d2e0044;color:#d29922}}
.badge-assert{{background:#0d1117;color:#58a6ff;border:1px solid #58a6ff22}}
.badge-time{{background:#0d1117;color:#d29922;border:1px solid #d2992222}}
.log-block{{background:#0d1117;border-radius:6px;padding:8px 12px;max-height:300px;overflow-y:auto;font-family:monospace;font-size:12px}}
.log-line{{padding:2px 0;line-height:1.6}}
.log-ok{{color:#3fb950}}
.log-err{{color:#f85149}}
.log-info{{color:#8b949e}}
.footer{{text-align:center;color:#484f58;font-size:12px;margin-top:40px;padding:20px}}
</style></head><body>
<div class="container">
<div class="report-title">设备综合管理系统 — 全量端到端测试报告</div>
<div class="report-time">执行时间: {ts} | 总耗时: {total_elapsed:.0f}秒</div>
<div class="summary-banner">
<div class="summary-stat stat-scene"><div class="num">{total_scene_pass}</div><div class="label">场景通过</div></div>
<div class="summary-stat stat-fail"><div class="num">{total_scene_fail}</div><div class="label">场景失败</div></div>
<div class="summary-stat stat-assert"><div class="num">{total_assert_pass}/{total_assert_pass+total_assert_fail}</div><div class="label">断言通过</div></div>
<div class="summary-stat stat-script"><div class="num">{passed_scripts}/{total_scripts}</div><div class="label">脚本通过</div></div>
<div class="summary-stat stat-time"><div class="num">{total_elapsed:.0f}s</div><div class="label">总耗时</div></div>
<div class="progress-area"><div class="progress-track">{"".join(f'<div class="progress-pass" style="flex:{r["scene_stats"]["passed"] or 0.5}"></div>' + f'<div class="progress-fail" style="flex:{r["scene_stats"]["failed"] or 0.1}"></div>' for r in results)}</div>
<div class="progress-labels"><span>通过率 {total_pct}%</span><span>{total_scene_pass+total_scene_fail} 场景 | {total_scripts} 脚本</span></div>
</div></div>
<div class="dep-chain">{dep_html}</div>
<h3 style="color:#8b949e;margin-bottom:12px;font-size:16px;">📋 脚本执行详情</h3>
{scripts_cards}
<div class="footer">由 Hermes Agent 自动生成</div>
</div>
<script>
document.querySelectorAll('.script-card.failed .script-header').forEach(function(h){{ h.click(); }});
</script>
</body></html>'''

    ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    master_path = os.path.join(work_dir, f"全量测试报告_{ts_file}.html")
    with open(master_path, "w", encoding="utf-8") as f:
        f.write(html)
    return master_path


def main():
    """
    [中] 主入口：解析命令行参数，按依赖链调度所有脚本，聚合生成报告
        工作目录和 Python 解释器路径在此确定，避免模块级硬编码。

    [EN] Main entry: parse CLI arguments, schedule all scripts by dependency
        chain, aggregate results, and generate the master report.
        Work directory and Python interpreter path are determined here to
        avoid module-level hard-coded values.
    """
    import argparse
    parser = argparse.ArgumentParser(description="全量端到端测试调度器")
    parser.add_argument("--headless", action="store_true", help="无头模式执行")
    args = parser.parse_args()

    work_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable

    # 数据清理（可选）：删除过期报告 / Optional data cleanup: remove stale reports
    # FIXME: [待实现] 可在此处添加清理逻辑，例如:
    #   cleanup_old_reports(work_dir, prefix="全量测试报告_", max_age_days=7)
    #   需要数据库连接时，可传入 db_url = os.environ.get("DB_URL", "sqlite:///default.db")

    results = []
    for script_info in SCRIPTS:
        # 检查依赖 / Check dependencies
        for dep_id in script_info["depends_on"]:
            dep = next((r for r in results if r["script_id"] == dep_id), None)
            if dep and not dep["success"]:
                print(f"❌ 依赖 '{dep_id}' 失败，跳过 '{script_info['id']}'")
                results.append({
                    "script_id": script_info["id"], "name": script_info["name"],
                    "description": script_info["description"], "success": False,
                    "returncode": -1, "elapsed": 0, "report_path": None,
                    "scene_stats": {"passed": 0, "failed": 0, "skipped": 0},
                    "assert_stats": {"passed": 0, "failed": 0},
                    "output_lines": ["[跳过] 依赖未通过"],
                })
                continue

        print(f"\n▶ 开始执行: {script_info['name']}")
        result = run_script(script_info, work_dir, python_exe, headless=args.headless)
        results.append(result)
        print(f"  {'✅' if result['success'] else '❌'} {result['name']}: "
              f"{result['scene_stats']['passed']}场景通过, {result['elapsed']:.0f}秒")

    master_path = generate_master_report(results, work_dir, headless=args.headless)
    print(f"\n📋 总报告: {master_path}")
    for r in results:
        if r["report_path"]:
            print(f"   ├─ {r['name']}: {r['report_path']}")


if __name__ == "__main__":
    main()
