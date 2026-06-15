# IoT 物联管理平台 — 路由全映射（2026-06-08 验证）

> 通过浏览器菜单逐一点击验证，每条路由已确认页面正常渲染（非 404、非 nginx 默认页）。
> 最终验证 24 条路由全部通过。

## 装置管理

| 菜单项 | 路由 | 类型 | 备注 |
|:---|:---|---:|:---|
| 全局视图 | `/pv/list` | 列表 | 实际上是 PV 管理列表（全局视图可能就是 PV 默认页） |
| 系统视图 | `/overview/home` | 仪表盘 | 平台整体概览 |
| 系统管理 | `/logicalView/view` | 列表 | 逻辑视图管理 |
| 装置模型 | `/system/device` | 列表 | 装置模型列表（类型 `FACILITY`）— ⚠️ 直接 `page.goto()` 不触发 FACILITY 过滤，页面显示空列表。必须通过左侧菜单点击「装置模型」导航，或使用 `navigate_to_facility_list()` 辅助函数 |
| 装置 | `/equipmentType/eqcTypeList` | 列表 | 装置实例列表 |
| 段模型 | `/compositeDeviceType/cTypeList` | 列表 | ⚠️ 之前误列为 `/eqcompositeDevice/eqcDeviceList`（2026-06-10 修正） |
| 段（实体） | `/compositeDevice/cDeviceList` | 列表 | ⚠️ 之前误列为 `/compositeDeviceType/cTypeList`（2026-06-10 修正） |
| 设备模型 | `/controllerType/clist` | 列表 | 设备模型列表（类型 `GIANT`） |
| 设备 | `/controller/cDeviceList` | 列表 | 设备实例列表（类型 `GIANT`） |
| 元件模型 | `/elementType/elist` | 列表 | 元件模型列表（类型 `SI`） |
| 元件 | `/element/eDeviceList` | 列表 | 元件实例列表（类型 `SI`） |
| SN管理 | `/sn/list` | 列表 | SN 管理列表 |

### PV 管理子项

| 菜单项 | 路由 | 备注 |
|:---|---:|:---|
| PV管理 | `/pv/list` | 默认页 |
| 批次导入 | `/pv/list`（同页） | 表格上方按钮 |
| 我的已办 | `/pv/done` | 已完成待办 |
| 我的待办 | `/pv/todo` | 待处理事项 |
| Bypass管理 | `/pv/relation` | Bypass 关联列表 |
| 分类标签 | `/tag/list` | 标签管理列表 |

## 运行管理

| 菜单项 | 路由 | 类型 |
|:---|---:|:---|
| 设备控制 | `/deviceControl/operate` | 操作页 |
| 批量控制 | `/deviceControl/operate` | 同页（参数不同） |
| 操作历史 | `/typeSet/setting` | 类型设置 |
| 告警总览 | `/operate/historyLog` | 操作日志（实际是历史日志） |
| 告警管理 | `/alarm/list` | 告警列表 |
| 设备协同 | `/sceneLinkage/sceneList` | 场景联动 |
| 设备故障 | `/Snapshot/list` | 故障快照 |
| 系统日志 | `/systemLog/logList` | 系统日志列表 |

## 数据服务

| 菜单项 | 路由 | 类型 |
|:---|---:|:---|
| 设备订阅 | `/subscribe/list` | 订阅列表 |
| 数据权限 | `/auth/label` | 权限标签管理 |
| 业务字典 | `/subscribe/list`（同上） | 与设备订阅同页 |

## 新增/编辑页面路由模式

| 模块 | 列表路由 | 新增路由 | 编辑路由 |
|:---|---:|---:|---:|
| 元件模型 | `/elementType/elist` | `/elementType/eEdit?type=create` | `/elementType/eEdit?type=edit&id={id}` |
| 设备模型 | `/controllerType/clist` | `/controllerType/cEdit?type=create` | `/controllerType/cEdit?type=edit&id={id}` |
| 装置模型 | `/system/device`（SPA 路由） | `/equipmentType/eqcTypeEdit?type=create` | `/equipmentType/eqcTypeEdit?type=edit&id={id}` |
| 装置（设备实例） | `/eqcompositeDevice/eqcDeviceList` | 通过列表页「快速初始化」按钮进入 | 无独立编辑路由 |
| 段模型 | `/compositeDeviceType/cTypeList` | `/compositeDeviceType/cTypeEdit?type=create` | `/compositeDeviceType/cTypeEdit?type=edit&id={id}` |
| 段（实体） | `/compositeDevice/cDeviceList` | `/compositeDevice/cDeviceEdit?type=create` | `/compositeDevice/cDeviceEdit?type=edit&id={id}&deviceStatus={status}` |
| 元件 | `/element/eDeviceList` | `/element/eDeviceEdit?type=create` | — |
| 设备 | `/controller/cDeviceList` | `/controller/cDeviceEdit?type=create` | — |
| PV | `/pv/list` | `/pv/edit?type=create` | `/pv/edit?type=edit&id={id}` |
| SN | `/sn/list` | `/sn/edit?type=create` | — |
| 标签 | `/tag/list` | `/tag/edit?type=create` | — |
| Bypass | `/pv/relation` | `/pv/relationEdit?type=create` | — |

> **注意**：装置、段模型、段的 create 路由标记为"待验证"——基于模型路由模式推测，需实际浏览器确认。

## DB 关键表结构

### thing_model（所有模型的统一存储表）

| 列 | 类型 | 说明 |
|:---|---:|:---|
| `id` | int | PK |
| `thing_name` | varchar | 模型名称 |
| `thing_code` | varchar | 模型编码 |
| `thing_type` | varchar | `SI`=元件, `GIANT`=设备, `FACILITY`=装置 |
| `thing_status` | varchar | `draft`, `release` |

### thing_model_version

| 列 | 类型 |
|:---|---:|
| `id` | int |
| `thing_model_id` | int (FK → thing_model.id) |
| `version_status` | varchar (`draft`, `release`) |

### pv_data_info（PV 存储）

| 列 | 类型 | 是否可为空 |
|:---|---:|:---:|
| `id` | int | NO |
| `pv_code` | varchar | NO |
| `pv_desc` | varchar | YES (**注意：不是 `description`**) |
| `ip` | varchar | YES |
| `port` | varchar | YES |
| `acq_mode` | varchar | YES (搜索过滤器要求此字段有值) |
| `acq_freq` | int | YES |
| `arch_freq` | int | YES |
| `device_id` | int (FK → device.id) | YES (搜索过滤器要求此字段有值) |
| `is_delete` | bool | YES (搜索过滤 `is_delete=false`) |
