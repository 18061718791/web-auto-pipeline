# UI 前置数据（Fixture）创建规范

> 2026-06-09 创建，源自 device_model_atomic 和 element_atomic 中「设备模型需要已发布的元件模型才能关联」的调试经验。

## 问题背景

某些自动化场景依赖前置数据，且该数据**必须通过 UI 流程创建**才能被目标页面识别。典型场景：

- **设备模型 → 添加元件模型**：autocomplete 后端过滤 `version_status='release'`，DB 直插的模型不会出现在下拉中
- **设备 → 关联元件**：同样依赖已发布的元件/设备模型

## 核心原则

1. **前置数据必须走真实 UI 流程创建** — 不准 DB 直插。DB 直插的数据可能不满足后端的隐藏过滤条件（如版本状态、缓存索引等）
2. **前置场景不拿来做功能验证** — 中间步骤（填写表单、点击保存等）不做断言，只对最终发布结果做校验
3. **前置数据可复用** — 已存在的数据不重复创建，跳过创建步骤直接执行发布

## 标准实现模板

```python
# 在 run() 开头，try 块之前
MODEL_FIXTURE_NAME = f"{DATA_PREFIX}_关联模型"
MODEL_FIXTURE_CODE = f"{DATA_PREFIX}_md_code"

# 检查是否已存在
conn = get_db_connection(); cur = conn.cursor()
cur.execute("SELECT id FROM thing_model WHERE thing_name=%s", (MODEL_FIXTURE_NAME,))
existing = cur.fetchone()
cur.close(); conn.close()

if not existing:
    log(f"前置: 创建元件模型 {MODEL_FIXTURE_NAME}")
    page.goto(fixture_create_url, wait_until="domcontentloaded"); time.sleep(2)
    page.get_by_label("模型名称").fill(MODEL_FIXTURE_NAME)
    page.get_by_label("模型编码").fill(MODEL_FIXTURE_CODE)
    page.get_by_role("button", name="保存").click(); time.sleep(3)

    # 发布（让 autocomplete 能搜索到）
    page.goto(fixture_list_url, wait_until="domcontentloaded"); time.sleep(1)
    page.get_by_label("模型名称").fill(MODEL_FIXTURE_NAME)
    page.get_by_role("button", name="搜索").click(); time.sleep(2)
    row_m = page.locator("tr").filter(has_text=MODEL_FIXTURE_NAME)
    if row_m.count() > 0:
        row_m.locator("button").filter(has_text="版本详情").first.click(); time.sleep(2)
        page.get_by_role("button", name="发布版本").click(); time.sleep(1)
        c = page.locator("button").filter(has_text="确定").first
        if c.count() > 0: c.click(); time.sleep(2)
else:
    log(f"前置: 元件模型已存在 {MODEL_FIXTURE_NAME}")

# 最终仅校验发布结果
vs = get_version_status(MODEL_FIXTURE_NAME)
report.assertion("前置: 元件模型已发布(release)", vs == "release", f"版本状态={vs}")
```

## 适用范围

| 脚本 | 前置数据 | 数据通过了 UI 创建？ |
|:---|:---|:---:|
| `element_atomic_test.py` | 已发布的元件模型 | ✅ |
| `device_atomic_test.py` | 已发布的设备模型 | ✅ |
| `device_model_atomic_test.py` | 已发布的元件模型 | ✅ |

## 与 ensure_prerequisites() 自愈的区别

| 维度 | UI Fixture 模式 | `ensure_prerequisites()` 自愈 |
|:---|:---|:---|
| 创建方式 | 走完整 UI 流程（增→查→发布） | 直接 DB INSERT/UPDATE |
| 适用场景 | autocomplete 等 UI 组件依赖的状态 | 仅数据层面的前置依赖（Bypass 关联） |
| 断言粒度 | 仅最终发布状态 | 不断言 |
| 失败影响 | 前置失败 → 整个脚本无法运行 | 自愈失败 → 跳到下一个前置 |
