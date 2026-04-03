# VFB Instance Manager

**Blender add-on · v1.0.1** — Find duplicate scene structure (collections, object roots, shared data, mesh geometry) relative to a **reference**, then **simplify** or replace duplicates with **collection-instance empties**. Save your work before destructive operators; use **Undo** when needed.

**Copyright [Viclant](https://viclant.com).** **V.F.B** is the department responsible for this add-on. Site: **https://viclant.com**

**Repository:** [github.com/Viclant/VFB_instance_manager](https://github.com/Viclant/VFB_instance_manager)

| Item | Value |
|------|--------|
| Display name | **VFB Instance Manager** |
| Module / folder | **`VFB_instance_manager`** |
| Release archive | **`VFB_instance_manager.zip`** (folder `VFB_instance_manager/` at zip root with `__init__.py`) |
| `bl_info.version` | **(1, 0, 1)** |
| Copyright holder | **Viclant** |
| Responsible department | **V.F.B** |
| Website | **https://viclant.com** |

---

## English

### Features

- **Reference collection** — duplicate root collections vs reference; **parts inside reference** (sibling subcollections, shared data blocks, mesh fingerprint groups).
- **Reference object root** — other scene roots with the same object-hierarchy signature; merge uses **collection instancing** (`_DedupeObj_*`).
- **No reference** — cluster all duplicate root collections or all duplicate object roots by signature (scope-aware).
- **Scene mesh** — legacy list by mesh geometry fingerprint only.
- **UI language** — add-on preference **English / Chinese** (`i18n.py`), independent of Blender’s UI locale.
- **Optional layout** — `{Name}_Master_and_Instances` grouping beside the master collection.

### Requirements

- **Blender 3.3+** (`bl_info.blender`) for running the add-on from source or older installs. Release zip includes **`blender_manifest.toml`** with **4.2.0** minimum. **4.2+:** **Preferences → Extensions → Install from Disk…**; **3.x:** **Add-ons → Install…** (older Blender may ignore the manifest minimum).

### Installation

1. Download **`VFB_instance_manager.zip`** from your repository’s **GitHub Releases** page, or build it locally (see below).
2. Blender **4.2+:** **Edit → Preferences → Extensions → Install from Disk…** → select the zip (or **Add-ons → Install…** if you use the classic tab). **3.3–4.1:** **Edit → Preferences → Add-ons → Install…** → select the zip.
3. Enable **VFB Instance Manager** (module id `VFB_instance_manager` / extension id `vfb_instance_manager` in the manifest).

**Clean reinstall:** remove any old copy under Blender’s `extensions` or `scripts/addons` path for this add-on before installing again.

### Build the zip

From the **repository root** (this folder contains `build_vfb_zip.py` and `VFB_instance_manager/`):

```bash
python build_vfb_zip.py
```

Writes **`VFB_instance_manager.zip`** next to the script, **including** `blender_manifest.toml` (default **Extensions-style** package). If you hit a rare loader issue, rebuild with **`python build_vfb_zip.py --legacy`** to omit the manifest.

### User interface

- **3D Viewport** sidebar (**N**) → tab **VFB**.
- **Add-on preferences:** **Edit → Preferences → Add-ons → VFB Instance Manager** — **language** only (no other prefs in v1.0.1).

Use **Solid** shading with **Object** color to see temporary highlight tints.

### Equivalent copy search scope

Used for collection/object duplicate counts and **Duplicate collections vs reference**:

| Scope | Meaning |
|--------|---------|
| **Same parent as reference** *(default)* | Siblings under the **same parent collection** as the reference; also covers assets directly under **Scene Collection** when the reference is there. |
| **Scene root children** | Only collections whose **parent is Scene Collection**. |
| **Any collection in file** | No parent filter; use if duplicates live under different parents. |

Collection matching tries a **strict structure signature** first, then **fallbacks** (normalized root collection name + flat multiset of objects, with optional expansion of **collection-instance empties**).

### Analysis modes (unified list)

Depends on **reference tab** (Collection / Object / None) and the **analysis mode** menu:

| Mode | Row kinds | Purpose |
|------|-----------|---------|
| Duplicate collections vs reference | `COLLECTION` | Root collections isomorphic to the reference (per scope + signatures). |
| Parts inside reference | `COLLECTION`, `SHARED_DATA`, `MESH_GEOM` | Inside reference subtree: duplicate **child** collections, shared data, mesh fingerprints. |
| Duplicate roots vs reference object | `OBJECT_ROOT` | Other roots matching the reference hierarchy signature. |
| Scene mesh only | `MESH_GEOM` | Fingerprints under chosen mesh scope. |
| All duplicate collections (no ref) | `COLLECTION` | Clustered by signature; master name on row. |
| All duplicate object roots (no ref) | `OBJECT_ROOT` | Clustered by object-tree signature. |

### Merge workflow (summary)

- **Parts in reference:** simplify / pack actions target **collection rows**, **shared data**, and **mesh** rows; mesh duplicate rows are packed with **collection-instance** subcollections under the reference.
- **Other modes:** **Simplify current / all** plus, when the list contains matching rows, **Instance collection rows** or **Instance object-root rows** (collection-instance empties only in v1.0).

Destructive replaces **delete** duplicate subtree / collection contents as designed — keep backups.

### Repository layout

| Path | Role |
|------|------|
| `VFB_instance_manager/__init__.py` | `bl_info`, register |
| `VFB_instance_manager/blender_manifest.toml` | Extension metadata (included in release zip by default) |
| `VFB_instance_manager/prefs.py` | Preferences |
| `VFB_instance_manager/i18n.py` | Strings EN/ZH |
| `VFB_instance_manager/ui.py` | Operators, RNA, panels |
| `VFB_instance_manager/core.py` | Mesh fingerprint, linking |
| `VFB_instance_manager/collection_instances.py` | Collection → instance empty |
| `VFB_instance_manager/object_instance_replace.py` | Object root → collection instance |
| `VFB_instance_manager/object_hierarchy.py` | Object-tree signatures |
| `VFB_instance_manager/structure_match.py` | Collection signatures + fallbacks |
| `VFB_instance_manager/unified_results.py` | Unified analysis list |
| `VFB_instance_manager/part_row_pack.py` | Mesh row pack (collection instance) |
| `VFB_instance_manager/organization.py` | `_Master_and_Instances` layout |
| `VFB_instance_manager/instance_stats.py` | Instance statistics |
| `build_vfb_zip.py` | Build release zip |
| `VERSION` | Release number text (`1.0.1`) |
| `CHANGELOG.md` | Version history (EN + ZH) |
| `VFB_instance_manager/GPL-3.0.txt` | Full GNU GPL v3 (included in release zip) |

### License

**Repository (GitHub):** [MIT](LICENSE) — read the **Licensing overview** at the top of that file (dual licensing). Copyright **Viclant**.

**Release zip:** `VFB_instance_manager/LICENSE` and **`VFB_instance_manager/GPL-3.0.txt`** (full GPL v3) match **`blender_manifest.toml`** (`SPDX:GPL-3.0-or-later`).

### Disclaimer

This software is provided “as is”. Viclant is not responsible for data loss; keep backups of `.blend` files before batch or destructive operations.

---

## 中文（简体）

**版权主体 [Viclant](https://viclant.com)**；**V.F.B** 为负责本插件所属业务板块的部门。官网：**https://viclant.com**

**仓库：** [github.com/Viclant/VFB_instance_manager](https://github.com/Viclant/VFB_instance_manager)

### 功能概要

- **参考集合**：与参考**同构的根集合**；**参考集合内零件**（兄弟子集合、共享数据块、网格几何指纹组）。
- **参考根物体**：与参考**物体层级签名**一致的其它场景根；合并路径使用 **集合实例**（`_DedupeObj_*`）。
- **无参考**：按签名聚类**全部重复根集合**或**全部重复根物体**（受查找范围约束）。
- **全场景网格**：仅按网格几何指纹的旧版列表流程。
- **界面语言**：插件偏好里选 **英文 / 中文**（`i18n.py`），与 Blender 系统界面语言无关。
- **可选收纳**：`{Name}_Master_and_Instances` 分组（与主编集合同父级）。

### 环境要求

- **Blender 3.3+**（`bl_info`）可运行插件本体。发行 zip 内含 **`blender_manifest.toml`**，声明 **最低 4.2.0**。**4.2+** 建议 **偏好设置 → 扩展 → 从磁盘安装…**；**3.x** 仍可用 **插件 → 安装…**（旧版可能不严格按 manifest 最低版本拦截）。

### 安装

1. 在仓库的 **GitHub Releases** 页面下载 **`VFB_instance_manager.zip`**，或在本地用下方命令打包生成。
2. **Blender 4.2+：** **编辑 → 偏好设置 → 扩展 → 从磁盘安装…** 选择 zip（仍可在 **插件** 里用 **安装…**）。**3.3–4.1：** **编辑 → 偏好设置 → 插件 → 安装…** 选择 zip。
3. 启用 **VFB Instance Manager**（模块文件夹 `VFB_instance_manager`；manifest 中 id 为 `vfb_instance_manager`）。

**干净重装：** 删除本插件在用户目录下 **extensions** 或 **scripts/addons** 中的旧副本后再安装。

### 打包 zip

在**仓库根目录**（含 `build_vfb_zip.py` 与 `VFB_instance_manager/`）执行：

```bash
python build_vfb_zip.py
```

会在脚本旁生成 **`VFB_instance_manager.zip`**，**默认包含** `blender_manifest.toml`（**扩展式**安装包）。若个别环境加载异常，可用 **`python build_vfb_zip.py --legacy`** 生成不含 manifest 的 zip。

### 界面位置

- **3D 视图** 侧栏 **N 面板** → 选项卡 **VFB**。
- **插件偏好设置**：**编辑 → 偏好设置 → 插件 → VFB Instance Manager** — 仅 **语言** 一项。

高亮工具依赖实体模式下的 **物体** 颜色显示。

### 同构副本查找范围

用于集合同构计数及 **相对参考的重复集合** 分析：

| 范围 | 含义 |
|------|------|
| **与参考同父级**（默认） | 与参考集合**同一父集合**下的兄弟；参考挂在**场景集合**下时，与「场景根第一层」效果一致。 |
| **场景根下第一层** | 父级必须是 **场景集合**。 |
| **整个文件任意集合** | 不限制父级；副本在不同分组下时可试。 |

匹配顺序：**严格集合结构签名** → 失败则 **规范化根集合名 + 子树物体扁平多重集** → 再失败则尝试 **展开集合实例空物体** 后的多重集。

### 分析模式（统一列表）

随 **参考选项卡**（集合 / 物体 / 无）与 **分析模式** 变化：

| 模式 | 行类型 | 作用 |
|------|--------|------|
| 重复集合（相对参考） | `COLLECTION` | 与参考同构的其它根集合（受范围与签名逻辑约束）。 |
| 参考集合内零件 | `COLLECTION`、`SHARED_DATA`、`MESH_GEOM` | 参考子树内：同构子集合、共享数据、网格指纹。 |
| 重复根物体（相对参考物体） | `OBJECT_ROOT` | 与参考根同构的其它根物体。 |
| 全场景仅网格几何 | `MESH_GEOM` | 按所选范围做网格指纹分组。 |
| 全部重复根集合（无参考） | `COLLECTION` | 按签名聚类。 |
| 全部重复根物体（无参考） | `OBJECT_ROOT` | 按物体树签名聚类。 |

### 合并工作流（摘要）

- **参考集合内零件**：对 **集合行 / 共享数据 / 网格行** 做简化或打包；网格重复行在参考下建 **子集合 + 集合实例**。
- **其它模式**：**简化当前行 / 一键全部**；若列表中存在对应类型，再显示 **集合同构行 → 实例化** 或 **物体层级行 → 实例化**（v1.0 均为 **集合实例**）。

会删除副本子树内容的操作具有破坏性，请先保存工程。

### 仓库结构

与上文英文 **Repository layout** 表一致；另见根目录 **`VERSION`**（`1.0.1`）、**`CHANGELOG.md`**（中英变更说明）。

### 许可证

**仓库（GitHub）：** [MIT](LICENSE)，文首有 **许可总览**（双重许可）。版权 **Viclant**。

**发行 zip：** `VFB_instance_manager/LICENSE` 与 **`VFB_instance_manager/GPL-3.0.txt`**（GPL v3 全文）与 **`blender_manifest.toml`**（`SPDX:GPL-3.0-or-later`）一致。

### 免责声明

软件按「原样」提供。Viclant 不对数据丢失负责；批量或破坏性操作前请自行备份 `.blend` 文件。
