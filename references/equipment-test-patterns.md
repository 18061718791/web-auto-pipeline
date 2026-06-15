
## 跨场景导航：左侧菜单直接点击（不回首页，不用顶部 tab）

场景 4 → 5 → 6 之间不再需要回首页重新点菜单，也不推荐使用顶部 tab 链接。
**正确做法**：直接点击左侧菜单项，从当前页面切换。

```
场景4: 装置设备列表 → 点击左侧菜单[全局视图] → 验证段
场景5: 全局视图 → 点击左侧菜单[系统视图] → 验证段+系统
场景6: 系统视图 → 点击左侧菜单[装置→装置] → 搜索 → 注销
```

### click_menu_item() 实现

```python
def click_menu_item(page, text):
    """直接点击左侧菜单项（不回首页）"""
    return page.evaluate("""(text) => {
        var items = document.querySelectorAll('.el-menu-item');
        for (var item of items) {
            var t = item.innerText.trim();
            if (t === text || t.includes(text)) {
                item.click(); return true;
            }
        }
        return false;
    }""", text)


def navigate_to_device_list(page, first_time=False):
    """导航到装置设备列表页。"""
    if first_time:
        # 首次：从首页点菜单进入
        page.goto(f"{BASE_URL}/overview/home", wait_until="domcontentloaded")
        time.sleep(2)
        page.evaluate("""() => {
            var items = document.querySelectorAll('.el-menu-item, .el-sub-menu__title');
            for (var item of items) {
                if (item.innerText.trim() === '装置' && item.closest('.el-sub-menu')) {
                    item.click(); return;
                }
            }
        }""")
        time.sleep(1.5)
        page.evaluate("""() => {
            var items = document.querySelectorAll('.el-menu-item');
            for (var item of items) {
                var t = item.innerText.trim();
                if (t === '装置设备' || t === '装置') { item.click(); return; }
            }
        }""")
        time.sleep(2)
    else:
        # 后续：直接用左侧菜单点击 "装置 → 装置"（子菜单项）
        page.evaluate("""() => {
            var subs = document.querySelectorAll('.el-sub-menu__title');
            for (var s of subs) {
                if (s.innerText.trim() === '装置') {
                    var parent = s.closest('.el-sub-menu');
                    if (parent && !parent.classList.contains('is-opened')) { s.click(); }
                    break;
                }
            }
            setTimeout(function() {
                var items = document.querySelectorAll('.el-menu-item');
                for (var item of items) {
                    var t = item.innerText.trim();
                    if (t === '装置') {
                        var parentSub = item.closest('.el-sub-menu');
                        if (parentSub) { item.click(); return; }
                    }
                }
            }, 500);
        }""")
        time.sleep(2)
```

> ⚠️ **关键注意**：左侧菜单子项的文字是"装置"（不是"装置设备"）。`click_menu_item("装置")` 会匹配两个元素（子菜单标题 + 子菜单项），必须通过 `closest('.el-sub-menu')` 区分。

### 首次 vs 后续导航

| 时机 | 方法 | 说明 |
|:---|:---|:---|
| 首次进入（场景1） | goto 首页 → 左侧菜单 JS evaluate | 确保 SPA 状态正确初始化 |
| 后续跨页（场景2→6） | 左侧菜单直接 `click_menu_item()` | 不回首页，不污染 SPA 状态 |
