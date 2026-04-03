"""
参考集合内「零件 / 网格重复行」：在参考下建子集合，主编进 ``_DedupeObj_*``，副本位姿用
**集合实例**空物体（无 Empty OBJECT 路径）。
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

import bpy

from . import core
from . import object_instance_replace as oir
from . import organization as org
from . import structure_match


def _sanitize_coll(name: str) -> str:
    s = re.sub(r"[^\w\-.]", "_", name)
    return (s[:48] or "Pack").strip("_") or "Pack"


def _restrict_object_to_collections(
    obj: bpy.types.Object,
    keep: set,
) -> None:
    """Remove object from every collection except those in ``keep`` (must stay non-empty for viewport)."""
    for c in list(obj.users_collection):
        if c in keep:
            continue
        try:
            c.objects.unlink(obj)
        except RuntimeError:
            pass


def _unique_collection_name(base: str) -> str:
    name = base
    i = 0
    while name in bpy.data.collections:
        i += 1
        name = f"{base}_{i:02d}"
    return name


def _resolve_mesh_master(scene: bpy.types.Scene, fingerprint: str, objects: List[bpy.types.Object]) -> bpy.types.Object:
    if not objects:
        raise RuntimeError("Empty group")
    datas = {o.data for o in objects}
    if len(datas) == 1:
        mdat = objects[0].data
        if mdat is not None and core.MASTER_ID_PROP in mdat:
            name = mdat[core.MASTER_ID_PROP]
            if isinstance(name, str):
                cand = bpy.data.objects.get(name)
                if cand and cand in objects:
                    return cand
    if fingerprint:
        for ovr in scene.inst_mgr_master_overrides:
            if ovr.fingerprint == fingerprint:
                cand = bpy.data.objects.get(ovr.master_name)
                if cand and cand in objects:
                    return cand
    return sorted(objects, key=lambda o: o.name)[0]


def _mesh_candidates_from_row(row) -> List[bpy.types.Object]:
    from . import unified_results

    out: List[bpy.types.Object] = []
    for o in unified_results.resolve_row_objects(row):
        if o.type != "MESH" or o.data is None:
            continue
        if getattr(o, "library", None) is not None or getattr(o.data, "library", None) is not None:
            continue
        out.append(o)
    return out


def _link_pack_collection_under_reference(ref: bpy.types.Collection, sub: bpy.types.Collection) -> None:
    """Parent packed result as a **child** of the reference collection."""
    try:
        names = {ch.name for ch in ref.children}
        if sub.name not in names:
            ref.children.link(sub)
    except RuntimeError:
        pass


def row_supports_mesh_pack(row) -> bool:
    if row.row_kind == "MESH_GEOM":
        return True
    if row.row_kind == "SHARED_DATA" and getattr(row, "data_block_type", "") == "MESH":
        return True
    return False


def pack_mesh_row_into_subcollection_collection_instance(
    scene: bpy.types.Scene,
    ref: bpy.types.Collection,
    row,
    row_index: int,
) -> Tuple[bool, str]:
    """
    Child collection under ``ref``; master mesh in ``_DedupeObj_*``; duplicates become
    collection-instance empties.
    """
    if not row_supports_mesh_pack(row):
        return False, "ERR_PACK_ROW_KIND"
    objs = _mesh_candidates_from_row(row)
    if len(objs) < 2:
        return False, "ERR_PACK_NEED_TWO"

    ref_objs = set(structure_match.iter_objects_in_collection_deep(ref))
    if not all(o in ref_objs for o in objs):
        return False, "ERR_PACK_OUTSIDE_REF"

    try:
        fp = (getattr(row, "fp_hash", None) or "").strip()
    except Exception:
        fp = ""
    if not fp and objs[0].data:
        fp = core.mesh_fingerprint(objs[0].data) or ""

    try:
        master = _resolve_mesh_master(scene, fp, objs)
    except RuntimeError:
        return False, "ERR_PACK_MASTER"

    core.merge_group_to_linked_data(objs, master=master)
    master_coll = oir.ensure_master_collection_for_object_root(master)
    others = [o for o in objs if o != master]

    _restrict_object_to_collections(master, {master_coll})

    base_name = _sanitize_coll(f"{ref.name}_R{row_index:02d}_{master.name}_CI")
    sub_name = _unique_collection_name(f"VFB_{base_name}")
    sub = bpy.data.collections.new(sub_name)
    _link_pack_collection_under_reference(ref, sub)

    org._move_collection_under_parent(master_coll, sub, scene)

    for dup in others:
        if dup.name not in bpy.data.objects:
            continue
        T = dup.matrix_world.copy()
        bpy.data.objects.remove(dup, do_unlink=True)

        base_en = f"VfbCI_{_sanitize_coll(master.name)}"
        en_name = base_en[:59]
        j = 0
        while en_name in bpy.data.objects:
            j += 1
            en_name = f"{base_en[:50]}_{j:03d}"

        empty = bpy.data.objects.new(en_name, None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.empty_display_size = 0.35
        empty.instance_type = "COLLECTION"
        empty.instance_collection = master_coll
        oir._set_instance_object_safe(empty, None)
        empty.matrix_world = T

        try:
            if empty.name not in sub.objects:
                sub.objects.link(empty)
        except RuntimeError:
            pass
        _restrict_object_to_collections(empty, {sub})

    return True, sub_name


def pack_all_mesh_part_rows_collection_instance(
    scene: bpy.types.Scene,
    ref: bpy.types.Collection,
) -> Tuple[int, Optional[str]]:
    """Pack every mesh row using collection-instance empties. Returns (count, first_error_key)."""
    rows = scene.inst_mgr_unified_results
    n_ok = 0
    for i, row in enumerate(rows):
        if not row_supports_mesh_pack(row):
            continue
        objs = _mesh_candidates_from_row(row)
        if len(objs) < 2:
            continue
        ok, msg = pack_mesh_row_into_subcollection_collection_instance(scene, ref, row, i)
        if not ok:
            return n_ok, msg
        n_ok += 1
    if n_ok == 0:
        return 0, "ERR_PACK_NONE"
    return n_ok, None
