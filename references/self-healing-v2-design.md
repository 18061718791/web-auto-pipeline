# Self-Healing v2 设计：从「事后诊断」到「运行时治愈」

> 2026-06-10 基于 13 个脚本、378 张截图、28 个故障信号的调试经验沉淀。

## 现状：当前自愈的局限

| 维度 | 当前状态 | 问题 |
|:---|:---|:---|
| 时机 | 事后诊断（跑完后读日志/报告） | 不能预防失败，失败已经发生 |
| 介入 | 只输出修复建议 | 不自动修复，需要用户手动改脚本 |
| 上下文 | 无运行时状态 | 不知道当前页面、组件类型、场景阶段 |
| 信号覆盖 | 28 个已知信号 | 只覆盖了 4 个高确定性信号做自动修复 |
| 集成度 | 独立 CLI 工具 | 不集成到 runner 中，不参与脚本执行 |

## v2 架构：6 模块运行时 Healer

```
┌─────────────────────────────────────────────────────────────────┐
│                    HealingOrchestrator                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Selector     │  │ Component    │  │ Save         │          │
│  │ Healer       │  │ Healer       │  │ Healer       │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ 5-level      │  │ autocomplete │  │ pre-close    │          │
│  │ fallback:    │  │ select       │  │ popper       │          │
│  │ placeholder │  │ cascader     │  │ 3-signal     │          │
│  │ → label      │  │ upload       │  │ verify       │          │
│  │ → aria-label │  │ retry        │  │ auto-retry   │          │
│  │ → visible    │  │ chain        │  │ IP/MAC fix   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ State        │  │ Assert       │  │ Recovery     │          │
│  │ Healer       │  │ Healer       │  │ Healer       │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ about:blank  │  │ auto detect  │  │ browser      │          │
│  │ → navigate   │  │ column type  │  │ crash →      │          │
│  │ login page   │  │ → adapt      │  │ restart      │          │
│  │ → re-navi    │  │ comparison   │  │ page deadlock │          │
│  │ scene offset │  │              │  │ → refresh    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 1. SelectorHealer：选择器 5 级降级

当 `get_by_placeholder` / `get_by_label` 超时时，自动按链降级：

| 级别 | 策略 | 命中场景 |
|:---:|:---|:---|
| 1 | `get_by_placeholder(hint)` | 标准输入框 |
| 2 | `get_by_label(hint)` | 模型页表单（有 `<label>`） |
| 3 | `locator('[aria-label="hint"]')` | 无 label 无 placeholder |
| 4 | `locator('input:visible').filter(has_text=hint)` | 模糊匹配 |
| 5 | `locator('input[placeholder*="hint"]')` | 属性子串匹配 |

每级超时 3 秒，命中后记录级别，同 hint 下次优先从历史命中级别开始。

### 2. ComponentHealer：组件交互自愈

**el-autocomplete（#1 静默失败源）：** fill → 等 3s debounce → `.el-autocomplete__popper li` click → 验证值 → Escape 关闭 popper。失败后自动降级 dispatchEvent 点击。

**el-select：** force click 打开 → 1.5s 等待 → force click 选项 → 验证选中。降级链：键盘 ArrowDown+Enter → JS dispatchEvent mousedown。

**el-cascader：** force click 展开 → 勾选 `.el-checkbox` 而非节点文本 → Escape 关闭。

### 3. SaveHealer：保存操作自愈

保存前：检查 popper 遮挡 → Escape 关闭 → 检查 `.el-form-item__error` → 自动 IP/MAC 修正。

保存后：四路信号轮询 15 秒（API 200 / URL 跳转 / 成功 toast / DB 直查）。

失败后：自动重试 2 次（含 Escape + 重新点击）。

```python
save_ok = healer.save_and_verify(page, report, "创建设备",
    db_verify_fn=db_check_device, db_args=[CON_NAME],
    expected_url="cDeviceList")
```

### 4. StateHealer：页面状态恢复

检测当前页面状态与预期状态的偏差：
- `about:blank` → 自动导航到目标 URL
- 登录页（session 过期） → 自动导航
- 详情页/编辑页 → 导航回列表页
- 场景衔接偏移 → 自动检测 + 导航恢复

### 5. AssertHealer：DB 断言类型适配

自动查询 `information_schema.columns` 获取真实类型：
- `boolean` → `actual is True/False`
- `integer/smallint/bigint` → `actual == int(expected)`
- `varchar/text` → `actual == str(expected)`

### 6. RecoveryHealer：严重故障恢复

- 浏览器崩溃（`browser closed` / `Target closed`） → 重启浏览器
- 页面死锁（30s 超时） → 刷新页面
- 网络请求异常 → 重试

## 集成路径

```
Step 1（P0）：实现 SaveHealer + ComponentHealer（autocomplete）
  影响：13 个脚本中每个保存/autocomplete 操作
  文件：core/healer/save_healer.py, core/healer/component_healer.py
  
Step 2（P1）：实现 SelectorHealer + StateHealer
  影响：定位失败减少 50%，场景衔接稳定
  文件：core/healer/selector_healer.py, core/healer/state_healer.py
  
Step 3（P2）：实现 AssertHealer + RecoveryHealer
  影响：DB 断言类型错误归零，崩溃自动恢复
  文件：core/healer/assert_healer.py, core/healer/recovery_healer.py
```

## 效果预估

| 故障类型 | 当前 | v2 后 | 降低 |
|:---|:---:|:---:|:---:|
| el-autocomplete 静默失败 | 人工排查 | 自动重试 + 降级 | ~85% |
| 保存按钮无响应 | 5 步排查 | Escape + 重试 + 修正 | ~80% |
| 选择器不匹配 | 改脚本 | 自动 5 级降级 | ~90% |
| 场景边界偏移 | 加 goto | 自检 + 导航恢复 | ~70% |
| DB 类型猜错 | 人工查表 | 自动检测适配 | ~95% |
| 浏览器崩溃 | 脚本重跑 | 自动恢复 | ~60% |

整体可靠性提升约 5 倍（中断点从 65 降至 ~13）。
