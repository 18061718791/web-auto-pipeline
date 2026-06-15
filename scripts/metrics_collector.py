#!/usr/bin/env python3
"""
metrics_collector.py — 成功率追踪与度量采集

记录每次运行的结果到 metrics_history.json，支持成功率趋势分析。
可在 master_runner 中集成调用。

Usage:
    python metrics_collector.py record --script device_managent_test --pass 7 --fail 2 --skip 0 --elapsed 157.3
    python metrics_collector.py record --from-report path/to/test_results.json
    python metrics_collector.py trend --last 10
    python metrics_collector.py trend --days 7
    python metrics_collector.py summary
    python metrics_collector.py dashboard --last 20
"""

import json
import argparse
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DEFAULT_HISTORY_PATH = Path(__file__).parent.parent / "docs" / "metrics_history.json"

# ---- 跨平台文件锁 ----

try:
    import portalocker
    _USE_PORTALOCKER = True
except ImportError:
    _USE_PORTALOCKER = False


class FileLockTimeout(Exception):
    """文件锁超时异常"""


class _FileLock:
    """跨平台文件锁（5 秒超时）

    优先使用 portalocker，回退到 msvcrt (Windows) 或 fcntl (Linux/macOS)。
    """

    def __init__(self, path: Path):
        self.path = path
        self.fh = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 'a+' — 文件不存在则创建，可读写，不截断
        self.fh = open(self.path, "a+", encoding="utf-8")
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                if _USE_PORTALOCKER:
                    portalocker.lock(self.fh, portalocker.LOCK_EX)
                elif sys.platform == "win32":
                    import msvcrt
                    msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (BlockingIOError, PermissionError, OSError):
                time.sleep(0.1)
        raise FileLockTimeout(f"无法获取文件锁: {self.path}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fh is not None:
            try:
                if _USE_PORTALOCKER:
                    portalocker.unlock(self.fh)
                elif sys.platform == "win32":
                    import msvcrt
                    msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            self.fh.close()
            self.fh = None

    def read_json(self) -> list:
        """从已锁定的文件中读取 JSON 数组"""
        self.fh.seek(0)
        try:
            return json.load(self.fh)
        except (json.JSONDecodeError, ValueError):
            return []

    def write_json(self, data: list):
        """将 JSON 数组写入已锁定的文件（截断重写）"""
        self.fh.seek(0)
        self.fh.truncate()
        json.dump(data, self.fh, indent=2, ensure_ascii=False)
        self.fh.flush()
        os.fsync(self.fh.fileno())


# ---- 数据 I/O（带锁保护）----


def load_history(path: Path) -> list:
    """加载历史记录（文件锁保护，超时回退到无锁读取）"""
    try:
        with _FileLock(path) as lock:
            return lock.read_json()
    except FileLockTimeout as e:
        print(f"[METRICS] ⚠ 文件锁超时，尝试无锁读取: {e}", file=sys.stderr)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                return []
        return []


def save_history(path: Path, history: list):
    """保存历史记录（文件锁保护，超时回退到无锁写入）"""
    try:
        with _FileLock(path) as lock:
            lock.write_json(history)
    except FileLockTimeout as e:
        print(f"[METRICS] ⚠ 文件锁超时，尝试无锁写入: {e}", file=sys.stderr)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(history, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---- 核心功能 ----


def record_entry(
    path: Path,
    script: str,
    passed: int,
    failed: int,
    skipped: int,
    elapsed: float,
    detail: str = "",
    max_entries: int = 1000,
):
    """记录一次运行结果，超出 max_entries 时裁剪旧数据"""
    history = load_history(path)
    entry = {
        "date": datetime.now().isoformat(),
        "script": script,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": passed + failed + skipped,
        "pass_rate": (
            round(passed / max(passed + failed, 1) * 100, 1)
            if passed + failed > 0
            else 0.0
        ),
        "elapsed": round(elapsed, 1),
        "detail": detail,
    }
    history.append(entry)
    # 数据过期裁剪
    if len(history) > max_entries:
        history = history[-max_entries:]
    save_history(path, history)
    print(
        f"[METRICS] 已记录: {script} | "
        f"通过={passed} 失败={failed} 跳过={skipped} | "
        f"通过率={entry['pass_rate']}%"
    )


def record_from_report(
    report_path: str,
    history_path: Path = DEFAULT_HISTORY_PATH,
    max_entries: int = 1000,
):
    """从 test_results.json 报告文件记录"""
    rp = Path(report_path)
    if not rp.exists():
        print(f"[METRICS] 报告文件不存在: {report_path}")
        return
    try:
        data = json.loads(rp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[METRICS] JSON 解析失败: {e}")
        return

    script = data.get("title", rp.stem.replace("_test_results", ""))
    scenes = data.get("scenes", [])
    passed = sum(1 for s in scenes if s.get("status") == "passed")
    failed = sum(1 for s in scenes if s.get("status") == "failed")
    skipped = sum(1 for s in scenes if s.get("status") == "skipped")
    elapsed = data.get("total_elapsed", 0)
    total_assert = data.get("total_assert", 0)
    assert_pass = data.get("assert_pass", 0)
    detail = f"断言: {assert_pass}/{total_assert} 通过"

    record_entry(
        history_path,
        script,
        passed,
        failed,
        skipped,
        elapsed,
        detail,
        max_entries=max_entries,
    )


def show_trend(
    path: Path,
    last_n: Optional[int] = None,
    last_days: Optional[int] = None,
):
    """显示成功率趋势"""
    history = load_history(path)
    if not history:
        print("[METRICS] 尚无历史记录")
        return

    if last_days:
        cutoff = datetime.now() - timedelta(days=last_days)
        history = [e for e in history if datetime.fromisoformat(e["date"]) >= cutoff]
    if last_n:
        history = history[-last_n:]

    if not history:
        print("[METRICS] 筛选范围内无记录")
        return

    print(f"\n{'=' * 70}")
    print(f"  成功率趋势（最近 {len(history)} 次运行）")
    print(f"{'=' * 70}")
    print(
        f"{'日期':16s} {'脚本':25s} {'通过':>4s} {'失败':>4s} {'跳过':>4s} {'通过率':>7s} {'耗时':>7s}"
    )
    print(
        f"{'-' * 16} {'-' * 25} {'-' * 4} {'-' * 4} {'-' * 4} {'-' * 7} {'-' * 7}"
    )

    for e in reversed(history[-30:]):  # 最多显示30条
        d = datetime.fromisoformat(e["date"]).strftime("%m-%d %H:%M")
        pct = f"{e['pass_rate']}%"
        elapsed = f"{e['elapsed']}s"
        print(
            f"{d:16s} {e['script'][:25]:25s} {e['passed']:4d} {e['failed']:4d} {e['skipped']:4d} {pct:>7s} {elapsed:>7s}"
        )

    # 汇总统计
    total_runs = len(history)
    all_passed = sum(e["passed"] for e in history)
    all_failed = sum(e["failed"] for e in history)
    all_skipped = sum(e["skipped"] for e in history)
    total_scenes = sum(e["total"] for e in history)
    overall_pass_rate = round(
        all_passed / max(all_passed + all_failed, 1) * 100, 1
    )

    print(f"{'=' * 70}")
    print(f"  汇总: {total_runs} 次运行, {total_scenes} 场景")
    print(f"  总通过率: {overall_pass_rate}%")
    print(
        f"  平均耗时: {round(sum(e['elapsed'] for e in history) / len(history), 1)}s / run"
    )
    print()


def show_summary(path: Path):
    """显示脚本级汇总"""
    history = load_history(path)
    if not history:
        print("[METRICS] 尚无历史记录")
        return

    scripts = set(e["script"] for e in history)
    print(f"\n{'=' * 60}")
    print(f"  度量总览 — {len(history)} 条记录, {len(scripts)} 个脚本")
    print(f"{'=' * 60}")

    for script in sorted(scripts):
        entries = [e for e in history if e["script"] == script]
        passed = sum(e["passed"] for e in entries)
        failed = sum(e["failed"] for e in entries)
        skipped = sum(e["skipped"] for e in entries)
        total = sum(e["total"] for e in entries)
        rate = round(passed / max(passed + failed, 1) * 100, 1)
        avg_elapsed = round(sum(e["elapsed"] for e in entries) / len(entries), 1)
        print(
            f"  {script:30s} 通过率: {rate:>5.1f}%  |  {total} 场景  |  平均 {avg_elapsed}s"
        )

    # 全局
    all_p = sum(e["passed"] for e in history)
    all_f = sum(e["failed"] for e in history)
    print(f"{'=' * 60}")
    print(
        f"  {'全局':30s} 通过率: {round(all_p / max(all_p + all_f, 1) * 100, 1)}%  |  {sum(e['total'] for e in history)} 场景"
    )
    print()


# ---- Dashboard HTML 生成 ----


def _pass_rate_class(rate: float) -> str:
    if rate >= 80:
        return "high"
    elif rate >= 50:
        return "mid"
    return "low"


def _bar_color(rate: float) -> str:
    if rate >= 80:
        return "#4ecca3"
    elif rate >= 50:
        return "#ffc107"
    return "#e94560"


def generate_dashboard(path: Path, last_n: Optional[int] = None):
    """
    生成自包含 HTML Dashboard（深色主题，纯 CSS 柱状图）
    输出到 docs/output/metrics_dashboard.html
    """
    history = load_history(path)
    if not history:
        print("[METRICS] 尚无历史记录，无法生成 Dashboard")
        return

    if last_n:
        history = history[-last_n:]

    if not history:
        print("[METRICS] 筛选范围内无记录")
        return

    # ---- 构建表格行（最新在前）----
    table_rows = ""
    for i, e in enumerate(reversed(history), 1):
        d = datetime.fromisoformat(e["date"]).strftime("%Y-%m-%d %H:%M")
        rate = e["pass_rate"]
        cls = _pass_rate_class(rate)
        table_rows += (
            f"<tr>"
            f"<td>{i}</td>"
            f"<td>{d}</td>"
            f"<td>{e['script'][:40]}</td>"
            f"<td>{e['passed']}</td>"
            f"<td>{e['failed']}</td>"
            f"<td>{e['skipped']}</td>"
            f'<td class="pass-rate {cls}">{rate}%</td>'
            f"<td>{e['elapsed']}s</td>"
            f"</tr>\n"
        )

    # ---- 构建柱状图（时间顺序从左到右）----
    bar_parts = ""
    for e in history:
        rate = e["pass_rate"]
        color = _bar_color(rate)
        height_px = max(2, int(rate * 2))  # rate% * 2 → 最大 200px
        script_short = e["script"][:12]
        bar_parts += (
            f'<div class="bar-wrapper">'
            f'<div class="bar-value">{rate}%</div>'
            f'<div class="bar" style="height:{height_px}px;background:{color};"></div>'
            f'<div class="bar-label" title="{e["script"]}">{script_short}</div>'
            f"</div>\n"
        )

    # ---- 汇总统计 ----
    all_p = sum(e["passed"] for e in history)
    all_f = sum(e["failed"] for e in history)
    overall_rate = round(all_p / max(all_p + all_f, 1) * 100, 1)
    title = f"Metrics Dashboard — 总体通过率 {overall_rate}%"

    html = _DASHBOARD_HTML_TEMPLATE.format(
        title=title,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_runs=len(history),
        table_rows=table_rows,
        bar_chart=bar_parts,
    )

    output_dir = Path(__file__).parent.parent / "docs" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "metrics_dashboard.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"[METRICS] Dashboard 已生成: {output_path.resolve()}")


_DASHBOARD_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: -apple-system, 'Segoe UI', sans-serif;
    padding: 30px;
  }}
  h1 {{ color: #e94560; font-size: 24px; margin-bottom: 8px; }}
  .subtitle {{ color: #888; font-size: 14px; margin-bottom: 24px; }}
  table {{
    width: 100%; border-collapse: collapse; background: #16213e;
    border-radius: 8px; overflow: hidden; margin-bottom: 30px;
  }}
  th {{ background: #0f3460; color: #e94560; padding: 10px 12px; text-align: left; font-weight: 600; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #1a1a3e; }}
  tr:hover td {{ background: #1a2744; }}
  .pass-rate {{ font-weight: bold; }}
  .pass-rate.high {{ color: #4ecca3; }}
  .pass-rate.mid {{ color: #ffc107; }}
  .pass-rate.low {{ color: #e94560; }}
  .chart-section {{ background: #16213e; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
  .chart-section h2 {{ color: #e94560; font-size: 18px; margin-bottom: 16px; }}
  .bar-chart {{ display: flex; align-items: flex-end; gap: 6px; min-height: 220px; padding: 10px 0; overflow-x: auto; }}
  .bar-wrapper {{ display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }}
  .bar {{ width: 28px; border-radius: 4px 4px 0 0; min-height: 2px; transition: height 0.3s; }}
  .bar-label {{ font-size: 10px; color: #aaa; margin-top: 4px; writing-mode: vertical-lr; text-orientation: mixed; max-height: 60px; overflow: hidden; }}
  .bar-value {{ font-size: 10px; color: #ccc; margin-bottom: 2px; }}
  .footer {{ text-align: center; color: #555; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="subtitle">生成时间: {generated_at} | 共 {total_runs} 条记录</div>

<h2 style="color:#e94560;font-size:18px;margin-bottom:12px;">趋势表格</h2>
<table>
<thead>
<tr><th>#</th><th>日期</th><th>脚本</th><th>通过</th><th>失败</th><th>跳过</th><th>通过率</th><th>耗时</th></tr>
</thead>
<tbody>
{table_rows}
</tbody>
</table>

<div class="chart-section">
<h2>通过率柱状图 ({total_runs} 次)</h2>
<div class="bar-chart">
{bar_chart}
</div>
</div>

<div class="footer">Metrics Dashboard — Auto-generated by metrics_collector.py</div>
</body>
</html>"""


# ---- CLI ----


def main():
    parser = argparse.ArgumentParser(description="成功率追踪与度量采集")
    sub = parser.add_subparsers(dest="command")

    # record
    p_record = sub.add_parser("record", help="记录一次运行结果")
    p_record.add_argument("--script", required=True)
    p_record.add_argument("--pass", type=int, default=0, dest="passed")
    p_record.add_argument("--fail", type=int, default=0, dest="failed")
    p_record.add_argument("--skip", type=int, default=0, dest="skipped")
    p_record.add_argument("--elapsed", type=float, default=0)
    p_record.add_argument("--detail", default="")
    p_record.add_argument("--history", default=str(DEFAULT_HISTORY_PATH))
    p_record.add_argument(
        "--max-entries",
        type=int,
        default=1000,
        help="最大保留条目数（默认 1000，超出则裁剪旧数据）",
    )

    # record-from-report
    p_report = sub.add_parser("record-from-report", help="从 test_results.json 记录")
    p_report.add_argument("report_path")
    p_report.add_argument("--history", default=str(DEFAULT_HISTORY_PATH))
    p_report.add_argument(
        "--max-entries",
        type=int,
        default=1000,
        help="最大保留条目数（默认 1000，超出则裁剪旧数据）",
    )

    # trend
    p_trend = sub.add_parser("trend", help="显示趋势")
    p_trend.add_argument("--last", type=int, default=None)
    p_trend.add_argument("--days", type=int, default=None)
    p_trend.add_argument("--history", default=str(DEFAULT_HISTORY_PATH))

    # summary
    p_summary = sub.add_parser("summary", help="显示汇总")
    p_summary.add_argument("--history", default=str(DEFAULT_HISTORY_PATH))

    # dashboard
    p_dash = sub.add_parser("dashboard", help="生成 HTML Dashboard")
    p_dash.add_argument("--last", type=int, default=20, help="最近 N 条记录（默认 20）")
    p_dash.add_argument("--history", default=str(DEFAULT_HISTORY_PATH))

    args = parser.parse_args()

    if args.command == "record":
        record_entry(
            Path(args.history),
            args.script,
            args.passed,
            args.failed,
            args.skipped,
            args.elapsed,
            args.detail,
            max_entries=args.max_entries,
        )
    elif args.command == "record-from-report":
        record_from_report(
            args.report_path,
            Path(args.history),
            max_entries=args.max_entries,
        )
    elif args.command == "trend":
        show_trend(Path(args.history), last_n=args.last, last_days=args.days)
    elif args.command == "summary":
        show_summary(Path(args.history))
    elif args.command == "dashboard":
        generate_dashboard(Path(args.history), last_n=args.last)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
