"""
几何指纹与合并逻辑：在不动物体层级/变换的前提下，将相同几何的独立 Mesh 数据关联网到同一数据块。
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

import bpy


def inst_mgr_pg_str(props, attr: str, default: str = "") -> str:
    """Read a string RNA field from ``inst_mgr_props`` (or any PropertyGroup).

    After add-on reload or if a dynamic ``PropertyGroup`` lacks ``__module__``, Blender can
    return ``_PropertyDeferred`` instead of ``str`` — never call ``.strip()`` blindly.
    """
    if props is None:
        return default
    try:
        raw = getattr(props, attr, default)
    except Exception:
        return default
    if raw is None:
        return default
    if isinstance(raw, str):
        return raw.strip()
    if type(raw).__name__ == "_PropertyDeferred":
        return default
    try:
        return str(raw).strip()
    except Exception:
        return default


def mesh_fingerprint(mesh: bpy.types.Mesh) -> Optional[str]:
    if mesh is None or len(mesh.vertices) == 0:
        return None
    parts: List[str] = []
    parts.append(f"v{len(mesh.vertices)}")
    parts.append(f"p{len(mesh.polygons)}")
    for v in mesh.vertices:
        c = v.co
        parts.append(f"{c.x:.6f},{c.y:.6f},{c.z:.6f}")
    for p in mesh.polygons:
        parts.append(",".join(str(i) for i in p.vertices))
    s = "|".join(parts)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def iter_mesh_objects(
    context: bpy.types.Context,
    scope: str,
    only_mesh: bool = True,
) -> List[bpy.types.Object]:
    out: List[bpy.types.Object] = []
    scene = context.scene

    def consider(obj: bpy.types.Object) -> None:
        if only_mesh and obj.type != "MESH":
            return
        if obj.type != "MESH":
            return
        if getattr(obj, "library", None) is not None:
            return
        if obj.data is None or obj.data.library is not None:
            return
        out.append(obj)

    if scope == "SELECTED":
        for obj in context.selected_objects:
            consider(obj)
        return out

    if scope == "SCENE":
        for obj in scene.objects:
            consider(obj)
        return out

    if scope == "PER_COLLECTION":
        seen = set()
        for coll in bpy.data.collections:
            for obj in _all_objects_in_collection(coll):
                if obj.name in seen:
                    continue
                seen.add(obj.name)
                consider(obj)
        return out

    if scope == "VISIBLE_VIEW_LAYER":
        vl = context.view_layer
        for obj in vl.objects:
            consider(obj)
        return out

    # fallback
    for obj in scene.objects:
        consider(obj)
    return out


def _all_objects_in_collection(coll: bpy.types.Collection) -> Iterable[bpy.types.Object]:
    for obj in coll.objects:
        yield obj
    for child in coll.children:
        yield from _all_objects_in_collection(child)


def group_by_fingerprint(
    objects: List[bpy.types.Object],
) -> Dict[str, List[bpy.types.Object]]:
    buckets: Dict[str, List[bpy.types.Object]] = defaultdict(list)
    for obj in objects:
        fp = mesh_fingerprint(obj.data)
        if fp is None:
            continue
        buckets[fp].append(obj)
    return {k: v for k, v in buckets.items() if len(v) >= 2}


def group_by_fingerprint_per_collection(
    context: bpy.types.Context,
    only_mesh: bool = True,
) -> List[Tuple[str, str, List[bpy.types.Object]]]:
    """
    返回 [(collection_name, fingerprint, objects), ...]
    仅在同一集合树内合并，满足「资产包内部去重」。
    """
    results: List[Tuple[str, str, List[bpy.types.Object]]] = []
    root = context.scene.collection
    for coll in bpy.data.collections:
        # 跳过场景根集合，否则会包含全场景物体，列表重复且巨大
        if coll == root:
            continue
        objs: List[bpy.types.Object] = []
        for obj in _all_objects_in_collection(coll):
            if only_mesh and obj.type != "MESH":
                continue
            if obj.type != "MESH":
                continue
            if getattr(obj, "library", None) is not None:
                continue
            if obj.data is None or obj.data.library is not None:
                continue
            objs.append(obj)
        buckets: Dict[str, List[bpy.types.Object]] = defaultdict(list)
        for obj in objs:
            fp = mesh_fingerprint(obj.data)
            if fp is None:
                continue
            buckets[fp].append(obj)
        for fp, group in buckets.items():
            if len(group) < 2:
                continue
            results.append((coll.name, fp, group))
    return results


MASTER_ID_PROP = "INST_MGR_MASTER"


def objects_sharing_mesh_data(mesh: bpy.types.Mesh) -> List[bpy.types.Object]:
    """返回所有使用同一块 Mesh 数据的物体（已链接副本）。"""
    if mesh is None:
        return []
    return [o for o in bpy.data.objects if o.type == "MESH" and o.data == mesh]


def objects_with_same_fingerprint(
    scene: bpy.types.Scene,
    ref: bpy.types.Object,
) -> Tuple[Optional[str], List[bpy.types.Object]]:
    """
    与 ref 的网格几何指纹相同的全部网格物体（含未链接副本）。
    返回 (fingerprint 或 None, objects)。
    """
    if ref.type != "MESH" or ref.data is None:
        return None, []
    fp = mesh_fingerprint(ref.data)
    if not fp:
        return None, [ref]
    matches: List[bpy.types.Object] = []
    for o in scene.objects:
        if o.type != "MESH":
            continue
        if getattr(o, "library", None) is not None:
            continue
        if o.data is None or getattr(o.data, "library", None) is not None:
            continue
        if mesh_fingerprint(o.data) == fp:
            matches.append(o)
    return fp, matches


def merge_group_to_linked_data(
    objects: List[bpy.types.Object],
    master: Optional[bpy.types.Object] = None,
    master_index: int = 0,
) -> Tuple[bpy.types.Object, int]:
    """
    将组内物体关联网格到 master。返回 (master, linked_count)。
    若传入 master 且在列表中，优先使用；否则按 master_index 在按名排序后的列表中取。
    """
    if not objects:
        raise RuntimeError("Empty group")
    sorted_objs = sorted(objects, key=lambda o: o.name)
    if master is not None and master in sorted_objs:
        m = master
    else:
        m = sorted_objs[master_index % len(sorted_objs)]
    mesh_data = m.data
    linked = 0
    for obj in sorted_objs:
        if obj is m:
            continue
        if obj.data is mesh_data:
            continue
        obj.data = mesh_data
        linked += 1
    if mesh_data:
        try:
            mesh_data[MASTER_ID_PROP] = m.name
        except Exception:
            pass
    return m, linked
