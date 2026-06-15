#!/usr/bin/env python3
"""
核心运行器 - 按依赖顺序执行多个自动化脚本，生成聚合HTML总报告。

从 master_runner.py 重构而来，适配新目录结构：
  - SCRIPTS 从 config 导入（平台路由器自动选择当前平台）
  - 脚本路径基于 SCRIPTS_DIR
  - 新增 list_scripts() 函数

用法:
  python -m core.runner                   # 完整执行
  python core/runner.py                    # 完整执行
  python core/runner.py --headless         # 无头模式
  python core/runner.py --exclude sn_lifecycle  # 排除指定脚本
  python core/runner.py --only device_management  # 仅执行指定脚本
  python core/runner.py --list             # 列出可用脚本
"""

import sys
import os

# ── 将项目根目录加入 sys.path，以便导入根目录的 config 模块 ──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import re
import subprocess
import time
from datetime import datetime

# 通过根 config.py（平台路由器）获取当前平台的配置
from config import SCRIPTS, SCRIPTS_DIR, REPORT_DIR, cleanup_old_reports, ATOMIC_SCRIPTS, ATOMIC_SCRIPTS_DIR, PLATFORM_NAME

PYTHON = sys.executable


def list_scripts(script_list=None):
    """列出当前平台所有可用的测试脚本"""
    scripts = script_list or SCRIPTS
    print(f"\n{'='*60}")
    print(f"  当前平台测试脚本列表")
    print(f"  {'='*60}")
    print(f"  脚本目录: {SCRIPTS_DIR}")
    print(f"  脚本数量: {len(scripts)}")
    print()
    for i, s in enumerate(scripts, 1):
        deps = ", ".join(s.get("depends_on", [])) or "无"
        print(f"  {i}. [{s['id']}] {s['name']}")
        print(f"     文件: {s['file']}")
        print(f"     说明: {s['description']}")
        print(f"     依赖: {deps}")
        print()
    return scripts


def resolve_script_path(file):
    """从 E2E 或原子目录中查找脚本文件"""
    e2e_path = os.path.join(SCRIPTS_DIR, file)
    if os.path.isfile(e2e_path):
        return e2e_path, "e2e"
    atomic_path = os.path.join(ATOMIC_SCRIPTS_DIR, file)
    if os.path.isfile(atomic_path):
        return atomic_path, "atomic"
    raise FileNotFoundError(f"脚本文件未找到: {file} (搜索目录: {SCRIPTS_DIR}, {ATOMIC_SCRIPTS_DIR})")


def run_script(script_info, headless=False):
    """执行单个测试脚本，返回执行结果"""
    script_path, script_type = resolve_script_path(script_info["file"])
    # 原子脚本运行时添加 --headless 参数（如果支持）
    cmd = [PYTHON, "-u", script_path]
    if headless:
        cmd.append("--headless")

    print(f"\n{'='*60}")
    print(f"  开始执行: {script_info['name']}")
    print(f"  {'='*60}")
    print(f"  命令: {' '.join(cmd)}")
    print()

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=_PROJECT_ROOT, timeout=600)
    elapsed = time.time() - start

    # 合并输出
    output = result.stdout
    if result.stderr:
        output += "\n[STDERR]\n" + result.stderr

    # 提取报告路径，转为相对于 REPORT_DIR 的路径
    report_path = None
    for line in output.split("\n"):
        m = re.search(r'📋\s*(?:测试报告|报告已生成|报告):\s*(.+)', line)
        if m:
            report_path = m.group(1).strip()
            # 转为相对路径（相对于 REPORT_DIR），便于聚合报告链接
            if report_path and REPORT_DIR:
                try:
                    report_path = os.path.relpath(report_path, REPORT_DIR)
                except ValueError:
                    pass  # 跨驱动器路径（如 D: 到 C:），保持原样

    # 提取场景统计（兼容多种格式）
    scene_stats = {"passed": 0, "failed": 0, "skipped": 0}
    for line in output.split("\n"):
        # 格式1: 📊 场景: 通过9 失败0 跳过0
        m = re.search(r'📊\s*场景:\s*通过(\d+)\s*失败(\d+)\s*跳过(\d+)', line)
        if m:
            scene_stats = {"passed": int(m.group(1)), "failed": int(m.group(2)), "skipped": int(m.group(3))}
        # 格式2: 📊 场景: 通过9 失败0 总计6 (原子脚本，无跳过项)
        m2 = re.search(r'📊\s*场景:\s*通过(\d+)\s*失败(\d+)\s*总计(\d+)', line)
        if m2:
            passed = int(m2.group(1))
            failed = int(m2.group(2))
            total = int(m2.group(3))
            scene_stats = {"passed": passed, "failed": failed, "skipped": total - passed - failed}
        # 格式3: 总计: 9  通过: 9  跳过: 0  失败: 0  (无 📊 前缀)
        m3 = re.search(r'总计:\s*(\d+)\s*通过:\s*(\d+)\s*跳过:\s*(\d+)\s*失败:\s*(\d+)', line)
        if m3:
            scene_stats = {"passed": int(m3.group(2)), "failed": int(m3.group(4)), "skipped": int(m3.group(3))}

    # 提取断言统计
    assert_stats = {"passed": 0, "failed": 0}
    for line in output.split("\n"):
        m = re.search(r'📊\s*断言:\s*通过(\d+)\s*失败(\d+)', line)
        if m:
            assert_stats = {"passed": int(m.group(1)), "failed": int(m.group(2))}
        # 兼容格式: 25/26 断言通过 或 断言通过: 25/26
        m2 = re.search(r'(\d+)/(\d+)\s*断言通过', line)
        if m2:
            assert_stats = {"passed": int(m2.group(1)), "failed": int(m2.group(2)) - int(m2.group(1))}

    success = result.returncode == 0

    return {
        "script_id": script_info["id"],
        "name": script_info["name"],
        "description": script_info["description"],
        "success": success,
        "returncode": result.returncode,
        "elapsed": elapsed,
        "report_path": report_path,
        "scene_stats": scene_stats,
        "assert_stats": assert_stats,
        "output_lines": output.split("\n"),
        "full_output": output,
    }


