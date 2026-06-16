#!/usr/bin/env python3
"""
Platform Explorer Core v2 - 重构版
使用ARIA菜单遍历，修复菜单发现和报告生成问题
"""

import asyncio, json, logging, os, re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class PlatformExplorer:
    def __init__(self, base_url: str, output_dir: str):
        self.base_url = base_url.rstrip("/")
        self.output_dir = Path(output_dir)
        self.screenshots_dir = self.output_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.all_pages = {}
        self.platform_name = ""
        self.component_lib = "unknown"

    async def run(self):
        print("=" * 60)
        print("  Platform Explorer v2 启动")
        print(f"  目标: {self.base_url}")
        print(f"  输出: {self.output_dir}")
        print("=" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
            page = await ctx.new_page()

            await self._navigate_home(page)
            self.platform_name = await page.title() or "UnknownPlatform"
            await self._discover_all_pages(page)
            await self._deep_explore_all(page)
            analysis = self._analyze()
            await self._generate_report(analysis)

            await browser.close()

        print(f"\n探索完成！报告: {self.output_dir / 'report.html'}")
        return self.output_dir

    async def _navigate_home(self, page):
        print(f"\n[1/6] 导航到首页")
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        print(f"  URL: {page.url}")
        print(f"  Title: {await page.title()}")

    async def _discover_all_pages(self, page):
        """通过Vue Router发现所有页面"""
        print(f"\n[2/6] 发现所有页面")

        discovered = {}
        visit_urls = set()
        visit_urls.add(self.base_url)

        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # 方法1: 从Vue Router获取所有路由
        routes = await page.evaluate("""
        () => {
            try {
                const app = document.querySelector('#app').__vue_app__;
                const router = app.config.globalProperties.$router;
                if (router) {
                    return router.getRoutes()
                        .filter(r => r.path && !r.path.includes(':') && !r.path.includes('*') && r.path !== '/' && r.path !== '/login' && r.path !== '/401')
                        .map(r => ({path: r.path, name: r.name || '', title: r.meta?.title || r.name || ''}));
                }
                return [];
            } catch(e) {
                return [];
            }
        }
        """)

        if routes:
            print(f"  从Vue Router发现 {len(routes)} 个路由")
            origin = self.base_url.split("/jwsiot")[0]
            # 只取列表页（不包含 edit/detail/Detail/version/edit/add 的路径）
            list_routes = [
                r
                for r in routes
                if not any(
                    x in r["path"].lower()
                    for x in [
                        "edit",
                        "detail",
                        "version",
                        "add",
                        "instrument",
                        "quick",
                        "subdevice",
                        "redirect",
                        "login",
                        "register",
                        "develop",
                        "home2",
                        "list2",
                        ":path",
                    ]
                )
            ]
            print(f"  过滤后 {len(list_routes)} 个列表页面")
            for r in list_routes:
                full_url = f"{origin}{r['path']}"
                if full_url not in visit_urls:
                    visit_urls.add(full_url)
                    discovered[full_url] = {
                        "name": r.get("title", "")[:40] or r["path"],
                        "url": full_url,
                    }
        else:
            # 方法2: 通过菜单遍历（降级方案）
            print("  Vue Router不可用，使用菜单遍历...")
            await page.evaluate("""
            () => document.querySelectorAll('.el-sub-menu').forEach(el => {
                el.classList.add('is-opened');
                el.setAttribute('aria-expanded', 'true');
            })
            """)
            await page.wait_for_timeout(1000)

            top_items = await page.evaluate("""
            () => {
                const items = [];
                const menubar = document.querySelector('[role="menubar"]');
                if (!menubar) return [];
                menubar.querySelectorAll(':scope > [role="menuitem"]').forEach(el => {
                    const text = el.textContent.trim().replace(/\\s+/g, ' ').substring(0, 30);
                    items.push(text);
                });
                return items;
            }
            """)

            for top_name in top_items:
                await page.goto(
                    self.base_url, wait_until="domcontentloaded", timeout=30000
                )
                await page.wait_for_timeout(1500)
                top_btn = (
                    page.locator('[role="menuitem"]').filter(has_text=top_name).first
                )
                if await top_btn.count() == 0:
                    continue
                await top_btn.click()
                await page.wait_for_timeout(1000)
                await page.evaluate("""
                () => document.querySelectorAll('.el-sub-menu').forEach(el => {
                    el.classList.add('is-opened');
                    el.setAttribute('aria-expanded', 'true');
                })
                """)
                await page.wait_for_timeout(500)

                leaf_items = await page.evaluate("""
                () => [...new Set([...document.querySelectorAll('.el-menu-item')].map(el => el.textContent.trim()).filter(t => t))];
                """)

                for leaf_text in leaf_items:
                    try:
                        item = page.get_by_role("menuitem", name=leaf_text).first
                        if await item.count() > 0:
                            await item.click()
                            await page.wait_for_timeout(2000)
                            url = page.url
                            if url not in visit_urls:
                                visit_urls.add(url)
                                discovered[url] = {"name": leaf_text[:40], "url": url}
                            await page.goto(
                                self.base_url,
                                wait_until="domcontentloaded",
                                timeout=30000,
                            )
                            await page.wait_for_timeout(1500)
                            await top_btn.click()
                            await page.wait_for_timeout(1000)
                            await page.evaluate("""
                            () => document.querySelectorAll('.el-sub-menu').forEach(el => {
                                el.classList.add('is-opened');
                                el.setAttribute('aria-expanded', 'true');
                            })
                            """)
                            await page.wait_for_timeout(500)
                    except Exception as e:
                        logger.warning(f"菜单遍历点击 '{leaf_text}' 失败: {e}")

        self.all_pages = discovered
        print(f"  共 {len(discovered)} 个页面")
        for u, info in discovered.items():
            print(f"    {info['name'][:35]:35s} {u}")

    async def _deep_explore_all(self, page):
        print(f"\n[3/6] 深度探索 {len(self.all_pages)} 个页面")
        for idx, (url, info) in enumerate(self.all_pages.items(), 1):
            print(f"  [{idx}/{len(self.all_pages)}] {info['name'][:30]}", end="")
            try:
                result = await self._explore_page(page, url, info["name"])
                info.update(result)
                print(f" OK")
            except Exception as e:
                print(f" ERR: {str(e)[:50]}")
                info["error"] = str(e)[:100]

    async def _detect_component_library(self, page) -> str:
        """检测页面使用的组件库（Element UI / Ant Design）"""
        html = await page.content()
        if "el-" in html and self.component_lib == "unknown":
            self.component_lib = "Element UI (Vue)"
        elif "ant-" in html:
            self.component_lib = "Ant Design"
        return self.component_lib

    async def _collect_page_fields(self, page) -> dict:
        """收集页面表单字段（输入框 placeholder、文本域、下拉框）"""
        inputs = []
        textareas = []
        comboboxes = []

        # 输入框
        for inp in await page.get_by_role("textbox").all():
            try:
                ph = (await inp.get_attribute("placeholder") or "")[:20]
                if ph:
                    inputs.append(ph)
            except Exception as e:
                logger.warning(f"收集输入框字段失败: {e}")

        # 文本域
        for i in range(await page.locator("textarea").count()):
            try:
                ph = (
                    await page.locator("textarea").nth(i).get_attribute("placeholder")
                    or ""
                )[:20]
                if ph:
                    textareas.append(ph)
            except Exception as e:
                logger.warning(f"收集文本域字段失败: {e}")

        # 下拉框
        for i in range(await page.get_by_role("combobox").count()):
            try:
                lb = (
                    await page.get_by_role("combobox")
                    .nth(i)
                    .get_attribute("aria-label")
                    or ""
                )[:20]
                if lb:
                    comboboxes.append(lb)
            except Exception as e:
                logger.warning(f"收集下拉框字段失败: {e}")

        return {"inputs": inputs, "textareas": textareas, "comboboxes": comboboxes}

    async def _identify_components(self, page) -> dict:
        """识别页面中的表格、按钮、Tab等组件及其数据状态"""
        tables = []
        buttons = []
        tabs = []
        has_data = False
        data_count = 0
        data_state = ""

        # 表格
        for i in range(await page.get_by_role("table").count()):
            try:
                rows = await page.get_by_role("table").nth(i).get_by_role("row").all()
                hs = []
                if rows:
                    for h in await rows[0].get_by_role("columnheader").all():
                        hs.append((await h.inner_text()).strip()[:12])
                dr = max(0, len(rows) - 1)
                if dr > 0:
                    has_data = True
                    data_count += dr
                tables.append({"headers": hs[:8], "data_rows": dr})
            except Exception as e:
                logger.warning(f"识别表格失败: {e}")

        # 按钮
        for b in (await page.get_by_role("button").all())[:30]:
            try:
                t = (await b.inner_text()).strip()
                if t:
                    buttons.append(t[:25])
            except Exception as e:
                logger.warning(f"识别按钮失败: {e}")

        # Tab
        for i in range(await page.get_by_role("tab").count()):
            try:
                t = (await page.get_by_role("tab").nth(i).inner_text()).strip()[:20]
                if t:
                    tabs.append(t)
            except Exception as e:
                logger.warning(f"识别Tab失败: {e}")

        # 数据状态
        body = (await page.inner_text("body")).lower()
        for phrase in ["暂无数据", "没有数据", "无数据"]:
            if phrase in body:
                data_state = f"空数据({phrase})"
                break
        if not data_state:
            data_state = f"有数据({data_count}条)" if has_data else "待确认"

        return {
            "tables": tables,
            "buttons": buttons,
            "tabs": tabs,
            "has_data": has_data,
            "data_count": data_count,
            "data_state": data_state,
        }

    async def _explore_page(self, page, url, name):
        """探索单个页面（协调函数，调用子函数收集各项信息）"""
        result = {
            "buttons": [],
            "inputs": [],
            "tables": [],
            "tabs": [],
            "comboboxes": [],
            "textareas": [],
            "checks": [],
            "has_data": False,
            "data_count": 0,
            "data_state": "",
            "sub_pages": [],
        }

        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        result["title"] = await page.title()

        # 面包屑
        try:
            bc = await page.locator(
                "[class*='breadcrumb'], nav[aria-label*='breadcrumb']"
            ).inner_text()
            result["breadcrumb"] = bc.strip().replace("\n", " > ")[:60]
        except Exception as e:
            logger.warning(f"获取面包屑失败: {e}")

        # 截图
        safe = re.sub(r'[\\/*?:"<>|]', "_", name)[:30]
        await page.screenshot(path=str(self.screenshots_dir / f"{safe}.png"))

        # 检测组件库
        await self._detect_component_library(page)

        # 收集表单字段
        fields = await self._collect_page_fields(page)
        result["inputs"] = fields["inputs"]
        result["textareas"] = fields["textareas"]
        result["comboboxes"] = fields["comboboxes"]

        # 识别组件
        components = await self._identify_components(page)
        result["tables"] = components["tables"]
        result["buttons"] = components["buttons"]
        result["tabs"] = components["tabs"]
        result["has_data"] = components["has_data"]
        result["data_count"] = components["data_count"]
        result["data_state"] = components["data_state"]

        # 尝试点击"新增""编辑"等
        for action in ["新增", "添加", "编辑"]:
            btn = page.get_by_role("button", name=action)
            if await btn.count() > 0:
                try:
                    await btn.first.click()
                    await page.wait_for_timeout(2000)
                    sub = {"action": action, "url": page.url, "fields": []}
                    for inp in await page.get_by_role("textbox").all():
                        try:
                            ph = (await inp.get_attribute("placeholder") or "")[:20]
                            if ph:
                                sub["fields"].append(ph)
                        except Exception as e:
                            logger.warning(f"收集子页面字段失败: {e}")
                    result["sub_pages"].append(sub)
                    # 返回
                    back = page.get_by_role("button", name="返回")
                    if await back.count() > 0:
                        await back.first.click()
                        await page.wait_for_timeout(1500)
                except Exception as e:
                    logger.warning(f"操作 '{action}' 失败: {e}")

        return result

    def _analyze(self):
        print(f"\n[5/6] 数据分析")
        empty = [
            (n, p.get("name", ""), p.get("data_state", ""))
            for n, p in self.all_pages.items()
            if "空数据" in p.get("data_state", "")
        ]
        return {
            "total_pages": len(self.all_pages),
            "data_pages": sum(
                1
                for p in self.all_pages.values()
                if "有数据" in p.get("data_state", "")
            ),
            "empty_pages": len(empty),
            "component_lib": self.component_lib,
            "total_buttons": sum(
                len(p.get("buttons", [])) for p in self.all_pages.values()
            ),
            "total_inputs": sum(
                len(p.get("inputs", [])) for p in self.all_pages.values()
            ),
            "total_tables": sum(
                len(p.get("tables", [])) for p in self.all_pages.values()
            ),
            "total_tabs": sum(len(p.get("tabs", [])) for p in self.all_pages.values()),
            "total_combos": sum(
                len(p.get("comboboxes", [])) for p in self.all_pages.values()
            ),
            "empty_details": empty,
        }

    async def _generate_report(self, a):
        print(f"\n[6/6] 生成HTML报告")
        pages_json = json.dumps(
            [
                {
                    "name": p.get("name", ""),
                    "url": u,
                    "data_state": p.get("data_state", ""),
                    "buttons": len(p.get("buttons", [])),
                    "inputs": len(p.get("inputs", [])),
                    "tables": len(p.get("tables", [])),
                    "tabs": len(p.get("tabs", [])),
                    "sub_pages": p.get("sub_pages", []),
                }
                for u, p in self.all_pages.items()
            ],
            ensure_ascii=False,
        )

        DP = a["data_pages"]
        EP = a["empty_pages"]
        TB = a["total_buttons"]
        TI = a["total_inputs"]
        TBL = a["total_tables"]
        TT = a["total_tabs"]
        TC = a["total_combos"]

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self.platform_name} - 平台探索报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f0f2f5; color:#333; }}
.header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color:white; padding:30px 40px; }}
.header h1 {{ font-size:24px; margin-bottom:5px; }}
.header .sub {{ opacity:0.7; font-size:14px; }}
.stats-row {{ display:flex; gap:15px; padding:20px 40px; flex-wrap:wrap; }}
.stat-card {{ background:white; border-radius:10px; padding:20px; flex:1; min-width:140px; box-shadow:0 2px 8px rgba(0,0,0,0.08); text-align:center; }}
.stat-card .num {{ font-size:28px; font-weight:700; color:#1a1a2e; }}
.stat-card .label {{ font-size:12px; color:#666; margin-top:5px; }}
.chart-row {{ display:flex; gap:15px; padding:0 40px 20px; }}
.chart-card {{ background:white; border-radius:10px; padding:15px; width:380px; margin:0 auto; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
.chart-card h3 {{ font-size:13px; margin-bottom:10px; color:#666; }}
.chart-card canvas {{ max-width:260px; max-height:260px; display:block; margin:0 auto; }}
.tree-container {{ padding:0 40px 20px; }}
.tree-card {{ background:white; border-radius:10px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
.tree-card h3 {{ font-size:14px; margin-bottom:15px; color:#666; }}
.page-item {{ padding:8px 12px; margin:4px 0; border-radius:6px; cursor:pointer; display:flex; align-items:center; gap:10px; }}
.page-item:hover {{ background:#f5f5f5; }}
.page-item .dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}
.dot-green {{ background:#52c41a; }}
.dot-yellow {{ background:#faad14; }}
.dot-red {{ background:#ff4d4f; }}
.page-item .pn {{ flex:1; }}
.page-item .ps {{ font-size:12px; color:#999; }}
.gallery {{ padding:0 40px 40px; }}
.gallery-card {{ background:white; border-radius:10px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
.gallery-card h3 {{ font-size:14px; margin-bottom:15px; color:#666; }}
.gal-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:12px; }}
.gal-item {{ border:1px solid #eee; border-radius:6px; overflow:hidden; }}
.gal-item img {{ width:100%; height:140px; object-fit:cover; display:block; }}
.gal-item .cap {{ padding:6px 10px; font-size:12px; color:#666; }}
footer {{ text-align:center; padding:20px; color:#999; font-size:12px; }}
</style>
</head>
<body>
<div class="header">
    <h1>{self.platform_name} - 平台全量探索报告</h1>
    <div class="sub">探索时间: {datetime.now().strftime("%Y-%m-%d %H:%M")} | 组件库: {a["component_lib"]} | {a["total_pages"]} 页面</div>
</div>

<div class="stats-row">
    <div class="stat-card"><div class="num">{a["total_pages"]}</div><div class="label">总页面</div></div>
    <div class="stat-card"><div class="num">{DP}</div><div class="label">有数据</div></div>
    <div class="stat-card"><div class="num" style="color:{"#ff4d4f" if EP > 0 else "#52c41a"}">{EP}</div><div class="label">空数据</div></div>
    <div class="stat-card"><div class="num">{TB}</div><div class="label">按钮</div></div>
    <div class="stat-card"><div class="num">{TI}</div><div class="label">输入框</div></div>
    <div class="stat-card"><div class="num">{TBL}</div><div class="label">表格</div></div>
    <div class="stat-card"><div class="num">{TT}</div><div class="label">Tab页</div></div>
    <div class="stat-card"><div class="num">{TC}</div><div class="label">下拉框</div></div>
</div>

<div class="chart-row">
    <div class="chart-card">
        <h3>数据状态分布</h3>
        <canvas id="chartData"></canvas>
    </div>
    <div class="chart-card">
        <h3>页面元素分布</h3>
        <canvas id="chartElem"></canvas>
    </div>
</div>

<div class="tree-container">
    <div class="tree-card">
        <h3>页面列表</h3>
        <div id="pageList"></div>
    </div>
</div>

<div class="gallery">
    <div class="gallery-card">
        <h3>截图画廊</h3>
        <div class="gal-grid" id="galleryGrid"></div>
    </div>
</div>

<footer>Generated by Platform Explorer | <a href="#" onclick="downloadJSON()">下载JSON</a></footer>

<script>
const pages = {pages_json};
new Chart(document.getElementById('chartData'), {{
    type: 'doughnut',
    data: {{
        labels: ['有数据('+{DP}+')', '空数据('+{EP}+')'],
        datasets: [{{ data: [{DP}, {EP}], backgroundColor: ['#52c41a', '#ff4d4f'] }}]
    }}
}});
new Chart(document.getElementById('chartElem'), {{
    type: 'bar',
    data: {{
        labels: ['按钮','输入框','表格','Tab页','下拉框'],
        datasets: [{{ data: [{TB},{TI},{TBL},{TT},{TC}], backgroundColor: '#1890ff' }}]
    }},
    options: {{ plugins: {{ legend: {{ display: false }} }} }}
}});

const list = document.getElementById('pageList');
pages.forEach(p => {{
    const cls = p.data_state.includes('空数据') ? 'dot-red' : p.data_state.includes('有数据') ? 'dot-green' : 'dot-yellow';
    const d = document.createElement('div');
    d.className = 'page-item';
    d.innerHTML = '<span class="dot '+cls+'"></span><span class="pn">'+p.name+'</span><span class="ps">'+p.data_state+'</span>';
    list.appendChild(d);
}});

const gal = document.getElementById('galleryGrid');
pages.forEach(p => {{
    const name = p.name.replace(/[\\\\/:*?"<>|]/g, '_').substring(0,30);
    const item = document.createElement('div');
    item.className = 'gal-item';
    item.innerHTML = '<img src="screenshots/'+encodeURIComponent(name)+'.png" loading="lazy" onerror="this.style.display=\\'none\\'"><div class="cap">'+p.name+'</div>';
    item.onclick = () => window.open('screenshots/'+encodeURIComponent(name)+'.png');
    gal.appendChild(item);
}});

function downloadJSON() {{
    const blob = new Blob([JSON.stringify(pages, null, 2)], {{type:'application/json'}});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'explore_data.json'; a.click();
}}
</script>
</body>
</html>"""
        (self.output_dir / "report.html").write_text(html, encoding="utf-8")
        json.dump(
            pages_json,
            (self.output_dir / "explore_data.json").open("w", encoding="utf-8"),
            ensure_ascii=False,
        )
        print(f"  HTML报告: {self.output_dir / 'report.html'}")
        print(f"  JSON数据: {self.output_dir / 'explore_data.json'}")


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="平台探索引擎（Platform Explorer）")
    parser.add_argument(
        "url",
        nargs="?",
        default=os.environ.get("PLATFORM_URL", "http://localhost:28080"),
        help="平台基础URL（默认从 PLATFORM_URL 环境变量读取）",
    )
    parser.add_argument(
        "--platform-id", default="iot", help="平台标识（用于报告目录，默认: iot）"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录（默认: docs/output/{platform_id}/explore_{ts}/）",
    )
    args = parser.parse_args()

    if args.output_dir:
        out = args.output_dir
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = f"docs/output/{args.platform_id}/explore_{ts}"

    print(f"  平台ID: {args.platform_id}")
    print(f"  输出目录: {out}")

    explorer = PlatformExplorer(args.url, out)
    asyncio.run(explorer.run())
