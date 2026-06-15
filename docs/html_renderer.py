#!/usr/bin/env python3
"""
HTML 渲染器 — 平台功能结构树 + 内容区 + 搜索 + 面包屑
======================================================
- 左侧：功能结构树 + 搜索框
- 右侧：内容区 + 面包屑导航
- 支持 goal / prerequisites / time_estimate / dependency / faq / task / overview
- 截图支持文件引用 / data URI 嵌入
"""
import os
import base64
import re

STYLE = """@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap');

/* ── 科学仪器风格配色 ── */
:root {
    --primary: #0d7377;
    --primary-light: #e2f3f4;
    --primary-dark: #085b5e;
    --sidebar-bg: #111c2a;
    --sidebar-text: #b4c9e0;
    --sidebar-active: #00e5a0;
    --sidebar-indent: #1f3348;
    --accent-cyan: #00d4d4;
    --accent-green: #00e5a0;
    --accent-amber: #ffb300;
    --accent-orange: #ff6d00;
    --accent-rose: #e91e63;
    --text: #1a1d23;
    --text-secondary: #5f6368;
    --border: #d4d8dd;
    --bg: #f2f3f5;
    --bg-card: #ffffff;
    --tree-hover: rgba(0,229,160,0.08);
    --warning-bg: #fff3e0;
    --warning-border: #ffb300;
    --info-bg: #e0f7fa;
    --info-border: #00acc1;
    --important-bg: #fce4ec;
    --important-border: #e91e63;
    --success-bg: #e8f5e9;
    --success-border: #00c853;
    --search-highlight: #fff176;
    --shadow-sm: 0 1px 4px rgba(0,0,0,0.06);
    --shadow-md: 0 6px 20px rgba(13,115,119,0.12);
    --shadow-lg: 0 12px 40px rgba(0,0,0,0.15);
    --glow-cyan: 0 0 12px rgba(0,212,212,0.3);
    --glow-green: 0 0 12px rgba(0,229,160,0.3);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", "Microsoft YaHei", sans-serif;
    font-size: 15px; line-height: 1.8; color: var(--text); background: var(--bg);
}

.wrapper { display: flex; min-height: 100vh; }

/* ── 侧边栏：控制台面板风格 ── */
.sidebar {
    width: 280px; flex-shrink: 0;
    background: var(--sidebar-bg);
    border-right: 1px solid rgba(255,255,255,0.06);
    position: fixed; top: 0; left: 0;
    height: 100vh; overflow-y: auto;
    padding: 0;
    z-index: 100;
    display: flex; flex-direction: column;
}
/* 顶部霓虹灯带 */
.sidebar::before {
    content: ''; display: block;
    height: 3px; width: 100%; flex-shrink: 0;
    background: linear-gradient(90deg, var(--accent-cyan) 0%, var(--accent-green) 40%, var(--accent-amber) 70%, var(--accent-orange) 100%);
    box-shadow: 0 0 20px rgba(0,229,160,0.3);
}
.sidebar-header {
    padding: 20px 18px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 0; flex-shrink: 0;
    position: relative;
}
/* 示波器脉冲信号——签名元素 */
.sidebar-header::after {
    content: '';
    position: absolute; right: 18px; top: 50%; margin-top: -8px;
    width: 48px; height: 16px;
    background:
        linear-gradient(90deg, transparent 0%, var(--accent-green) 20%, transparent 22%,
                               transparent 25%, var(--accent-cyan) 40%, transparent 42%,
                               transparent 45%, var(--accent-green) 55%, var(--accent-amber) 60%, transparent 62%,
                               transparent 65%, var(--accent-cyan) 75%, transparent 77%);
    opacity: 0.6;
    mask: linear-gradient(90deg, transparent, #000 15%, #000 85%, transparent);
    -webkit-mask: linear-gradient(90deg, transparent, #000 15%, #000 85%, transparent);
}
.sidebar-header h2 {
    font-family: 'DM Mono', monospace;
    font-size: 12px; font-weight: 500;
    color: var(--accent-green); letter-spacing: 1.2px;
    text-transform: uppercase;
}
.sidebar-header h2::after {
    content: ''; display: block;
    width: 24px; height: 1.5px;
    background: var(--accent-cyan);
    margin-top: 6px;
}
.sidebar-header .version {
    font-size: 11px; color: rgba(255,255,255,0.35);
    margin-top: 6px; font-family: 'DM Mono', monospace;
}

/* 搜索 */
.sidebar-search {
    padding: 10px 14px; flex-shrink: 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.sidebar-search input {
    width: 100%; padding: 8px 10px 8px 32px;
    border: 1px solid rgba(255,255,255,0.12); border-radius: 6px;
    font-size: 13px; outline: none; color: var(--sidebar-text);
    background: rgba(0,0,0,0.3) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' fill='%23688'%3E%3Cpath d='M6 0a6 6 0 014.24 10.24l3.38 3.38-1.06 1.06-3.38-3.38A6 6 0 116 0zm0 1.5a4.5 4.5 0 100 9 4.5 4.5 0 000-9z'/%3E%3C/svg%3E") 9px center no-repeat;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.sidebar-search input:focus {
    border-color: var(--accent-cyan);
    box-shadow: 0 0 0 2px rgba(0,212,212,0.15);
}
.sidebar-search input::placeholder { color: rgba(255,255,255,0.25); }
.search-no-result { padding: 20px 16px; text-align: center; color: var(--sidebar-text); font-size: 13px; display: none; opacity: 0.5; }

.tree-wrapper { flex: 1; overflow-y: auto; }
.tree-wrapper::-webkit-scrollbar { width: 4px; }
.tree-wrapper::-webkit-scrollbar-track { background: transparent; }
.tree-wrapper::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

.tree { list-style: none; padding: 4px 0; }

/* ── 树节点 ── */
.tree-group { margin: 0; }

/* 外层 group：完整章节分隔 */
li.tree-group > .tree-group-header {
    display: flex; align-items: center; cursor: pointer;
    padding: 11px 18px 9px 18px; user-select: none;
    font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.55);
    letter-spacing: 1.5px; text-transform: uppercase;
    font-family: 'DM Mono', monospace;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin-top: 8px;
    transition: background 0.2s, color 0.2s;
}
li.tree-group > .tree-group-header:hover { background: var(--tree-hover); color: var(--accent-cyan); }
li.tree-group > .tree-group-header .toggle-icon {
    flex-shrink: 0; width: 16px; height: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; color: rgba(255,255,255,0.3);
    transition: transform 0.2s; margin-right: 8px;
}
li.tree-group > .tree-group-header .toggle-icon.expanded { transform: rotate(90deg); }

/* 内层 group */
.tree-group .tree-group .tree-group-header {
    display: flex; align-items: center; cursor: pointer;
    padding: 8px 18px 8px 28px; user-select: none;
    font-size: 13px; font-weight: 700; color: var(--accent-cyan);
    border-top: none; margin-top: 0;
    transition: background 0.2s, color 0.2s;
}
.tree-group .tree-group .tree-group-header:hover { background: var(--tree-hover); color: var(--accent-green); }
.tree-group .tree-group .tree-group-header .toggle-icon {
    flex-shrink: 0; width: 14px; height: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; color: var(--accent-cyan);
    transition: transform 0.2s; margin-right: 6px;
}
.tree-group .tree-group .tree-group-header .toggle-icon.expanded { transform: rotate(90deg); }

/* branch */
.tree-branch { margin: 0; }
.tree-branch-header {
    display: flex; align-items: center; cursor: pointer;
    padding: 6px 18px 6px 42px; user-select: none;
    font-size: 13px; font-weight: 500; color: var(--sidebar-text);
    transition: background 0.15s, color 0.15s;
    border-left: 2px solid transparent;
}
.tree-branch-header:hover { background: var(--tree-hover); color: var(--accent-green); border-left-color: var(--accent-green); }
.tree-branch-header .toggle-icon {
    flex-shrink: 0; width: 14px; height: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 8px; color: rgba(255,255,255,0.25);
    transition: transform 0.2s; margin-right: 6px;
}
.tree-branch-header .toggle-icon.expanded { transform: rotate(90deg); }

/* 根层级 branch */
ul.tree > li.tree-branch > .tree-branch-header {
    padding: 5px 18px 5px 18px;
    font-size: 14px; font-weight: 500; color: var(--sidebar-text);
    border-left: 2px solid transparent;
    margin: 0;
}
ul.tree > li.tree-branch > .tree-branch-header:hover {
    border-left-color: var(--accent-green);
    color: var(--accent-green);
}
ul.tree > li.tree-branch > .tree-branch-header .toggle-icon {
    font-size: 9px; color: rgba(255,255,255,0.3); margin-right: 8px;
}

/* 叶节点 */
.tree-leaf { margin: 0; }
.tree-leaf a {
    display: block; padding: 5px 18px 5px 48px;
    color: rgba(255,255,255,0.5); text-decoration: none;
    font-size: 13px; line-height: 1.6;
    border-left: 2px solid transparent;
    transition: all 0.15s; cursor: pointer;
}
.tree-leaf a:hover { color: var(--accent-green); background: var(--tree-hover); border-left-color: var(--accent-green); }

.tree-leaf.level-1 a {
    padding-left: 22px; font-size: 14px; font-weight: 500;
    color: var(--sidebar-text); border-left: 2px solid transparent;
}
.tree-leaf.level-1 a:hover { border-left-color: var(--accent-cyan); color: var(--accent-cyan); }

.tree-leaf.level-2 a { padding-left: 56px; font-size: 12.5px; color: rgba(255,255,255,0.4); }
.tree-leaf.level-3 a { padding-left: 64px; font-size: 12px; color: rgba(255,255,255,0.35); }
.tree-leaf.level-4 a { padding-left: 72px; font-size: 11.5px; color: rgba(255,255,255,0.3); }

.tree-leaf.active a {
    color: var(--accent-green) !important; font-weight: 600;
    border-left-color: var(--accent-green) !important;
    background: rgba(0,229,160,0.08);
    box-shadow: inset 3px 0 0 0 var(--accent-green);
}

.tree-children { list-style: none; padding: 0; margin: 0; }
.tree-children.collapsed { display: none; }

.tree-leaf.search-hidden, .tree-branch.search-hidden, .tree-group.search-hidden { display: none !important; }
.tree-leaf.search-match a { color: var(--accent-cyan) !important; font-weight: 600; }
.tree-group-header.search-match, .tree-branch-header.search-match { color: var(--accent-cyan) !important; font-weight: 600; }
mark.search-highlight { background: var(--search-highlight); padding: 0 2px; border-radius: 2px; color: #333; }


/* ── 内容区 ── */
.content {
    flex: 1; margin-left: 280px;
    max-width: 1000px; padding: 0 70px 80px;
    background: var(--bg-card);
    box-shadow: 0 0 60px rgba(0,0,0,0.04), -4px 0 20px rgba(0,0,0,0.03);
    min-height: 100vh;
    position: relative;
}

.breadcrumb {
    position: sticky; top: 0; z-index: 50;
    background: rgba(255,255,255,0.95); backdrop-filter: blur(12px);
    padding: 14px 0; margin-bottom: 8px;
    font-size: 13px; color: var(--text-secondary);
    border-bottom: 1px solid var(--border);
    letter-spacing: 0.2px;
}
.breadcrumb span { color: var(--primary); font-weight: 600; }
.breadcrumb span.sep { color: #bbb; margin: 0 4px; }

.cover { text-align: center; padding: 70px 0 56px; margin-bottom: 48px; position: relative; }
.cover::before {
    content: ''; display: block;
    position: absolute; top: 0; left: 50%; transform: translateX(-50%);
    height: 2px; width: 120px;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green), var(--accent-amber));
    border-radius: 1px;
}
.cover::after {
    content: ''; display: block;
    height: 1px; width: 60px; margin: 0 auto;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
    opacity: 0.5;
}
.cover h1 {
    font-family: 'Inter', sans-serif;
    font-size: 32px; font-weight: 700;
    color: var(--primary-dark); margin-bottom: 10px;
    letter-spacing: -0.5px;
}
.cover .meta { color: var(--text-secondary); font-size: 14px; line-height: 2.2; }

h2.module-title {
    font-family: 'Inter', sans-serif;
    font-size: 22px; font-weight: 700;
    color: var(--primary-dark);
    padding-bottom: 10px;
    margin: 48px 0 24px;
    position: relative;
}
h2.module-title::after {
    content: ''; display: block;
    position: absolute; bottom: 0; left: 0;
    width: 100%; height: 2px;
    background: linear-gradient(90deg, var(--primary) 0%, var(--accent-green) 50%, transparent 100%);
    border-radius: 1px;
}
h3.sub-title {
    font-family: 'Inter', sans-serif;
    font-size: 17px; font-weight: 600;
    color: var(--text);
    margin: 32px 0 16px; padding-left: 14px;
    border-left: 3px solid var(--accent-cyan);
    position: relative;
}
h3.sub-title::before {
    content: ''; position: absolute;
    left: -3px; top: 0; bottom: 0; width: 3px;
    background: linear-gradient(180deg, var(--accent-cyan), var(--accent-green));
}
h4.step-title { font-size: 15px; font-weight: 600; margin: 24px 0 8px; color: var(--text); }

p { margin: 12px 0; color: var(--text); line-height: 1.8; }
p.desc { color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; letter-spacing: 0.1px; }

/* ── P2: 三要素卡片 ── */
.meta-bar {
    display: flex; gap: 12px; margin: 16px 0 24px; flex-wrap: wrap;
}
.meta-item {
    display: flex; align-items: center; gap: 8px;
    padding: 10px 18px; border-radius: 8px; font-size: 13px;
    background: var(--bg); border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.2s;
}
.meta-item:hover { box-shadow: var(--shadow-md); }
.meta-item .icon { font-size: 16px; }
.meta-item.goal { border-color: var(--info-border); }
.meta-item.time { border-color: var(--success-border); }
.meta-item.prereq { border-color: var(--warning-border); }

/* ── P2: 学习目标 ── */
.goal-box {
    background: linear-gradient(135deg, var(--info-bg), #e8f9fa);
    border-left: 4px solid var(--accent-cyan);
    padding: 18px 22px; margin: 16px 0; border-radius: 0 10px 10px 0;
    font-size: 14px; box-shadow: var(--shadow-sm);
    position: relative;
}
.goal-box strong { color: var(--primary-dark); display: block; margin-bottom: 6px; font-size: 15px; }

/* ── P2: 前置条件 ── */
.prereq-box {
    background: var(--warning-bg);
    border-left: 4px solid var(--warning-border);
    padding: 14px 18px; margin: 12px 0; border-radius: 0 8px 8px 0;
    font-size: 14px; box-shadow: var(--shadow-sm);
}
.prereq-box strong { color: #b45100; display: block; margin-bottom: 4px; }
.prereq-box ul { margin: 4px 0 0 16px; }
.prereq-box li { padding: 2px 0; color: var(--text-secondary); }

/* ── P0: 依赖标注 ── */
.dep-box {
    background: linear-gradient(135deg, #fff8e6, #fff3d6);
    border: 1px solid var(--warning-border);
    padding: 16px 20px; margin: 20px 0; border-radius: 10px;
    font-size: 13px; color: #bf5a00;
    box-shadow: var(--shadow-sm);
}
.dep-box strong { display: block; margin-bottom: 4px; font-size: 14px; color: #a04a00; }
.dep-box a { color: var(--primary); }

/* ── P1: 任务卡片 ── */
.task-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px 28px; margin: 18px 0;
    transition: box-shadow 0.25s, transform 0.2s; cursor: default;
    box-shadow: var(--shadow-sm);
    position: relative;
}
.task-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
    border-radius: 12px 12px 0 0;
}
.task-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.task-card h4 {
    font-family: 'Inter', sans-serif;
    font-size: 16px; font-weight: 600; color: var(--text); margin-bottom: 6px;
}
.task-card .task-goal { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
.task-card ol { margin-left: 20px; font-size: 14px; line-height: 2.2; color: var(--text); }
.task-card a { color: var(--primary); text-decoration: none; font-weight: 500; }
.task-card a:hover { text-decoration: underline; }

/* ── P3: FAQ ── */
.faq-item {
    border-bottom: 1px solid var(--border); padding: 18px 0;
    transition: background 0.2s, padding-left 0.2s;
}
.faq-item:hover { background: #f8f9fb; padding-left: 4px; }
.faq-q {
    font-weight: 600; font-size: 15px; color: var(--text);
    cursor: pointer; display: flex; align-items: flex-start; gap: 10px;
    user-select: none;
}
.faq-q .faq-icon {
    color: var(--accent-cyan); flex-shrink: 0; font-size: 16px;
    transition: transform 0.2s;
}
.faq-item.open .faq-icon { transform: rotate(90deg); }
.faq-a {
    margin-top: 8px; padding-left: 26px;
    font-size: 14px; color: var(--text-secondary); line-height: 1.8;
    display: none;
}
.faq-item.open .faq-a { display: block; animation: fadeIn 0.25s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
.faq-a a { color: var(--primary); text-decoration: none; font-weight: 500; }
.faq-a a:hover { text-decoration: underline; }

/* ── P0: 平台总览 ── */
.overview-box {
    background: linear-gradient(135deg, var(--info-bg), #e8f9fa); border: 1px solid var(--info-border);
    border-radius: 10px; padding: 18px 22px; margin: 16px 0; font-size: 14px;
    box-shadow: var(--shadow-sm);
    border-left: 3px solid var(--accent-cyan);
}
.overview-box h4 { margin-bottom: 10px; font-size: 15px; color: var(--primary-dark); font-weight: 600; }

.step-number {
    display: inline-flex; align-items: center; justify-content: center;
    width: 30px; height: 30px;
    background: linear-gradient(135deg, var(--primary), var(--accent-cyan));
    color: #fff;
    border-radius: 50%; font-size: 13px; font-weight: 700; margin-right: 10px;
    font-family: 'DM Mono', monospace;
    box-shadow: 0 2px 6px rgba(0,212,212,0.3);
    transition: box-shadow 0.2s, transform 0.2s;
}
h4.step-title:hover .step-number { box-shadow: 0 4px 12px rgba(0,212,212,0.4); transform: scale(1.05); }

.screenshot-container {
    margin: 14px 0 22px;
    border: 1px solid var(--border); border-radius: 10px; overflow: hidden;
    cursor: pointer; transition: box-shadow 0.25s, transform 0.2s, border-color 0.2s;
    box-shadow: var(--shadow-sm);
}
.screenshot-container:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
    border-color: var(--accent-cyan);
}
.screenshot-container img { display: block; width: 100%; height: auto; }

.field-table {
    width: 100%; border-collapse: separate; border-spacing: 0;
    margin: 20px 0; font-size: 14px;
    border-radius: 10px; overflow: hidden;
    box-shadow: var(--shadow-sm);
}
.field-table th {
    background: linear-gradient(135deg, var(--primary-dark), var(--primary));
    padding: 13px 18px; text-align: left;
    font-weight: 600; color: #fff; font-size: 13px; letter-spacing: 0.4px;
    border-bottom: none;
}
.field-table td { padding: 12px 18px; border-bottom: 1px solid var(--border); color: var(--text); }
.field-table tr:last-child td { border-bottom: none; }
.field-table tr:hover td { background: rgba(0,212,212,0.04); }

.concept-box {
    background: linear-gradient(135deg, var(--info-bg), #e8f9fa);
    border-left: 4px solid var(--accent-cyan);
    padding: 18px 22px; margin: 16px 0; border-radius: 0 10px 10px 0;
    box-shadow: var(--shadow-sm);
}
.concept-box h4 { color: var(--primary-dark); margin-bottom: 8px; font-size: 15px; font-weight: 600; }
.concept-box p { color: var(--text-secondary); font-size: 14px; margin: 0; line-height: 1.8; }

.note-box { padding: 16px 20px; margin: 16px 0; border-radius: 10px; font-size: 14px; border-left: 4px solid; box-shadow: var(--shadow-sm); }
.note-box.info { background: var(--info-bg); border-color: var(--info-border); color: #0c6b7a; }
.note-box.warning { background: var(--warning-bg); border-color: var(--warning-border); color: #b45100; }
.note-box.important { background: var(--important-bg); border-color: var(--important-border); color: #a31545; }
.note-box.success { background: var(--success-bg); border-color: var(--success-border); color: #1b7a34; }
.note-box strong:first-child { display: block; margin-bottom: 4px; }

.page-desc-box { background: linear-gradient(135deg, var(--info-bg), #e8f9fa); border: 1px solid var(--info-border); border-radius: 10px; padding: 18px 22px; margin: 16px 0; box-shadow: var(--shadow-sm); border-left: 3px solid var(--accent-cyan); }
.page-desc-box h4 { margin-bottom: 10px; font-size: 15px; color: var(--primary-dark); font-weight: 600; }

.footer { text-align: center; color: var(--text-secondary); font-size: 12px; padding: 40px 0 20px; border-top: 1px solid var(--border); margin-top: 60px; }

/* ── 灯箱动画 ── */
@keyframes lightboxFadeIn { from { opacity: 0; transform: scale(0.92); } to { opacity: 1; transform: scale(1); } }
.lightbox-overlay {
    position: fixed; inset: 0; z-index: 9999;
    background: rgba(0,0,0,0.85); cursor: zoom-out;
    display: flex; align-items: center; justify-content: center;
    animation: lightboxFadeIn 0.2s ease-out;
}
.lightbox-overlay img {
    max-width: 92vw; max-height: 92vh;
    border-radius: 6px; box-shadow: 0 8px 40px rgba(0,0,0,0.5);
}

@media print { .sidebar { display: none; } .content { margin-left: 0; padding: 20px 40px; max-width: 100%; } .breadcrumb { display: none; } }
@media (max-width: 768px) { .sidebar { display: none; } .content { margin-left: 0; padding: 20px; } }

.lightbox { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 99999; cursor: zoom-out; justify-content: center; align-items: center; }
.lightbox.show { display: flex; }
.lightbox img { max-width: 95%; max-height: 95%; object-fit: contain; border-radius: 4px; }

.content .no-search-result { display: none; text-align: center; padding: 60px 0; color: var(--text-secondary); font-size: 16px; }
.content .no-search-result.show { display: block; }
.content section.search-hidden { display: none !important; }
"""

