# 平台探索方法论（4 阶段标准化流程）

## 概览

| 阶段 | 目标 | 输入 | 产出 |
|:---|:---|:---|:---|
| **Phase 1: 菜单发现** | 获取完整导航树和所有可访问 URL | 平台首页 URL | `all_pages.json` |
| **Phase 2: 页面深度分析** | 每个页面的交互元素清单 | `all_pages.json` | `phase2_report.json` |
| **Phase 3: 表单/详情页** | 文档化每个编辑表单的字段 | Phase 2 结果 | `phase3_forms.json` |
| **Phase 4: 数据依赖图谱** | 完整的实体-数据依赖链 | Phase 3 结果 | `phase4_dependency.json` |

## 工作流

### Phase 1：全量路由发现 + 菜单遍历

两种互补方式获取所有可访问页面：

**方法 A：Vue Router 直接读取**
```python
routes = page.evaluate("""() => {
    try {
        const app = document.querySelector('#app').__vue_app__;
        const router = app.config.globalProperties.$router;
        if (router) {
            return router.getRoutes().filter(r => r.path && !r.path.includes(':')
                && !r.path.includes('*') && r.path !== '/')
                .map(r => ({path: r.path, name: r.name || ''}));
        }
        return [];
    } catch(e) { return []; }
}""")
```

**方法 B：菜单树遍历**
```python
# 展开所有菜单
page.evaluate("""() => {
    document.querySelectorAll('.el-sub-menu').forEach(el => {
        el.classList.add('is-opened');
        el.setAttribute('aria-expanded', 'true');
    });
}""")
time.sleep(1)
# 收集所有菜单项及其链接
menu_items = page.evaluate("""() => {
    return Array.from(document.querySelectorAll('.el-menu-item')).map(el => ({
        text: el.innerText.trim(),
        path: el.getAttribute('data-vue-router-path') || ''
    }));
}""")
```

### Phase 2：逐页深度分析

对每个列表页，自动化分析：
- 搜索/筛选区域（input、select、button）
- 表格/列表（列数、数据类型、操作按钮）
- 分页组件
- 导出/导入入口

### Phase 3：表单字段提取

```python
inputs = page.locator('input:visible, textarea:visible, .el-input__inner:visible').all()
for inp in inputs:
    pid = inp.get_attribute('id') or ''
    ph = inp.get_attribute('placeholder') or ''
    label_el = page.locator(f'label[for="{pid}"]').first
    label_text = label_el.inner_text().strip() if label_el.count() > 0 else ''
    print(f"  placeholder='{ph}' label='{label_text}'")
```

### Phase 4：数据依赖图

1. 识别所有实体类型（PV、元件模型、元件、设备模型、设备 等）
2. 标记每对实体之间的创建依赖（如"设备模型需要已发布的元件模型"）
3. 标记关联操作（如"设备模型页面有`添加元件模型`按钮"）
4. 输出完整的有向依赖图

### 输出格式

每个阶段输出一个 JSON 文件到 `platforms/{id}/docs/output/{id}/explore_{ts}/`：

```json
{
  "phase": 1,
  "timestamp": "20260608_120000",
  "pages": [
    {"path": "/controllerType/clist", "type": "list", "components": [...]}
  ]
}
```


---

## 附录：平台探索器常见陷阱（来源：`explorer_pitfalls.md`）

# 平台探索器 - 常见问题与陷阱

## URL 构造陷阱

**错误方式（会导致URL路径重复）：**
```python
full_url = f"{base_url.rstrip('/jwsiot')}{r['path']}"
# 当 base_url = "http://host/jwsiot/overview/home" 时
# rstrip('/jwsiot') 不会按你想的工作！
# 结果: http://host/jwsiot/overview/home/controllerType/clist  ❌
```

**正确方式：**
```python
# 方法1: 直接提取 origin
origin = "http://host:port"  # 从 base_url 的 scheme + netloc
full_url = f"{origin}{r['path']}"

# 方法2: 从 base_url 提取根
origin = base_url.split('/jwsiot')[0]  # 取到 "http://host:port"
full_url = f"{origin}{r['path']}"

# 方法3: 固定已知origin
full_url = f"http://10.30.25.183:28080{r['path']}"
```

