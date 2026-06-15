#!/usr/bin/env python3
"""
Page Manifest → Playwright 脚本骨架生成器
===========================================
读取 manifests/*.json，生成可直接运行的 Playwright 测试函数。

用法:
  # 生成单个页面的骨架代码
  python manifest_generator.py manifests/pv_create.json

  # 生成所有页面的骨架代码（输出到 terminal）
  python manifest_generator.py manifests/*.json

  # 生成完整测试脚本（按场景组合）
  python manifest_generator.py --compose scene_def.json

输出: 打印到 stdout，可重定向到 .py 文件
"""
import json, sys, os, textwrap
from datetime import datetime

# ── 可选 Jinja2 模板引擎 ──
try:
    import jinja2
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


# ============================================================
# 组件 → Playwright 代码映射
# ============================================================

def gen_component_fill(field, var_name, indent=12):
    """生成字段填写代码"""
    comp = field.get("component", "input")
    placeholder = field.get("placeholder", "")
    key = field.get("key", "unknown")
    test_val = field.get("test_value", f"${{{key}}}")
    lines = []

    if comp == "input":
        lines.append(f'page.get_by_placeholder("{placeholder}").fill({var_name})')

    elif comp == "select":
        opt_sel = field.get("option_selector", "[role='option']")
        deb = field.get("debounce_seconds", 2)
        lines.append(f'page.get_by_placeholder("{placeholder}").click()')
        lines.append(f'page.get_by_placeholder("{placeholder}").fill({var_name})')
        lines.append(f'time.sleep({deb})')
        lines.append(f'opt = page.locator("{opt_sel}").filter(has_text={var_name}).first')
        lines.append(f'if opt.count() > 0: opt.click(); time.sleep(0.5)')

    elif comp == "autocomplete":
        pop = field.get("popper", ".el-autocomplete__popper")
        opt_sel = field.get("option_selector", "li")
        deb = field.get("debounce_seconds", 2.5)
        is_bug = field.get("known_bug", False)
        lines.append(f'page.get_by_placeholder("{placeholder}").click()')
        lines.append(f'page.get_by_placeholder("{placeholder}").fill({var_name})')
        lines.append(f'time.sleep({deb})')
        lines.append(f'pv_opt = page.locator("{pop} {opt_sel}").filter(has_text={var_name})')
        lines.append(f'for wait_i in range(3):')
        lines.append(f'    if pv_opt.count() > 0: break')
        lines.append(f'    time.sleep(1.5)')
        lines.append(f'if pv_opt.count() > 0:')
        lines.append(f'    pv_opt.first.click()')
        lines.append(f'    time.sleep(1)')
        if is_bug:
            lines.append(f'# ⚠️ 已知BUG: 此字段选择后可能不持久化（见known_bugs）')

    elif comp == "textarea":
        lines.append(f'page.locator("textarea[placeholder=\'{placeholder}\']").fill({var_name})')

    elif comp == "switch":
        lines.append(f'page.locator(".el-switch").first.click()')

    return lines


def gen_tab_switch(tab, indent=8):
    """生成Tab切换代码"""
    name = tab["name"]
    return [
        f'page.get_by_role("tab", name="{name}").click()',
        f'time.sleep(2)',
    ]


def gen_sub_panel(panel, var_name, indent=8):
    """生成子面板（如添加元件模型弹窗）代码"""
    lines = []
    add_btn = panel.get("add_button", "添加")
    dlg = panel.get("dialog", {})
    search_ph = dlg.get("search_placeholder", "")
    confirm = dlg.get("confirm_text", "确定")
    lines.append(f'# 子面板: {panel.get("title", "")}')
    lines.append(f'add_btn = page.locator("button").filter(has_text="{add_btn}")')
    lines.append(f'if add_btn.count() > 0:')
    lines.append(f'    add_btn.click(); time.sleep(1.5)')
    if search_ph:
        lines.append(f'    si = page.get_by_placeholder("{search_ph}")')
        lines.append(f'    if si.count() > 0:')
        lines.append(f'        si.fill({var_name}); time.sleep(2)')
        lines.append(f'        o = page.locator("[role=\'option\'], tr").filter(has_text={var_name}).first')
        lines.append(f'        if o.count() > 0: o.click(); time.sleep(0.5)')
        lines.append(f'        ok = page.locator("button").filter(has_text="{confirm}").first')
        lines.append(f'        if ok.count() > 0: ok.click(); time.sleep(1)')
    return lines


