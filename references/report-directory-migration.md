# 测试报告目录迁移：从平铺到模块子目录

当平台的测试报告文件平铺在 `e2e/` 或 `atomic/` 根目录下时，可以按模块归类到子目录以便查找。

## 原理

每个脚本的报告文件名以 `{script_id}_` 开头。`SCRIPT_REPORT_SUBDIRS` 字典定义了 `script_id → 模块子目录名` 的映射。迁移脚本遍历报告目录，按前缀匹配文件名，按映射移入子目录。

## 迁移脚本模板

```python
import os, shutil

# 配置（按实际情况修改）
REPORT_DIR = 'platforms/{platform}/docs/reports'
SCRIPT_REPORT_SUBDIRS = {
    # 从 config.py 复制
    "device_management": "device-management",
    "sn_lifecycle": "sn-management",
    # ...
}

def migrate(base_dir, script_type):
    if not os.path.isdir(base_dir):
        return
    for fname in sorted(os.listdir(base_dir)):
        fpath = os.path.join(base_dir, fname)
        if not os.path.isfile(fpath):
            continue
        # 按 script_id 前缀匹配
        matched = next((sid for sid in SCRIPT_REPORT_SUBDIRS
                        if fname.startswith(sid + '_')), None)
        if matched:
            subdir = SCRIPT_REPORT_SUBDIRS[matched]
            target_dir = os.path.join(base_dir, subdir)
            os.makedirs(target_dir, exist_ok=True)
            shutil.move(fpath, os.path.join(target_dir, fname))
            print(f'  Moved: {fname} -> {script_type}/{subdir}/')
        else:
            print(f'  Skipped (unmatched): {fname}')

migrate(os.path.join(REPORT_DIR, 'e2e'), 'e2e')
migrate(os.path.join(REPORT_DIR, 'atomic'), 'atomic')
```

## 注意事项

- **先备份**：迁移前确认有备份或版本控制
- **旧文件名兼容**：严格按 `{script_id}_` 前缀匹配。裸 `测试报告_{ts}.html`（无前缀）无法匹配，会留在根目录，后续由 `cleanup_old_reports()` 清理
- **跨平台统一**：所有平台使用同一份 `SCRIPT_REPORT_SUBDIRS` 模式，`config.py` 中定义，`get_script_report_dir()` 使用
- **runner 兼容**：迁移后 runner 中的报告路径已改为相对路径（相对于 `REPORT_DIR`），自动适配子目录