JS = """
function toggleTree(id, type) {
    var children = document.getElementById('tc-' + id);
    var icon = document.getElementById('ti-' + id);
    if (!children || !icon) return;
    var isCollapsed = children.classList.toggle('collapsed');
    icon.classList.toggle('expanded', !isCollapsed);
}

function showLightbox(src) {
    document.getElementById('lightbox-img').src = src;
    document.getElementById('lightbox').classList.add('show');
}
document.addEventListener('keydown', function(e) {
    if(e.key === 'Escape') document.getElementById('lightbox').classList.remove('show');
});

(function() {
    var anchors = [];
    document.querySelectorAll('h2.module-title[id]').forEach(function(el) {
        anchors.push({id: el.id, top: el.offsetTop});
    });
    document.querySelectorAll('.step-item[id]').forEach(function(el) {
        anchors.push({id: el.id, top: el.offsetTop});
    });

    function updateActive() {
        var scrollY = window.scrollY + 120;
        var activeId = null;
        for (var i = anchors.length - 1; i >= 0; i--) {
            if (anchors[i].top <= scrollY) { activeId = anchors[i].id; break; }
        }
        document.querySelectorAll('.tree-leaf.active').forEach(function(el) { el.classList.remove('active'); });
        if (activeId) {
            var leaf = document.getElementById('tleaf-' + activeId);
            if (leaf) leaf.classList.add('active');
        }
        updateBreadcrumb(activeId);
    }

    window.addEventListener('scroll', updateActive);
    setTimeout(updateActive, 200);
})();

var breadcrumbMap = {};
(function buildBreadcrumbMap() {
    var tree = document.getElementById('sidebar-tree');
    if (!tree) return;
    function walk(node, path) {
        var children = node.children;
        for (var i = 0; i < children.length; i++) {
            var child = children[i];
            if (child.classList.contains('tree-group')) {
                var hdr = child.querySelector('.tree-group-header span:nth-child(2)');
                var title = hdr ? hdr.textContent.trim() : '';
                var subUl = child.querySelector('.tree-children');
                if (subUl) walk(subUl, path.concat([title]));
            } else if (child.classList.contains('tree-branch')) {
                var hdr2 = child.querySelector('.tree-branch-header span:nth-child(2)');
                var title2 = hdr2 ? hdr2.textContent.trim() : '';
                var subUl2 = child.querySelector('.tree-children');
                if (subUl2) walk(subUl2, path.concat([title2]));
            } else if (child.classList.contains('tree-leaf')) {
                var a = child.querySelector('a');
                if (a) {
                    var href = a.getAttribute('href');
                    if (href && href.startsWith('#')) {
                        breadcrumbMap[href.substring(1)] = path.concat([a.textContent.trim()]);
                    }
                }
            }
        }
    }
    walk(tree, []);
})();

function updateBreadcrumb(activeId) {
    var bc = document.getElementById('breadcrumb');
    if (!bc) return;
    if (!activeId) { bc.innerHTML = '<span>首页</span>'; return; }
    var path = breadcrumbMap[activeId];
    if (!path) {
        var m = /^(.+)-step-\\d+$/.exec(activeId);
        if (m) {
            Object.keys(breadcrumbMap).forEach(function(k) {
                if (k === m[1] || k.indexOf(m[1]) === 0) { if (!path) path = breadcrumbMap[k]; }
            });
        }
        if (!path) {
            Object.keys(breadcrumbMap).forEach(function(k) {
                if (activeId.indexOf(k) === 0 && !path) path = breadcrumbMap[k];
            });
        }
    }
    if (!path) { bc.innerHTML = '<span>首页</span>'; return; }
    var html = path.map(function(p, i) {
        if (i < path.length - 1) return '<span>' + p + '</span><span class="sep">›</span>';
        else return '<span>' + p + '</span>';
    }).join('');
    bc.innerHTML = html;
}

/* ── FAQ 展开/收起 ── */
document.addEventListener('click', function(e) {
    var faqQ = e.target.closest('.faq-q');
    if (faqQ) {
        var faqItem = faqQ.closest('.faq-item');
        if (faqItem) faqItem.classList.toggle('open');
    }
});

/* ── 全文搜索 ── */
(function() {
    var searchInput = document.getElementById('search-input');
    var noResultTip = document.getElementById('search-no-result');
    var contentSections = document.querySelectorAll('.content section.module-section');
    var allLeafItems = document.querySelectorAll('.tree-leaf');
    var allBranches = document.querySelectorAll('.tree-branch');
    var allGroups = document.querySelectorAll('.tree-group');
    var contentNoResult = document.getElementById('content-no-result');

    if (!searchInput) return;

    searchInput.addEventListener('input', function() {
        var query = this.value.trim().toLowerCase();
        var hasQuery = query.length > 0;

        allLeafItems.forEach(function(l) { l.classList.remove('search-hidden', 'search-match'); });
        allBranches.forEach(function(b) { b.classList.remove('search-hidden', 'search-match'); });
        allGroups.forEach(function(g) { g.classList.remove('search-hidden', 'search-match'); });
        if (contentNoResult) contentNoResult.classList.remove('show');
        noResultTip.style.display = 'none';

        document.querySelectorAll('mark.search-highlight').forEach(function(m) {
            var p = m.parentNode;
            p.replaceChild(document.createTextNode(m.textContent), m);
            p.normalize();
        });

        if (!hasQuery) {
            contentSections.forEach(function(s) { s.classList.remove('search-hidden'); });
            return;
        }

        var matchedSections = new Set();

        contentSections.forEach(function(section) {
            var textContent = section.textContent.toLowerCase();
            var sectionId = section.getAttribute('data-id') || '';
            if (textContent.indexOf(query) >= 0) {
                section.classList.remove('search-hidden');
                matchedSections.add(sectionId);
            } else {
                section.classList.add('search-hidden');
            }
        });

        if (matchedSections.size > 0) {
            allLeafItems.forEach(function(leaf) {
                var a = leaf.querySelector('a');
                if (!a) return;
                var href = a.getAttribute('href') || '';
                var id = href.replace('#', '');
                leaf.classList.add(matchedSections.has(id) ? 'search-match' : 'search-hidden');
            });

            allBranches.forEach(function(branch) {
                var children = branch.querySelector('.tree-children');
                if (!children) return;
                var visible = children.querySelectorAll('.tree-leaf:not(.search-hidden)');
                if (visible.length === 0) { branch.classList.add('search-hidden'); }
                else { branch.classList.add('search-match'); }
            });

            allGroups.forEach(function(group) {
                var children = group.querySelector('.tree-children');
                if (!children) return;
                var visible = children.querySelectorAll('.tree-branch:not(.search-hidden), .tree-leaf:not(.search-hidden)');
                if (visible.length === 0) { group.classList.add('search-hidden'); }
                else { group.classList.add('search-match'); }
            });

            noResultTip.style.display = 'none';
            if (contentNoResult) contentNoResult.classList.remove('show');
        } else {
            noResultTip.style.display = 'block';
            if (contentNoResult) contentNoResult.classList.add('show');
        }

        highlightMatches(query);
    });

    function highlightMatches(query) {
        if (!query) return;
        var walker = document.createTreeWalker(
            document.querySelector('.content'), NodeFilter.SHOW_TEXT, null, false
        );
        var textNodes = [];
        while (walker.nextNode()) textNodes.push(walker.currentNode);

        textNodes.forEach(function(node) {
            var parent = node.parentNode;
            if (parent.closest('script,style,mark,.sidebar')) return;
            var text = node.textContent.toLowerCase();
            var idx = text.indexOf(query);
            if (idx >= 0) {
                var span = document.createElement('span');
                span.innerHTML = escapeHtml(node.textContent.substring(0, idx)) +
                    '<mark class="search-highlight">' +
                    escapeHtml(node.textContent.substring(idx, idx + query.length)) +
                    '</mark>' +
                    escapeHtml(node.textContent.substring(idx + query.length));
                parent.replaceChild(span, node);
            }
        });
    }

    function escapeHtml(text) {
        return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
})();
"""


