# Runner 报告解析修复 — regex 模式兼容多种输出格式

## 发现问题

2026-06-08 执行全量测试(有头模式)后 runner 未生成聚合报告。根因为 `core/runner.py` 的 `run_script()` 函数使用固定 regex 解析子脚本 stdout，但 regex 与脚本实际输出格式不匹配。

## 症状

- Runner 正常执行脚本（脚本生成 HTML 报告）
- 但聚合报告中 `report_path` 为 None，`scene_stats` 全部为 0
- 聚合报告无法链接到各子报告

## 根因

`run_script()` 中有 3 个 regex 解析点，均与脚本输出不匹配：

### 1. 报告路径提取（L82）

```python
# 匹配失败 regex
m = re.search(r'📋.*报告已生成:\s*(.+)', line)

# 实际输出格式（device_management_test.py）
# 📋 测试报告: D:\path\to\report.html
# 📋 报告: D:\path\to\report.html  (atomic scripts)
```

### 2. 场景统计提取（L89）

```python
# 匹配失败 regex
m = re.search(r'📊\s*场景:\s*通过(\d+)\s*失败(\d+)\s*跳过(\d+)', line)

# 实际输出格式
# E2E: 总计: 9  通过: 9  跳过: 0  失败: 0  （无 📊 前缀）
# Atomic: 📊 场景: 通过6 失败0 总计6  （无 跳过 字段）
```

### 3. 断言统计提取（L96）

```python
# 匹配失败 regex
m = re.search(r'📊\s*断言:\s*通过(\d+)\s*失败(\d+)', line)

# 实际输出格式
# 无断言统计单独行，仅报告中有 25/26 断言通过
```

## 修复方案

替换为兼容多种格式的 regex：

```python
# 1. 报告路径 — 兼容 测试报告 / 报告已生成 / 报告
m = re.search(r'📋\s*(?:测试报告|报告已生成|报告):\s*(.+)', line)

# 2a. 场景统计 — 完整格式（E2E 脚本）
m = re.search(r'📊\s*场景:\s*通过(\d+)\s*失败(\d+)\s*跳过(\d+)', line)

# 2b. 场景统计 — 无跳过字段（原子脚本）
m2 = re.search(r'📊\s*场景:\s*通过(\d+)\s*失败(\d+)\s*总计(\d+)', line)

# 2c. 场景统计 — 无 📊 前缀（device_management_test.py 最终输出）
m3 = re.search(r'总计:\s*(\d+)\s*通过:\s*(\d+)\s*跳过:\s*(\d+)\s*失败:\s*(\d+)', line)

# 3. 断言统计 — 兼容 25/26 断言通过 格式
m2 = re.search(r'(\d+)/(\d+)\s*断言通过', line)
```

选型原则：每个场景统计格式之间是 **OR 关系**（如果格式1没匹配到，尝试格式2/3），不是 AND。用独立的 `if m / if m2 / if m3` 避免了交叉覆盖问题。

## 验证方式

```bash
# 有头模式验证输出可见
python run.py --platform iot

# 检查聚合报告
# platforms/iot/docs/reports/全量测试报告_{ts}.html
# 确认：
#  - 所有脚本卡片有场景统计数字（非0/0/0）
#  - 每个脚本卡片有"查看详细报告"链接
#  - 数据流向图显示正确状态
```
