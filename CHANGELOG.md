# Changelog

All notable changes to **VFB Instance Manager** are documented here.

---

## 1.0.1 — 2026-04-03

### English

- **Preferences / Extensions:** `ADDON_ID` is derived from `__package__` so `AddonPreferences.bl_idname` matches Blender’s registered module name whether the add-on loads as `VFB_instance_manager` (zip folder) or `vfb_instance_manager` (manifest `id`). Fixes **“Could not read add-on preferences.”** in Preferences and the sidebar settings panel.
- **Licensing / zip:** `GPL-3.0.txt` in the zip; dual-licensing notices in root and add-on `LICENSE` files.

### 中文（1.0.1）

- **偏好 / 扩展安装：** `ADDON_ID` 改为由 `__package__` 解析，使 `AddonPreferences.bl_idname` 与 Blender 实际注册的模块名一致（zip 目录名或 manifest `id`），修复偏好设置与侧栏里 **「无法读取插件偏好」**。
- **许可 / zip：** zip 内 `GPL-3.0.txt`；根目录与插件内 `LICENSE` 双重许可说明。

---

## 1.0.0 — 2026-03-29 (stable)

### English

- **Stable v1.0** — suitable for GitHub releases and production use with backups.
- **Release zip defaults to Extensions-style:** `build_vfb_zip.py` now **includes** `blender_manifest.toml`; use `--legacy` to omit it. On Blender **4.2+**, install via **Preferences → Extensions → Install from Disk** when available.
- **Extension manifest:** `blender_manifest.toml` uses **GPL-3.0-or-later**, **blender_version_min = 4.2.0**, and a **tagline ≤ 64** characters. **`VFB_instance_manager/GPL-3.0.txt`** — full GNU GPL v3 in the zip. **`VFB_instance_manager/LICENSE`** and root **`LICENSE`** — dual-licensing (MIT source tree + GPL for the distributed add-on package as declared).
- **Collection duplicate matching:** default equivalent scope is **Same parent as reference**; parent resolution uses a **scene-tree DFS** from `scene.collection`. If strict structure signatures do not match, **fallback matching** uses normalized root collection names plus a **flat multiset** of object `(type, normalized name)`, optionally **expanding collection-instance empties** so inline meshes and instanced copies can still pair.
- **Merge / instance UI:** batch operators for collection rows vs object-root rows are **shown only when the current result list actually contains** those row kinds; analysis mode also gates which button appears.
- **Instancing:** duplicate handling uses **collection-instance empties** (including object-root merge via `_DedupeObj_*`); the older empty **OBJECT / `instance_object`** mesh-pack path has been **removed** — mesh duplicate rows in reference use **collection-instance** subcollections under the reference collection.
- **Preferences:** add-on preferences are reduced to **language** (EN / ZH UI strings).
- **Docs:** root `README.md` is bilingual (English, then Chinese).
- **Credit:** **[Viclant](https://viclant.com)** (copyright holder); **V.F.B** is the department responsible for this add-on. `bl_info` / manifest / UI hint link to **https://viclant.com**.

### 中文（1.0.0）

- **稳定版 v1.0**，可配合备份用于日常与 GitHub 发布。
- **发行 zip 默认为扩展式：** `build_vfb_zip.py` **默认打入** `blender_manifest.toml`；需要时用 **`--legacy`** 省略。Blender **4.2+** 可优先 **偏好设置 → 扩展 → 从磁盘安装…**。
- **扩展清单 manifest：** **GPL-3.0-or-later**、**blender_version_min 4.2.0**、**tagline 不超过 64 字符**。**`VFB_instance_manager/GPL-3.0.txt`** — zip 内 GPL v3 全文。**`VFB_instance_manager/LICENSE`** 与根目录 **`LICENSE`** — 双重许可（源码树 MIT + 分发包按 manifest 声明的 GPL）。
- **集合同构匹配：** 默认「同构副本查找范围」为 **与参考同父级**；父级从当前 **`scene.collection`** 做 **DFS** 解析。严格结构签名不一致时，依次用 **规范化根集合名 + 子树物体扁平多重集**、以及 **展开集合实例空物体** 后的多重集做回退匹配。
- **合并 / 实例化 UI：** 仅当当前列表存在对应行类型（及分析模式允许）时显示「集合同构行 / 物体层级行」的批量实例化按钮。
- **实例化：** 统一以 **集合实例空物体** 为主路径（含物体根合并时的 `_DedupeObj_*`）；已移除空物体 **OBJECT / `instance_object`** 的网格打包链路；参考内网格重复行使用参考下的 **子集合 + 集合实例** 打包。
- **插件设置：** 仅保留 **语言**（界面中英字符串，与 Blender 系统语言无关）。
- **文档：** 仓库根目录 `README.md` **先英文、后中文**。
- **署名：** 版权主体 **[Viclant](https://viclant.com)**；**V.F.B** 为本插件所属板块负责部门。`bl_info` / 扩展清单 / 面板提示与 **https://viclant.com** 一致。

---

## 0.1.0 — earlier public beta

### English

- Initial public beta track: reference-driven analysis, unified result list, collection / object-root / mesh workflows, optional `_Master_and_Instances` organization.

### 中文

- 早期公开测试：参考驱动分析、统一结果列表、集合 / 物体根 / 网格流程、可选 `_Master_and_Instances` 收纳。
