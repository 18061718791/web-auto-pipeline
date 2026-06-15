# Verify-Save 模式：防静默保存失败

> 2026-06-09 基于 device_management_test.py 调试总结

## 问题

表单保存后无任何提示（无成功/错误 toast、无 console error、无网络请求异常），但数据未写入 DB，脚本继续执行后续场景导致断言失败。

**典型触发因素：**
- el-autocomplete popper 未关闭，遮挡保存按钮（点击到 popper 上）
- 表单验证错误被隐藏（字段格式错误但不显示错误消息）
- 后端唯一约束冲突（如设备 IP 与已有 PV IP 重复）
- 外键约束导致 INSERT 被静默拒绝

## `verify_save()` 实现

```python
def verify_save(page, report, step_name, db_verify_fn, db_args,
                expected_url_segment=None, timeout=15):
    """
    保存结果三重确认：
    1. API 响应监听（匹配 save/add/insert/edit/update URL）
    2. URL 变化检测（保存成功通常跳转列表页）
    3. DB 直查轮询（最终保障，循环重试 15 秒）
    4. 成功 toast 检测（.el-message--success）
    """
```

### 调用示例

```python
save_ok = verify_save(page, report, "创建设备",
                      db_check_device, [CON_NAME, "draft"],
                      expected_url_segment="cDeviceList")
if not save_ok:
    report.scene_end(False)
    return report
```

### 返回值

| 值 | 含义 | 后续处理 |
|:---|:---|:---|
| `True` | 保存成功（API/URL/toast/DB 任一确认） | 继续执行后续断言 |
| `False` | 15 秒内无确认信号 | `scene_end(False); return report` 终止 |

### 关键设计约束

1. **函数必须自包含** — 定义在 `run()` 外部时，不能依赖 `log()` 闭包，所有输出用 `print()`
2. **`page.on("response")` 必须在 click 前注册** — 否则可能错过 200 响应
3. **每次调用创建新监听器** — 函数内部定义 `on_save_response`，不污染全局
4. **超时后重试一次 DB** — 偶现后端写入延迟超过 15 秒，在 return False 前做最后一次 DB 直查

## 适用于

- 所有表单类型的保存操作（创建/编辑）
- 发布操作（若涉及确认对话框，需区分「点击确认」和「等待发布完成」两个阶段）
- 不适用于纯列表翻页查询操作

## 集成 checklist

- [ ] `page.on("response", ...)` 在 click 前注册
- [ ] 函数外定义时用 `print()` 输出，不依赖 `log()` 闭包
- [ ] `import time` 在函数内部导入
- [ ] `from urllib.parse import urlparse` 在函数内部导入
- [ ] 保存前检查 `.el-form-item__error` 是否存在
- [ ] `expected_url_segment` 传目标列表页路径片段
- [ ] 调用后判断返回值并提前 `return report`
