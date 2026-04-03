"""
Scan collection-instance empties: counts by master collection, summary totals, or per object.
"""

from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, List, Set, Tuple

import bpy

from . import core


def _is_collection_instance_empty(obj: bpy.types.Object) -> bool:
    return (
        obj is not None
        and obj.type == "EMPTY"
        and getattr(obj, "instance_type", "NONE") == "COLLECTION"
        and getattr(obj, "instance_collection", None) is not None
    )


def _objects_deep(coll: bpy.types.Collection) -> Set[bpy.types.Object]:
    return {
        o
        for o in core._all_objects_in_collection(coll)
        if getattr(o, "library", None) is None
    }


def collect_instancer_map() -> Tuple[
    Dict[bpy.types.Collection, List[bpy.types.Object]],
    List[Tuple[bpy.types.Collection, bpy.types.Object]],
]:
    """
    Returns:
      coll_direct: collection -> list of empties that instance this collection directly
      flat_pairs: list of (ic, empty) for per-object aggregation
    """
    coll_direct: DefaultDict[bpy.types.Collection, List[bpy.types.Object]] = defaultdict(list)
    flat_pairs: List[Tuple[bpy.types.Collection, bpy.types.Object]] = []

    for o in bpy.data.objects:
        if getattr(o, "library", None) is not None:
            continue
        if not _is_collection_instance_empty(o):
            continue
        ic = o.instance_collection
        if ic is None or getattr(ic, "library", None) is not None:
            continue
        coll_direct[ic].append(o)
        flat_pairs.append((ic, o))

    return dict(coll_direct), flat_pairs


def _add_summary_rows(
    rows,
    n_instancer_empties: int,
    n_unique_objects: int,
    n_master_collections: int,
) -> None:
    """row_kind SUMMARY; master_name holds i18n key."""
    specs = [
        ("STATS_SUM_N_INST", n_instancer_empties),
        ("STATS_SUM_N_OBJ", n_unique_objects),
        ("STATS_SUM_N_COLL", n_master_collections),
    ]
    for key, val in specs:
        r = rows.add()
        r.row_kind = "SUMMARY"
        r.master_name = key
        r.instance_count = int(val)


def rebuild_instance_stats(scene: bpy.types.Scene, mode: str = "SUMMARY") -> int:
    """Fill scene.inst_mgr_instance_stats. mode: MASTERS | SUMMARY | BY_OBJECT."""
    rows = scene.inst_mgr_instance_stats
    rows.clear()
    scene.inst_mgr_instance_stat_index = 0

    coll_direct, flat_pairs = collect_instancer_map()

    if mode == "SUMMARY":
        if not coll_direct:
            _add_summary_rows(rows, 0, 0, 0)
            return len(rows)
        total_empties = sum(len(v) for v in coll_direct.values())
        n_masters = len(coll_direct)
        all_objs: Set[str] = set()
        for ic in coll_direct:
            for ob in _objects_deep(ic):
                if ob.type == "EMPTY" and _is_collection_instance_empty(ob):
                    continue
                all_objs.add(ob.name)
        _add_summary_rows(rows, total_empties, len(all_objs), n_masters)
        return len(rows)

    if not coll_direct:
        return 0

    coll_items: List[Tuple[str, int, List[str]]] = []
    for coll, empties in sorted(coll_direct.items(), key=lambda x: (-len(x[1]), x[0].name)):
        n = len(empties)
        if n <= 0:
            continue
        names = sorted(e.name for e in empties)
        coll_items.append((coll.name, n, names))

    ic_deep_cache: Dict[bpy.types.Collection, Set[bpy.types.Object]] = {}
    for ic in coll_direct:
        ic_deep_cache[ic] = _objects_deep(ic)

    obj_counts: DefaultDict[str, int] = defaultdict(int)
    obj_empties: DefaultDict[str, List[str]] = defaultdict(list)

    for ic, empty in flat_pairs:
        deep = ic_deep_cache.get(ic)
        if not deep:
            continue
        seen_for_this_empty: Set[str] = set()
        for ob in deep:
            if ob.type == "EMPTY" and _is_collection_instance_empty(ob):
                continue
            key = ob.name
            if key in seen_for_this_empty:
                continue
            seen_for_this_empty.add(key)
            obj_counts[key] += 1
            obj_empties[key].append(empty.name)

    obj_items: List[Tuple[str, int, List[str]]] = []
    for name, n in sorted(obj_counts.items(), key=lambda x: (-x[1], x[0])):
        if n <= 0:
            continue
        obj_items.append((name, n, sorted(set(obj_empties[name]))))

    if mode == "MASTERS":
        for cname, n, enames in coll_items:
            r = rows.add()
            r.row_kind = "COLLECTION"
            r.master_name = cname
            r.instance_count = n
            for en in enames:
                s = r.instancers.add()
                s.name = en
    elif mode == "BY_OBJECT":
        for oname, n, enames in obj_items:
            r = rows.add()
            r.row_kind = "OBJECT"
            r.master_name = oname
            r.instance_count = n
            for en in enames:
                s = r.instancers.add()
                s.name = en
    else:
        for cname, n, enames in coll_items:
            r = rows.add()
            r.row_kind = "COLLECTION"
            r.master_name = cname
            r.instance_count = n
            for en in enames:
                s = r.instancers.add()
                s.name = en
        for oname, n, enames in obj_items:
            r = rows.add()
            r.row_kind = "OBJECT"
            r.master_name = oname
            r.instance_count = n
            for en in enames:
                s = r.instancers.add()
                s.name = en

    return len(rows)