def gen_inline_table(table, indent=8):
    """生成行内表格（如属性行）代码"""
    lines = []
    add_btn = table.get("add_button", "添加")
    lines.append(f'page.get_by_role("button", name="{add_btn}").click()')
    lines.append(f'time.sleep(1)')
    for col in table.get("columns", []):
        ph = col.get("placeholder", "")
        tv = col.get("test_value", "")
        comp = col.get("component", "input")
        if comp == "input":
            if ph:
                lines.append(f'page.locator("input[placeholder=\'{ph}\']").first.fill("{tv}")')
        elif comp == "select":
            default = col.get("default", "")
            set_to = col.get("set_to", "")
            if default:
                lines.append(f'rw = page.locator(".el-select").filter(has_text="{default}").first')
                lines.append(f'if rw.count() > 0:')
                lines.append(f'    rw.click(); time.sleep(0.5)')
                lines.append(f'    ro = page.locator("[role=\'option\']").filter(has_text="{set_to}").first')
                lines.append(f'    if ro.count() > 0: ro.click(); time.sleep(0.3)')
    return lines


def gen_row_action(action, search_var, indent=8):
    """生成行内操作按钮代码"""
    text = action["text"]
    act = action.get("action", "click")
    lines = []
    lines.append(f'row = page.locator("tr").filter(has_text={search_var})')
    lines.append(f'if row.count() > 0:')
    if act == "publish":
        lines.append(f'    pub = row.locator("button").filter(has_text="{text}")')
        lines.append(f'    if pub.count() > 0:')
        lines.append(f'        pub.click(); time.sleep(1.5)')
        dlg_confirm = action.get("dialog", "确定")
        lines.append(f'        confirm = page.locator(".el-message-box__btns button").filter(has_text="{dlg_confirm}").first')
        lines.append(f'        if confirm.count() > 0: confirm.click(); time.sleep(2)')
    elif act == "navigate":
        lines.append(f'    row.locator("button").filter(has_text="{text}").first.click(); time.sleep(2)')
    elif act == "open_dialog":
        lines.append(f'    row.locator("button").filter(has_text="{text}").first.click(); time.sleep(2)')
    return lines


def gen_dialog_interaction(dialog, indent=8):
    """生成弹窗交互代码"""
    lines = []
    search_ph = dialog.get("search_placeholder", "")
    confirm = dialog.get("confirm_text", "确定")
    if search_ph:
        lines.append(f'# 弹窗中搜索')
        lines.append(f'page.locator(".el-dialog input[placeholder*=\'{search_ph}\']").fill({dialog.get("search_var", "DEVICE_NAME")})')
        lines.append(f'time.sleep(0.5)')
        lines.append(f'page.locator(".el-dialog button").filter(has_text="搜索").click()')
        lines.append(f'time.sleep(2)')
        sel_type = dialog.get("select_type", "radio")
        if sel_type == "radio":
            lines.append(f'page.locator(".el-dialog .el-radio").first.click()')
            lines.append(f'time.sleep(0.5)')
        lines.append(f'page.locator(".el-dialog button").filter(has_text="{confirm}").click()')
        lines.append(f'time.sleep(3)')
    return lines


# ============================================================
# 断言代码生成
# ============================================================

