"""Bilingual UI strings (EN / ZH) for panels, enums, and list row titles."""

from __future__ import annotations

from typing import Dict

import bpy

# Must match Blender’s registered add-on module name (Preferences key). Extensions often use
# manifest ``id`` (e.g. vfb_instance_manager); zip-from-disk uses the folder name (VFB_instance_manager).
ADDON_ID = __package__ if __package__ else "VFB_instance_manager"

STRINGS: Dict[str, Dict[str, str]] = {
    "EN": {
        "PANEL_MAIN": "VFB Instance Manager",
        "PANEL_WORKFLOW": "Analysis & merge",
        "PANEL_INSTANCE_STATS": "Instance statistics",
        "PANEL_REFERENCE": "Reference",
        "PREFS_DISPLAY_TITLE": "VFB Instance Manager",
        "PREFS_USE_SIDEBAR_SETTINGS": "Language: sidebar N › VFB › Plugin settings (bottom).",
        "MAIN_PANEL_HINT": "Copyright Viclant · V.F.B — Sub-panels: Reference, Analysis & merge, Instance stats. Settings at the bottom.",
        "PANEL_SETTINGS": "Plugin settings",
        "ERR_PREFS_ACCESS": "Could not read add-on preferences.",
        "LANGUAGE": "Language",
        "REF_SUMMARY": "Quick status",
        "REF_COLL_BOUND": "Collection",
        "REF_OBJ_BOUND": "Object root",
        "REF_NONE": "(not set)",
        "REF_TAB_NONE": "No reference",
        "REF_TAB_NONE_D": "Cluster all duplicate roots by signature; or scene mesh only",
        "REF_NONE_MODE_HINT": "No reference: use analysis modes below (all duplicate collections/roots or scene meshes).",
        "ROW_COLL_PAIR": "Inst. [{dup}] ← master [{master}]",
        "ROW_OBJ_PAIR": "Inst. [{dup}] ← master [{master}]",
        "UA_AC_N": "All duplicate collections (no ref.)",
        "UA_AC_D": "Group root collections by structure signature; each row = one copy vs group master",
        "UA_AO_N": "All duplicate object roots (no ref.)",
        "UA_AO_D": "Group scene roots by hierarchy signature; each row = one copy vs group master",
        "ERR_ANALYSIS_MODE": "This analysis mode does not match the current reference tab.",
        "AUTO_ORGANIZE": "Group master + instances",
        "AUTO_ORGANIZE_TIP": "Puts master and instance empties in {Name}_Master_and_Instances",
        "PROP_COL_ORG_LAYOUT": "Collection-instance folder layout",
        "PROP_COL_ORG_LAYOUT_TIP": (
            "Legacy: one Master_and_Instances beside the master. "
            "Packed: VFB_* with Name_Source (master / _DedupeObj_*) and Name_Instances (instance empties). "
            "Collection path anchors to the duplicate collection's parent; "
            "object-root path anchors to the duplicate object's containing collection."
        ),
        "SHOW_DETAILS": "Show structure details",
        "EQUIV_COUNTS": "Equiv. counts (refresh in Reference)",
        "EQUIV_COUNTS_LINE": "Equiv. copies | collections: {nc} | object roots: {no}",
        "ANALYSIS": "Analysis",
        "RESULTS": "Results",
        "RESULTS_DUP_GROUPS": "Duplicate groups: {n}",
        "SOLID_HINT": "Solid shading: Color = Object",
        "TAB_COLLECTION": "Collection",
        "TAB_OBJECT": "Object root",
        "SCOPE_SHARED": "Search scope (collection + object)",
        "HINT_ZERO": "If zero: try scope Entire file, or only a single copy exists in the scene.",
        "COLL_TOOLS": "Collection: color / instance all",
        "AUTO_NUM": "Auto: BaseName.001 / .002",
        "LIST_HINT": "Reference: (1) dup collections vs ref; (2) dup roots vs ref object; (3) parts inside ref collection. No ref: all dup collections/roots by signature, or scene mesh.",
        "STATS_HINT": "Collection-instance empties only; [C]=master collection, [O]=object inside instanced tree",
        "STATS_TAB": "Statistics view",
        "STATS_TAB_MASTERS_N": "By collection",
        "STATS_TAB_MASTERS_D": "Each master collection and instancer count",
        "STATS_TAB_SUMMARY_N": "Overview",
        "STATS_TAB_SUMMARY_D": "Instance, object, and collection counts",
        "STATS_TAB_BYOBJ_N": "By object",
        "STATS_TAB_BYOBJ_D": "Each object in instanced trees and instancer count",
        "STATS_HINT_TABS": "Pick a view, then Refresh (or switch tab to auto-refresh).",
        "STATS_SUM_N_INST": "Instancer empties",
        "STATS_SUM_N_OBJ": "Objects (unique, under masters)",
        "STATS_SUM_N_COLL": "Master collections",
        "STATS_SUM_HELP": "Counts only collection-instance empties and their target collections.",
        "STATS_WARN_SUMMARY_SELECT": "Summary rows have no instance empties to select.",
        "STATS_ROWS": "Rows",
        "STATS_DETAIL": "Instancer empties for",
        "COUNT_SEP": " | ",
        "DASH": "-",
        "PROP_BATCH": "Batch count",
        "PROP_ONLY_MESH": "Meshes only",
        "PROP_ONLY_MESH_TIP": "Dedup uses mesh verts/faces; lights/cameras/empties have no mesh by default",
        "PROP_MESH_SCOPE": "Scope",
        "PROP_COLL_INST_ROOT": "Auto-pair scene-root only",
        "PROP_COLL_INST_ROOT_TIP": "Only for Auto Base.001/.002: search among direct children of scene collection. Equiv. matching uses Search scope below.",
        "PROP_MASTER_COLL": "Master collection",
        "PROP_MASTER_COLL_TIP": "Exact outliner collection name",
        "PROP_DUP_COLL": "Duplicate collection",
        "PROP_DUP_COLL_TIP": "Collection to delete and replace with instance",
        "PROP_REF_COLL": "Reference collection",
        "PROP_REF_COLL_TIP": "Asset root collection; can sync from active collection",
        "PROP_REF_OBJ": "Reference root object",
        "PROP_REF_OBJ_TIP": "Hierarchy root (e.g. ParkingLot01); set from 3D view",
        "PROP_REF_TAB": "Reference tab",
        "PROP_REF_ADV_TOOLS": "Collection tools & auto-instance",
        "SECTION_EQUIV_COUNTS": "Equiv. scope & counts",
        "SECTION_REF_TARGET": "Reference target",
        "SECTION_AUTO_FOLDER": "Master / instance folder",
        "SECTION_WF_LIST": "Result rows",
        "SECTION_WF_MERGE": "Merge",
        "SECTION_MERGE_PARTS_IN_REF": "Parts in reference (shared data / mesh)",
        "SECTION_WF_NAV": "Select & highlight",
        "SECTION_STATS_VIEW": "View & refresh",
        "SECTION_STATS_LIST": "Statistics list",
        "SECTION_STATS_OPTS": "Options & detail",
        "PROP_SHOW_DETAILS": "Show structure details",
        "PROP_MASTER_INST_COLL": "Master_and_Instances collection",
        "PROP_MASTER_INST_COLL_TIP": "Put master + instance empties in {Name}_Master_and_Instances",
        "PROP_STATS_NAMES": "Show instance empty names",
        "PROP_STATS_NAMES_TIP": "Expand detail under the stats list for the selected row",
        "PROP_EQ_SCOPE": "Equivalent copy search scope",
        "PROP_ANALYSIS_MODE": "Analysis mode",
        "REF_TAB_COLL": "Collection",
        "REF_TAB_OBJ": "Object root",
        "EQ_SR_N": "Scene root children",
        "EQ_SR_D": (
            "Only collections parented directly under Scene Collection. "
            "If Building_GS / Building_GS.001 sit under a folder collection, use Same parent as reference."
        ),
        "EQ_SP_N": "Same parent as reference",
        "EQ_SP_D": "Search among siblings under the same parent",
        "EQ_EF_N": "Any collection in file",
        "EQ_EF_D": "No parent limit; try when counts are zero",
        "HINT_COLL_TRY_SAME_PARENT": (
            "No collection matches with Scene root scope. "
            "Your reference is not a direct child of Scene Collection — set scope to Same parent as reference and analyze again."
        ),
        "UA_CD_N": "Duplicate collections (vs reference)",
        "UA_CD_D": "Other root collections matching reference; scope applies",
        "UA_OD_N": "Duplicate roots (vs reference object)",
        "UA_OD_D": (
            "Match other roots by hierarchy, types, normalized names. "
            "Merging uses collection-instance empties (_DedupeObj_*), same as other simplify / instance actions."
        ),
        "UA_PR_N": "Parts inside reference collection",
        "UA_PR_D": "Reference subtree: shared data (incl. lights) + mesh dupes",
        "UA_MS_N": "Scene mesh geometry only",
        "UA_MS_D": "Legacy: scope below, mesh fingerprints only",
        "MS_SC_N": "Entire scene",
        "MS_SC_D": "All mesh objects in scene",
        "MS_VL_N": "View layer visible",
        "MS_VL_D": "view_layer.objects",
        "MS_SE_N": "Selected only",
        "MS_SE_D": "Select suspects then analyze",
        "MS_PC_N": "Per collection tree",
        "MS_PC_D": "Dedupe inside each collection tree",
        "OP_SET_REF_COLL": "Set reference collection (outliner)",
        "OP_SET_REF_OBJ": "Set reference object (active → root)",
        "OP_REFRESH_COUNTS": "Refresh equivalent counts",
        "OP_STRUCT_COLOR": "Color by structure match",
        "OP_STRUCT_INST": "Equivalent roots → instance to reference",
        "OP_COLL_AUTO": "Auto: duplicate collections → instances",
        "OP_COLL_PAIR": "Named master + duplicate → instance",
        "OP_ANALYZE": "Analyze duplicate groups",
        "OP_CLEAR": "Clear results",
        "OP_SEL_GROUP": "Select current row/group",
        "OP_SEL_BATCH": "Select batch",
        "OP_HIGHLIGHT_ROW": "Highlight current row",
        "OP_HIGHLIGHT_LINKED": "Highlight linked",
        "OP_CLEAR_HI": "Clear highlight",
        "OP_SET_MASTER": "Set as master",
        "OP_MERGE_ROW": "Simplify active row",
        "OP_MERGE_ALL": "Simplify all rows",
        "OP_MERGE_COLL_ALL": "Collection duplicate rows → collection instances",
        "OP_MERGE_OBJ_ALL": "Object-root rows → collection instances",
        "OP_PACK_CURRENT_MESH_ROW_CI": "Pack current mesh row → under reference (collection instance)",
        "OP_PACK_ALL_MESH_ROWS_CI": "Pack all mesh rows → groups under reference (collection instance)",
        "INFO_PACK_ROW": "Packed into collection [{name}]",
        "INFO_PACK_ALL": "Packed {n} row(s) into sub-collections",
        "ERR_PACK_PARTIAL": "Packed {ok} row(s), then stopped: {why}",
        "ERR_PACK_ROW_KIND": "Current row is not a mesh / shared-mesh duplicate row",
        "ERR_PACK_NEED_TWO": "Need at least two mesh objects in the row",
        "ERR_PACK_OUTSIDE_REF": "Row objects must lie inside the reference collection subtree",
        "ERR_PACK_MASTER": "Could not pick a master mesh object",
        "ERR_PACK_NONE": "No packable mesh duplicate rows in the list",
        "OP_PURGE_STALE_EMPTY": "Remove stale instance empties",
        "OP_PURGE_STALE_EMPTY_TIP": (
            "Delete Empty objects named CI_/OI_/VfbCI_ that are not collection instances "
            "(leftovers from conflicts or cleared instance settings). Does not remove valid instance empties."
        ),
        "INFO_PURGE_STALE_EMPTY": "Removed {n} stale instance empty(ies)",
        "WARN_PURGE_STALE_EMPTY_NONE": "No stale CI/OI/VfbCI empties found",
        "OP_PURGE": "Purge unused data",
        "OP_REFRESH_STATS": "Refresh instance statistics",
        "OP_SEL_STATS": "Select instance empties",
        "ROW_MESH": "[Mesh] {prefix}{first}… ×{n}",
        "ROW_OBJ": "[Object root] {dup} → instance of [{root}]",
        "ROW_COLL": "[Collection] {dup} → reference [{ref}]",
        "ROW_SHARED": "[{typ}] shared data [{data}] x{n}",
        "ERR_NO_REF_OBJ": "Set a reference object (pick in 3D/outliner, then use Set reference object)",
        "ERR_NO_REF_COLL": "Set a reference collection name or pick from outliner",
        "STRUCT_PARENT": "Parent: {parent}  |  Direct under scene: {yesno}",
        "STRUCT_SUBTREE": "Subtree: {ncoll} collection(s) (incl. self)  |  {nobj} object(s)",
        "STRUCT_TYPES": "Types: {parts}",
        "STRUCT_SIG": "Structure sig: {sig}...",
        "STRUCT_YES": "yes",
        "STRUCT_NO": "no",
        "OBJ_ROOT": "Root: {root}  |  Object parent: {par}",
        "OBJ_SCENE_MEM": "Direct member of scene collection: {yesno}",
        "OBJ_SUBTREE": "Subtree objects: {n}  |  Max parent depth: {d}",
        "OBJ_TYPES": "Types: {parts}",
        "OBJ_SIG": "Structure sig: {sig}...",
    },
    "ZH": {
        "PANEL_MAIN": "VFB 实例管理",
        "PANEL_WORKFLOW": "分析与合并",
        "PANEL_INSTANCE_STATS": "实例统计",
        "PANEL_REFERENCE": "参考",
        "PREFS_DISPLAY_TITLE": "VFB 实例管理",
        "PREFS_USE_SIDEBAR_SETTINGS": "语言：侧栏 N › VFB › 插件设置（最下）。",
        "MAIN_PANEL_HINT": "版权属 Viclant，V.F.B 负责本板块 — 子面板：参考、分析与合并、实例统计；插件设置在最下方。",
        "PANEL_SETTINGS": "插件设置",
        "ERR_PREFS_ACCESS": "无法读取插件偏好。",
        "LANGUAGE": "界面语言",
        "REF_SUMMARY": "快速状态",
        "REF_COLL_BOUND": "集合",
        "REF_OBJ_BOUND": "根物体",
        "REF_NONE": "（未设置）",
        "REF_TAB_NONE": "无参考",
        "REF_TAB_NONE_D": "按签名聚类全部重复根集合/根物体，或仅场景网格",
        "REF_NONE_MODE_HINT": "无参考：在分析与合并里用「全量重复集合/根物体」或「场景网格」等模式，无需指定参考目标。",
        "ROW_COLL_PAIR": "实例化 [{dup}] ← 主编 [{master}]",
        "ROW_OBJ_PAIR": "实例化 [{dup}] ← 主编 [{master}]",
        "UA_AC_N": "全部重复集合（无参考）",
        "UA_AC_D": "按结构签名聚类根集合；每行=一个副本相对组内主编",
        "UA_AO_N": "全部重复根物体（无参考）",
        "UA_AO_D": "按层级签名聚类场景根物体；每行=一个副本相对组内主编",
        "ERR_ANALYSIS_MODE": "当前分析模式与参考选项卡不匹配。",
        "AUTO_ORGANIZE": "主物体与实例收入集合",
        "AUTO_ORGANIZE_TIP": "生成「名称_Master_and_Instances」集合并收纳主编与实例空物体",
        "PROP_COL_ORG_LAYOUT": "集合实例收纳结构",
        "PROP_COL_ORG_LAYOUT_TIP": (
            "经典：主编旁一个 Master_and_Instances。"
            "分层：VFB_* 下 名称_Source（主编 / _DedupeObj_*）与 名称_Instances（实例空物体）。"
            "集合副本以副本集合的父级为锚；物体根副本以副本所在集合为锚。"
        ),
        "SHOW_DETAILS": "显示结构详情",
        "EQUIV_COUNTS": "同构数量（在参考面板刷新）",
        "EQUIV_COUNTS_LINE": "同构数量 | 集合 {nc} | 根物体 {no}",
        "ANALYSIS": "分析",
        "RESULTS": "结果列表",
        "RESULTS_DUP_GROUPS": "重复组数量：{n}",
        "SOLID_HINT": "Solid：着色方式选「物体」可看颜色",
        "TAB_COLLECTION": "集合",
        "TAB_OBJECT": "根物体",
        "SCOPE_SHARED": "查找范围（集合与物体同构共用）",
        "HINT_ZERO": "为 0 时：试「整个文件任意集合」，或场景中只有一份。",
        "COLL_TOOLS": "集合：着色 / 全部实例化",
        "AUTO_NUM": "自动：基名.001 / .002",
        "LIST_HINT": "有参考：（1）相对参考集合的重复根集合；（2）相对参考物体的重复根物体；（3）参考集合内零件重复。无参考：按签名聚类全部重复集合/根物体，或仅场景网格。",
        "STATS_HINT": "仅统计「集合实例」空物体；[C]=主编集合，[O]=实例树内的物体",
        "STATS_TAB": "统计视图",
        "STATS_TAB_MASTERS_N": "按集合",
        "STATS_TAB_MASTERS_D": "各主编集合及实例空物体数量",
        "STATS_TAB_SUMMARY_N": "总览",
        "STATS_TAB_SUMMARY_D": "实例数、物体数、集合数",
        "STATS_TAB_BYOBJ_N": "按物体",
        "STATS_TAB_BYOBJ_D": "实例树内各物体及被多少实例引用",
        "STATS_HINT_TABS": "切换视图后点刷新（或切换选项卡会自动刷新）。",
        "STATS_SUM_N_INST": "实例空物体数",
        "STATS_SUM_N_OBJ": "物体数（主编下去重）",
        "STATS_SUM_N_COLL": "主编集合数",
        "STATS_SUM_HELP": "仅统计集合实例空物体及其指向的主编集合。",
        "STATS_WARN_SUMMARY_SELECT": "汇总行没有可选中的实例空物体。",
        "STATS_ROWS": "条目数",
        "STATS_DETAIL": "实例空物体（当前行）",
        "COUNT_SEP": "  ·  ",
        "DASH": "-",
        "PROP_BATCH": "分批数量",
        "PROP_ONLY_MESH": "仅网格",
        "PROP_ONLY_MESH_TIP": "去重依赖 Mesh 顶点与面；灯光/相机/空物体默认跳过",
        "PROP_MESH_SCOPE": "范围",
        "PROP_COLL_INST_ROOT": "自动配对仅场景根",
        "PROP_COLL_INST_ROOT_TIP": "仅影响「自动：基名.001/.002」；同构匹配由下方查找范围控制",
        "PROP_MASTER_COLL": "主编集合名",
        "PROP_MASTER_COLL_TIP": "大纲中集合的完整名称",
        "PROP_DUP_COLL": "副本集合名",
        "PROP_DUP_COLL_TIP": "将被删除并替换为实例的集合",
        "PROP_REF_COLL": "参考集合名",
        "PROP_REF_COLL_TIP": "资产根集合；可与大纲活动集合同步",
        "PROP_REF_OBJ": "参考根物体名",
        "PROP_REF_OBJ_TIP": "层级根物体；可从 3D 视图指定",
        "PROP_REF_TAB": "参考选项卡",
        "PROP_REF_ADV_TOOLS": "集合工具与自动实例",
        "SECTION_EQUIV_COUNTS": "同构范围与数量",
        "SECTION_REF_TARGET": "参考目标（集合 / 物体）",
        "SECTION_AUTO_FOLDER": "主编与实例收纳",
        "SECTION_WF_LIST": "结果列表",
        "SECTION_WF_MERGE": "合并操作",
        "SECTION_MERGE_PARTS_IN_REF": "参考集合内零件（共享数据 / 网格）",
        "SECTION_WF_NAV": "选择与高亮",
        "SECTION_STATS_VIEW": "视图与刷新",
        "SECTION_STATS_LIST": "统计列表",
        "SECTION_STATS_OPTS": "选项与明细",
        "PROP_SHOW_DETAILS": "显示结构详情",
        "PROP_MASTER_INST_COLL": "Master_and_Instances 收纳集合",
        "PROP_MASTER_INST_COLL_TIP": "将主编与实例空物体收入 {Name}_Master_and_Instances",
        "PROP_STATS_NAMES": "显示实例空物体名",
        "PROP_STATS_NAMES_TIP": "在统计列表下方展开当前行实例名",
        "PROP_EQ_SCOPE": "同构副本查找范围",
        "PROP_ANALYSIS_MODE": "分析模式",
        "REF_TAB_COLL": "集合",
        "REF_TAB_OBJ": "根物体",
        "EQ_SR_N": "场景根下第一层",
        "EQ_SR_D": (
            "仅父级为「场景集合」的集合；若 Building_GS / Building_GS.001 挂在中间分组下，请改用「与参考同父级」。"
        ),
        "EQ_SP_N": "与参考同父级",
        "EQ_SP_D": "在同一父集合下的兄弟中查找",
        "EQ_EF_N": "整个文件任意集合",
        "EQ_EF_D": "不限制父级；计数为 0 时可试此项",
        "HINT_COLL_TRY_SAME_PARENT": (
            "当前为「场景根下第一层」且未找到同构集合。参考集合不是场景集合的直接子项时，"
            "请把「同构副本查找范围」改为「与参考同父级」后重新分析。"
        ),
        "UA_CD_N": "重复集合（相对参考集合）",
        "UA_CD_D": "与参考同构的其它根集合；范围由上项决定",
        "UA_OD_N": "重复根物体（相对参考物体）",
        "UA_OD_D": (
            "按层级、类型、规范化名匹配其它根；"
            "合并时与其它「简化/实例化」一致，均为集合实例空物体（_DedupeObj_*）。"
        ),
        "UA_PR_N": "参考集合内零件",
        "UA_PR_D": "参考子树：共享数据块 + 网格几何重复",
        "UA_MS_N": "全场景仅网格几何",
        "UA_MS_D": "旧版：按下方范围，仅网格指纹",
        "MS_SC_N": "整个场景",
        "MS_SC_D": "场景内全部网格物体",
        "MS_VL_N": "当前视图层可见",
        "MS_VL_D": "view_layer.objects",
        "MS_SE_N": "仅选中",
        "MS_SE_D": "先选中再分析",
        "MS_PC_N": "按集合树分别",
        "MS_PC_D": "每个 Collection 内独立去重",
        "OP_SET_REF_COLL": "指定参考集合（大纲）",
        "OP_SET_REF_OBJ": "指定参考物体（活动→根）",
        "OP_REFRESH_COUNTS": "刷新同构数量",
        "OP_STRUCT_COLOR": "按结构匹配着色",
        "OP_STRUCT_INST": "同构根集合→全部实例化到参考",
        "OP_COLL_AUTO": "自动：重复资产集合→实例",
        "OP_COLL_PAIR": "指定主编+副本→集合实例",
        "OP_ANALYZE": "分析重复组",
        "OP_CLEAR": "清空结果",
        "OP_SEL_GROUP": "选中当前行/组",
        "OP_SEL_BATCH": "分批选中",
        "OP_HIGHLIGHT_ROW": "高亮当前行",
        "OP_HIGHLIGHT_LINKED": "查看关联项",
        "OP_CLEAR_HI": "清除高亮",
        "OP_SET_MASTER": "设为主物体",
        "OP_MERGE_ROW": "简化当前行",
        "OP_MERGE_ALL": "一键简化全部行",
        "OP_MERGE_COLL_ALL": "集合同构行：实例化为集合实例",
        "OP_MERGE_OBJ_ALL": "物体层级行：实例化为集合实例",
        "OP_PACK_CURRENT_MESH_ROW_CI": "打包当前网格行→参考集合下（集合实例）",
        "OP_PACK_ALL_MESH_ROWS_CI": "全部网格行→各组放在参考集合下（集合实例）",
        "INFO_PACK_ROW": "已打包到子集合「{name}」",
        "INFO_PACK_ALL": "已打包 {n} 组到子集合",
        "ERR_PACK_PARTIAL": "已打包 {ok} 组后中断：{why}",
        "ERR_PACK_ROW_KIND": "当前行不是网格/共享网格重复行",
        "ERR_PACK_NEED_TWO": "该行至少需要两个网格物体",
        "ERR_PACK_OUTSIDE_REF": "行内物体必须在参考集合子树内",
        "ERR_PACK_MASTER": "无法确定主编物体",
        "ERR_PACK_NONE": "列表中没有可打包的网格重复行",
        "OP_PURGE_STALE_EMPTY": "清理失效的实例空物体",
        "OP_PURGE_STALE_EMPTY_TIP": (
            "删除名为 CI_/OI_/VfbCI_ 且未作为集合实例使用的空物体"
            "（命名冲突残留或实例属性被清空）。不会删除有效的集合实例空物体。"
        ),
        "INFO_PURGE_STALE_EMPTY": "已删除 {n} 个失效的实例空物体",
        "WARN_PURGE_STALE_EMPTY_NONE": "没有需要清理的 CI/OI/VfbCI 空物体",
        "OP_PURGE": "清理未使用数据",
        "OP_REFRESH_STATS": "刷新实例统计",
        "OP_SEL_STATS": "选中实例空物体",
        "ROW_MESH": "[网格] {prefix}{first}… ×{n}",
        "ROW_OBJ": "[物体层级] {dup} → 实例化到 [{root}]",
        "ROW_COLL": "[集合同构] {dup} → 参考 [{ref}]",
        "ROW_SHARED": "[{typ}] 共享数据「{data}」 ×{n}",
        "ERR_NO_REF_OBJ": "请先指定参考物体（3D 或大纲选中后点「指定参考物体」）",
        "ERR_NO_REF_COLL": "请先设置参考集合名或从大纲读取",
        "STRUCT_PARENT": "父集合: {parent}  ·  场景根直属: {yesno}",
        "STRUCT_SUBTREE": "子树: 集合×{ncoll}（含自身）  ·  物体×{nobj}",
        "STRUCT_TYPES": "类型: {parts}",
        "STRUCT_SIG": "结构签名: {sig}…",
        "STRUCT_YES": "是",
        "STRUCT_NO": "否",
        "OBJ_ROOT": "根物体: {root}  ·  物体父级: {par}",
        "OBJ_SCENE_MEM": "在场景集合直接成员: {yesno}",
        "OBJ_SUBTREE": "子树物体×{n}  ·  最大父子深度: {d}",
        "OBJ_TYPES": "类型: {parts}",
        "OBJ_SIG": "结构签名: {sig}…",
    },
}


def _blender_ui_lang_bucket(context) -> str:
    """Map Blender interface locale to EN or ZH for addon strings."""
    try:
        if context is not None:
            v = context.preferences.view.language
            s = str(v).upper()
            if "ZH" in s or "CHINESE" in s:
                return "ZH"
    except Exception:
        pass
    try:
        loc = bpy.app.translations.locale
        if loc and str(loc).lower().startswith("zh"):
            return "ZH"
    except Exception:
        pass
    return "EN"


def get_lang(context) -> str:
    try:
        if context is None:
            return "EN"
        ad = context.preferences.addons.get(ADDON_ID)
        if ad is None:
            return "EN"
        lang = getattr(ad.preferences, "language", "EN")
    except Exception:
        lang = "EN"
    if lang == "OTHER":
        return _blender_ui_lang_bucket(context)
    if lang not in STRINGS:
        lang = "EN"
    return lang


def t(lang: str, key: str) -> str:
    if lang not in STRINGS:
        lang = "EN"
    return STRINGS[lang].get(key) or STRINGS["EN"].get(key) or key


def tr(context, key: str) -> str:
    return t(get_lang(context), key)