def _make_id(text):
    aid = re.sub(r'[^\w\u4e00-\u9fff]+', '-', text)
    return aid.strip('-').lower() or "section"


def _img_to_data_uri(image_dir, filename):
    if not filename:
        return ""
    filepath = os.path.join(image_dir, filename)
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        ext = os.path.splitext(filename)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    except:
        return ""


_MODULE_NAMES = {
    "pv": "PV管理", "element_model": "元件模型", "element": "元件",
    "device_model": "设备模型", "device": "设备", "sn": "SN管理",
    "bypass": "Bypass管理", "批次导入": "批次导入",
}
def _module_name(module_id):
    return _MODULE_NAMES.get(module_id, module_id)


def _render_child(child, mid, image_dir, embed_images, step_num, step_count_ref):
    """渲染单个 child 元素为 HTML 片段"""
    ct = child["type"]

    if ct == "goal":
        return f'<div class="goal-box"><strong>🎯 学习目标</strong><p style="margin:4px 0 0;color:var(--text);">{child["text"]}</p></div>'

    elif ct == "time_estimate":
        mins = child.get("minutes", 0)
        emoji = "⏱️" if mins <= 5 else "⏳"
        return f'<div class="meta-bar"><div class="meta-item time"><span class="icon">{emoji}</span>预计 {mins} 分钟</div></div>'

    elif ct == "prerequisites":
        items_html = "".join(f"<li>{it}</li>" for it in child.get("items", []))
        return f'<div class="prereq-box"><strong>📋 前置条件</strong><ul>{items_html}</ul></div>'

    elif ct == "dependency":
        deps = child.get("depends_on", [])
        note = child.get("note", "")
        if not deps and not note:
            return ""
        deps_links = "、".join(f'<a href="#{_make_id(d)}">{d}</a>' for d in deps)
        dep_text = f'数据依赖：{deps_links}' if deps else ""
        note_text = f'<div style="margin-top:4px;">{note}</div>' if note else ""
        return f'<div class="dep-box"><strong>🔗 前置依赖</strong>{dep_text}{note_text}</div>'

    elif ct == "faq":
        return f"""
        <div class="faq-item">
            <div class="faq-q"><span class="faq-icon">Q:</span><span>{child["question"]}</span></div>
            <div class="faq-a"><strong>A:</strong> {child["answer"]}</div>
        </div>
        """

    elif ct == "task":
        steps_html = "\n".join(f"<li>{s}</li>" for s in child.get("steps", []))
        goal = child.get("goal", "")
        goal_html = f'<div class="task-goal">{goal}</div>' if goal else ""
        task_id = _make_id(child["title"])
        return f"""
        <div class="task-card" id="{task_id}">
            <h4>{child["title"]}</h4>
            {goal_html}
            <ol>{steps_html}</ol>
        </div>
        """

    elif ct == "overview":
        return f"""
        <div class="overview-box">
            <h4>{child["title"]}</h4>
            {child["content"]}
        </div>
        """

    elif ct == "sub_heading":
        cid = f"{mid}-{_make_id(child['title'])}"
        return f'<h3 class="sub-title" id="{cid}">{child["title"]}</h3>'

    elif ct == "concept":
        return f'<div class="concept-box"><h4>{child["title"]}</h4><p>{child["text"]}</p></div>'

    elif ct == "note":
        level = child.get("level", "info")
        label = {"info": "💡 提示", "warning": "⚠️ 注意", "important": "🚫 重要"}[level]
        return f'<div class="note-box {level}"><strong>{label}</strong>{child["text"]}</div>'

    elif ct == "glossary":
        rows = "".join(
            f"<tr><td><strong>{item['term']}</strong></td>"
            f"<td>{item['definition']}"
            + (f'（参见 <a href="#{item.get("module_ref","")}">{item["module_ref"]}</a>）' if item.get('module_ref') else "")
            + "</td></tr>"
            for item in child.get("items", []))
        return (f'<table class="field-table">'
                f'<tr><th style="width:30%;">术语</th><th>定义</th></tr>{rows}</table>')

    elif ct == "role_matrix":
        rows = "".join(
            f"<tr><td><strong>{item['role']}</strong></td>"
            f"<td>{item['permissions']}</td></tr>"
            for item in child.get("items", []))
        return (f'<table class="field-table">'
                f'<tr><th style="width:20%;">角色</th><th>权限范围</th></tr>{rows}</table>')

    elif ct == "quick_start":
        steps_html = "".join(
            f'<li><strong>{s["action"]}</strong> — {s["description"]}'
            + (f'（详见 <a href="#{s.get("module_ref","")}">{s.get("module_name", s["module_ref"])}</a>）' if s.get('module_ref') else "")
            + "</li>"
            for s in child.get("steps", []))
        return (f'<div class="goal-box">'
                f'<strong>⏱️ {child.get("title","快速入门")}</strong>'
                f'<ol style="margin-top:8px;line-height:2.2;">{steps_html}</ol></div>')

    elif ct == "end_to_end":
        flow = child.get("flow", [])
        steps_parts = []
        for i, s in enumerate(flow):
            module_link = f'（<a href="#{s.get("module","")}">{_module_name(s["module"])}</a>）' if s.get('module') else ""
            desc_html = f'<div style="font-size:13px;color:var(--text-secondary);margin-top:4px;line-height:1.5;">{s["description"]}</div>' if s.get('description') else ""
            step_div = (f'<div style="display:flex;flex-direction:column;align-items:center;text-align:center;'
                        f'padding:14px 20px;background:var(--primary-light);border-radius:10px;border:1px solid var(--primary);'
                        f'font-size:14px;font-weight:600;max-width:480px;width:100%;">'
                        f'<span>{s["step"]}{module_link}</span>{desc_html}</div>')
            arrow = (f'<div style="font-size:20px;color:var(--primary);margin:6px 0;">↓</div>'
                     if i < len(flow) - 1 else "")
            steps_parts.append(step_div + arrow)
        return (f'<div class="dep-box">'
                f'<strong>📊 {child.get("title","")}</strong>'
                f'<div style="margin-top:12px;display:flex;flex-direction:column;align-items:center;gap:0;">{"".join(steps_parts)}</div></div>')

    elif ct == "appendix_section":
        return ""

    elif ct == "field_dictionary":
        tables_html = ""
        for table in child.get("tables", []):
            rows = "".join(
                f"<tr><td>{f.get('name','')}</td><td>{f.get('type','')}</td>"
                f"<td>{'✅' if f.get('required') else '❌'}</td><td>{f.get('desc','')}</td></tr>"
                for f in table.get("fields", []))
            tables_html += (f'<h5 style="margin:20px 0 6px;font-size:14px;color:var(--text-secondary);">'
                           f'{table.get("table","")}</h5>')
            tables_html += (f'<table class="field-table">'
                           f'<tr><th>字段</th><th>类型</th><th>必填</th><th>说明</th></tr>{rows}</table>')
        return tables_html

    elif ct == "state_machine":
        def _sm_transition(t):
            return "{0} → {1}（{2}）".format(t.get("from",""), t.get("to",""), t.get("action",""))
        rows = "".join(
            f"<tr><td>{sm['entity']}</td>"
            f"<td>{' → '.join(sm.get('states',[]))}</td>"
            f"<td><br>".join(_sm_transition(t) for t in sm.get('transitions',[])) + "</td></tr>"
            for sm in child.get("items", []))
        return (f'<table class="field-table">'
                f'<tr><th style="width:30%;">实体</th><th style="width:25%;">状态</th><th>状态转换</th></tr>{rows}</table>')

    elif ct == "revision":
        rows = "".join(
            f"<tr><td>{r['version']}</td><td>{r['date']}</td>"
            f"<td>{'、'.join(r.get('changes',[]))}</td></tr>"
            for r in child.get("items", []))
        return (f'<table class="field-table">'
                f'<tr><th style="width:12%;">版本</th><th style="width:18%;">日期</th><th>变更内容</th></tr>{rows}</table>')


    elif ct == "appendix":
        parts = []
        for sub in child.get("sections", []):
            st = sub["type"]
            title = sub.get("title", "")
            item = {"type": st, "title": title}
            if st == "field_dictionary":
                item["tables"] = sub.get("tables", [])
            elif st == "state_machine":
                item["items"] = sub.get("items", [])
            elif st == "revision":
                item["items"] = sub.get("items", [])
            rendered = _render_child(item, mid, image_dir, embed_images, step_num, step_count_ref)
            if rendered:
                parts.append(f'<h4 style="margin:28px 0 10px;font-size:16px;color:var(--text);border-bottom:1px solid var(--border);padding-bottom:6px;">{title}</h4>')
                parts.append(rendered)
        return "".join(parts)

    elif ct == "page_desc":
        fields_html = "".join(
            f"<tr><td>{f.get('name','')}</td><td>{f.get('desc','')}</td></tr>"
            for f in child.get("fields", []))
        return (f'<div class="page-desc-box"><h4>{child["title"]}</h4>'
                f'<table class="field-table"><tr><th>字段</th><th>说明</th></tr>{fields_html}</table></div>')

    elif ct == "field_table":
        rows = "".join(
            f"<tr><td>{f.get('name','')}</td><td>{f.get('type','')}</td><td>{f.get('required','')}</td><td>{f.get('desc','')}</td></tr>"
            for f in child.get("fields", []))
        return (f'<h4 style="margin:20px 0 8px;font-size:15px;">{child["title"]}</h4>'
                f'<table class="field-table"><tr><th>字段</th><th>类型</th><th>必填</th><th>说明</th></tr>{rows}</table>')

    elif ct == "step":
        step_count_ref[0] += 1
        nn = next(step_num)
        desc = child["description"]
        cid = f"{mid}-step-{nn}"
        img_path = child.get("screenshot_path", "")
        if embed_images:
            img_src = _img_to_data_uri(image_dir, img_path)
        else:
            img_src = f"images/{img_path}" if img_path else ""
        img_html = (
            f'<div class="screenshot-container" onclick="showLightbox(this.querySelector(\'img\').src)">'
            f'<img src="{img_src}" alt="步骤{step_count_ref[0]}截图" loading="lazy"></div>'
        ) if img_src else ""
        return (f'<div class="step-item" id="{cid}">'
                f'<h4 class="step-title"><span class="step-number">{step_count_ref[0]}</span>{desc}</h4>{img_html}</div>')

    else:
        return ""


