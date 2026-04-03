"""
将「同名前缀 + 数字后缀」的重复集合（如 ParkingLot01.001 / .002）替换为
空物体的集合实例（instance_collection 指向主编集合），并删除副本集合内的物体。

适用于 Shift+D 复制整套资产层级后的减负；会破坏副本集合内的数据，请先保存工程。
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import bpy
from mathutils import Matrix

from . import core, organization


def _collection_asset_key(name: str) -> Optional[Tuple[str, int]]:
    """ParkingLot01.001 -> ('ParkingLot01', 1)；无数字后缀则 None。"""
    if "." not in name:
        return None
    base, suf = name.rsplit(".", 1)
    if not suf.isdigit():
        return None
    return base, int(suf)


def _normalize_object_name(name: str) -> str:
    """去掉末尾 .数字，便于跨副本匹配同一零件。"""
    return re.sub(r"\.\d+$", "", name)


def _iter_objects_in_tree(coll: bpy.types.Collection) -> List[bpy.types.Object]:
    return list(core._all_objects_in_collection(coll))


def find_parent_collection(
    coll: bpy.types.Collection,
    scene: Optional[bpy.types.Scene] = None,
) -> Optional[bpy.types.Collection]:
    """父级以「当前场景」大纲树为准：从 ``scene.collection`` DFS，避免多场景或遍历顺序问题。"""
    if scene is None:
        scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return None
    sc = scene.collection
    if coll == sc:
        return None

    def walk(parent: bpy.types.Collection) -> Optional[bpy.types.Collection]:
        for ch in parent.children:
            if ch == coll:
                return parent
            found = walk(ch)
            if found is not None:
                return found
        return None

    found = walk(sc)
    if found is not None:
        return found
    for parent in bpy.data.collections:
        if parent == coll:
            continue
        for ch in parent.children:
            if ch == coll:
                return parent
    return None


def _build_normalized_object_map(coll: bpy.types.Collection) -> Dict[str, bpy.types.Object]:
    m: Dict[str, bpy.types.Object] = {}
    for o in _iter_objects_in_tree(coll):
        if getattr(o, "library", None) is not None:
            continue
        key = _normalize_object_name(o.name)
        if key not in m:
            m[key] = o
    return m


def compute_instance_matrix_world(master_coll: bpy.types.Collection, dup_coll: bpy.types.Collection) -> Matrix:
    """用规范化物体名对齐：T = M_dup @ inv(M_master)。"""
    ma = _build_normalized_object_map(master_coll)
    da = _build_normalized_object_map(dup_coll)
    common = sorted(set(ma.keys()) & set(da.keys()))
    if not common:
        return Matrix.Identity(4)
    k = common[0]
    return da[k].matrix_world @ ma[k].matrix_world.inverted()


def remove_collection_subtree(coll: bpy.types.Collection) -> None:
    """删除集合子树内所有子集合与直接物体（递归）。"""
    for child in list(coll.children):
        remove_collection_subtree(child)
    for obj in list(coll.objects):
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    if coll.name in bpy.data.collections:
        bpy.data.collections.remove(coll)


def replace_duplicate_collection_with_instance(
    master_coll: bpy.types.Collection,
    dup_coll: bpy.types.Collection,
    *,
    empty_name_prefix: str = "CI_",
    scene: Optional[bpy.types.Scene] = None,
    auto_organize_master_instances: bool = False,
) -> bpy.types.Object:
    """
    在 dup 的父集合下：创建空物体实例 master，对齐变换后删除 dup 集合子树。
    返回新建的空物体。
    """
    if master_coll == dup_coll:
        raise ValueError("Master and duplicate cannot be the same collection")
    if getattr(dup_coll, "library", None) is not None or getattr(master_coll, "library", None) is not None:
        raise ValueError("Linked library collections are not supported")

    parent = find_parent_collection(dup_coll, scene)
    if parent is None:
        raise RuntimeError(f"No parent collection for [{dup_coll.name}]")

    T = compute_instance_matrix_world(master_coll, dup_coll)

    empty_name = f"{empty_name_prefix}{dup_coll.name}"
    if empty_name in bpy.data.objects:
        base = empty_name
        i = 0
        while f"{base}.{i:03d}" in bpy.data.objects:
            i += 1
        empty_name = f"{base}.{i:03d}"

    empty = bpy.data.objects.new(empty_name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.5
    empty.instance_type = "COLLECTION"
    empty.instance_collection = master_coll
    empty.matrix_world = T

    parent.children.unlink(dup_coll)
    parent.objects.link(empty)
    remove_collection_subtree(dup_coll)
    if scene is not None and auto_organize_master_instances:
        try:
            layout = organization.read_collection_organize_layout(scene)
            organization.after_collection_instance_empty(
                scene,
                master_coll,
                empty,
                layout=layout,
                twin_anchor_parent=parent if layout == "TWIN" else None,
            )
        except Exception:
            import traceback

            traceback.print_exc()
    return empty


def group_collections_by_numeric_suffix(
    *,
    only_direct_child_of_scene_root: bool = True,
) -> Dict[str, List[Tuple[int, bpy.types.Collection]]]:
    """
    按「去掉末尾 .数字」得到的资产基名分组。
    返回 { base: [(suffix_int, collection), ...] }，仅包含至少 2 个集合的组。

    only_direct_child_of_scene_root:
        True 时只处理「场景根集合」的直接子集合（如 ParkingLot01.001 / .002），
        避免资产内部的子集合名带 .001 被误当成另一套 Shift+D 副本。
    """
    buckets: Dict[str, List[Tuple[int, bpy.types.Collection]]] = {}
    root = bpy.context.scene.collection
    for coll in bpy.data.collections:
        if coll == root:
            continue
        if getattr(coll, "library", None) is not None:
            continue
        if only_direct_child_of_scene_root:
            par = find_parent_collection(coll, bpy.context.scene)
            if par != root:
                continue
        key = _collection_asset_key(coll.name)
        if key is None:
            continue
        base, num = key
        buckets.setdefault(base, []).append((num, coll))

    out: Dict[str, List[Tuple[int, bpy.types.Collection]]] = {}
    for base, items in buckets.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda x: x[0])
        out[base] = items
    return out


def auto_replace_all_duplicate_asset_collections(
    *,
    only_direct_child_of_scene_root: bool = True,
) -> Tuple[int, int]:
    """
    对每个资产基名：保留编号最小的集合为主编，其余转为集合实例。
    返回 (处理的副本集合数, 新建空物体数)。
    """
    groups = group_collections_by_numeric_suffix(
        only_direct_child_of_scene_root=only_direct_child_of_scene_root,
    )
    replaced = 0
    empties = 0
    scene = bpy.context.scene
    props = getattr(scene, "inst_mgr_props", None)
    org = bool(props.auto_organize_master_instances) if props else False
    for base, items in sorted(groups.items()):
        master = items[0][1]
        for _n, dup in items[1:]:
            replace_duplicate_collection_with_instance(
                master,
                dup,
                scene=scene,
                auto_organize_master_instances=org,
            )
            replaced += 1
            empties += 1
    return replaced, empties
