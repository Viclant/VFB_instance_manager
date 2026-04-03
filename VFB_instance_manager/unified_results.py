"""
统一「重复组」列表：集合级同构副本、参考集合内同构子集合与共享数据块、网格几何重复。
"""

from __future__ import annotations

from collections import defaultdict
from typing import List, Optional, Tuple

import bpy

from . import core
from . import i18n
from . import object_hierarchy
from . import structure_match


UNIFIED_MODE_LABEL_KEY = {
    "COLLECTION_DUPES": "UA_CD_N",
    "OBJECT_DUPES": "UA_OD_N",
    "PARTS_IN_REF": "UA_PR_N",
    "MESH_SCENE": "UA_MS_N",
    "ALL_COLL_DUPES": "UA_AC_N",
    "ALL_OBJ_DUPES": "UA_AO_N",
}


def unified_mode_label_key(mode: str) -> str:
    """i18n key for short mode name (addon language, not Blender UI locale)."""
    return UNIFIED_MODE_LABEL_KEY.get(mode, "PROP_ANALYSIS_MODE")


def allowed_unified_modes(reference_tab: str) -> Tuple[str, ...]:
    """Which unified_analysis_type values are valid for the current reference tab."""
    if reference_tab == "NONE":
        return ("ALL_COLL_DUPES", "ALL_OBJ_DUPES", "MESH_SCENE")
    if reference_tab == "OBJECT":
        return ("OBJECT_DUPES",)
    return ("COLLECTION_DUPES", "PARTS_IN_REF", "MESH_SCENE")


def clear_unified(scene: bpy.types.Scene) -> None:
    scene.inst_mgr_unified_results.clear()
    scene.inst_mgr_unified_index = 0


def _add_mesh_geom_row(
    scene: bpy.types.Scene,
    fp: str,
    objs: list,
    title_prefix: str = "",
    *,
    lang: str = "EN",
) -> None:
    sorted_objs = sorted(objs, key=lambda o: o.name)
    row = scene.inst_mgr_unified_results.add()
    row.row_kind = "MESH_GEOM"
    row.master_coll_name = ""
    row.master_root_name = ""
    row.fp_hash = fp
    prefix = f"{title_prefix} " if title_prefix else ""
    row.title = i18n.t(lang, "ROW_MESH").format(
        prefix=prefix,
        first=sorted_objs[0].name,
        n=len(sorted_objs),
    )
    for o in sorted_objs:
        row.members.add().name = o.name


def analyze_object_dupes(scene: bpy.types.Scene, context: bpy.types.Context) -> Tuple[int, Optional[str]]:
    """与参考根物体（父子层级）同构的其它根物体。"""
    clear_unified(scene)
    L = i18n.get_lang(context)
    props = scene.inst_mgr_props
    obj = bpy.data.objects.get(core.inst_mgr_pg_str(props, "ref_object_name"))
    if obj is None:
        return 0, i18n.t(L, "ERR_NO_REF_OBJ")
    root = object_hierarchy.root_object(obj)
    others = object_hierarchy.find_equivalent_root_objects(
        root,
        scene,
        props.collection_equiv_scope,
    )
    for dup in others:
        row = scene.inst_mgr_unified_results.add()
        row.row_kind = "OBJECT_ROOT"
        row.root_object_name = dup.name
        row.master_root_name = ""
        row.master_coll_name = ""
        row.title = i18n.t(L, "ROW_OBJ").format(dup=dup.name, root=root.name)
        for o in object_hierarchy.iter_subtree_objects(dup):
            if getattr(o, "library", None) is not None:
                continue
            row.members.add().name = o.name
    scene.inst_mgr_equiv_object_count = len(others)
    return len(scene.inst_mgr_unified_results), None


def analyze_collection_dupes(scene: bpy.types.Scene, context: bpy.types.Context) -> Tuple[int, Optional[str]]:
    """列出与参考同构的其它根集合（不含参考内物体枚举，合并时再遍历）。"""
    clear_unified(scene)
    L = i18n.get_lang(context)
    props = scene.inst_mgr_props
    ref = bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))
    if ref is None:
        return 0, i18n.t(L, "ERR_NO_REF_COLL")
    others = structure_match.find_equivalent_root_collections(
        ref,
        scene=scene,
        mode=props.collection_equiv_scope,
    )
    for dup in others:
        row = scene.inst_mgr_unified_results.add()
        row.row_kind = "COLLECTION"
        row.coll_name = dup.name
        row.master_coll_name = ""
        row.master_root_name = ""
        row.title = i18n.t(L, "ROW_COLL").format(dup=dup.name, ref=ref.name)
        for o in structure_match.iter_objects_in_collection_deep(dup):
            if getattr(o, "library", None) is not None:
                continue
            row.members.add().name = o.name
    scene.inst_mgr_equiv_collection_count = len(others)
    return len(scene.inst_mgr_unified_results), None