def render_html(data, output_dir, embed_images=False):
    image_dir = os.path.join(output_dir, "images")
    step_num = iter(range(1, 10000))

    sections_map = {}
    for sec in data.get("sections", []):
        sections_map[sec["id"]] = sec
        sections_map[sec["title"]] = sec

    tree = data.get("tree", [])
    if not tree:
        return _render_fallback(data, output_dir, embed_images)

    tree_html = []
    content_parts = []

    content_parts.append(f"""
    <div class="cover">
        <h1>{data['title']}</h1>
        <div class="meta"><div>版本：V{data['version']}</div><div>日期：{data['date']}</div></div>
    </div>
    """)

    def render_tree_node(node, level=1):
        t = node.get("type", "leaf")
        title = node.get("title", "")
        node_id = _make_id(title)

        if t == "group":
            children = node.get("children", [])
            kids_tree = []
            kids_content = []
            for child in children:
                kt, kc = render_tree_node(child, level + 1)
                kids_tree.append(kt)
                kids_content.append(kc)
            ch_tree = "\n".join(kids_tree)
            ch_content = "\n".join(kids_content)
            group_tree = f"""
            <li class="tree-group">
                <div class="tree-group-header" onclick="toggleTree('{node_id}','group')">
                    <span class="toggle-icon" id="ti-{node_id}">▶</span>
                    <span>{title}</span>
                </div>
                <ul class="tree-children collapsed" id="tc-{node_id}">{ch_tree}</ul>
            </li>
            """
            return group_tree, ch_content

        elif t == "branch":
            children = node.get("children", [])
            branch_cid = node.get("content_id")
            kids_tree = []
            kids_content = []
            
            # If branch has its own content_id, render its section too
            sec_html = ""
            if branch_cid:
                sec = sections_map.get(branch_cid) or sections_map.get(title)
                if sec and sec.get("children"):
                    mid = sec["id"]
                    sec_children = []
                    step_count_ref = [0]
                    sec_children.append(f'<section class="module-section" data-id="{mid}">')
                    sec_children.append(f'<h2 class="module-title" id="{mid}">{sec["title"]}</h2>')
                    if sec.get("description"):
                        sec_children.append(f'<p class="desc">{sec["description"]}</p>')
                    meta_parts = []
                    content_parts_list = []
                    for child in sec.get("children", []):
                        ct = child["type"]
                        if ct in ("time_estimate",):
                            meta_parts.append(_render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))
                        elif ct in ("goal", "prerequisites"):
                            content_parts_list.insert(0, _render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))
                        elif ct == "dependency":
                            content_parts_list.append(_render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))
                        else:
                            content_parts_list.append(_render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))
                    sec_children.extend(meta_parts)
                    sec_children.extend(content_parts_list)
                    sec_children.append("</section>")
                    sec_html = "\n".join(sec_children)
            
            if sec_html:
                kids_content.append(sec_html)
            
            for child in children:
                kt, kc = render_tree_node(child, level + 1)
                kids_tree.append(kt)
                kids_content.append(kc)
            ch_tree = "\n".join(kids_tree)
            ch_content = "\n".join(kids_content)
            branch_tree = f"""
            <li class="tree-branch">
                <div class="tree-branch-header" onclick="toggleTree('{node_id}','branch')">
                    <span class="toggle-icon" id="ti-{node_id}">▶</span>
                    <span>{title}</span>
                </div>
                <ul class="tree-children collapsed" id="tc-{node_id}">{ch_tree}</ul>
            </li>
            """
            return branch_tree, ch_content

        else:
            content_id = node.get("content_id", node_id)
            href_id = content_id
            content_html = ""

            sec = sections_map.get(content_id) or sections_map.get(title)
            if sec and sec.get("children"):
                mid = sec["id"]
                sec_children = []
                step_count_ref = [0]

                sec_children.append(f'<section class="module-section" data-id="{mid}">')
                sec_children.append(f'<h2 class="module-title" id="{mid}">{sec["title"]}</h2>')
                if sec.get("description"):
                    sec_children.append(f'<p class="desc">{sec["description"]}</p>')

                # 先收集 meta 信息集中展示
                meta_parts = []
                content_parts_list = []
                for child in sec.get("children", []):
                    ct = child["type"]
                    if ct in ("time_estimate",):
                        meta_parts.append(_render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))
                    elif ct in ("goal", "prerequisites"):
                        content_parts_list.insert(0, _render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))
                    elif ct == "dependency":
                        content_parts_list.append(_render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))
                    else:
                        content_parts_list.append(_render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))

                sec_children.extend(meta_parts)
                sec_children.extend(content_parts_list)
                sec_children.append("</section>")
                content_html = "\n".join(sec_children)

            leaf_class = f"tree-leaf level-{level}"
            leaf_tree = f"""
            <li class="{leaf_class}" id="tleaf-{href_id}">
                <a href="#{href_id}">{title}</a>
            </li>
            """
            return leaf_tree, content_html

    for group_node in tree:
        gt, gc = render_tree_node(group_node, 1)
        tree_html.append(gt)
        content_parts.append(gc)

    tree_str = "\n".join(tree_html)
    content_str = "\n".join(content_parts)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{data['title']} V{data['version']}</title>
