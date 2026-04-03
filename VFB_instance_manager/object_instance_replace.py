"""
将「同构根物体」整棵子树删除，在原集合成员关系下放置 **集合实例** 空物体（``_DedupeObj_*``）。

与用哪种**分析模式**列出重复根无关；处理统一为集合实例。网格零件打包见 ``part_row_pack``。
"""

from __future__ import annotations

import re
from typing import List, Optional

import bpy
from mathutils import Matrix

from . import object_hierarchy, organization


def _rna_object_has(prop_name: str) -> bool:
    return bpy.types.Object.bl_rna.properties.get(prop_name) is not None


def _set_instance_object_safe(empty: bpy.types.Object, value) -> None:
    if not _rna_object_has("instance_object"):
        return
    try:
        empty.instance_object = value
    except (AttributeError, TypeError):
        pass


def _sanitize_collection_name(name: str) -> str:
    s = re.sub(r"[^\w\-]", "_", name)[:50]
    return s or "DedupeRoot"


def ensure_master_collection_for_object_root(master_root: bpy.types.Object) -> bpy.types.Collection:
    """主编子树全部放进同一 ``_DedupeObj_*`` 集合，并从其它集合 unlink，避免大纲里同一条出现多次。"""
    master_root = object_hierarchy.root_object(master_root)
    target_name = f"_DedupeObj_{_sanitize_collection_name(master_root.name)}"
    coll = bpy.data.collections.get(target_name)
    if coll is None:
        coll = bpy.data.collections.new(target_name)
    keep = {coll}
    for o in object_hierarchy.iter_subtree_objects(master_root):
        if getattr(o, "library", None) is not None:
            continue
        try:
            if o.name not in coll.objects:
                coll.objects.link(o)
        except RuntimeError:
            pass
        organization._unlink_object_from_collections_except(o, keep)
    return coll


def compute_instance_matrix_world_for_object_roots(
    master_root: bpy.types.Object,
    dup_root: bpy.types.Object,
) -> Matrix:
    ma = object_hierarchy.build_normalized_object_map_from_root(master_root)
    da = object_hierarchy.build_normalized_object_map_from_root(dup_root)
    common = sorted(set(ma.keys()) & set(da.keys()))
    if not common:
        return dup_root.matrix_world @ master_root.matrix_world.inverted()
    k = common[0]
    return da[k].matrix_world @ ma[k].matrix_world.inverted()


def remove_object_subtree(dup_root: bpy.types.Object) -> None:
    for o in object_hierarchy.list_subtree_post_order_for_delete(dup_root):
        if o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)


def replace_duplicate_object_root_with_instance(
    master_root: bpy.types.Object,
    dup_root: bpy.types.Object,
    *,
    empty_name_prefix: str = "OI_",
    scene: Optional[bpy.types.Scene] = None,
    auto_organize_master_instances: bool = False,
) -> bpy.types.Object:
    """删除 dup 整棵子树，在 dup 曾属的集合中放入集合实例空物体（``instance_collection`` → ``_DedupeObj_*``）。"""
    master_root = object_hierarchy.root_object(master_root)
    dup_root = object_hierarchy.root_object(dup_root)
    if master_root == dup_root:
        raise ValueError("Master and duplicate cannot be the same object")
    if getattr(master_root, "library", None) or getattr(dup_root, "library", None):
        raise ValueError("Linked library objects are not supported")

    master_coll = ensure_master_collection_for_object_root(master_root)

    T = compute_instance_matrix_world_for_object_roots(master_root, dup_root)

    collections: List[bpy.types.Collection] = list(dup_root.users_collection)

    remove_object_subtree(dup_root)

    empty_name = f"{empty_name_prefix}{_sanitize_collection_name(master_root.name)}"
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
    _set_instance_object_safe(empty, None)
    empty.matrix_world = T

    for c in collections:
        try:
            if empty.name not in c.objects:
                c.objects.link(empty)
        except RuntimeError:
            pass
    if not collections:
        try:
            bpy.context.scene.collection.objects.link(empty)
        except RuntimeError:
            pass

    sc = scene if scene is not None else bpy.context.scene
    if sc is not None and auto_organize_master_instances:
        try:
            layout = organization.read_collection_organize_layout(sc)
            twin_anchor = (
                organization.pick_twin_anchor_for_object_dup(collections, sc)
                if layout == "TWIN"
                else None
            )
            organization.after_object_instance_empty(
                sc,
                master_root,
                empty,
                master_data_coll=master_coll,
                layout=layout,
                twin_anchor_parent=twin_anchor,
            )
        except Exception:
            import traceback

            traceback.print_exc()

    return empty