## Vue Router 发现时机

首页加载完成后**立刻**读取 Vue Router，不要等到菜单展开后。有些平台的路由表只在首页初始化注入。

**检测方式：**
```python
routes = await page.evaluate("""
() => {
    try {
        const app = document.querySelector('#app').__vue_app__;
        const router = app.config.globalProperties.$router;
        if (router) {
            return router.getRoutes().map(r => ({path: r.path, title: r.meta?.title || r.name || ''}));
        }
        return [];
    } catch(e) {
        return [];
    }
}
""")
```

## 页面过滤

Vue Router 会返回全部路由（包括 edit/add/detail 等后台页面）。需要过滤只保留列表页：

```python
list_routes = [r for r in routes if not any(
    x in r['path'].lower() for x in [
        'edit', 'detail', 'version', 'add', 
        'instrument', 'quick', 'subdevice',
        'redirect', 'login', 'register', 'develop',
        'home2', 'list2', ':path'
    ]
)]
```

## 超时处理

批量探索多个页面时，每个页面需要单独超时控制（15s/页），否则整体会在600s超时：

```python
try:
    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    await page.wait_for_timeout(2000)
except:
    pass  # 超时的页面跳过，不影响后续
```

## 报告图表大小

Chart.js 默认会撑满容器。`chart-card` 必须**固定宽度**（不用 `flex:1`），`canvas` 必须约束大小：

```css
.chart-card { width: 380px; margin: 0 auto; }
.chart-card canvas { max-width: 260px; max-height: 260px; margin: 0 auto; display: block; }
```


---

## 附录：Vue SPA 路由探索技术（来源：`vue-spa-route-exploration.md`）

# Vue SPA 路由探索技术

## 问题

Vue SPA 的路由由前端 Router 管理，`page.goto()` 直接访问 URL 可能触发路由守卫/重定向，无法100%复现菜单真实路径。点击菜单时 `page.url` 的更新有异步延迟，直接读 `page.url` 会拿到前一个页面的 URL。

## 两步验证法

### 第一步：JS 点击菜单获取候选路由

```python
def click_by_js(page, item_text):
    """用JS直接点击菜单项，绕过Playwright可见性检查"""
    ok = page.evaluate("""(t) => {
        const items = document.querySelectorAll('.el-menu-item');
        for (let i of items) {
            if (i.innerText.trim() === t) {
                i.click();
                return true;
            }
        }
        return false;
    }""", item_text)
    time.sleep(2.5)  # 等待SPA路由完成
    return ok

# 使用
click_by_js(page, '装置模型')
candidate = page.url  # 候选路由
```

### 第二步：直接 goto 验证

```python
# 对每个候选路由，直接 page.goto 验证非404
page.goto(f"{BASE_URL}{candidate}", wait_until='domcontentloaded', timeout=15000)
time.sleep(2)
title = page.title()
body = page.locator('body').inner_text()[:300]

is_valid = True
if '404' in title: is_valid = False
if 'nginx' in body.lower()[:50]: is_valid = False
# 检查页面是否渲染正常（有侧边栏、非空白页）
```

## 常见问题

| 问题 | 表现 | 原因 | 解决 |
|:---|:---|:---|:---|
| 路由串位 | 菜单A显示路由B的URL | JS click后 SPA 路由未完成，`page.url` 仍是上一个页面 | 加 `time.sleep(2.5)`；或用 `page.wait_for_url()` 等待变化 |
| 元素不可见 | Playwright timeout | `el-menu-item` 在sidebar视口外（overflow hidden） | 用 `page.evaluate()` 执行原生的 `el.click()`，不经过 Playwright 可见性检查 |
| 子菜单折叠 | 找不到菜单项 | 父级 `.el-sub-menu` 未展开 `is-opened` | 先 JS 点击 `.el-sub-menu__title` 展开，再点子项 |
| `get_by_placeholder("* 模型名称")` 超时 | 表单字段无法定位 | Element Plus 表单使用 `<label for="id">`，`*` 在 label 文本中**不存在** | 用 `get_by_label("模型名称")` 而非在placeholder中加 `*` |

