#!/usr/bin/env python3
"""
HTML 测试报告渲染器 - 将 TestCollector 数据渲染为自包含 HTML 报告
样式匹配 device_management_测试报告_20260610_092050.html 的 cyberpunk 设计
"""
import os
from datetime import datetime


class HtmlRenderer:
    """将收集的测试数据渲染为自包含 HTML 报告"""

    @staticmethod
    def render(data: dict) -> str:
        """渲染为 HTML 字符串"""
        total = data["total"]
        passed = data["passed"]
        failed = data["failed"]
        skipped = data["skipped"]
        total_assert = data["total_assert"]
        assert_pass = data["assert_pass"]
        assert_fail = data["assert_fail"]
        total_elapsed = data["total_elapsed"]
        title = data["title"]

        # 断言通过率
        pass_rate = 100 if total_assert == 0 else round(assert_pass / total_assert * 100)

        # 总体状态
        if failed == 0 and passed > 0:
            overall_icon, overall_text, overall_class = "✓", "全部通过", "overall-pass"
        elif passed == 0 and failed > 0:
            overall_icon, overall_text, overall_class = "✕", "全部失败", "overall-fail"
        elif failed > 0:
            overall_icon, overall_text, overall_class = "⚠", "部分失败", "overall-partial"
        else:
            overall_icon, overall_text, overall_class = "⏭", "全部跳过", "overall-skip"

        # 确定 em 后缀
        em_suffix = "E2E" if "管理" in title or "生命周期" in title or "Bypass" in title else "ATOMIC"

        # 执行时间和耗时
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dur_str = HtmlRenderer._duration(total_elapsed)

        # 场景卡片
        scenes_html = ""
        for sc in data["scenes"]:
            status_icon = {"passed": "✓", "failed": "✕", "skipped": "⏭"}.get(sc["status"], "?")
            status_text = {"passed": "通过", "failed": "失败", "skipped": "跳过"}.get(sc["status"], "未知")
            sc_dur = HtmlRenderer._duration(sc.get("duration") or 0)

            assert_info = f"{sc['assert_pass']}通过/{sc['assert_fail']}失败" if sc["assertions"] else "无断言"

            # 断言按步骤分组
            assert_by_step = {}
            for a in sc["assertions"]:
                step_seq = a.get("after_step", 0)
                assert_by_step.setdefault(step_seq, []).append(a)

            # 时间线
            timeline_html = ""
            for st in sc.get("steps", []):
                step_asserts = assert_by_step.pop(st["seq"], [])
                badges = ""
                for a in step_asserts:
                    a_icon = "✓" if a["passed"] else "✕"
                    a_cls = "pass" if a["passed"] else "fail"
                    badges += f'<span class="assert-badge {a_cls}">{a_icon} {a["desc"]}</span>'

                timeline_html += f'<div class="step">'
                timeline_html += f'<span class="step-seq">#{st["seq"]}</span>'
                timeline_html += f'<span class="step-msg">{st["msg"]}</span>'
                if badges:
                    timeline_html += badges
                timeline_html += f'<span class="step-ts">{st["ts"]}</span>'
                if st.get("screenshot"):
                    timeline_html += f'<div class="screenshot-wrapper"><img src="{st["screenshot"]}" onclick="this.classList.toggle(\'expanded\')" title="点击放大/缩小" loading="lazy"/></div>'
                timeline_html += '</div>'

            # 兜底断言（没有关联到特定步骤的）
            for step_seq, leftovers in assert_by_step.items():
                for a in leftovers:
                    a_icon = "✓" if a["passed"] else "✕"
                    a_cls = "pass" if a["passed"] else "fail"
                    timeline_html += f'<div class="step"><span class="assert-badge {a_cls}">{a_icon} {a["desc"]}</span><span class="step-ts">{a.get("detail","")}</span></div>'

            # 每个场景的进度块（flex权重基于断言数）
            flex_weight = max(sc["assert_pass"], 1)

            scenes_html += f'''<div class="scene-card {sc["status"]}">
                <div class="scene-header" onclick="toggleScene(this)">
                    <span class="scene-status">{status_icon}</span>
                    <span class="scene-id">{sc["id"]}</span>
                    <span class="scene-desc">{sc["desc"]}</span>
                    <span class="scene-stat">{status_text} | {assert_info} | {sc_dur}</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="scene-body">
                    {timeline_html if timeline_html else '<div class="no-data">无操作记录</div>'}
                </div>
            </div>'''

        # 进度条各场景权重
        progress_bars = "".join(
            f'<div class="progress-pass" style="flex:{max(sc["assert_pass"],1)}"></div>'
            + (f'<div class="progress-fail" style="flex:{sc["assert_fail"]}"></div>' if sc["assert_fail"] > 0 else '')
            for sc in data["scenes"]
        )

        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · 场景测试报告</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Inter:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#f0f2f5;--surface:#ffffff;--border:rgba(0,0,0,0.07);--text:#1a1d23;--text2:rgba(26,29,35,0.72);--text3:rgba(26,29,35,0.40);--cyan:#0ea5e9;--green:#10b981;--magenta:#ef4444;--amber:#f59e0b;--blue:#3b82f6}}
