#!/usr/bin/env python3
"""
replay_render.py — 离屏重放渲染器
==================================
从导出的 JSON 数据文件重新渲染 HTML / PDF，无需启动浏览器录制。

用法:
    python replay_render.py manual_data.json
    python replay_render.py manual_data.json --format pdf
    python replay_render.py manual_data.json --embed-images --output my_manual.html
"""
import sys
import os
import json
import argparse

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ_ROOT)

from docs.html_renderer import render_html


def parse_args():
    parser = argparse.ArgumentParser(description="离屏重放渲染 — 从 JSON 生成 HTML/PDF")
    parser.add_argument("json_file", help="JSON 数据文件路径")
    parser.add_argument("--output", "-o", metavar="文件名", help="输出文件名")
    parser.add_argument("--format", "-f", choices=["html", "pdf", "both"], default="html",
                        help="输出格式 (默认 html)")
    parser.add_argument("--embed-images", action="store_true",
                        help="将截图嵌入 HTML")
    parser.add_argument("--output-dir", "-d", metavar="目录", help="输出目录")
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.exists(args.json_file):
        print(f"❌ 文件不存在: {args.json_file}")
        sys.exit(1)

    with open(args.json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    output_dir = args.output_dir or os.path.dirname(os.path.abspath(args.json_file))
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.getcwd(), output_dir)
    os.makedirs(output_dir, exist_ok=True)

    title = data.get("title", "操作手册")
    version = data.get("version", "V1.0")

    if args.format in ("html", "both"):
        out_name = args.output or f"{title}_V{version}.html"
        out_path = os.path.join(output_dir, out_name)
        html = render_html(data, output_dir, embed_images=args.embed_images)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ HTML 已生成: {out_path}")
        print(f"   大小: {len(html):,} 字节")
        print(f"   嵌入图片: {'是' if args.embed_images else '否 (外部文件引用)'}")

    if args.format in ("pdf", "both"):
        from docs.pdf_renderer import render_pdf

        html_for_pdf = render_html(data, output_dir, embed_images=True)
        tmp_html = os.path.join(output_dir, "_temp_for_pdf.html")
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html_for_pdf)

        pdf_name = args.output or f"{title}_V{version}.pdf"
        if pdf_name.endswith(".html"):
            pdf_name = pdf_name[:-5] + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_name)
        render_pdf(tmp_html, pdf_path, title=title, version=version)

        try:
            os.remove(tmp_html)
        except:
            pass

    if args.format == "both":
        print(f"\n🎉 HTML + PDF 双格式已生成到: {output_dir}")


if __name__ == "__main__":
    main()
