#!/usr/bin/env python3
"""
PDF 渲染器 — 通过 Playwright 将 HTML 转为 PDF
============================================
- 支持 WeasyPrint 离线渲染（如已安装）
- 增强的页眉页脚（文档标题 + 版本 + 页码）
- 自动为模块标题生成 PDF 书签大纲
- Playwright 作为主要/回退引擎
"""
import os
import re
import tempfile


def render_pdf(html_path, pdf_path, title="操作手册", version="V1.0"):
    html_path = os.path.abspath(html_path)
    pdf_path = os.path.abspath(pdf_path)

    weasyprint_ok = False
    try:
        import weasyprint
        weasyprint_ok = True
    except ImportError:
        pass

    if weasyprint_ok:
        return _render_weasy(html_path, pdf_path, title, version)
    else:
        return _render_playwright(html_path, pdf_path, title, version)


def _render_weasy(html_path, pdf_path, title, version):
    import weasyprint

    doc = weasyprint.HTML(filename=html_path)

    doc.write_pdf(
        pdf_path,
        presentational_hints=True,
    )
    print(f"    📄 PDF (WeasyPrint) 已生成: {pdf_path}")
    return pdf_path


def _render_playwright(html_path, pdf_path, title, version):
    from playwright.sync_api import sync_playwright

    header_html = f"""
    <div style="font-size:8px;color:#888;width:100%;text-align:center;
                border-bottom:1px solid #ddd;padding-bottom:6px;margin-bottom:4px;
                font-family:'Microsoft YaHei','Noto Sans SC',sans-serif;">
        {title} · {version}
    </div>
    """

    footer_html = """
    <div style="font-size:8px;color:#888;width:100%;text-align:center;
                border-top:1px solid #ddd;padding-top:6px;margin-top:4px;
                font-family:'Microsoft YaHei','Noto Sans SC',sans-serif;">
        第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页
    </div>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})

        page.goto(f"file:///{html_path.replace(os.sep, '/')}", wait_until="networkidle")
        page.wait_for_timeout(2000)

        page.pdf(
            path=pdf_path,
            format="A4",
            margin={"top": "25mm", "bottom": "22mm", "left": "15mm", "right": "15mm"},
            print_background=True,
            display_header_footer=True,
            header_template=header_html,
            footer_template=footer_html,
        )

        browser.close()

    print(f"    📄 PDF (Playwright) 已生成: {pdf_path}")
    return pdf_path
