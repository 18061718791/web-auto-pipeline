# Ghost 文件清理方法论

> 从 2026-06-09 的 web-auto-pipeline 全量优化 session 中提炼。将 41 个 reference 文件中的 16 个真幽灵文件分类清理，降至 28 个有效文件。

## 三步法

### Step 1: 审计列表

用 Python 脚本统计当前文件状态：

```python
import os, re

ref_dir = "path/to/references/"
all_files = sorted(f for f in os.listdir(ref_dir) if f.endswith('.md'))
skill = open("SKILL.md", encoding='utf-8').read()

# 提取被索引的文件名
indexed = set()
for line in skill.split('\n'):
    if '| `' in line and '.md`' in line:
        matches = re.findall(r'`([^`]+\.md)`', line)
        for m in matches:
            indexed.add(m)

# 从正文中提取被引用的文件名
mentioned = set(f for f in all_files if f in skill)

unindexed = set(all_files) - indexed
truly_ghost = unindexed - mentioned       # 完全无人引用的
mentioned_but_not_indexed = unindexed & mentioned  # 被引用但不在索引表中
```

产出 3 个分类列表：真幽灵、引用未索引、已索引。

### Step 2: 分类处置

| 分类 | 判断标准 | 处置 |
|:---|:---|:---|
| **可安全删除** | 内容已被更高层次文件完全覆盖 | `os.remove()` 直接删除 |
| **可合并到宿主** | 有独立价值，但与现有文件有重叠 | 将唯一内容作为附录追加到宿主文件末尾，删除原文件 |
| **保留并索引** | 有完全独立的价值，不可被其他文件替代 | 加入 SKILL.md 文件索引表 |

**合并时的安全模式**（关键 — 历史上发生过内容丢失事故）：

```python
# ✅ 安全：用 += 分步拼接
result = target_file
result += "\n\n---\n\n## 附录：{标签}（来源：`{source_filename}`）\n\n"
result += source_content
open(target_path, 'w').write(result)

# ❌ 危险：条件表达式优先级陷阱
# pem_updated = pem + "\n..." + content if cond else "\n..." + content
# 当 cond=False 时，pem 被完全丢弃！
```

### Step 3: 索引同步更新

1. 删除被合并文件后，更新 SKILL.md 中的「其他(N 个)」计数
2. 新增索引条目给合并后的宿主文件
3. 验证交叉引用无断裂：`re.findall(r'references/([a-zA-Z0-9_.-]+)', skill)` 全部存在

## 合并附录模板

```markdown
---

## 附录：{原文件名描述用途}（来源：`{原文件名}`）

{原文件内容}
```

## 验证清单

- [ ] 所有被删除的源文件已从 SKILL.md 索引中移除
- [ ] 「其他(N 个)」计数与实际未索引文件数一致
- [ ] 所有合并后的宿主文件开头非空行（无截断）
- [ ] `skill_view` 返回的 `linked_files` 与实际磁盘文件一致
- [ ] 所有 SKILL.md 中的 `references/xxx.md` 交叉引用可解析