def analyze_parts_in_ref(scene: bpy.types.Scene, context: bpy.types.Context) -> Tuple[int, Optional[str]]:
    """参考集合子树内：同构兄弟子集合 + 共享数据块（Mesh/Light/…）+ 网格几何指纹。"""
    clear_unified(scene)
    L = i18n.get_lang(context)
    props = scene.inst_mgr_props
    ref = bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))
    if ref is None:
        return 0, i18n.t(L, "ERR_NO_REF_COLL")

    coll_pairs = sorted(
        structure_match.iter_duplicate_child_collection_pairs_in_subtree(ref, scene),
        key=lambda t: (t[0].name, t[1].name),
    )
    for master, dup in coll_pairs:
        row = scene.inst_mgr_unified_results.add()
        row.row_kind = "COLLECTION"
        row.coll_name = dup.name
        row.master_coll_name = master.name
        row.master_root_name = ""
        row.title = i18n.t(L, "ROW_COLL_PAIR").format(dup=dup.name, master=master.name)
        for o in structure_match.iter_objects_in_collection_deep(dup):
            if getattr(o, "library", None) is not None:
                continue
            row.members.add().name = o.name

    objs: List[bpy.types.Object] = [
        o
        for o in structure_match.iter_objects_in_collection_deep(ref)
        if getattr(o, "library", None) is None
    ]

    buckets = defaultdict(list)
    for o in objs:
        if o.data is not None:
            buckets[(o.type, o.data)].append(o)
    shared = [(k, v) for k, v in buckets.items() if len(v) >= 2]
    shared.sort(key=lambda x: -len(x[1]))
    for (typ, data), group in shared:
        row = scene.inst_mgr_unified_results.add()
        row.row_kind = "SHARED_DATA"
        row.master_coll_name = ""
        row.master_root_name = ""
        row.data_block_type = typ
        row.data_block_name = data.name
        row.title = i18n.t(L, "ROW_SHARED").format(
            typ=typ,
            data=data.name,
            n=len(group),
        )
        for o in sorted(group, key=lambda x: x.name):
            row.members.add().name = o.name

    mesh_objs = [o for o in objs if o.type == "MESH" and o.data is not None]
    fp_groups = core.group_by_fingerprint(mesh_objs)
    for fp, group in sorted(fp_groups.items(), key=lambda x: -len(x[1])):
        _add_mesh_geom_row(scene, fp, group, lang=L)

    scene.inst_mgr_equiv_collection_count = -1
    return len(scene.inst_mgr_unified_results), None


def analyze_all_collection_clusters(scene: bpy.types.Scene, context: bpy.types.Context) -> Tuple[int, Optional[str]]:
    """无参考：按结构签名聚类根集合，每行一个副本→主编为组内名称序第一。"""
    clear_unified(scene)
    L = i18n.get_lang(context)
    props = scene.inst_mgr_props
    groups = structure_match.cluster_root_collections_by_signature(
        props.collection_equiv_scope,
        scene=scene,
    )
    nd = 0
    for group in groups:
        master = group[0]
        for dup in group[1:]:
            nd += 1
            row = scene.inst_mgr_unified_results.add()
            row.row_kind = "COLLECTION"
            row.coll_name = dup.name
            row.master_coll_name = master.name
            row.master_root_name = ""
            row.title = i18n.t(L, "ROW_COLL_PAIR").format(dup=dup.name, master=master.name)
            for o in structure_match.iter_objects_in_collection_deep(dup):
                if getattr(o, "library", None) is not None:
                    continue
                row.members.add().name = o.name
    scene.inst_mgr_equiv_collection_count = nd
    scene.inst_mgr_equiv_object_count = -1
    return len(scene.inst_mgr_unified_results), None


def analyze_all_object_root_clusters(scene: bpy.types.Scene, context: bpy.types.Context) -> Tuple[int, Optional[str]]:
    """无参考：按层级签名聚类场景根物体，每行一个副本→主编为组内名称序第一。"""
    clear_unified(scene)
    L = i18n.get_lang(context)
    props = scene.inst_mgr_props
    groups = object_hierarchy.cluster_root_objects_by_signature(scene, props.collection_equiv_scope)
    nd = 0
    for group in groups:
        master = group[0]
        for dup in group[1:]:
            nd += 1
            row = scene.inst_mgr_unified_results.add()
            row.row_kind = "OBJECT_ROOT"
            row.root_object_name = dup.name
            row.master_root_name = master.name
            row.master_coll_name = ""
            row.title = i18n.t(L, "ROW_OBJ_PAIR").format(dup=dup.name, master=master.name)
            for o in object_hierarchy.iter_subtree_objects(dup):
                if getattr(o, "library", None) is not None:
                    continue
                row.members.add().name = o.name
    scene.inst_mgr_equiv_object_count = nd
    scene.inst_mgr_equiv_collection_count = -1
    return len(scene.inst_mgr_unified_results), None


def analyze_mesh_scene_legacy(scene: bpy.types.Scene, context: bpy.types.Context) -> Tuple[int, Optional[str]]:
    """旧版：全场景 / 视图层 / 选中 / 按集合树 的纯网格几何组。"""
    clear_unified(scene)
    L = i18n.get_lang(context)
    props = scene.inst_mgr_props
    if props.scope == "PER_COLLECTION_TREE":
        rows = core.group_by_fingerprint_per_collection(context, only_mesh=props.only_mesh)
        for coll_name, fp, objs in rows:
            _add_mesh_geom_row(scene, fp, objs, title_prefix=f"{coll_name}", lang=L)
    else:
        objs = core.iter_mesh_objects(context, props.scope, only_mesh=props.only_mesh)
        buckets = core.group_by_fingerprint(objs)
        for fp, group in sorted(buckets.items(), key=lambda x: -len(x[1])):
            _add_mesh_geom_row(scene, fp, group, lang=L)
    scene.inst_mgr_equiv_collection_count = -1
    return len(scene.inst_mgr_unified_results), None


def resolve_row_objects(row) -> List[bpy.types.Object]:
    out: List[bpy.types.Object] = []
    for m in row.members:
        o = bpy.data.objects.get(m.name)
        if o:
            out.append(o)
    return out


def row_collection(row) -> Optional[bpy.types.Collection]:
    if row.row_kind != "COLLECTION" or not row.coll_name:
        return None
    return bpy.data.collections.get(row.coll_name)