def gen_assertions(assertions, search_var="SEARCH_NAME", indent=8):
    """生成断言验证代码"""
    lines = []
    if "db" in assertions:
        db = assertions["db"]
        db_key = db.get("by_key", search_var)
        lines.append(f'try:')
        lines.append(f'    detail = db_check_exists("{db["table"]}", "{db["by_field"]}", {db_key})')
        lines.append(f'    report.assertion("DB: {db["table"]}已创建", True, detail)')
        lines.append(f'except AssertionError as e:')
        lines.append(f'    report.assertion("DB: {db["table"]}已创建", False, str(e))')

    if "detail_tab" in assertions:
        dt = assertions["detail_tab"]
        is_bug = dt.get("known_bug", False)
        lines.append(f'row = page.locator("tr").filter(has_text={search_var})')
        lines.append(f'if row.count() > 0:')
        lines.append(f'    page.evaluate(f"""')
        lines.append(f'        var tr = Array.from(document.querySelectorAll("tr")).find(function(r) {{')
        lines.append(f'            return r.textContent.includes("{" + search_var + "}");')
        lines.append(f'        }});')
        lines.append(f'        if(tr) {{')
        lines.append(f'            var btns = tr.querySelectorAll("button");')
        lines.append(f'            for(var i=0;i<btns.length;i++) {{')
        lines.append(f'                if(btns[i].textContent.includes("查看详情")) btns[i].click();')
        lines.append(f'            }}')
        lines.append(f'        }}')
        lines.append(f'    """)')
        lines.append(f'    time.sleep(3)')
        lines.append(f'    tab = page.get_by_role("tab", name="{dt["tab_name"]}")')
        lines.append(f'    if tab.count() > 0: tab.click(); time.sleep(2)')
        if is_bug:
            lines.append(f'    # ⚠️ 已知BUG: 详情页字段可能为空（软检查）')

    return lines


# ============================================================
# 主生成器
# ============================================================