def generate_master_report(e2e_results, atomic_results, headless=False):
    """生成聚合总报告HTML，分两个模块展示"""
    total_elapsed = sum(r["elapsed"] for r in e2e_results + atomic_results)

    # 统计
    all_results = e2e_results + atomic_results
    total_scripts = len(all_results)
    passed_scripts = sum(1 for r in all_results if r["success"])
    failed_scripts = sum(1 for r in all_results if not r["success"])
    total_scenes = sum(r["scene_stats"]["passed"] + r["scene_stats"]["failed"] + r["scene_stats"]["skipped"] for r in all_results)
    total_scene_pass = sum(r["scene_stats"]["passed"] for r in all_results)
    total_scene_fail = sum(r["scene_stats"]["failed"] for r in all_results)
    total_assert_pass = sum(r["assert_stats"]["passed"] for r in all_results)
    total_assert_fail = sum(r["assert_stats"]["failed"] for r in all_results)

    # 总体状态（新设计用 ✓/✕/⚠ 替代 emoji）
    if total_scene_fail == 0 and total_scene_pass > 0:
        overall_icon, overall_text, overall_class = "✓", "全部通过", "overall-pass"
    elif total_scene_pass == 0 and total_scene_fail > 0:
        overall_icon, overall_text, overall_class = "✕", "全部失败", "overall-fail"
    elif total_scene_fail > 0:
        overall_icon, overall_text, overall_class = "⚠", "部分失败", "overall-partial"
    else:
        overall_icon, overall_text, overall_class = "⏭", "全部跳过", "overall-skip"
    total_pct = round(total_assert_pass / (total_assert_pass + total_assert_fail) * 100) if (total_assert_pass + total_assert_fail) > 0 else 100

    def _elapsed_str(s):
        return f"{s:.0f}秒" if s < 60 else f"{s / 60:.1f}分"

    def _log_class(line):
        # 汇总/统计行用中性色（含"失败"但不代表真的失败）
        if any(kw in line for kw in ["总计", "∑", "📊", "断言:"]):
            return "log-info"
        if "❌" in line or "失败" in line or "⚠" in line:
            return "log-err"
        if "✅" in line or "✓" in line or "通过" in line:
            return "log-ok"
        return "log-info"

    def _ts_icon(line):
        if "▶" in line or "场景" in line[:4]:
            return "▶"
        if "✅" in line or "✓" in line:
            return "✓"
        if "∑" in line or "📊" in line or "总计" in line:
            return "∑"
        if "⚠" in line or "❌" in line:
            return "⚠"
        return "·"

    def build_script_cards(results):
        cards = ""
        for i, r in enumerate(results):
            sc_pass = r["scene_stats"]["passed"]
            sc_fail = r["scene_stats"]["failed"]
            sc_skip = r["scene_stats"]["skipped"]
            card_class = "passed" if (sc_fail == 0 and sc_pass > 0) else ("failed" if sc_pass == 0 and sc_fail > 0 else ("partial" if sc_fail > 0 else "skipped"))
            dot_class = "pass" if card_class == "passed" else "fail"
            elapsed_disp = _elapsed_str(r["elapsed"])
            assert_total = r["assert_stats"]["passed"] + r["assert_stats"]["failed"]

            # 提取关键日志行
            key_lines = []
            for line in r["output_lines"]:
                if any(kw in line for kw in ["📊", "✅ 场景", "❌ 场景", "▶ 场景", "✓场景", "∑", "通过:", "失败:", "场景1", "场景2", "场景3", "场景4", "场景5", "场景6", "场景7", "场景8", "场景9", "总计:", "Healing"]):
                    key_lines.append(line)
            if not key_lines:
                key_lines = r["output_lines"][-15:]

            log_html = "<div class='log-block'>"
            for l in key_lines:
                icon = _ts_icon(l)
                cls = _log_class(l)
                # 清理行首的 emoji 和时间戳
                display = l.strip()
                log_html += f'<div class="log-line {cls}"><span class="ts">{icon}</span>{display}</div>'
            log_html += "</div>"

            report_link = ""
            if r["report_path"]:
                report_link = f'<a href="{r["report_path"]}" class="script-link" onclick="openModal(this.href,this.closest(\'.script-card\').querySelector(\'.script-name\').textContent);return false">详细报告 →</a>'

            cards += f'''<div class="script-card">
            <div class="script-header" onclick="toggleScript(this)">
                <span class="script-idx">#{i + 1}</span>
                <span class="script-dot {dot_class}"></span>
                <span class="script-name">{r["name"]}</span>
                <span class="script-tags">
                    <span class="tag">{sc_pass} 场景</span>
                    <span class="tag">{assert_total} 断言</span>
                    <span class="tag">{elapsed_disp}</span>
                </span>
                <span class="script-actions">
                    {report_link}
                    <span class="script-chevron">▼</span>
                </span>
            </div>
            <div class="script-body">
                <div>
                    <div class="script-body-inner">
                        <div class="script-desc">{r["description"]}</div>
                        <div class="badge-strip">
                            <span class="badge badge-pass">✓ {sc_pass} 场景通过</span>
                            {'<span class="badge badge-fail">✕ 场景失败 ' + str(sc_fail) + '</span>' if sc_fail > 0 else ''}
                            <span class="badge badge-assert">✓ 断言 {r["assert_stats"]["passed"]}/{assert_total}</span>
                            <span class="badge badge-time">⏱ {elapsed_disp}</span>
                        </div>
                        {log_html}
                    </div>
                </div>
            </div>
        </div>'''
        return cards

    def build_dep_flow(results):
        """构建数据依赖流"""
        if not results:
            return ""
        dep_html = "<div class='flowline'>"
        for i, r in enumerate(results):
            sc_pass = r["scene_stats"]["passed"]
            sc_fail = r["scene_stats"]["failed"]
            dep_cls = "pass" if (sc_fail == 0 and sc_pass > 0) else ("fail" if sc_pass == 0 and sc_fail > 0 else "partial")
            dep_html += f"<span class='flow-node {dep_cls}'>{r['name']}</span>"
            if i < len(results) - 1:
                dep_html += "<span class='flow-arr'>→</span>"
        dep_html += "<span class='flow-label'>数据流向</span></div>"
        return dep_html

    # 构建模块
    e2e_cards = build_script_cards(e2e_results)
    atomic_cards = build_script_cards(atomic_results)
    e2e_dep = build_dep_flow(e2e_results)
    atomic_dep = ""

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    e2e_pass = sum(r["scene_stats"]["passed"] for r in e2e_results)
    e2e_fail = sum(r["scene_stats"]["failed"] for r in e2e_results)
    atomic_pass = sum(r["scene_stats"]["passed"] for r in atomic_results)
    atomic_fail = sum(r["scene_stats"]["failed"] for r in atomic_results)

    total_min = total_elapsed / 60

    # 环形图参数
    ring_circumference = 440  # 2 * π * 70 ≈ 440
    ring_offset = ring_circumference - (ring_circumference * total_pct / 100)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{PLATFORM_NAME} · 任务控制报告</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Inter:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#05070a;--surface:#0b0e14;--surface2:#11161f;--border:rgba(255,255,255,0.06);--text:#eef1f5;--text2:rgba(238,241,245,0.78);--text3:rgba(238,241,245,0.42);--cyan:#36f0f0;--green:#70e59a;--magenta:#ff4d85;--amber:#f0b34b;--blue:#5b8def;--purple:#a67cff}}
