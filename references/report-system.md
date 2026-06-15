# Report System — 测试报告系统
> 附属于 `web-auto-pipeline` 技能

## 架构

双报告架构：
- **子报告**（`report_renderer.py`）：单脚本测试报告，含场景/步骤/断言/截图
- **全量报告**（`runner.py`）：多脚本聚合，含全局统计/数据依赖流/Modal iframe 弹窗

## 2026-06-10 升级变更

### cyberpunk 设计（统一风格）
- 深色主题 `#05070a` + CSS 变量（cyan/green/magenta/amber/purple）
- Google Fonts：DM Mono + Inter
- Canvas 星云动画（120粒子，鼠标交互）
- SVG 环形图（全量报告左侧状态）
- 指标卡片（全量报告右侧 3×2 网格）
- shimmer 动画进度条
- Modal iframe 弹窗（替代 target="_blank" 新开页）
- 场景卡片左侧强调色条 + hover 发光
- 断言徽章内联显示
- in-iframe 检测（子报告在 iframe 内隐藏星云背景）

### 断言汇总提取（Runner stdout 解析）

`TestCollector.get_data()` 在脚本末尾打印 `📊 断言: 通过X 失败Y`，runner.py 从 stdout 解析此模式。**所有使用 TestReport 的脚本自动生效**，无需额外配置。

### ⚠️ `_log_class` 优先级：汇总行不能标为红色

`runner.py` 的 `_log_class(line)` 原逻辑先检测关键词后着色，汇总行「总计: 9 通过 9 失败」因含"失败"关键词被标为红色（`log-err`）。

**修复方案（2026-06-10）**：
```python
def _log_class(line):
    # 汇总行优先判断 — 即使含"失败"也标记为中性色
    if any(kw in line for kw in ["∑", "总计", "📊", "断言:"]):
        return "log-info"
    if "失败" in line or "❌" in line:
        return "log-err"
    if "通过" in line or "✓" in line:
        return "log-ok"
    return "log-info"
```

### ⚠️ f-string CSS/JS 大括号转义陷阱

`runner.py` 和 `report_renderer.py` 的 HTML 模板使用 Python f-string (`f'''...'''`)。CSS 和 JS 中的 `{}` 需要用 `{{}}` 转义。特别容易遗漏的位置：

| 位置 | 后果 | 正确写法 |
|:---|:---|:---|
| JS 字符串内嵌 CSS | `{display: none}` 被 f-string 解析为变量 | `{{display: none}}` |
| CSS 规则块 | `body {{ color: var(--text) }}` 正确 | — |
| JS 模板字面量 `${var}` | `${this.color}` 被解析为 f-string 变量 | `${{this.color}}`（输出 `${this.color}`） |

**反复踩坑案例**（iframe onload CSS inject）：
```python
# ❌ 错误（NameError: name 'display' is not defined）
style.textContent = 'canvas { display: none !important; }';
# ✅ 正确
style.textContent = 'canvas {{ display: none !important; }}';
```

### PLATFORM_NAME 动态标题

在 `platforms/{id}/config.py` 中添加 `PLATFORM_NAME`，runner.py 在 hero 标题和页面 `<title>` 中引用：

```python
# platforms/iot/config.py
PLATFORM_NAME = "设备综合管理平台"

# runner.py HTML 模板
<title>{PLATFORM_NAME} · 任务控制报告</title>
<div class="hero__title">
  {PLATFORM_NAME}<br>自动化验证
</div>
```

与 `PLATFORM_ID` 不同，`PLATFORM_NAME` 是面向用户的显示名称。

## 2026-06-10 优化

### JSON 报告已弃用

`JsonRenderer.save()` 现为 no-op，不生成 `.json` 文件。`core/json_renderer.py` 的所有文件写入逻辑已移除。原因：用户不再需要 JSON 报告，仅保留 HTML。

如果将来需要恢复 JSON 输出，恢复 `json_renderer.py` 的 `save()` 方法即可（2026-06-10 版本保留了 `render()` 方法供可能的程序化消费）。

### 报告主题浅色化

保持 cyberpunk 风格的核心元素（渐变色标题、neon 强调色、星云动画、场景卡片动效），但整体背景改为浅色以减轻视觉疲劳：

| CSS 变量 | 旧（深色） | 新（浅色） |
|:---|:---|:---|
| `--bg` | `#05070a` | `#f0f2f5` |
| `--surface` | `#0b0e14` | `#ffffff` |
| `--text` | `#eef1f5` | `#1a1d23` |
| `--cyan` | `#36f0f0` | `#0ea5e9` |
| `--green` | `#70e59a` | `#10b981` |

配套调整：网格线改为浅灰（`rgba(0,0,0,0.04)`）、步骤背景淡化（`rgba(0,0,0,0.02)`）、卡片阴影减到 `rgba(0,0,0,0.04)`、星云粒子透明度降低（`opacity:0.35`）。详见 `core/report_renderer.py` 的 CSS `:root` 变量定义。