<style>{STYLE}</style>
</head>
<body>

<div class="wrapper">
    <nav class="sidebar">
        <div class="sidebar-header">
            <h2>{data['title']}</h2>
            <div class="version">V{data['version']} · {data['date']}</div>
        </div>
        <div class="sidebar-search">
            <input type="text" id="search-input" placeholder="搜索功能模块或步骤...">
        </div>
        <div class="search-no-result" id="search-no-result">未找到匹配内容</div>
        <div class="tree-wrapper">
            <ul class="tree" id="sidebar-tree">{tree_str}</ul>
        </div>
    </nav>

    <main class="content">
        <div class="breadcrumb" id="breadcrumb"><span>首页</span></div>
        {"".join(content_parts)}
        <div class="no-search-result" id="content-no-result">
            <p>🔍 未找到与搜索关键词匹配的内容</p>
        </div>
        <div class="footer"><p>{data['title']} V{data['version']} · {data['date']}</p></div>
    </main>
</div>

<div class="lightbox" id="lightbox" onclick="this.classList.remove('show')">
    <img id="lightbox-img" src="" alt="放大截图">
</div>

<script>{JS}</script>
</body>
</html>"""
    return html


def _render_fallback(data, output_dir, embed_images=False):
    image_dir = os.path.join(output_dir, "images")
    step_num = iter(range(1, 10000))
    content_parts = []

    content_parts.append(
        f'<div class="cover"><h1>{data["title"]}</h1><div class="meta"><div>版本：V{data["version"]}</div><div>日期：{data["date"]}</div></div></div>')

    for module in data.get("sections", []):
        mid = module["id"]
        parts = [f'<section class="module-section" data-id="{mid}">',
                 f'<h2 class="module-title" id="{mid}">{module["title"]}</h2>']
        if module.get("description"):
            parts.append(f'<p class="desc">{module["description"]}</p>')
        step_count_ref = [0]
        for child in module.get("children", []):
            parts.append(_render_child(child, mid, image_dir, embed_images, step_num, step_count_ref))
        parts.append("</section>")
        content_parts.append("\n".join(parts))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{data['title']} V{data['version']}</title><style>{STYLE}</style></head>
<body>
<div class="wrapper" style="display:block;">
    <main class="content" style="margin-left:0;max-width:100%;">
        {"".join(content_parts)}
        <div class="footer"><p>{data['title']} V{data['version']} · {data['date']}</p></div>
    </main>
</div>
<div class="lightbox" id="lightbox" onclick="this.classList.remove('show')"><img id="lightbox-img" src="" alt="放大截图"></div>
<script>{JS}</script>
</body></html>"""