## 表单字段定位检查清单

写入脚本前必须逐一确认：

```python
inputs = page.locator('input, textarea, .el-input__inner').all()
for inp in inputs:
    if inp.is_visible():
        pid = inp.get_attribute('id') or ''
        ph = inp.get_attribute('placeholder') or ''
        label_el = page.locator(f'label[for="{pid}"]').first
        label_text = label_el.inner_text().strip() if label_el.count() > 0 else ''
        aria = inp.get_attribute('aria-label') or ''
        print(f"  id='{pid}' ph='{ph}' label='{label_text}' aria='{aria}'")
```

据此选择：
- 有 `placeholder` → `get_by_placeholder("完整文本")`
- 无 placeholder 但有 `label[for]` → `get_by_label("label文本")`
- 只有 `aria-label` → `get_by_role("textbox", name="aria文本")`


---

## 附录：Vue Router 全量路由发现技术（来源：`vue_router_discovery.md`）

# Vue Router 全量路由发现技术

## 原理

对于 Vue 3 + Element UI 框架的 Web 管理平台，可以通过 `__vue_app__` 全局属性直接读取 Vue Router 的完整路由表。这比菜单遍历更全面（能发现隐藏页面、半成品页面），也比菜单遍历更快。

## 核心代码

```python
routes = await page.evaluate("""
() => {
    try {
        const app = document.querySelector('#app').__vue_app__;
        const router = app.config.globalProperties.$router;
        if (router) {
            return router.getRoutes()
                .filter(r => r.path && !r.path.includes(':') 
                    && !r.path.includes('*') && r.path !== '/' 
                    && r.path !== '/login' && r.path !== '/401')
                .map(r => ({
                    path: r.path, 
                    name: r.name || '', 
                    title: r.meta?.title || r.name || ''
                }));
        }
        return [];
    } catch(e) {
        return [];
    }
}
""")
```

## URL 拼接

不能直接用 `base_url + path` 拼接，因为 base_url 可能包含子路径（如 `/jwsiot/overview/home`）。

**正确做法：** 取 base_url 的 origin 部分：

```python
origin = self.base_url.split('/jwsiot')[0]
full_url = f"{origin}{r['path']}"
```

或者更通用的方式：

```python
from urllib.parse import urlparse
parsed = urlparse(self.base_url)
origin = f"{parsed.scheme}://{parsed.netloc}"
full_url = f"{origin}{r['path']}"
```

## 过滤策略

路由表通常包含大量 detail/edit 类页面，需要过滤掉。过滤规则：

```python
list_routes = [r for r in routes if not any(
    x in r['path'].lower() for x in [
        'edit', 'detail', 'version', 'add', 'instrument', 
        'quick', 'subdevice', 'redirect', 'login', 'register',
        'develop', 'home2', 'list2', ':path'
    ]
)]
```

## 降级方案

当 Vue Router 不可用时（非 Vue 框架、Vue 版本差异、CSP 限制），必须降级到菜单遍历。

**识别不可用的信号：** `evaluate` 返回空数组或包含 `error` 字段。

**菜单遍历策略：**

1. 用 JS 展开所有 `el-sub-menu`：
```javascript
document.querySelectorAll('.el-sub-menu').forEach(el => {
    el.classList.add('is-opened');
    el.setAttribute('aria-expanded', 'true');
})
```

2. 通过 `querySelectorAll(':scope > [role="menuitem"]')` 找到顶级菜单

3. 对每项顶级菜单: click 展开 → 获取所有可见的 `el-menu-item` → 逐个 click → 记录 URL

## 已知陷阱

- 有些平台的路由 path 包含 `:param` 参数占位符（如 `/detail/:id`），需要过滤掉，否则访问会 404
- `overview/home` 类型路径中如果 base_url 已有 `/jwsiot/overview/home`，拼接后会得到 `/jwsiot/overview/home/controllerType/clist`（错误），必须用 origin 级别拼接
- Vue 3.4+ 的 `__vue_app__` 可能在严格 CSP 下不可访问