html,body{{height:100%}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;overflow-x:hidden}}
#nebula{{position:fixed;inset:0;z-index:0;pointer-events:none}}
.grid-overlay{{position:fixed;inset:0;background-image:linear-gradient(rgba(54,240,240,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(54,240,240,0.03) 1px,transparent 1px);background-size:80px 80px;z-index:0;pointer-events:none}}
.container{{position:relative;z-index:1;max-width:1340px;margin:0 auto;padding:40px 28px 60px}}
.top-bar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:60px;opacity:0;animation:fadeIn 1s ease 0.2s forwards}}
.brand{{display:flex;align-items:center;gap:14px}}
.logo-mark{{width:36px;height:36px;border:2px solid var(--cyan);border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'DM Mono',monospace;font-size:14px;font-weight:500;color:var(--cyan);box-shadow:0 0 30px rgba(54,240,240,0.08)}}
.brand-text{{font-size:13px;font-weight:400;letter-spacing:3px;text-transform:uppercase;color:var(--text2)}}
.brand-text strong{{color:var(--cyan);font-weight:500}}
.top-meta{{font-family:'DM Mono',monospace;font-size:12px;color:var(--text2);letter-spacing:1px;line-height:2;padding:14px 22px;background:var(--surface);border:1px solid var(--border);border-radius:10px;min-width:220px}}
.top-meta .row{{display:flex;gap:16px}}
.top-meta .row .k{{color:var(--text3);min-width:64px;text-align:right}}
.top-meta .row .v{{color:var(--text)}}
hero{{display:block;margin-bottom:56px;opacity:0;animation:fadeIn 1s ease 0.4s forwards}}
.hero__title{{font-size:clamp(48px,8vw,92px);font-weight:900;line-height:1;letter-spacing:-2px;color:var(--text)}}
.hero__title em{{font-style:normal;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero__sub{{display:flex;gap:32px;flex-wrap:wrap;margin-top:16px;font-size:14px;color:var(--text2);font-weight:300;letter-spacing:0.5px}}
.hero__sub span{{display:flex;align-items:center;gap:8px}}
.hero__sub .dot{{width:5px;height:5px;border-radius:50%;display:inline-block}}
.dot-cyan{{background:var(--cyan);box-shadow:0 0 8px var(--cyan)}}
.dot-green{{background:var(--green);box-shadow:0 0 8px var(--green)}}
.dot-amber{{background:var(--amber);box-shadow:0 0 8px var(--amber)}}
dash-grid{{display:grid;grid-template-columns:280px 1fr;gap:24px;margin-bottom:48px}}
.status-ring-panel{{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:28px 24px;display:flex;flex-direction:column;align-items:center;position:relative;overflow:hidden;opacity:0;animation:fadeIn 1s ease 0.6s forwards}}
.status-ring-panel::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--cyan),transparent)}}
.ring-wrapper{{position:relative;width:160px;height:160px;margin-bottom:16px}}
.ring-wrapper svg{{transform:rotate(-90deg)}}
.ring-bg{{fill:none;stroke:rgba(255,255,255,0.04);stroke-width:6}}
.ring-fg{{fill:none;stroke:var(--green);stroke-width:6;stroke-linecap:round;stroke-dasharray:440;filter:drop-shadow(0 0 12px rgba(112,229,154,0.2))}}
.ring-center{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}}
.ring-center .big-num{{font-family:'DM Mono',monospace;font-size:44px;font-weight:500;color:var(--green);line-height:1}}
.ring-center .big-label{{font-size:11px;color:var(--text3);letter-spacing:2px;text-transform:uppercase;margin-top:4px}}
.status-ring-panel .status-text{{font-size:15px;font-weight:600;color:var(--green);letter-spacing:1px}}
.status-ring-panel .status-sub{{font-size:12px;color:var(--text3);margin-top:4px;font-family:'DM Mono',monospace}}
.metrics-panel{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;opacity:0;animation:fadeIn 1s ease 0.7s forwards}}
.metric-card{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px 22px;position:relative;overflow:hidden;transition:all 0.35s cubic-bezier(0.22,1,0.36,1)}}
.metric-card:hover{{border-color:rgba(255,255,255,0.08);transform:translateY(-3px)}}
.metric-card::after{{content:'';position:absolute;top:0;left:0;right:0;height:2px;opacity:0;transition:opacity 0.35s ease}}
.metric-card:hover::after{{opacity:1}}
.metric-card.green::after{{background:linear-gradient(90deg,transparent,var(--green),transparent)}}
.metric-card.cyan::after{{background:linear-gradient(90deg,transparent,var(--cyan),transparent)}}
.metric-card.magenta::after{{background:linear-gradient(90deg,transparent,var(--magenta),transparent)}}
.metric-card.purple::after{{background:linear-gradient(90deg,transparent,var(--purple),transparent)}}
.metric-card.amber::after{{background:linear-gradient(90deg,transparent,var(--amber),transparent)}}
.metric-card .label{{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:2px;font-family:'DM Mono',monospace;margin-bottom:8px}}
.metric-card .value{{font-size:36px;font-weight:700;line-height:1;letter-spacing:-1px}}
.metric-card .sub{{font-size:12px;color:var(--text2);margin-top:6px;font-weight:300}}
.metric-card.green .value{{color:var(--green)}}
.metric-card.cyan .value{{color:var(--cyan)}}
.metric-card.magenta .value{{color:var(--magenta)}}
.metric-card.purple .value{{color:var(--purple)}}
.metric-card.amber .value{{color:var(--amber)}}
.metric-card.big{{grid-column:span 2}}
.metric-card.big .value{{font-size:48px}}
.progress-strip{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px 24px;margin-bottom:48px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;opacity:0;animation:fadeIn 1s ease 0.8s forwards}}
.progress-strip .p-label{{font-family:'DM Mono',monospace;font-size:11px;color:var(--text3);letter-spacing:2px;text-transform:uppercase;white-space:nowrap}}
.progress-strip .p-track{{flex:1;min-width:120px;height:28px;background:rgba(255,255,255,0.02);border-radius:14px;overflow:hidden;position:relative;border:1px solid rgba(255,255,255,0.03)}}
.progress-strip .p-fill{{height:100%;border-radius:14px;background:linear-gradient(90deg,var(--green),#90f0b8);transition:width 1.5s cubic-bezier(0.22,1,0.36,1);position:relative}}
.progress-strip .p-fill::after{{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.15),transparent);animation:shimmer 2.5s ease-in-out infinite}}
.progress-strip .p-info{{font-family:'DM Mono',monospace;font-size:13px;color:var(--text2);white-space:nowrap}}
@keyframes shimmer{{0%{{transform:translateX(-100%)}}100%{{transform:translateX(100%)}}}}
.section-head{{display:flex;align-items:center;gap:16px;margin-bottom:6px;opacity:0;animation:fadeIn 1s ease forwards}}
.section-head .num{{font-family:'DM Mono',monospace;font-size:13px;font-weight:400;color:var(--text3);letter-spacing:2px}}
.section-head h2{{font-size:32px;font-weight:700;letter-spacing:-0.5px}}
.section-head .accent{{width:40px;height:3px;border-radius:2px;margin-left:auto}}
.section-head .accent.cyan{{background:var(--cyan)}}
.section-head .accent.purple{{background:var(--purple)}}
.section-head.cyan h2{{color:var(--cyan)}}
.section-head.purple h2{{color:var(--purple)}}
.section-sub{{font-size:14px;color:var(--text3);margin-bottom:28px;padding-left:58px;font-family:'DM Mono',monospace;opacity:0;animation:fadeIn 1s ease 0.1s forwards}}
.module-box{{border:1px solid var(--border);border-radius:20px;padding:28px 24px 20px;margin-bottom:44px;position:relative;opacity:0;animation:fadeIn 1s ease 0.1s forwards}}
.module-box.cyan{{background:linear-gradient(135deg,rgba(54,240,240,0.02),transparent 60%);border-color:rgba(54,240,240,0.06)}}
.module-box.purple{{background:linear-gradient(135deg,rgba(166,124,255,0.02),transparent 60%);border-color:rgba(166,124,255,0.06)}}
.module-box .box-label{{position:absolute;top:-14px;left:28px;padding:0 16px;font-family:'DM Mono',monospace;font-size:15px;font-weight:600;letter-spacing:4px;text-transform:uppercase;background:var(--bg)}}
.module-box.cyan .box-label{{color:var(--cyan)}}
.module-box.purple .box-label{{color:var(--purple)}}
.flowline{{display:flex;align-items:center;gap:8px;padding:12px 20px;margin-bottom:24px;flex-wrap:nowrap;opacity:0;animation:fadeIn 1s ease 0.15s forwards}}
.flow-node{{padding:8px 16px;border-radius:6px;font-family:'DM Mono',monospace;font-size:12px;font-weight:400;white-space:nowrap;border:1px solid transparent;letter-spacing:0.5px;transition:all 0.3s ease}}
.flow-node.pass{{background:rgba(112,229,154,0.04);border-color:rgba(112,229,154,0.1);color:var(--green)}}
.flow-node.fail{{background:rgba(255,77,133,0.04);border-color:rgba(255,77,133,0.1);color:var(--magenta)}}
.flow-node.partial{{background:rgba(240,179,75,0.04);border-color:rgba(240,179,75,0.1);color:var(--amber)}}
.flow-node:hover{{background:rgba(112,229,154,0.08);transform:translateY(-2px);box-shadow:0 4px 24px rgba(0,0,0,0.3)}}
.flow-arr{{color:var(--text3);font-size:18px;font-weight:300;font-family:'DM Mono',monospace;animation:flowPulse 2.4s ease-in-out infinite}}
@keyframes flowPulse{{0%,100%{{opacity:0.25}}50%{{opacity:0.7}}}}
.flow-label{{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--text3);padding:2px 10px;border:1px dashed rgba(255,255,255,0.06);border-radius:3px;margin-left:8px}}
.script-card{{background:var(--surface);border:1px solid var(--border);border-radius:16px;margin-bottom:12px;overflow:hidden;transition:all 0.4s cubic-bezier(0.22,1,0.36,1);opacity:0;animation:cardIn 0.7s cubic-bezier(0.22,1,0.36,1) forwards}}
.script-card:hover{{border-color:rgba(255,255,255,0.06);box-shadow:0 8px 48px rgba(0,0,0,0.2)}}
.script-header{{display:flex;align-items:center;gap:16px;padding:18px 24px 18px 28px;cursor:pointer;user-select:none;transition:background 0.25s ease;flex-wrap:wrap}}
.script-header:hover{{background:rgba(255,255,255,0.008)}}
.script-idx{{font-family:'DM Mono',monospace;font-size:12px;color:var(--text3);font-weight:400;min-width:32px}}
.script-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.script-dot.pass{{background:var(--green);box-shadow:0 0 12px rgba(112,229,154,0.2)}}
.script-dot.fail{{background:var(--magenta);box-shadow:0 0 12px rgba(255,77,133,0.2)}}
.script-name{{font-weight:600;font-size:15px;color:var(--text);letter-spacing:0.2px}}
.script-tags{{display:flex;gap:10px;flex-wrap:wrap;font-family:'DM Mono',monospace;font-size:11px;color:var(--text2)}}
.script-tags .tag{{padding:2px 8px;border-radius:4px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.03)}}
.script-actions{{margin-left:auto;display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.script-link{{font-family:'DM Mono',monospace;font-size:12px;font-weight:500;color:var(--cyan);text-decoration:none;padding:5px 16px;border:1px solid rgba(54,240,240,0.15);border-radius:6px;transition:all 0.3s ease;letter-spacing:0.5px}}
.script-link:hover{{border-color:rgba(54,240,240,0.4);color:var(--cyan);background:rgba(54,240,240,0.06);box-shadow:0 0 24px rgba(54,240,240,0.06)}}
.script-chevron{{color:var(--text3);font-size:12px;transition:transform 0.5s cubic-bezier(0.22,1,0.36,1);font-family:'DM Mono',monospace}}
.script-header.active .script-chevron{{transform:rotate(180deg);color:var(--cyan)}}
.script-body{{display:grid;grid-template-rows:0fr;transition:grid-template-rows 0.5s cubic-bezier(0.22,1,0.36,1);padding:0 28px}}
.script-body.active{{grid-template-rows:1fr}}
.script-body>div{{overflow:hidden}}
.script-body-inner{{padding-bottom:22px}}
.script-desc{{font-size:13px;color:var(--text2);padding:10px 14px;background:rgba(255,255,255,0.01);border-radius:8px;border:1px solid rgba(255,255,255,0.02);margin-bottom:14px;line-height:1.7;font-weight:300}}
.badge-strip{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}}
.badge{{padding:3px 12px;border-radius:4px;font-family:'DM Mono',monospace;font-size:11px;font-weight:400;border:1px solid transparent;transition:all 0.2s ease}}
.badge:hover{{transform:translateY(-1px)}}
.badge-pass{{background:rgba(112,229,154,0.04);color:var(--green);border-color:rgba(112,229,154,0.08)}}
.badge-fail{{background:rgba(255,77,133,0.04);color:var(--magenta);border-color:rgba(255,77,133,0.08)}}
.badge-assert{{background:rgba(91,141,239,0.04);color:var(--blue);border-color:rgba(91,141,239,0.08)}}
.badge-time{{background:rgba(240,179,75,0.04);color:var(--amber);border-color:rgba(240,179,75,0.08)}}
.log-block{{background:rgba(0,0,0,0.25);border:1px solid rgba(255,255,255,0.02);border-radius:8px;padding:12px 14px;max-height:320px;overflow-y:auto;font-family:'DM Mono',monospace;font-size:12px;line-height:1.8;font-weight:300}}
.log-block::-webkit-scrollbar{{width:3px}}
.log-block::-webkit-scrollbar-track{{background:transparent}}
.log-block::-webkit-scrollbar-thumb{{background:rgba(54,240,240,0.08);border-radius:2px}}
.log-line{{padding:1px 0}}
.log-line .ts{{color:var(--text3);margin-right:10px}}
.log-ok{{color:var(--green)}}
.log-err{{color:var(--magenta)}}
.log-info{{color:var(--text2)}}
.tip-bar{{display:flex;align-items:center;gap:14px;padding:14px 20px;margin:36px 0 40px;border:1px solid rgba(54,240,240,0.04);border-radius:10px;background:rgba(54,240,240,0.01);font-size:13px;color:var(--text2);font-weight:300;opacity:0;animation:fadeIn 1s ease 1.2s forwards}}
.tip-bar .tip-label{{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--text3);text-transform:uppercase;padding:2px 10px;border:1px solid rgba(54,240,240,0.06);border-radius:3px}}
footer{{text-align:center;padding:32px 0 16px;opacity:0;animation:fadeIn 1s ease 1.4s forwards}}
footer .line{{width:160px;height:1px;margin:0 auto 20px;background:linear-gradient(90deg,transparent,var(--cyan),var(--purple),transparent)}}
footer p{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:4px;color:var(--text3);text-transform:uppercase}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes cardIn{{from{{opacity:0;transform:translateY(20px) scale(0.98)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
.script-card:nth-child(1){{animation-delay:0.1s}}
.script-card:nth-child(2){{animation-delay:0.15s}}
.script-card:nth-child(3){{animation-delay:0.2s}}
.script-card:nth-child(4){{animation-delay:0.25s}}
.script-card:nth-child(5){{animation-delay:0.3s}}
.script-card:nth-child(6){{animation-delay:0.35s}}
.script-card:nth-child(7){{animation-delay:0.4s}}
.script-card:nth-child(8){{animation-delay:0.45s}}
.script-card:nth-child(9){{animation-delay:0.5s}}
.script-card:nth-child(10){{animation-delay:0.55s}}
.script-card:nth-child(11){{animation-delay:0.6s}}
.script-card:nth-child(12){{animation-delay:0.65s}}
.script-card:nth-child(13){{animation-delay:0.7s}}
.modal-overlay{{position:fixed;inset:0;background:rgba(5,7,10,0.85);backdrop-filter:blur(8px);z-index:9999;display:none;justify-content:center;align-items:center;padding:24px;opacity:0;transition:opacity 0.3s ease}}
.modal-overlay.active{{display:flex;opacity:1}}
.modal-box{{background:var(--bg);border:1px solid var(--border);border-radius:16px;width:100%;max-width:1200px;height:85vh;display:flex;flex-direction:column;position:relative;box-shadow:0 24px 80px rgba(0,0,0,0.5);animation:modalIn 0.35s cubic-bezier(0.22,1,0.36,1)}}
@keyframes modalIn{{from{{opacity:0;transform:scale(0.95) translateY(10px)}}to{{opacity:1;transform:scale(1) translateY(0)}}}}
.modal-header{{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;border-bottom:1px solid var(--border);flex-shrink:0}}
.modal-header .title{{font-family:'DM Mono',monospace;font-size:13px;letter-spacing:2px;color:var(--text2)}}
.modal-header .title strong{{color:var(--cyan);font-weight:500}}
.modal-close{{width:32px;height:32px;display:flex;align-items:center;justify-content:center;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text2);font-size:16px;cursor:pointer;transition:all 0.2s ease;font-family:'DM Mono',monospace}}
.modal-close:hover{{border-color:rgba(255,255,255,0.1);color:var(--text);background:rgba(255,255,255,0.03)}}
.modal-body{{flex:1;overflow-y:auto;position:relative}}
.modal-box.maximized{{max-width:100%;height:100vh;border-radius:0}}
.modal-actions{{display:flex;align-items:center;gap:8px}}
.modal-toggle{{width:32px;height:32px;display:flex;align-items:center;justify-content:center;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text2);font-size:14px;cursor:pointer;transition:all 0.2s ease;font-family:'DM Mono',monospace}}
.modal-toggle:hover{{border-color:rgba(255,255,255,0.1);color:var(--text);background:rgba(255,255,255,0.03)}}
.modal-body iframe{{width:100%;height:100%;border:none;display:block}}
.modal-body::-webkit-scrollbar{{width:4px}}
.modal-body::-webkit-scrollbar-track{{background:transparent}}
.modal-body::-webkit-scrollbar-thumb{{background:rgba(54,240,240,0.1);border-radius:2px}}
.modal-loading{{display:flex;align-items:center;justify-content:center;height:100%;color:var(--text3);font-family:'DM Mono',monospace;font-size:13px;letter-spacing:2px;gap:12px}}
.modal-loading .spinner{{width:20px;height:20px;border:2px solid var(--border);border-top-color:var(--cyan);border-radius:50%;animation:spin 0.8s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@media(max-width:860px){{.container{{padding:24px 16px 40px}}dash-grid{{grid-template-columns:1fr}}.status-ring-panel{{flex-direction:row;gap:24px;padding:20px}}.ring-wrapper{{width:100px;height:100px;margin-bottom:0}}.ring-wrapper svg{{width:100px;height:100px}}.ring-center .big-num{{font-size:28px}}.ring-bg,.ring-fg{{stroke-width:5}}.metrics-panel{{grid-template-columns:repeat(2,1fr)}}.hero__title{{font-size:36px}}.script-header{{flex-direction:column;align-items:flex-start;gap:8px}}.script-actions{{margin-left:0;width:100%}}.flowline{{flex-wrap:wrap}}}}
@media(max-width:480px){{.metrics-panel{{grid-template-columns:1fr}}.metric-card.big{{grid-column:span 1}}}}
</style>
</head>
<body>

<canvas id="nebula"></canvas>
<div class="grid-overlay"></div>

<div class="container">

  <!-- Top Bar -->
  <div class="top-bar">
    <div class="brand">
      <div class="logo-mark">⌘</div>
      <div class="brand-text"><strong>Hermes</strong> Agent</div>
    </div>
    <div class="top-meta">
      <div class="row"><span class="k">EXEC</span><span class="v">{ts}</span></div>
      <div class="row"><span class="k">DURATION</span><span class="v">{total_elapsed:.0f}s</span></div>
      <div class="row"><span class="k">MODE</span><span class="v">{"HEADLESS" if headless else "HEADED"}</span></div>
    </div>
  </div>

  <!-- Hero -->
  <hero>
    <div class="hero__title">
      {PLATFORM_NAME}<br>自动化验证
    </div>
    <div class="hero__sub">
      <span><span class="dot dot-cyan"></span> 端到端场景 · 基础功能</span>
      <span><span class="dot dot-green"></span> {total_scenes} 场景 · {total_scripts} 脚本</span>
      <span><span class="dot dot-amber"></span> {total_assert_pass} 断言 · {"全部通过" if total_scene_fail == 0 else "有失败"}</span>
    </div>
  </hero>

  <!-- Dashboard -->
  <dash-grid>
    <!-- 左：环形状态 -->
    <div class="status-ring-panel">
      <div class="ring-wrapper">
        <svg width="160" height="160" viewBox="0 0 160 160">
          <circle class="ring-bg" cx="80" cy="80" r="70"/>
          <circle class="ring-fg" cx="80" cy="80" r="70"
            stroke-dashoffset="{ring_offset}" style="stroke-dashoffset: {ring_offset};" id="ringCircle"/>
        </svg>
        <div class="ring-center">
          <div class="big-num">{total_pct}%</div>
          <div class="big-label">通过率</div>
        </div>
      </div>
      <div>
        <div class="status-text">● {overall_text}</div>
        <div class="status-sub">{total_scene_pass}/{total_scenes} 场景 · {total_scene_fail} 失败</div>
      </div>
    </div>

    <!-- 右：指标 -->
    <div class="metrics-panel">
      <div class="metric-card green">
        <div class="label">场景通过</div>
        <div class="value">{total_scene_pass}</div>
        <div class="sub">{total_pct}% 通过率</div>
      </div>
      <div class="metric-card magenta">
        <div class="label">场景失败</div>
        <div class="value">{total_scene_fail}</div>
        <div class="sub">{"零缺陷" if total_scene_fail == 0 else "需关注"}</div>
      </div>
      <div class="metric-card cyan">
        <div class="label">脚本通过</div>
        <div class="value">{passed_scripts}<small style="font-size:18px;font-weight:400;color:var(--text3)">/{total_scripts}</small></div>
        <div class="sub">{"全部脚本执行成功" if passed_scripts == total_scripts else "部分脚本未通过"}</div>
      </div>
      <div class="metric-card purple">
        <div class="label">断言通过</div>
        <div class="value">{total_assert_pass}<small style="font-size:18px;font-weight:400;color:var(--text3)">/{total_assert_pass + total_assert_fail}</small></div>
        <div class="sub">{"全部断言验证通过" if total_assert_fail == 0 else "有断言失败"}</div>
      </div>
      <div class="metric-card amber">
        <div class="label">总耗时</div>
        <div class="value">{total_min:.1f}<small style="font-size:18px;font-weight:400;color:var(--text3)">min</small></div>
        <div class="sub">即 {total_elapsed:.0f} 秒</div>
      </div>
    </div>
  </dash-grid>

  <!-- 进度条 -->
  <div class="progress-strip">
    <span class="p-label">通过率</span>
    <div class="p-track">
      <div class="p-fill" style="width: {total_pct}%"></div>
    </div>
    <span class="p-info">{total_pct}% &middot; {total_scene_pass}/{total_scenes} 场景</span>
  </div>

  <!-- E2E 区块 -->
  <div class="module-box cyan">
  <div class="box-label">端到端场景</div>
  <div class="section-head cyan">
    <span class="num">01</span>
    <h2>E2E · 场景链路验证</h2>
    <div class="accent cyan"></div>
  </div>
  <div class="section-sub">{len(e2e_results)} 个脚本 · {e2e_pass} 场景通过 · {e2e_fail} 场景失败</div>

  {e2e_dep if e2e_results else ""}
  {e2e_cards if e2e_results else '<div class="script-card" style="text-align:center;padding:40px;color:var(--text3)">暂无端到端脚本执行</div>'}
  </div>

  <!-- ATOMIC 区块 -->
  <div class="module-box purple">
  <div class="box-label">基础功能</div>
  <div class="section-head purple">
    <span class="num">02</span>
    <h2>ATOMIC · 单模块验证</h2>
    <div class="accent purple"></div>
  </div>
  <div class="section-sub">{len(atomic_results)} 个脚本 · {atomic_pass} 场景通过 · {atomic_fail} 场景失败</div>

  {atomic_dep if atomic_results else ""}
  {atomic_cards if atomic_results else '<div class="script-card" style="text-align:center;padding:40px;color:var(--text3)">暂无基础功能脚本执行</div>'}
  </div>

  <!-- Tip -->
  <div class="tip-bar">
    <span class="tip-label">提示</span>
    <span>点击脚本卡片展开查看详细日志 · 点击「详细报告」在弹窗中查看完整报告（含截图）</span>
  </div>

  <!-- Footer -->
  <footer>
    <div class="line"></div>
    <p>Hermes Agent · 全量端到端测试报告</p>
  </footer>

</div>

<!-- Modal -->
<div class="modal-overlay" id="reportModal">
  <div class="modal-box">
    <div class="modal-header">
      <div class="title"><strong>子报告</strong> · 详细视图</div>
      <div class="modal-actions">
        <button class="modal-toggle" onclick="toggleMaximize()" title="最大化/还原">⛶</button>
        <button class="modal-close" onclick="closeModal()" title="关闭">✕</button>
      </div>
    </div>
    <div class="modal-body" id="modalBody">
      <div class="modal-loading">
        <div class="spinner"></div>
        加载中...
      </div>
    </div>
  </div>
</div>

<script>
/* Toggle */
function toggleScript(header) {{
  header.classList.toggle('active');
  const body = header.nextElementSibling;
  if (body) body.classList.toggle('active');
}}

/* Modal */
function openModal(url, name) {{
  var modal = document.getElementById('reportModal');
  var body = document.getElementById('modalBody');
  modal.classList.add('active');
  body.innerHTML = '<div class="modal-loading"><div class="spinner"></div>加载中...</div>';
  document.querySelector('.modal-header .title').innerHTML = '<strong>' + name + '</strong> · 详细视图';
  var iframe = document.createElement('iframe');
  iframe.style.width = '100%';
  iframe.style.height = '100%';
  iframe.style.border = 'none';
  iframe.style.opacity = '0';
  iframe.style.pointerEvents = 'none';
  body.appendChild(iframe);
  iframe.onload = function() {{
    try {{
      var idoc = iframe.contentDocument || iframe.contentWindow.document;
      if (idoc) {{
        var style = idoc.createElement('style');
        style.textContent = 'canvas, .grid-overlay, .scanline {{ display: none !important; }} body {{ padding: 0; overflow-x: hidden; }}';
        idoc.head.appendChild(style);
      }}
    }} catch(e) {{}}
    body.querySelector('.modal-loading')?.remove();
    iframe.style.opacity = '1';
    iframe.style.pointerEvents = 'auto';
    iframe.style.transition = 'opacity 0.3s ease';
  }};
  iframe.onerror = function() {{
    body.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text3);font-family:\\'DM Mono\\',monospace;font-size:13px">加载失败</div>';
  }};
  iframe.src = url;
}}
function toggleMaximize() {{
  var box = document.querySelector('.modal-box');
  box.classList.toggle('maximized');
}}
function closeModal() {{
  var modal = document.getElementById('reportModal');
  var box = document.querySelector('.modal-box');
  modal.classList.remove('active');
  box.classList.remove('maximized');
  document.getElementById('modalBody').innerHTML = '';
}}
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') closeModal();
}});
document.getElementById('reportModal').addEventListener('click', function(e) {{
  if (e.target === this) closeModal();
}});

