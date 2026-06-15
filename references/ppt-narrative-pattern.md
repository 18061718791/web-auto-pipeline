# 技术体系介绍 PPT 叙事结构模式

> 2026-06-09 由 web-auto-pipeline skill 介绍 PPT 的 3 轮迭代总结

## 核心原则

技术体系或 skill 的介绍 PPT 不是文档搬运，是**说服听众接受这个技术方案**的过程。叙事必须有一条自洽的逻辑链。

## 标准叙事结构

```
痛点引入         →  为什么需要这个方案
    ↓                （问题驱动，让听众共鸣）
解决思路         →  痛点→方案一对一映射
    ↓                （每个痛点有对应方案，不是孤立讲痛点）
演进脉络         →  从何而来、如何走到今天
    ↓                （原型→经验沉淀→框架化，体现合理性）
核心能力展开     →  逐项介绍方案做什么
    ↓                （平台架构/分类体系/报告/交互/组件）
实践案例         →  真实数据验证方案有效性
    ↓                （覆盖现状表 + 全量报告截图 + 发现的BUG）
核心价值总结     →  一句话记住这个方案
```

## 每页原则

| 环节 | 页数 | 要点 |
|:---|:---:|:---|
| 封面 | 1 | 标题 + 副标题（点名演进关系）|
| 痛点 | 1-2 | 4 个以内，每个痛点一句话讲清 |
| 解决思路 | 1 | 痛点→方案一对一连线，过渡页 |
| 演进 | 1-2 | 时间线或对比表，客观评价前身 |
| 核心能力 | 5-6 | 每页一个能力：架构/分类/报告/组件交互等 |
| 实践案例 | 2-3 | 覆盖表格 + 全量报告截图 + BUG 列表 |
| 价值总结 | 1 | 不超过 5 条，每条约 10 字 |
| Thank You | 1 | Q&A |

## 演示规范

- **颜色统一**：所有页面使用同一深色或浅色方案，不允许交替
- **深色系偏好**：页面 bg `#0B1926`，卡片 bg `#132B45`，强调色 `#F59E0B` / `#0891B2`
- **图片证据**：全量报告截图 + 单报告截图，具体说明关系
- **避免重复布局**：每页的卡片/表格/图示布局不重复
- **有截图的页面增加"全量报告 vs 单个报告"对比**，标记关联关系

## 程序化 PPT 生成（python-pptx）

本主机已安装 `python-pptx`（v1.0.2），可用 Python 脚本直接生成 .pptx 文件，无需手工拖拽。

### 核心实现模式

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)

BG_DARK   = RGBColor(0x0B, 0x19, 0x26)
CARD_BG   = RGBColor(0x13, 0x2B, 0x45)
ACCENT    = RGBColor(0xF5, 0x9E, 0x0B)
ACCENT2   = RGBColor(0x08, 0x91, 0xB2)
TEXT_W    = RGBColor(0xF0, 0xF6, 0xFC)
TEXT_G    = RGBColor(0x8B, 0x94, 0x9E)

def set_bg(slide, color=BG_DARK):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color

def add_card(slide, left, top, width, height, fill=CARD_BG, border=None):
    s = slide.shapes.add_shape(1, left, top, width, height)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if border: s.line.color.rgb = border; s.line.width = Pt(1)
    else: s.line.fill.background()
    return s

def add_txt(slide, left, top, width, height, text, sz=18, color=TEXT_W, bold=False, align=PP_ALIGN.LEFT):
    bx = slide.shapes.add_textbox(left, top, width, height)
    bx.text_frame.word_wrap = True
    p = bx.text_frame.paragraphs[0]
    p.text = text; p.font.size = Pt(sz); p.font.color.rgb = color
    p.font.bold = bold; p.font.name = 'Microsoft YaHei'; p.alignment = align
    return bx
```

### 布局元素策略

| 布局 | 实现方式 | 适用场景 |
|:---|:---|:---|
| 卡片 | add_card() + textbox | 并列模块 |
| 表格 | 矩形行叠加 + textbox | 对比表 |
| 时间线 | 横线 + 圆点 + 卡片排列 | 演进脉络 |
| 色条标题 | 顶部细矩形 + 标题 textbox | 统一风格 |
| 高亮条目 | 左侧竖条色块 + 右侧文本 | 痛点/价值 |

### 关键陷阱

- MSO_SHAPE_MIXED 不存在：用 add_shape(1, ...) 整数 1 代替
- 中文字体：必须显式 font.name = 'Microsoft YaHei'
- 图片不存在时 add_picture 抛异常：先 os.path.exists 检查
- 配色常量名一致：ACCENT_GOLD 非 ACENT_GOLD