def generate_page_function(manifest):
    """根据manifest生成一个页面操作函数"""
    pid = manifest["page_id"]
    title = manifest["title"]
    url = manifest["url"]
    base_ref = manifest.get("base_url_ref", "BASE_URL")
    fields = manifest.get("fields", [])
    tabs = manifest.get("tabs", [])
    buttons = manifest.get("buttons", [])
    row_actions = manifest.get("row_actions", [])
    dialogs = manifest.get("dialogs", [])
    inline_table = manifest.get("inline_table")
    sub_panel = manifest.get("sub_panel")
    assertions = manifest.get("assertions", {})
    post_save = manifest.get("post_save", "stay")
    known_bugs = manifest.get("known_bugs", [])

    lines = []
    lines.append(f'')
    lines.append(f'# ============================================================')
    lines.append(f'# {title} （manifest: {pid}.json）')
    lines.append(f'# ============================================================')
    lines.append(f'def do_{pid}(report, page, **kwargs):')
    lines.append(f'    """执行{title}操作"""')
    lines.append(f'    # 提取参数（带默认值）')
    for f in fields:
        k = f["key"]
        tv = f.get("test_value", "''")
        lines.append(f'    {k} = kwargs.get("{k}", "{tv}")')
    # Tab内的字段也需要提取参数
    for tab in tabs:
        for f in tab.get("fields", []):
            k = f["key"]
            tv = f.get("test_value", "''")
            if not any(k == ff["key"] for ff in fields):
                lines.append(f'    {k} = kwargs.get("{k}", "{tv}")')
    lines.append(f'')
    lines.append(f'    report.step("导航到{title}页", screenshot=page)')
    lines.append(f'    page.goto(f"{{{base_ref}}}{url}", wait_until="networkidle")')
    lines.append(f'    time.sleep(2)')
    lines.append(f'')

    # 基础字段填写
    for f in fields:
        k = f["key"]
        comp = f.get("component", "input")
        fill_lines = gen_component_fill(f, k, indent=12)
        if fill_lines:
            lines.append(f'    # {f["name"]}')
            for l in fill_lines:
                lines.append(f'    {l}')
            lines.append(f'    report.step("填写{f["name"]}", screenshot=page)')
            lines.append(f'')

    # 行内表格（如属性行）
    if inline_table:
        lines.append(f'    # ---- 行内表格: {inline_table.get("add_button", "添加")} ----')
        tbl_lines = gen_inline_table(inline_table)
        for l in tbl_lines:
            lines.append(f'    {l}')
        lines.append(f'    report.step("添加属性行", screenshot=page)')
        lines.append(f'')

    # 子面板（如添加元件模型）
    if sub_panel:
        # 找到关联字段key
        sp_key = "EL_MODEL_NAME"
        for f in fields:
            if f.get("placeholder", "").find("搜索") >= 0:
                sp_key = f["key"]
                break
        lines.append(f'    # ---- 子面板: {sub_panel.get("title", "")} ----')
        sp_lines = gen_sub_panel(sub_panel, sp_key)
        for l in sp_lines:
            lines.append(f'    {l}')
        lines.append(f'    report.step("关联{sub_panel.get("title", "")}", screenshot=page)')
        lines.append(f'')

    # Tab切换 + Tab内字段
    for tab in tabs:
        tab_name = tab["name"]
        lines.append(f'    # ---- Tab: {tab_name} ----')
        tab_lines = gen_tab_switch(tab)
        for l in tab_lines:
            lines.append(f'    {l}')
        lines.append(f'    report.step("切换到{tab_name}Tab", screenshot=page)')
        lines.append(f'')
        for f in tab.get("fields", []):
            k = f["key"]
            fill_lines = gen_component_fill(f, k, indent=12)
            if fill_lines:
                lines.append(f'    # {f["name"]}')
                for l in fill_lines:
                    lines.append(f'    {l}')
                lines.append(f'    report.step("填写{f["name"]}", screenshot=page)')
                lines.append(f'')

    # 操作按钮
    for btn in buttons:
        lines.append(f'    # 点击: {btn["text"]}')
        lines.append(f'    page.get_by_role("button", name="{btn["text"]}").click()')
        lines.append(f'    time.sleep(5)')
        lines.append(f'    report.step("点击{btn["text"]}", screenshot=page)')
        lines.append(f'')

    # 保存后行为
    if post_save == "stay":
        # 需要手动导航到列表页验证
        if "ui_list" in assertions:
            ul = assertions["ui_list"]
            list_url = ul.get("url", "")
            sp = ul.get("search_placeholder", "")
            lines.append(f'    # 验证: 导航到列表页')
            lines.append(f'    page.goto(f"{{{base_ref}}}{list_url}", wait_until="networkidle")')
            lines.append(f'    time.sleep(2)')
            if sp:
                lines.append(f'    page.get_by_placeholder("{sp}").fill({fields[0]["key"] if fields else "search_name"})')
                lines.append(f'    page.get_by_role("button", name="搜索").click()')
                lines.append(f'    time.sleep(2)')
            lines.append(f'    report.step("列表验证", screenshot=page)')
            lines.append(f'')

    # 断言
    if assertions:
        lines.append(f'    # ---- 断言验证 ----')
        search_key = fields[0]["key"] if fields else "search_name"
        assert_lines = gen_assertions(assertions, search_var=search_key)
        for l in assert_lines:
            lines.append(f'    {l}')
        lines.append(f'')

    # 行内操作（发布等）
    for act in row_actions:
        action_text = act.get("text", "")
        act_lines = gen_row_action(act, fields[0]["key"] if fields else "search_name")
        if act_lines:
            lines.append(f'    # 行内操作: {action_text}')
            for l in act_lines:
                lines.append(f'    {l}')
            # 发布后轮询
            if act.get("action") == "publish":
                lines.append(f'    time.sleep(8)')
                lines.append(f'    report.step("点击{action_text}→确认", screenshot=page)')
                lines.append(f'    # 轮询等待状态变更')
                lines.append(f'    page.goto(f"{{{base_ref}}}{url.replace("Edit","List")}", wait_until="networkidle")')
                lines.append(f'    published = False')
                lines.append(f'    for wait_i in range(6):')
                lines.append(f'        time.sleep(5)')
                lines.append(f'        page.goto(f"{{{base_ref}}}{url.replace("Edit","List")}", wait_until="networkidle")')
                lines.append(f'        time.sleep(1)')
                lines.append(f'        row = page.locator("tr").filter(has_text={fields[0]["key"] if fields else "search_name"})')
                lines.append(f'        if row.count() > 0:')
                lines.append(f'            cells = row.locator("td").filter(has_text="发布")')
                lines.append(f'            if cells.count() > 0:')
                lines.append(f'                report.assertion("UI: 状态变为发布", True, f"等待{{wait_i+1}}次")')
                lines.append(f'                published = True')
                lines.append(f'                break')
                lines.append(f'    if not published:')
                lines.append(f'        report.assertion("UI: 状态变为发布", False, "轮询超时")')
                lines.append(f'')

    # 弹窗交互
    for dlg in dialogs:
        if dlg.get("action_button") == "发布":
            continue  # 已在row_actions中处理
        dlg_lines = gen_dialog_interaction(dlg)
        for l in dlg_lines:
            lines.append(f'    {l}')

    lines.append(f'    return True')
    lines.append(f'')

    return "\n".join(lines)