/* Nebula */
const canvas = document.getElementById('nebula');
const ctx = canvas.getContext('2d');
let nebParticles = [];
let mouseX = 0, mouseY = 0;
function resizeNeb() {{
  canvas.width = window.innerWidth;
  canvas.height = Math.max(window.innerHeight, document.documentElement.scrollHeight);
}}
resizeNeb();
window.addEventListener('resize', resizeNeb);
window.addEventListener('scroll', resizeNeb);
document.addEventListener('mousemove', e => {{ mouseX = e.clientX; mouseY = e.clientY; }});
class NebParticle {{
  constructor() {{ this.reset(); }}
  reset() {{
    this.x = Math.random() * canvas.width;
    this.y = Math.random() * canvas.height;
    this.size = Math.random() * 2.8 + 0.4;
    this.speedX = (Math.random() - 0.5) * 0.15;
    this.speedY = (Math.random() - 0.5) * 0.15;
    this.opacity = Math.random() * 0.25 + 0.04;
    const colors = ['54,240,240', '166,124,255', '112,229,154', '240,179,75'];
    this.color = colors[Math.floor(Math.random() * colors.length)];
  }}
  update() {{
    const dx = mouseX - this.x;
    const dy = mouseY - this.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 200) {{
      const force = (200 - dist) / 200 * 0.005;
      this.x -= dx * force;
      this.y -= dy * force;
    }}
    this.x += this.speedX;
    this.y += this.speedY;
    if (this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) this.reset();
  }}
  draw() {{
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${{this.color}}, ${{this.opacity}})`;
    ctx.fill();
  }}
}}
for (let i = 0; i < 120; i++) nebParticles.push(new NebParticle());
function animateNeb() {{
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const grd = ctx.createRadialGradient(canvas.width*0.3+mouseX*0.02, canvas.height*0.4+mouseY*0.02, 0, canvas.width*0.3+mouseX*0.02, canvas.height*0.4+mouseY*0.02, 500);
  grd.addColorStop(0, 'rgba(54,240,240,0.012)');
  grd.addColorStop(0.5, 'rgba(166,124,255,0.006)');
  grd.addColorStop(1, 'transparent');
  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const grd2 = ctx.createRadialGradient(canvas.width*0.7-mouseX*0.01, canvas.height*0.6-mouseY*0.01, 0, canvas.width*0.7-mouseX*0.01, canvas.height*0.6-mouseY*0.01, 400);
  grd2.addColorStop(0, 'rgba(112,229,154,0.008)');
  grd2.addColorStop(1, 'transparent');
  ctx.fillStyle = grd2;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (const p of nebParticles) {{ p.update(); p.draw(); }}
  for (let i = 0; i < nebParticles.length; i++) {{
    for (let j = i + 1; j < nebParticles.length; j++) {{
      const dx = nebParticles[i].x - nebParticles[j].x;
      const dy = nebParticles[i].y - nebParticles[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 100) {{
        ctx.beginPath();
        ctx.moveTo(nebParticles[i].x, nebParticles[i].y);
        ctx.lineTo(nebParticles[j].x, nebParticles[j].y);
        ctx.strokeStyle = `rgba(54,240,240, ${{0.015 * (1 - dist / 100)}})`;
        ctx.lineWidth = 0.4;
        ctx.stroke();
      }}
    }}
  }}
  requestAnimationFrame(animateNeb);
}}
animateNeb();
</script>
</body>
</html>'''

    # 保存报告
    ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    master_path = os.path.join(REPORT_DIR, f"全量测试报告_{ts_file}.html")
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(master_path, "w", encoding="utf-8") as f:
        f.write(html)
    return master_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="全量端到端测试调度器")
    parser.add_argument("--headless", action="store_true", help="无头模式执行")
    parser.add_argument("--exclude", type=str, default="", help="要跳过的脚本ID列表，逗号分隔")
    parser.add_argument("--only", type=str, default="", help="仅执行的脚本ID列表，逗号分隔")
    parser.add_argument("--list", action="store_true", help="列出当前平台可用脚本")
    args = parser.parse_args()

    # --list 模式：仅列出脚本，不执行
    if args.list:
        list_scripts()
        return

    print(f"{'='*60}")
    print(f"  全量端到端测试")
    print(f"  {'='*60}")
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  执行模式: {'无头' if args.headless else '有头'}")
    print(f"  {'='*60}")

    # 🧹 清理过期的历史报告
    cleanup_old_reports()

    scripts_to_run = SCRIPTS[:] + ATOMIC_SCRIPTS[:]
    if args.exclude:
        exclude_set = set(s.strip() for s in args.exclude.split(",") if s.strip())
        scripts_to_run = [s for s in scripts_to_run if s["id"] not in exclude_set]
        print(f"  [配置] 排除脚本: {', '.join(exclude_set)}")
    if args.only:
        only_set = set(s.strip() for s in args.only.split(",") if s.strip())
        scripts_to_run = [s for s in scripts_to_run if s["id"] in only_set]
        print(f"  [配置] 仅执行脚本: {', '.join(only_set)}")

    e2e_results = []
    atomic_results = []
    all_ok = True

    for script_info in scripts_to_run:
        # 检查依赖是否已通过
        dep_failed = False
        for dep_id in script_info.get("depends_on", []):
            dep_result = next((r for r in e2e_results + atomic_results if r["script_id"] == dep_id), None)
            if dep_result and not dep_result["success"]:
                print(f"\n  ❌ 依赖 '{dep_id}' 执行失败，跳过 '{script_info['id']}'")
                dep_failed = True
                break
        if dep_failed:
            result = {
                "script_id": script_info["id"],
                "name": script_info["name"],
                "description": script_info["description"],
                "success": False,
                "returncode": -1,
                "elapsed": 0,
                "report_path": None,
                "scene_stats": {"passed": 0, "failed": 0, "skipped": 0},
                "assert_stats": {"passed": 0, "failed": 0},
                "output_lines": ["[跳过] 依赖脚本未通过"],
                "full_output": "[跳过] 依赖脚本未通过",
            }
            (atomic_results if script_info in ATOMIC_SCRIPTS else e2e_results).append(result)
            all_ok = False
            continue

        result = run_script(script_info, headless=args.headless)
        (atomic_results if script_info in ATOMIC_SCRIPTS else e2e_results).append(result)
        if not result["success"]:
            all_ok = False

    # 生成总报告
    all_results = e2e_results + atomic_results
    print(f"\n{'='*60}")
    print(f"  生成聚合测试报告...")
    master_path = generate_master_report(e2e_results, atomic_results, headless=args.headless)

    print(f"\n{'='*60}")
    print(f"  执行完成")
    print(f"  {'='*60}")
    print(f"  脚本: {len(all_results)} | 通过: {sum(1 for r in all_results if r['success'])} | 失败: {sum(1 for r in all_results if not r['success'])}")
    print(f"  总场景: {sum(r['scene_stats']['passed']+r['scene_stats']['failed']+r['scene_stats']['skipped'] for r in all_results)}")
    print(f"  总断言: {sum(r['assert_stats']['passed'] for r in all_results)}通过/{sum(r['assert_stats']['failed'] for r in all_results)}失败")
    print(f"  总耗时: {sum(r['elapsed'] for r in all_results):.0f}秒")

    if all_ok:
        print(f"\n  🎉 全部脚本执行通过！")
    else:
        print(f"\n  ⚠️ 部分脚本执行失败，请查看详细报告")

    print(f"\n  📋 总报告: {master_path}")
    if e2e_results:
        print(f"     ┌─ 📌 端到端场景 ─────────────────────")
        for r in e2e_results:
            if r["report_path"]:
                print(f"     ├─ {r['name']}: {r['report_path']}")
    if atomic_results:
        print(f"     ┌─ 📦 原子功能测试 ───────────────────")
        for r in atomic_results:
            if r["report_path"]:
                print(f"     ├─ {r['name']}: {r['report_path']}")
    print()

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
