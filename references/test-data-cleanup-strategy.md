# 测试数据清理策略

> 2026-06-09 用于解决 `AUTO_` 前缀测试数据残留问题。

## 问题背景

原子脚本使用 `AUTO_{MODULE}_{TIMESTAMP}` 时间戳前缀命名测试数据，每次运行创建不同名字。仅按当前名字清理不会触及上一次运行的数据——这是垃圾数据产生的核心原因。

## 解决方案

### 方案 A：`finally` 块追加 LIKE 模式清理（必须在每个脚本中实现）

```python
finally:
    browser.close()
    # 清理本模块所有 AUTO_ 前缀测试数据
    try:
        c = get_db_connection(); cu = c.cursor()
        cu.execute("DELETE FROM thing_model_relation_ship WHERE parent_id IN (SELECT id FROM thing_model WHERE thing_name LIKE 'AUTO_MODULE_%') OR sub_id IN (SELECT id FROM thing_model WHERE thing_name LIKE 'AUTO_MODULE_%')")
        cu.execute("DELETE FROM thing_model_version WHERE thing_model_id IN (SELECT id FROM thing_model WHERE thing_name LIKE 'AUTO_MODULE_%')")
        cu.execute("DELETE FROM thing_model WHERE thing_name LIKE 'AUTO_MODULE_%'")
        c.commit(); cu.close(); c.close()
    except: pass
```

- **放置位置**：`finally` 块中 `browser.close()` 之后，报告生成之前
- **清理时机**：无论脚本成功或失败，都能清理
- **模式匹配**：`AUTO_MODULE_%` 必须与脚本的 `DATA_PREFIX` 一致

### 方案 B：`_cleanup.py` 批量清理工具（项目根目录）

```bash
python _cleanup.py                    # dry-run 预览
python _cleanup.py --execute          # 实际清理
python _cleanup.py --execute --force  # 跳过确认
```

覆盖表（按删除顺序）：
1. `thing_model_relation_ship` — 通过 `thing_model.id` JOIN 关联
2. `thing_model_version` — 通过 `thing_model.id` JOIN 关联
3. `thing_model` — `thing_name LIKE 'AUTO_%'`
4. `device` — `device_name LIKE 'AUTO_%'`
5. `device_sn` — 通过 `device.id` JOIN 关联
6. `device_tags` — `tag_code LIKE 'AUTO_%'`
7. `pv_data_info` — `pv_code LIKE 'AUTO_%'`
8. `pv_data_relation` — 通过 `pv_data_info.id` JOIN 关联
9. `facility_info` — `facility_name LIKE 'AUTO_%'`

## 验证方法

```bash
# 运行一个原子脚本后验证无残留
python _cleanup.py
# 输出应为: 总计: 0 条待清理的 AUTO_ 测试数据
```

## 注意事项

- `AUTO_SEGMENT_%` → `AUTO_SEG_%` 一致性问题（2026-06-09 修复）
- 清理 SQL 必须写在 `browser.close()` 之后，避免浏览器进程未关闭时 DB 连接被占用
- `except: pass` 确保清理失败不影响测试结果