def generate_db_helpers():
    """生成数据库辅助函数"""
    return '''\
# ============ 数据库断言辅助 ============
from config import get_db_connection


def db_check_exists(table, by_field, by_value):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} WHERE {by_field}=%s", (by_value,))
    row = cur.fetchone()
    cur.close(); conn.close()
    assert row is not None, f"DB断言失败: {table}.{by_field}='{by_value}' 未找到"
    return f"DB: {table} 记录已存在 (by {by_field}={by_value})"
'''

def render_with_jinja2(manifests):
    """使用 Jinja2 模板渲染完整测试脚本（如果 jinja2 不可用则回退到字符串拼接）"""
    if not HAS_JINJA2:
        return None

    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    template_file = os.path.join(template_dir, "page_script.j2")
    if not os.path.isfile(template_file):
        return None

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("page_script.j2")

    page_functions = []
    for mf in manifests:
        pid = mf["page_id"]
        title = mf["title"]
        body = generate_page_function(mf)
        page_functions.append({
            "pid": pid,
            "title": title,
            "body": body,
        })

    return template.render(
        suite_name="设备综合管理系统自动化测试",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        page_functions=page_functions,
    )


def generate_full_script(manifests):
    """生成完整测试脚本"""
    # 优先尝试 Jinja2 模板渲染
    jinja2_output = render_with_jinja2(manifests)
    if jinja2_output is not None:
        return jinja2_output

    # 回退到原生字符串拼接
    lines = []
    lines.append('#!/usr/bin/env python3')
    lines.append('"""')
    lines.append('由 manifest_generator.py 自动生成的测试脚本骨架')
    lines.append(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append('"""')
    lines.append('import sys, time')
    lines.append('from playwright.sync_api import sync_playwright')
    lines.append('from report_helper import TestReport')
    lines.append('from config import BASE_URL')
    lines.append('')
    lines.append('')
    lines.append(generate_db_helpers())
    lines.append('')
    lines.append('')
    lines.append('def run():')
    lines.append('    report = TestReport("设备综合管理系统自动化测试")')
    lines.append('')
    lines.append('    with sync_playwright() as p:')
    lines.append('        browser = p.chromium.launch(headless=False)')
    lines.append('        ctx = browser.new_context(viewport={"width": 1500, "height": 900})')
    lines.append('        page = ctx.new_page()')
    lines.append('')
    lines.append('        try:')

    for mf in manifests:
        pid = mf["page_id"]
        title = mf["title"]
        lines.append(f'            report.scene_start("{title}", "执行{title}")')
        lines.append(f'            do_{pid}(report, page)')
        lines.append(f'            report.scene_end(True)')
        lines.append(f'')

    lines.append('        except Exception as e:')
    lines.append('            print(f"异常: {e}")')
    lines.append('            import traceback; traceback.print_exc()')
    lines.append('            if report.current_scene: report.scene_end(False)')
    lines.append('        finally:')
    lines.append('            browser.close()')
    lines.append('')
    lines.append('    html_path = report.generate_html()')
    lines.append('    print(f"\\n📋 报告: {html_path}")')
    lines.append('')
    lines.append('')
    lines.append('if __name__ == "__main__":')
    lines.append('    run()')
    lines.append('')

    return "\n".join(lines)


# ============================================================
# CLI入口
# ============================================================

if __name__ == "__main__":
    import glob

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--compose":
        # 组合模式：从场景定义文件生成完整脚本
        with open(sys.argv[2], encoding="utf-8") as f:
            scene_def = json.load(f)
        # 加载所有引用的manifest
        manifests = []
        for ref in scene_def.get("scenes", []):
            mf_path = os.path.join(os.path.dirname(sys.argv[2]), ref["manifest"])
            with open(mf_path, encoding="utf-8") as mf:
                manifests.append(json.load(mf))
        print(generate_full_script(manifests))
    else:
        # 单一manifest模式
        for path in sys.argv[1:]:
            for fpath in glob.glob(path):
                with open(fpath, encoding="utf-8") as f:
                    manifest = json.load(f)
                print(generate_page_function(manifest))
