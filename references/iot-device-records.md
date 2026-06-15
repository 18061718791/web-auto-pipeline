# IoT 设备模块调试记录

## 目录

- [设备创建流程](#设备创建流程)
- [设备模型创建流程](#设备模型创建流程)
- [全生命周期调试](#全生命周期调试)
- [设备管理调试记录](#设备管理调试记录)

---

## 设备创建流程

> 来源：device-creation.md

# 设备创建（实例化）流程与陷阱

## 页面路由

| 功能 | URL | 说明 |
|------|-----|------|
| 设备创建页 | `/controller/cDeviceEdit?type=create` | Vue Router 路径 |
| 设备列表页 | `/controller/cDeviceList` | 与设备模型列表 `/controllerType/clist` 不同 |
| 设备编辑页 | `/controller/cDeviceEdit?type=edit&id=N` | N 为设备 ID |

## 表单字段

| 字段 | placeholder | 必填 | 类型 |
|------|-------------|:----:|------|
| 设备名称 | 请输入设备名称 | * | textbox |
| 设备编码 | 请输入设备编码 | * | textbox |
| 安装位置 | 请输入安装位置 | | textbox |
| 设备模型 | 请输入设备模型名称搜索 | * | el-select (filterable) |
| IP地址 | 请输入IP地址 | * | textbox |
| 型号 | 请输入型号 | | textbox |
| 厂商 | 请输入厂商 | | textbox |
| MAC地址 | 请输入MAC地址 | * | textbox |
| 支持边缘计算 | 否（默认） | | combobox |
| 标签 | 请选择标签 | | tag selector |
| 描述信息 | 请输入描述信息 | | textarea |

## 操作流程

### 场景8：创建设备并关联元件

1. **填写基础信息**
   - 设备名称：自动化测试-设备v1
   - 设备编码：webwright-device-001
   - 安装位置：LEBT段

2. **选择设备模型**
   - 设备模型字段是 el-select（filterable 本地过滤模式）
   - 点击输入框 → 输入"自动化测试-设备模型" → 等待2s → 点选下拉选项
   - 选项容器：`.el-select-dropdown`，选项元素：`.el-select-dropdown__item`
   - 选择后顶部显示"模型名称：自动化测试-设备模型"和"模型版本：v1"

3. **填写其他必填项**
   - IP地址：192.168.1.100
   - 型号：WebWright-Test
   - 厂商：自动化测试厂商
   - MAC地址：00:1A:2B:3C:4D:5E

4. **切换到【元件】标签页**
   - 点击 tab "元件"
   - 切换到元件关联页面

5. **关联已发布的元件**
   - 树形结构中显示已选择的元件模型（如"自动化测试-元件模型(v1)"）
   - 在树节点下的 combobox 输入框中输入已发布的元件名称（如"自动化测试-元件v2"）
   - 等待下拉选项出现（需2s debounce 等待）
   - 点击选中该元件
   - 确认树节点下显示已选元件

6. **点击"保存"**

## 设备发布

### 场景9：发布设备

1. 在设备列表页找到目标设备行
2. 点击行内的"发布"按钮
3. 弹出确认对话框：**"确认发布设备 '自动化测试-设备v1' 吗？"**
4. 点击"确定"确认发布
5. 后台异步处理，等待后刷新列表
6. 状态变为"发布"，删除按钮 disabled

### 弹窗文案对比

| 场景 | 对话框文案 |
|------|-----------|
| 设备模型发布 | "确认发布吗？" |
| 设备发布 | "确认发布设备 'XXX' 吗？" |
| 元件发布 | "确认发布设备 'XXX' 吗？"（格式类似） |

## 常见陷阱

1. **el-select filterable 与 el-autocomplete 混淆**
   - 设备创建页的"设备模型"选择是 el-select（filterable），不是 el-autocomplete
   - 区别：el-select 选项在 `.el-select-dropdown`，内容本地过滤，无需异步等待
   - el-autocomplete 选项在 `.el-autocomplete__popper`，需要异步 fetch，需等待 2-2.5s

2. **必须关联元件后才能保存**
   - 如果不切换到【元件】tab 关联元件，保存后设备无关联元件
   - 但平台不会阻止保存（不报错），只是元件数量为0

3. **保存后页面停留在编辑页**
   - 设备保存后不会自动跳转到列表页
   - 必须手动导航到 `/controller/cDeviceList` 确认记录存在

4. **按钮点击需要 JS 方式**
   - 发布按钮在某些情况下 Hermes 的 ref 点击无法触发确认对话框
   - 可用 JS 方式代替：`document.querySelector('button').click()`

5. **确认对话框文案不同**
   - 设备发布的确认文案格式为"确认发布设备 'XXX' 吗？"
   - 发布确认脚本需要匹配具体文案

---

## 设备模型创建流程

> 来源：device-model-creation.md

# 设备模型创建完整流程与陷阱

## URL路径（关键！）

- ✅ 创建页：`/controllerType/cEdit?type=create`
- ✅ 列表页：`/controllerType/clist`
- ❌ 错误路径：`/deviceType/eDeviceTypeEdit?type=create`（返回404空页）
- ❌ 错误路径：`/deviceType/elist`（返回404空页）

Vue路由为 `controllerType` 而非 `deviceType`。

## 基础信息

| 字段 | placeholder | 备注 |
|------|-----------|------|
| 模型名称 | `请输入模型名称` | 必填 |
| 模型编码 | `请输入模型编码` | 必填 |
| 模型描述 | `请输入模型描述` | 必填 |
| 版本描述 | `版本描述` | 可选 |

**⚠️ 已调试确认：** placeholder 与元件模型页一致（`请输入模型名称`），不是旧版记录的 `* 模型名称`。不要用 `*` 前缀去匹配。

## 属性行操作

点击"添加属性"按钮后，表格中出现一行包含以下列：

### 读/写设置
- 默认值：**只读**
- 需要设置为：**读写**
- 操作：点击 combobox → 展开 dropdown → 点击"读写"选项
- combobox 在 snapshot 中表现为 `[ref=e30]` 这类 clickable generic

### 数据类型设置
- 默认值：**整数**
- 需要设置为：**双精度**
- 操作：点击 combobox → 展开 dropdown → 点击"双精度"选项
- 选择"双精度"后，类型规格区域会显示：最小值、最大值、单位、步长、精度 五个输入框

### 其他字段
- 名称：输入属性名（如"运行频率"）
- 描述：输入属性描述（如"设备运行频率回读"）

## 元件模型关联（必须！否则保存失败）

设备模型创建页底部有一个独立的"元件模型"区域（`<h3>元件模型</h3>` + `<button>添加元件模型</button>`）。

### 操作步骤
1. 点击"添加元件模型"按钮
2. 在出现的表格中，第一行是一个 combobox（el-autocomplete），其输入框 placeholder 为 `"请输入模型名称搜索"`
3. 在输入框中输入已发布的元件模型名称（如 `"自动化测试-元件模型"`）
4. 等待下拉选项出现（需要等 debounce + 异步请求）
5. 点击下拉选项中的对应项（如 `"自动化测试-元件模型 v1"`）
6. 确认表格中显示：
   - 模型名称列：显示已选模型名
   - 版本列：显示版本号（如 "v1"）
   - "查看详情"按钮从 disabled 变为 enabled

### 不关联的后果
**保存按钮点击后无任何反应**：
- 无 toast/notification
- 无网络请求（performance API 看不到 save/create 请求）
- 无表单验证错误提示
- 页面不跳转

这是因为表单验证未通过（关联元件模型是必填项），但 Element UI 的验证提示没有正确显示。

## 保存成功验证

保存成功后导航到列表页（`/controllerType/clist`），在列表中可以看到新创建的记录。

### 版本信息列解读
格式：`草稿:N 注销:N 发布:N`
- `草稿:1 注销:0 发布:0` = 刚创建，尚未发布
- `草稿:0 注销:0 发布:1` = 已发布

## 发布设备模型

在列表页点击"版本详情"按钮 → 进入版本详情页（`/controllerType/c-version-detail?mainVerId=X`）→ 点击"发布版本"按钮 → 确认对话框点击"确定"。

**注意**：设备模型的发布流程与元件模型相同（进入版本详情→发布版本），**与元件/设备的发布流程不同**（后者在列表页直接点发布即可）。

## 陷阱总结

| 陷阱 | 现象 | 修复 |
|------|------|------|
| URL路径错误 | 页面空白或404 | 用 `/controllerType/` 前缀 |
| 未关联元件模型就保存 | 保存无反应、无网络请求 | 必须先添加元件模型关联 |
| 读/写默认为"只读" | 属性不可读写 | 手动改为"读写" |
| 数据类型默认为"整数" | 精度不符合要求 | 手动改为"双精度" |
| placeholder用错（`* 模型名称`） | fill() 找不到元素 | 用 `请输入模型名称` 匹配 |

---

## 全生命周期调试

> 来源：device-full-lifecycle-20260605.md

# 设备管理模块全生命周期调试记录 (2026-06-05)

## 完整 9 场景依赖链

```
场景1: PV创建 (pv_data_info)
  ↓
场景2: 元件模型创建 (thing_model) + 属性
  ↓
场景3: 发布元件模型 (version_status=release)
  ↓
场景4: 元件创建 (device表, status=draft) + PV关联(物模型tab)
  ↓
场景5: 发布元件 (device_status=release)
  ↓
场景6: 设备模型创建 (thing_model) + 关联元件模型(弹窗)
  ↓
场景7: 发布设备模型 (version_status=release)
  ↓
场景8: 设备创建 (device表, status=draft) + 元件关联(元件tab)
  ↓
场景9: 发布设备 (device_status=release)
```

## 关键发现

### 1. Save 按钮不在 `<form>` 内

Element Plus 的页面布局中，保存按钮通常与表单字段分离——按钮在 `header` 区域，表单字段在 `body` 区域。这意味着：

- `form.submit()` 无效
- 按钮的 `onclick` 在 DOM 中为 `null`（Vue 使用事件委托）
- 必须点击按钮本身，且需确保无 popper overlay 遮挡

### 2. el-autocomplete Popper 阻塞后续点击

el-autocomplete 输入并选择选项后，popper 仍保持打开状态（透明不可见但仍在 DOM 中）。这个 popper 会拦截后续所有点击事件，包括保存按钮。

**修复：** 点击保存前必须执行至少一次 `page.keyboard.press("Escape")` 关闭 popper。

### 3. 设备模型选择决定表单行为

不同设备模型"自动化测试-设备模型"(无子设备)  vs  "Controller-Model-Temp"(有子设备) 有不同的保存要求：

- 无子设备模型 → 直接在设备信息 tab 填写后保存
- 有子设备模型 → 必须先切到"元件"tab，搜索并关联元件后保存
- 不关联元件会弹出警告："请为所有子设备选择具体的元件"

### 4. autocomplete 选中值含版本后缀

选择 autocomplete 选项后，输入框的值可能包含版本后缀：
```
"Controller-Model-Temp v1"   ← 实际值
```
这在代码断言和后续逻辑处理中需注意。

### 5. 保存成功不跳转不弹消息

IoT 平台的创建设备页面保存成功后的行为：
- URL 不变（仍为创建页）
- 无成功消息（无 el-message--success）
- 唯一的可靠验证方式是 DB 直查

### 6. 发布状态的正确检测方式

列表页中"发布"状态检测的关键区分：
- 草稿状态 → 操作列有"发布"按钮（button text="发布"）
- 已发布状态 → 状态列显示"发布"文字（td 文本含"发布"）

查看发布状态应检测 `row.locator("td").filter(has_text="发布")` 确认状态变更,而非查找"发布"按钮。

### 7. Tab 切换可能丢失表单绑定

元件创建页（场景4）需要先选元件模型，然后切换到"物模型"tab 才能看到 PV 关联字段。如果在选择模型前切换 Tab，该 Tab 内容为空。设备创建页（场景8）同理——需要先选设备模型再切换"元件"tab。

### 8. `[role='option']` 在某些页面可用

在设备创建页（`/controller/cDeviceEdit`），autocomplete 的下拉选项同时具备 `role='option'` 属性和 `<li>` 结构，两种定位方式均可。但元件创建页（`/element/eDeviceEdit`）的 autocomplete 选项只有 `<li>` 无 `role='option'`，只能用 `.el-autocomplete__popper li`。

---

## 设备管理调试记录

> 来源：device-mgmt-debugging-20260605.md

# 设备管理模块调试记录 (2026-06-05)

## 场景信息

- 测试对象: IoT 物联管理平台 - 设备管理模块 (场景6-9)
- 脚本: `device_mgmt_scenes6-9.py`
- 依赖链: 创建设备模型 → 发布设备模型 → 创建设备 → 发布设备
- 前置数据: 已发布的元件模型 "自动化测试-元件模型" + 已发布的元件 "自动化测试-元件v2"

## 验证结果

| 场景 | 内容 | 耗时 | 状态 |
|:---|:---|:---:|:---:|
| 场景6 | 创建设备模型 + 关联元件模型 | 25s | ✅ |
| 场景7 | 发布设备模型 | 18s | ✅ |
| 场景8 | 创建设备 | 32s | ✅ |
| 场景9 | 发布设备 | 24s | ✅ |
| **总计** | **4场景/12断言** | **99s** | **✅** |

## 根因分析 — 3个隐藏陷阱

### 陷阱1: MAC 地址数据库唯一约束

**现象**: 设备创建「保存」后无报错，但 DB 无数据、列表无记录。check_page_errors 显示 `✅ 页面无报错`。

**根因**: `device` 表的 `mac` 字段有 UNIQUE 约束。由于之前多次调试使用了相同的硬编码 MAC 地址，后续运行全部因唯一约束失败。`el-message--error` 弹出了 "MAC地址 [00:1A:2B:3C:4D:5E] 已被使用" 但在 8 秒轮询窗口内未捕获到（消息出现时间不确定）。

**修复**:
```python
mac_suffix = str(hash(DEVICE_NAME) % 1000000).zfill(6)[:6]
dev_mac = f"00:1A:2B:{mac_suffix[:2]}:{mac_suffix[2:4]}:{mac_suffix[4:6]}"
page.get_by_placeholder("请输入MAC地址").fill(dev_mac)
```

同时在 `check_page_errors` 的 `backend_keywords` 中添加 `"已被使用"`。

### 陷阱2: 发布状态检测逻辑反向

**现象**: 设备已发布成功（DB `device_status=release`），但脚本判断为「未发布」，超时失败。

**根因**: 列表页的行内状态列显示"发布"表示**已发布状态**（不是待发布）。之前写的条件是 `if "发布" not in row_text` → 已发布的行含有"发布"文本，所以条件为 False，判定为未发布。

**正确检测**:
```python
# 已发布的行中，状态列 td 包含"发布"文字
cells = row.locator("td").filter(has_text="发布")
if cells.count() > 0:
    published = True  # ✅ 文本"发布"=已发布
```

### 陷阱3: 切换到无内容的 Tab 后保存按钮失效

**现象**: 切换到「元件」Tab 再切回「设备信息」Tab 后，点击保存按钮无任何响应（无网络请求、无提示消息、数据未写入）。

**根因**: Vue SPA 的 `el-tabs` 切换会卸载/重建 Tab 内的组件。如果目标 Tab 无内容（显示"暂无数据"），切换操作可能导致表单的 v-model 绑定丢失，使保存按钮的事件监听失效。

**修复**: 如果「元件」Tab 的搜索输入框不存在（`input[placeholder='请输入元件名称搜索']` 的 count=0），**不切换 Tab**，直接在当前 Tab 保存。设备在没有关联元件的情况下也能创建成功。

---

## 关键经验总结

1. **保存成功不可靠的信号**: URL 未变化、无消息提示、无网络请求 — 这些都不能判定保存失败。**唯一可靠的验证方式是 DB 直查**。
2. **重复运行的硬编码陷阱**: MAC 地址、编码等 DB 唯一约束字段必须每次运行生成不同值。`RUN_ID` 时间戳 + `hash()` 取模是最简单的方式。
3. **先读现有脚本再动手**: 设计新场景前必须先通读已验证的 `device_managent_test.py`，画出完整的依赖链，否则会遗漏关键前置条件。
4. **check_page_errors 的局限性**: 8 秒轮询窗口不一定能捕获所有异步错误消息。对于关键保存操作，额外的验证手段是必要的（如监听 `page.on("request")`）。


---

## Bypass 生命周期记录（来源：`bypass-lifecycle.md`）

# Bypass 管理全生命周期场景设计

## 脚本信息

- **文件:** `bypass_lifecycle_test.py`
- **依赖:** device_management_test.py 创建的 PV（`IP-SAFE-RFQ-CR:MDP01:RunFreq_Rd`）+ 自愈创建 ASSOC_PV_1/2
- **自愈:** `ensure_prerequisites()` 自动 INSERT 缺失的 PV 到 `pv_data_info`
- **场景数:** 5（新增→查询→编辑增→编辑删→删除）
- **执行耗时:** ~47 秒

## 页面与URL

| 页面 | URL | 说明 |
|:---|:---|:---|
| Bypass关联列表 | `/pv/relation` | 搜索/查看 |
| Bypass关联编辑 | `/pv/relationEdit?type=create` | 新增/编辑 |

## 数据库

| 表名 | 字段 | 说明 |
|:---|:---|:---|
| `pv_data_relation` | `id`, `m_pv_id`, `c_pv_id` | Bypass关联关系 |
| `pv_data_info` | `id`, `pv_code` | PV 主表（关联外键） |

## 测试数据

| 变量 | 值 | 来源 | 创建方式 |
|:---|:---|---:|---:|
| `BYPASS_PV` | `IP-SAFE-RFQ-CR:MDP01:RunFreq_Rd` | device_management_test.py 创建 | 脚本数据链 |
| `ASSOC_PV_1` | `1111222333` | 自愈创建 | `create_pv_if_missing()` 自动 INSERT |
| `ASSOC_PV_2` | `IA-MEBT-NM:heartbeatst3` | 自愈创建 | `create_pv_if_missing()` 自动 INSERT |

## 场景设计（完整5场景）

### 场景1：新增Bypass关联

**操作流程：**
1. 导航到新增页 (`/pv/relationEdit?type=create`)
2. el-select 选择 BypassPV（`force=True` + `.el-select-dropdown__item` 方案）
3. 验证下拉文本已从"请选择"变为 PV 名
4. 搜索可关联 PV1
5. 点击行内"关联"按钮 → PV1 移到已关联区域
6. 验证已关联区域包含 PV1
7. 点击"确定"保存
8. 验证跳转到列表页
9. DB 验证关联记录已创建

**断言数：5**

### 场景2：查询Bypass关联

**操作流程：**
1. 复用列表页（`ensure_on_page` 跳过导航）
2. 按 BypassPV 名称搜索
3. 验证找到 1 行
4. 验证"影响PV"列计数 = 1

**断言数：2**

### 场景3：编辑—增加关联PV2

**操作流程：**
1. 复用列表页 → 搜索 → 点"编辑"
2. 验证编辑页加载
3. 搜索可关联 PV2
4. 点击行内"关联" → PV2 移到已关联区域
5. 验证已关联区域包含 PV2
6. 保存
7. DB 验证关联数 = 2

**断言数：3**

### 场景4：编辑—移除关联PV2（精细控制勾选框）

**操作流程：**
1. 复用列表页 → 搜索 → 点"编辑"
2. ★ 第一类验证：检查已关联 PV 区域的 checkbox 状态
3. 验证默认全勾选（表头 + PV1行 + PV2行 = 3个）
4. ★ 关键：取消勾选要保留的 PV1 行（nth(1)），PV2 行保持勾选
5. 验证勾选计数变为 1（仅 PV2）
6. 点击"移除"
7. 验证已关联 PV 计数从 2 → 1
8. 保存
9. DB 验证只剩 1 条关联（PV1）

**断言数：6**

### 场景5：删除Bypass关联

**操作流程：**
1. 复用列表页 → 搜索 → 点"删除"
2. 确认弹窗
3. 重新搜索验证已删除
4. DB 验证关联数为 0

**断言数：2**

## 自愈前置检查（2026-06-08 新增）

原 `check_prerequisites()` 仅检查 3 个 PV 是否存在，缺失则直接退出（`sys.exit(1)`）。重构为 `ensure_prerequisites()` + `create_pv_if_missing()`：

```python
def create_pv_if_missing(pv_name, ip="127.0.0.1", port="5064", desc="Bypass测试自动创建"):
    """自愈：如果PV不存在则自动创建（补全所有必要字段使其出现在可关联PV搜索中）"""
    from config import get_db_connection
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, acq_mode, device_id FROM pv_data_info WHERE pv_code=%s", (pv_name,))
        row = cur.fetchone()
        if row:
            pv_id, acq_mode, device_id = row
            # 如果已有PV但缺少必要字段 → 修复它
            if acq_mode is None or device_id is None:
                if device_id is None:
                    cur.execute("SELECT id FROM device WHERE device_status='release' ORDER BY id DESC LIMIT 1")
                    dev_row = cur.fetchone()
                    device_id = dev_row[0] if dev_row else None
                cur.execute(
                    "UPDATE pv_data_info SET acq_mode=%s, acq_freq=%s, arch_freq=%s, device_id=%s, is_delete=%s WHERE id=%s",
                    ('MONITOR', 1000, 3600000, device_id, False, pv_id)
                )
                conn.commit()
                log(f"  🔧 自愈: 已修复PV '{pv_name}' (id={pv_id}) acq_mode=MONITOR device_id={device_id}")
            cur.close(); conn.close()
            return pv_id

        # 找一个 release 状态的设备作为关联
        cur.execute("SELECT id FROM device WHERE device_status='release' ORDER BY id DESC LIMIT 1")
        dev_row = cur.fetchone()
        device_id = dev_row[0] if dev_row else None

        # 不存在 → 自动创建（必须补齐可关联PV搜索所需的字段）
        cur.execute(
            "INSERT INTO pv_data_info (pv_code, ip, port, pv_desc, acq_mode, acq_freq, arch_freq, device_id, is_delete) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (pv_name, ip, port, desc, 'MONITOR', 1000, 3600000, device_id, False)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        log(f"  🔧 自愈: 已创建PV '{pv_name}' (id={new_id}) acq_mode=MONITOR device_id={device_id}")
        cur.close(); conn.close()
        return new_id
    except Exception as e:
        conn.rollback()
        cur.close(); conn.close()
        log(f"  ❌ 自愈失败: 创建PV '{pv_name}' 时出错: {e}")
        return None
```
def ensure_prerequisites():
    ids = []
    for pv in [BYPASS_PV, ASSOC_PV_1, ASSOC_PV_2]:
        pid = create_pv_if_missing(pv)
        ids.append(pid)
    all_ok = all(ids)
    print(f"{'✅' if all_ok else '❌'} 前置检查: {'全部通过' if all_ok else f'部分失败 {ids}'}")
    return all_ok
```

**已知陷阱：**
- `pv_data_info` 表的描述列是 `pv_desc`，不是 `description`
- 仅 INSERT 不够 — PV 需要有 `acq_mode='MONITOR'`、`device_id`（任意 release 设备的 ID）、`is_delete=false` 才能在"可关联PV"搜索中出现
- 已存在但不完整的 PV 也需 UPDATE 修复（旧版本 `create_pv_if_missing` 只检查存在性，不补字段）

## 已知陷阱

### el-select 选择 — 使用双 force=True 方案

```python
page.get_by_role("combobox").click(force=True)       # 打开下拉
time.sleep(1.5)
opt = page.locator(".el-select-dropdown__item").filter(has_text="...").first
opt.click(force=True)                                  # 选选项
page.keyboard.press("Enter")
```

**关键：** 选项定位用 `.el-select-dropdown__item`（Element Plus 实际 class），不要用 `role="option"`（选项 DOM 无此 role）。

### 搜索框定位 — 用 get_by_label 而非 get_by_placeholder

Bypass 列表页的搜索输入框通过 `<label>` 元素关联，不是 `placeholder` 属性：
```python
# ❌ 错误
page.get_by_placeholder("BypassPV名称").fill(name)   # TimeoutError

# ✅ 正确
page.get_by_label("BypassPV名称").fill(name)
```

### 已关联PV区域的 checkbox 定位

- 用 `.el-checkbox.is-checked:not(.is-disabled)` 定位已勾选且可操作的 checkbox
- 顺序：第0个=表头全选，第1个=第1行，第2个=第2行
- 批量移除前必须验证 checkbox 状态，只让目标条目保持勾选

### 场景衔接 — 避免重复导航

脚本使用了 `ensure_on_page()` 工具方法，场景1保存后自动跳到列表页，后续场景不再重复 goto：
```python
ensure_on_page(page, LIST_URL)  # 判断当前URL，已到达则跳过
```
场景2~5 共跳过了 4 次导航，节省约 8 秒执行时间。


---

## SN 生命周期记录（来源：`sn-lifecycle.md`）

# SN全生命周期测试场景

## 页面路由

| 功能 | URL | 说明 |
|------|-----|------|
| SN编辑页（新增） | `/sn/edit?type=create` | 只有SN号一个字段 |
| SN列表页 | `/sn/list` | 支持搜索+分配操作 |

## 场景定义（sn_lifecycle.py）

| # | 场景 | 操作 | 断言 |
|:---:|:---|:---|:---|
| 1 | 新增SN号+分配按钮 | 填SN号 → 提交 → 列表搜索 | 列表显示 + 状态"待分配" + 有"分配"按钮 + DB pend_assign |
| 2 | 分配SN到设备 | 搜索 → 分配 → 弹窗选设备 → 确定 | 状态→"待激活"(无真实设备) + 设备标识填充 + 按钮禁用 + DB |
| 3 | 设备详情验证 | 查看设备详情 | 详情页含SN信息 |

## 关键交互细节

### SN新增
- **输入框placeholder**：`请输入SN号`（⚠️ 标签文字显示`* SN号`，但HTML placeholder属性是`请输入SN号` — 脚本必须用后者）
- 按钮文案：`提交`（不是`保存`）

### SN分配弹窗

- 弹窗标题：`选择设备`
- 搜索条件：设备名称(placeholder=`请输入设备名称`) + 设备编码(placeholder=`请输入设备编码`) + 搜索按钮
- 表格列：选择(单选radio) / 设备名称 / 设备编码 / 设备唯一标识 / 设备厂商 / 设备型号 / 设备状态 / 物理状态 / 创建时间
- 底部按钮：`取消` / `确认分配`
- ⚠️ **选择设备必须点击 `.el-radio` 的 label 元素**，点隐藏的 input 不会触发 Vue 事件
- ⚠️ **分配后确认按钮初始是 disabled 状态**，需选中设备后才启用

**Playwright 选择设备交互：**
```python
# 搜索设备
page.locator(".el-dialog input[placeholder*='设备名称']").fill(DEVICE_NAME)
page.locator(".el-dialog button").filter(has_text="搜索").click()
# 单选选择
page.locator(".el-dialog .el-radio").first.click()
# 确认分配
page.locator(".el-dialog button").filter(has_text="确认分配").click()
```

### 已分配SN与待分配SN的UI差异
- 列表行操作列：`编辑 分配 删除`（"待分配"状态的SN才有"分配"按钮）
- 分配弹窗：选择设备（el-select filterable）
- 分配后SN状态变为`待激活`（无真实设备激活的场景下），设备标识和设备名称自动填充
- 分配后编辑/删除按钮变为disabled

### 已分配SN与待分配SN的UI差异

| 属性 | 待分配 | 待激活（已分配，无真实设备） |
|:---|:---:|:---:|
| 设备标识列 | 空 | 已填充 |
| 设备名称列 | 空 | 已填充 |
| 证书列 | 空 | "查看证书" |
| 编辑按钮 | ✅ enabled | ❌ disabled |
| 删除按钮 | ✅ enabled | ❌ disabled |

## SN数据库表

SN数据存储在 `device_sn` 表中：

```sql
-- 表名：device_sn
-- 关键字段：sn, sn_state
-- 状态映射：pend_assign→待分配  effective→生效  expired→过期  wait_activate→待激活
SELECT id, sn, sn_state, create_at FROM device_sn WHERE sn='auto-test-sn-001';
```

设备SN关联存储在 `device.sn` 字段中：

```sql
SELECT device_name, device_code, sn FROM device WHERE device_name='自动化测试-设备v1';
```

**注意：** `device_sn` 表没有 `device_identification` 和 `device_name` 列 — 列表页显示的设备信息来自 device 表 JOIN。

## 脚本数据清理（必须两步走 ⚠️）

**执行SN全生命周期脚本前，必须先清理干净，否则旧SN绑定关系会导致测试失败：**

```python
# 必须同时做以下两步：
# 1) 删除 device_sn 表中的测试SN记录
cursor.execute("DELETE FROM device_sn WHERE sn LIKE 'auto-test-sn%'")
# 2) 将 device 表中对应测试设备的 sn 字段置空
cursor.execute("UPDATE device SET sn='' WHERE device_name LIKE '自动化测试%'")
#   （否则相同SN再次绑定时会处于"已绑定"状态，无法重新分配）
```

## 前置数据依赖

SN场景依赖场景1-9生成的数据：
- 需要已发布的设备（device_status='release'）
- 需要PV存在（验证前置数据完整性）
- 数据由 `e2e_full.py` 生成，`sn_lifecycle.py` 只消费不复写


---

## 标签生命周期记录（来源：`tag-lifecycle.md`）

# 分类标签全生命周期场景设计

## 场景定义（tag_lifecycle_test.py）

6个场景完整覆盖标签全生命周期：

| # | 场景 | 操作 | 断言 |
|:---:|:---|:---|:---|
| 1 | 新增标签 | 创建页 → 填名称/编码/描述 → 保存 | 列表存在 + 状态=草稿 + 操作列[发布][编辑][删除] + DB draft |
| 2 | 编辑标签 | 列表页→编辑→修改名称/描述→保存 | 列表显示新名称 + DB状态仍为draft |
| 3 | 标签查询 | 3次单条件(名称/编码/状态=草稿) + 1次组合条件(名称+编码+状态) | 每次查询都找到正确结果 |
| 4 | 发布标签 | 列表→行内发布→确认 | 状态=发布 + DB release |
| 5 | 发布后验证 | 搜索已发布标签 | 操作列[注销]替代[发布] + 不含[发布] |
| 6 | 设备关联 | 设备列表→编辑→选择标签→保存 | 设备列表标签列显示关联标签 |

## 关键发现

### 状态下拉框选择
el-select 的 dropdown popper 关闭后，选项 `<li>` 仍在 DOM 中但不可见。此时：
- `.click(force=True)` → Element is not visible
- `.evaluate("el => el.click()")` → 点了但 Vue 不更新 v-model
- **✅ `page.keyboard.press("ArrowDown")` + `Enter`** → 正确触发 Vue select 事件

### 查询场景必须完整
单条件查询必须测试 **所有** 条件各自的查询（3个条件就做3次单条件查询），再加1次组合条件。

### 状态差异验证
同一列表页在不同状态下显示不同的操作按钮。必须验证状态转换前后的操作列差异。


---

## PV 绑定 Bug 记录（来源：`pv-binding-bug.md`）

# PV绑定系统BUG — 确认复现

## 状态：已确认为平台系统BUG ✅

用户手动确认：**元件的关联PV功能存在系统BUG**（用户原话："元件的关联PV确实是有BUG"）

## BUG现象

使用正确的 el-autocomplete 交互流程（`.el-autocomplete__popper li` 选择器），输入框显示PV值正确，但保存后详情页为空：

```log
[17:04:19] [验证] 保存前输入框值: 'IP-SAFE-RFQ-CR:MDP01:RunFreq_Rd'
[17:04:19] [验证] PV值已绑定到输入框 ✅
[17:04:19] 点击保存...
[17:04:24] 保存完成 ✅
[17:04:27] 列表存在元件 ✅
[17:04:32] 详情页PV字段值: ''           ← BUG：未持久化
```

## 复现条件

| 条件 | 值 |
|:---|:---|
| 平台版本 | 物联管理平台（Vue 3 + Element Plus） |
| 入口 | 元件新增页 → 物模型tab → 关联PV |
| 组件 | el-autocomplete |
| 输入框placeholder | 请输入关联PV名称 |
| 选择器 | `.el-autocomplete__popper li`（正确选择器） |
| 操作步骤 | fill PV码 → 等2s → 点击选项 → 等2s → 保存 |
| 输入框显示值 | ✅ 正确显示（说明el-autocomplete select事件已触发） |
| 保存后详情页 | ❌ 空（说明后端没有接收到PV字段） |

## 尝试过的修复（均无效）

1. **JS强制设置Vue modelValue** — `ac.__vueParentComponent?.exposed?.modelValue = PV_CODE` → 无效
2. **原生input setter + 所有事件** — `nativeSetter.call(inp, PV_CODE)` + input/change/blur → 无效
3. **事后JS元素点击** — 在popper中再点击一次找到的li → `popper found but no matching li`（popper已关闭）

## 对脚本的影响

- 场景4的断言2（详情页→物模型tab→关联PV输入框）预期显示空值，不阻断脚本
- 该bug仅影响关联PV的持久化，不影响其他字段的保存
- **PV关联的断言应软检查** — 显示值则记录✅，不显示则记⚠️（已知BUG），不要FAIL

## 关联文件

- `e2e_full.py` 场景4 — PV关联步骤保持正确操作（即使有BUG）
- 主skill的「六、已确认的平台BUG」表已有记录


---

## 元件编辑 PV 绑定（来源：`element-edit-pv-binding.md`）

# 元件/设备编辑页 PV 绑定陷阱

## 问题背景

元件或设备创建时如果未在物模型 tab 中绑定 PV 就保存，之后必须通过编辑页面重新绑定。但编辑页面的 PV 绑定流程存在多个隐藏陷阱。

## 编辑页导航陷阱

### 直接导航 URL 失败

元件编辑页面的 URL 如 `eDeviceEdit?type=edit&id=9&deviceStatus=draft` 在 `browser_navigate` 中会触发 UTF-8 编码错误：

```
'utf-8' codec can't decode byte 0xb2 in position 5: invalid start byte
```

**解决方案**：不能直接 `browser_navigate` 到编辑页 URL。必须：
1. 先导航到元件列表页 `eDeviceList`
2. 通过 JavaScript 查找并点击行内编辑按钮

```javascript
// 在列表页执行
const rows = document.querySelectorAll('table tr');
for (let r of rows) {
    if (r.textContent.includes('目标元件名称')) {
        const btns = r.querySelectorAll('button');
        for (let b of btns) {
            if (b.textContent.includes('编辑')) {
                b.click();
                break;
            }
        }
    }
}
```

**注意**：Playwright 的 `browser_click` 点击列表页中的编辑按钮有时不触发导航（页面保持在列表页），JavaScript 直接 `.click()` 更稳定。

## 物模型 tab PV 绑定流程

### 步骤 1：切换到物模型 tab

元件编辑页默认显示"设备信息"tab，必须切换到"物模型"tab才能绑定 PV。

```python
await page.get_by_role("tab", name="物模型").click()
```

### 步骤 2：确认属性列表显示

切换后应显示属性配置列表，包含：名称、描述、读/写、关联PV列。

**如果显示"暂无数据"：**
- 元件模型未正确选择或未发布
- 必须先选择已发布的元件模型，物模型 tab 才会加载属性列表

### 步骤 3：点击关联PV输入框

关联PV列是一个 `el-autocomplete` 组件，内部结构为：

```html
<div class="el-autocomplete ...">
  <div class="el-input ...">
    <input class="el-input__inner" placeholder="请输入关联PV名称" />
  </div>
</div>
<button class="el-button el-button--text copy-btn ..." disabled>
  <!-- 复制按钮 -->
</button>
```

**关键观察点**：旁边的 `copy-btn` 按钮是 PV 绑定状态的最可靠指示器：
- `disabled` = PV 未被 Vue 正确识别（即使输入框有文本显示）
- `enabled` = PV 已被绑定（Vue v-model 已更新）

### 步骤 4：输入 PV 名称

用 Playwright 的 `browser_type` 向输入框写入完整 PV 名称（如 `IP-SAFE-RFQ-CR:MDP01:RunFreq_Rd`）。

### 步骤 5：触发下拉列表并选择

**仅仅输入文本不足以绑定 PV**。必须触发 `fetchSuggestions` 获取下拉列表，然后点击下拉选项以触发 Vue `select` 事件。

```python
# 1. 输入后等待 debounce
await page.wait_for_timeout(2000)

# 2. 用 JavaScript 查找并点击下拉选项
document.querySelectorAll('.el-popper li, .el-autocomplete-suggestion__list li').forEach(li => {
    if (li.textContent.includes('IP-SAFE-RFQ-CR')) {
        li.click();
    }
})
```

**特别注意**：即使下拉选项被点击了，也必须立即验证 `copy-btn` 是否从 `disabled` 变为 `enabled`。如果按钮仍为 disabled，说明 `select` 事件未触发，绑定未生效。

### 步骤 6：点击保存

保存按钮在页面顶部（与创建页位置相同）。

### 步骤 7：保存后验证

**必须做的验证（不能省略）**：

1. 保存后页面可能不自动跳转到列表页（某些版本保持在编辑页）
2. 手动导航到元件详情页 `eDeviceDetail?type=detail&id=9`
3. 切换到物模型 tab
4. 检查关联PV输入框是否显示已绑定的 PV 名称（而不是 placeholder"请输入关联PV名称"）

**如果详情页仍显示 placeholder**：说明绑定未生效，必须返回编辑页重试。

## 常见失败模式

| 现象 | 根因 | 解决 |
|------|------|------|
| 输入PV名后 copy-btn 仍为 disabled | Vue v-model 未更新，只是输入框显示值 | 确保点击下拉选项触发 select 事件 |
| 保存后详情页PV仍为空 | 保存请求未携带PV字段或服务端未处理 | 检查网络请求体，确认是否包含 pvId/pvName |
| 物模型 tab 显示"暂无数据" | 元件模型未选择或未发布 | 先选择已发布的元件模型 |
| 编辑页导航失败 | URL 含中文路径，browser_navigate 编码失败 | 通过列表页+按钮点击进入编辑页 |
| 保存后页面不跳转 | 平台特定行为 | 手动导航到列表页或详情页验证 |

## 发布元件时的 PV 连通性检查

元件发布不是立即完成的。后台需要确认 PV 连通性，会有一段时间的等待才会返回发布成功或失败的结果响应。

**建议流程**：
1. 在元件列表页点击"发布"按钮
2. 等待异步响应（可能几秒到几十秒）
3. 刷新列表页检查状态
4. 如果状态仍为"草稿"，检查是否有提示消息或错误对话框
5. 如果有连通性失败的错误提示，检查 PV 状态（如未连通则无法发布）

**注意**：发布元件和设备时必须确保 PV 已正确绑定，否则发布可能失败或返回错误。