html,body{{height:100%}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;overflow-x:hidden;padding:0}}
#nebula{{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:0.35}}
.grid-overlay{{position:fixed;inset:0;background-image:linear-gradient(rgba(0,0,0,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(0,0,0,0.04) 1px,transparent 1px);background-size:80px 80px;z-index:0;pointer-events:none}}
.container{{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:32px 24px 60px}}
.top-bar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:44px;opacity:0;animation:fadeIn 1s ease 0.2s forwards}}
.brand{{display:flex;align-items:center;gap:14px}}
.logo-mark{{width:32px;height:32px;border:2px solid var(--cyan);border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'DM Mono',monospace;font-size:12px;font-weight:500;color:var(--cyan);box-shadow:0 0 30px rgba(54,240,240,0.08)}}
.brand-text{{font-size:12px;font-weight:400;letter-spacing:3px;text-transform:uppercase;color:var(--text2)}}
.brand-text strong{{color:var(--cyan);font-weight:500}}
.top-meta{{font-family:'DM Mono',monospace;font-size:12px;color:var(--text2);line-height:2;padding:12px 20px;background:var(--surface);border:1px solid var(--border);border-radius:10px;min-width:200px}}
.top-meta .row{{display:flex;gap:14px}}
.top-meta .row .k{{color:var(--text3);min-width:58px;text-align:right}}
.top-meta .row .v{{color:var(--text)}}
hero{{display:block;margin-bottom:40px;opacity:0;animation:fadeIn 1s ease 0.4s forwards}}
.hero__title{{font-size:clamp(32px,4.5vw,48px);font-weight:900;line-height:1;letter-spacing:-2px;color:var(--text)}}
.hero__title em{{font-style:normal;background:linear-gradient(135deg,var(--cyan),var(--green));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero__sub{{display:flex;gap:24px;flex-wrap:wrap;margin-top:12px;font-size:14px;color:var(--text2);font-weight:300}}
.hero__sub span{{display:flex;align-items:center;gap:8px}}
.hero__sub .dot{{width:5px;height:5px;border-radius:50%;display:inline-block}}
.dot-green{{background:var(--green);box-shadow:0 0 8px var(--green)}}
.dot-cyan{{background:var(--cyan);box-shadow:0 0 8px var(--cyan)}}
.dot-amber{{background:var(--amber);box-shadow:0 0 8px var(--amber)}}
.summary-banner{{background:linear-gradient(135deg,rgba(14,165,233,0.03),rgba(16,185,129,0.03));border:1px solid var(--border);border-radius:16px;padding:24px 28px;display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin-bottom:32px;position:relative;overflow:hidden;opacity:0;animation:fadeIn 1s ease 0.5s forwards}}
.summary-banner::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--green),transparent)}}
.overall-status{{text-align:center;min-width:120px;padding:14px 20px;border-radius:10px;background:linear-gradient(135deg,rgba(16,185,129,0.06),rgba(16,185,129,0.02));border:1px solid rgba(16,185,129,0.15)}}
.overall-icon{{font-size:28px;display:block;filter:drop-shadow(0 0 10px rgba(16,185,129,0.2))}}
.overall-text{{font-family:'DM Mono',monospace;font-size:14px;font-weight:700;color:var(--green);margin-top:2px}}
.overall-detail{{font-size:12px;color:var(--text2);margin-top:4px}}
.stat-strip{{display:flex;gap:20px;flex-wrap:wrap;flex:1}}
.stat-item{{text-align:center;min-width:56px}}
.stat-item .num{{font-family:'DM Mono',monospace;font-size:24px;font-weight:700;line-height:1.1}}
.stat-item .label{{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:1px;margin-top:2px}}
.stat-pass .num{{color:var(--green)}}
.stat-fail .num{{color:var(--magenta)}}
.stat-skip .num{{color:var(--amber)}}
.stat-assert .num{{color:var(--blue)}}
.stat-time .num{{color:var(--cyan);font-size:20px}}
.progress-bar{{flex:1;min-width:160px}}
.progress-track{{height:6px;background:rgba(0,0,0,0.04);border-radius:3px;overflow:hidden;display:flex;border:1px solid rgba(0,0,0,0.03)}}
.progress-pass{{background:linear-gradient(90deg,var(--green),#90f0b8);border-radius:3px;position:relative}}
.progress-pass::after{{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.15),transparent);animation:shimmer 2.5s ease-in-out infinite}}
.progress-labels{{display:flex;justify-content:space-between;font-size:11px;color:var(--text2);margin-top:4px;font-family:'DM Mono',monospace}}
@keyframes shimmer{{0%{{transform:translateX(-100%)}}100%{{transform:translateX(100%)}}}}
.scene-card{{background:var(--surface);border:1px solid var(--border);border-radius:14px;margin-bottom:10px;overflow:hidden;transition:all 0.4s cubic-bezier(0.22,1,0.36,1);opacity:0;animation:cardIn 0.6s cubic-bezier(0.22,1,0.36,1) forwards;position:relative}}
.scene-card:hover{{border-color:rgba(0,0,0,0.10);box-shadow:0 6px 32px rgba(0,0,0,0.04)}}
.scene-card::before{{content:'';position:absolute;top:0;left:0;width:3px;bottom:0;border-radius:3px 0 0 3px}}
.scene-card.passed::before{{background:var(--green);box-shadow:0 0 8px rgba(112,229,154,0.15)}}
.scene-card.failed::before{{background:var(--magenta);box-shadow:0 0 8px rgba(255,77,133,0.15)}}
.scene-header{{display:flex;align-items:center;gap:14px;padding:14px 20px 14px 24px;cursor:pointer;user-select:none;transition:background 0.2s ease;flex-wrap:wrap;position:relative}}
.scene-header:hover{{background:rgba(0,0,0,0.015)}}
.scene-status{{font-size:16px;flex-shrink:0}}
.scene-id{{font-family:'DM Mono',monospace;font-size:13px;color:var(--text2);font-weight:500;min-width:52px}}
.scene-desc{{font-weight:500;font-size:14px;color:var(--text);flex:1}}
.scene-stat{{font-family:'DM Mono',monospace;font-size:12px;color:var(--text2);text-align:right}}
.toggle-icon{{color:var(--text3);font-size:12px;transition:transform 0.4s cubic-bezier(0.22,1,0.36,1);font-family:'DM Mono',monospace}}
.scene-header.active .toggle-icon{{transform:rotate(180deg);color:var(--cyan)}}
.scene-body{{display:none;padding:0 22px 20px 24px}}
.scene-body.active{{display:block}}
.step{{padding:8px 12px;margin-bottom:6px;background:rgba(0,0,0,0.02);border-radius:8px;border-left:2px solid rgba(14,165,233,0.12);font-family:'DM Mono',monospace;font-size:12px;line-height:1.6;display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap}}
.step-seq{{color:var(--cyan);font-weight:500;font-size:11px;flex-shrink:0}}
.step-msg{{color:var(--text2);flex:1}}
.step-ts{{color:var(--text3);font-size:11px;flex-shrink:0}}
.assert-badge{{display:inline-block;padding:1px 8px;margin:0 2px;border-radius:4px;font-size:11px;font-weight:500;font-family:'DM Mono',monospace;vertical-align:middle;line-height:1.6;white-space:nowrap;border:1px solid transparent}}
.assert-badge.pass{{background:rgba(112,229,154,0.04);color:var(--green);border-color:rgba(112,229,154,0.08)}}
.assert-badge.fail{{background:rgba(255,77,133,0.04);color:var(--magenta);border-color:rgba(255,77,133,0.08)}}
.screenshot-wrapper{{margin-top:6px;width:100%}}
.screenshot-wrapper img{{max-width:100%;height:auto;border-radius:6px;border:1px solid rgba(255,255,255,0.04);cursor:zoom-in;transition:all 0.25s ease;max-height:200px}}
.screenshot-wrapper img.expanded{{max-height:none;cursor:zoom-out}}
footer{{text-align:center;padding:32px 0 16px;opacity:0;animation:fadeIn 1s ease 1.2s forwards}}
footer .line{{width:120px;height:1px;margin:0 auto 20px;background:linear-gradient(90deg,transparent,var(--cyan),var(--green),transparent)}}
footer p{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:4px;color:var(--text3);text-transform:uppercase}}
.no-data{{text-align:center;color:var(--text3);font-size:14px;padding:40px 20px;font-family:'DM Mono',monospace;border:1px dashed var(--border);border-radius:12px}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes cardIn{{from{{opacity:0;transform:translateY(16px) scale(0.98)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
{chr(10).join(f'.scene-card:nth-child({i+1}){{animation-delay:{0.1+i*0.04:.2f}s}}' for i in range(len(data["scenes"])))}
@media(max-width:700px){{.container{{padding:20px 14px 40px}}.summary-banner{{gap:12px;padding:16px}}.stat-item{{min-width:44px}}.stat-item .num{{font-size:18px}}.scene-header{{flex-direction:column;align-items:flex-start;gap:4px}}.scene-stat{{width:100%;text-align:left}}.top-bar{{flex-direction:column;align-items:flex-start;gap:12px}}}}
.in-iframe #nebula,.in-iframe .grid-overlay{{display:none!important}}
</style>
<script>if(window.self!==window.top)document.documentElement.classList.add('in-iframe');</script>
</head>
<body>

<canvas id="nebula"></canvas>
<div class="grid-overlay"></div>

<div class="container">

  <div class="top-bar">
    <div class="brand">
      <div class="logo-mark">⌘</div>
      <div class="brand-text"><strong>Hermes</strong> Agent</div>
    </div>
    <div class="top-meta">
      <div class="row"><span class="k">EXEC</span><span class="v">{ts}</span></div>
      <div class="row"><span class="k">DURATION</span><span class="v">{dur_str}</span></div>
    </div>
  </div>

  <hero>
    <div class="hero__title">
      {title} <em>{em_suffix}</em>
    </div>
    <div class="hero__sub">
      <span><span class="dot dot-green"></span> {total} 场景 · {"全部通过" if failed==0 and passed>0 else f"{failed} 失败"}</span>
      <span><span class="dot dot-cyan"></span> 断言 {assert_pass}/{total_assert}</span>
      <span><span class="dot dot-amber"></span> 耗时 {dur_str}</span>
    </div>
  </hero>

  <div class="summary-banner">
    <div class="overall-status">
      <span class="overall-icon">{overall_icon}</span>
      <div class="overall-text">{overall_text}</div>
      <div class="overall-detail">{total}场景 · {passed}通过 · {failed}失败</div>
    </div>
    <div class="stat-strip">
      <div class="stat-item stat-pass"><div class="num">{passed}</div><div class="label">通过</div></div>
      <div class="stat-item stat-fail"><div class="num">{failed}</div><div class="label">失败</div></div>
      <div class="stat-item stat-skip"><div class="num">{skipped}</div><div class="label">跳过</div></div>
      <div class="stat-item stat-assert"><div class="num">{assert_pass}/{total_assert}</div><div class="label">断言通过</div></div>
      <div class="stat-item stat-time"><div class="num">{HtmlRenderer._duration(total_elapsed)}</div><div class="label">耗时</div></div>
    </div>
    <div class="progress-bar">
      <div class="progress-track">
        {progress_bars}
      </div>
      <div class="progress-labels">
        <span>通过率 {pass_rate}%</span>
        <span>断言 {assert_pass}/{total_assert}</span>
      </div>
    </div>
  </div>

  {scenes_html}

  <footer>
    <div class="line"></div>
    <p>Hermes Agent · {title}</p>
  </footer>

</div>

<script>
function toggleScene(header) {{
    header.classList.toggle('active');
    const body = header.nextElementSibling;
    if (body) body.classList.toggle('active');
}}
document.querySelectorAll('.scene-card.failed .scene-header').forEach(function(h) {{ h.click(); }});

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
    this.opacity = Math.random() * 0.12 + 0.02;
    const colors = ['14,165,233', '16,185,129', '245,158,11'];
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
for (let i = 0; i < 80; i++) nebParticles.push(new NebParticle());
function animateNeb() {{
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const grd = ctx.createRadialGradient(canvas.width*0.3+mouseX*0.02, canvas.height*0.4+mouseY*0.02, 0, canvas.width*0.3+mouseX*0.02, canvas.height*0.4+mouseY*0.02, 500);
  grd.addColorStop(0, 'rgba(14,165,233,0.008)');
  grd.addColorStop(0.5, 'rgba(16,185,129,0.004)');
  grd.addColorStop(1, 'transparent');
  ctx.fillStyle = grd;
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
if(window.self===window.top)animateNeb();
</script>
</body>
</html>'''  # NOQA

    @staticmethod
    def _duration(seconds):
        """将秒数格式化为易读字符串"""
        if seconds < 60:
            return f"{seconds:.0f}秒"
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.0f}分"
        hours = minutes / 60
        return f"{hours:.1f}小时"

    def save(self, data: dict, output_dir: str, filename: str = None) -> str:
        """生成 HTML 并保存到文件，返回文件路径"""
        import os
        html = self.render(data)
        if filename is None:
            from datetime import datetime
            filename = f"测试报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
