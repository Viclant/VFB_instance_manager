"""
按「物体父子链 + 子树类型与规范化名」匹配整套复杂资产（如 ParkingLot01 / .001 / .002），
与集合版 structure_match 并列使用。
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Dict, List, Optional

import bpy


def normalize_object_name(name: str) -> str:
    return re.sub(r"\.\d+$", "", name)


def root_object(obj: bpy.types.Object) -> bpy.types.Object:
    o = obj
    while o.parent is not None:
        o = o.parent
    return o


def iter_subtree_objects(root: bpy.types.Object) -> List[bpy.types.Object]:
    """深度优先，子按规范化名排序；含根。"""
    out: List[bpy.types.Object] = []

    def walk(o: bpy.types.Object) -> None:
        out.append(o)
        for ch in sorted(o.children, key=lambda x: (normalize_object_name(x.name), x.name)):
            walk(ch)

    walk(root)
    return out


def list_subtree_post_order_for_delete(root: bpy.types.Object) -> List[bpy.types.Object]:
    """先子后父，便于 bpy.data.objects.remove。"""
    out: List[bpy.types.Object] = []

    def walk(o: bpy.types.Object) -> None:
        for ch in sorted(o.children, key=lambda x: (normalize_object_name(x.name), x.name)):
            walk(ch)
        out.append(o)

    walk(root)
    return out


def object_hierarchy_signature(root: bpy.types.Object) -> str:
    """同构副本（忽略 .001/.002）应得到相同签名。"""
    parts: List[str] = []

    def walk(o: bpy.types.Object) -> None:
        if getattr(o, "library", None) is not None:
            return
        parts.append(f"O:{o.type}:{normalize_object_name(o.name)}")
        for ch in sorted(o.children, key=lambda x: (normalize_object_name(x.name), x.name)):
            walk(ch)

    walk(root)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _object_linked_to_scene_collection(obj: bpy.types.Object, scene: bpy.types.Scene) -> bool:
    return obj.name in scene.collection.objects


def cluster_root_objects_by_signature(scene: bpy.types.Scene, mode: str) -> List[List[bpy.types.Object]]:
    """
    Group scene root objects (no parent) by hierarchy signature; only groups with 2+ roots.
    Each group sorted by name (canonical master = first).
    """
    from collections import defaultdict

    if mode not in ("ENTIRE_FILE", "SCENE_ROOT", "SAME_PARENT"):
        mode = "SCENE_ROOT"
    buckets: Dict[tuple, List[bpy.types.Object]] = defaultdict(list)

    for o in scene.objects:
        if getattr(o, "library", None) is not None:
            continue
        if o.parent is not None:
            continue
        sig = object_hierarchy_signature(o)
        if mode == "SCENE_ROOT":
            if not _object_linked_to_scene_collection(o, scene):
                continue
            key = (sig,)
        elif mode == "SAME_PARENT":
            key = (o.parent, sig)
        else:
            key = (sig,)
        buckets[key].append(o)

    groups = [sorted(v, key=lambda x: x.name) for v in buckets.values() if len(v) >= 2]
    return sorted(groups, key=lambda g: g[0].name)


def find_equivalent_root_objects(
    ref_root: bpy.types.Object,
    scene: bpy.types.Scene,
    mode: str,
) -> List[bpy.types.Object]:
    """
    与参考根物体同构的其它根物体（parent is None，且在场景内）。
    mode 与集合版一致：SCENE_ROOT / SAME_PARENT / ENTIRE_FILE。
    """
    if mode not in ("ENTIRE_FILE", "SCENE_ROOT", "SAME_PARENT"):
        mode = "SCENE_ROOT"
    if getattr(ref_root, "library", None) is not None:
        return []
    if ref_root.parent is not None:
        ref_root = root_object(ref_root)

    sig_ref = object_hierarchy_signature(ref_root)
    ref_par = ref_root.parent
    out: List[bpy.types.Object] = []

    for o in scene.objects:
        if o == ref_root:
            continue
        if getattr(o, "library", None) is not None:
            continue
        if o.parent is not None:
            continue
        if mode == "SCENE_ROOT":
            if not _object_linked_to_scene_collection(o, scene):
                continue
        elif mode == "SAME_PARENT":
            if o.parent != ref_par:
                continue
        if object_hierarchy_signature(o) != sig_ref:
            continue
        out.append(o)

    return sorted(out, key=lambda x: x.name)


def build_normalized_object_map_from_root(root: bpy.types.Object) -> Dict[str, bpy.types.Object]:
    m: Dict[str, bpy.types.Object] = {}
    for o in iter_subtree_objects(root):
        if getattr(o, "library", None) is not None:
            continue
        k = normalize_object_name(o.name)
        if k not in m:
            m[k] = o
    return m


def summarize_object_subtree(
    root: bpy.types.Object,
    scene: Optional[bpy.types.Scene] = None,
) -> Dict[str, object]:
    root = root_object(root)
    if scene is None:
        scene = bpy.context.scene
    objs = [
        o
        for o in iter_subtree_objects(root)
        if getattr(o, "library", None) is None
    ]
    by_type = Counter(o.type for o in objs)
    depth = 0

    def max_depth(o: bpy.types.Object, d: int) -> int:
        if not o.children:
            return d
        return max(max_depth(ch, d + 1) for ch in o.children)

    if objs:
        depth = max_depth(root, 0)
    parent = root.parent
    in_scene_root = _object_linked_to_scene_collection(root, scene)
    return {
        "root_name": root.name,
        "parent_object": parent.name if parent else "—",
        "in_scene_collection_direct": in_scene_root,
        "object_count": len(objs),
        "max_depth": depth,
        "by_type": by_type,
        "sig8": object_hierarchy_signature(root)[:8],
    }


def format_object_summary_lines(info: Dict[str, object], lang: str = "EN") -> List[str]:
    from . import i18n

    L = lang if lang in i18n.STRINGS else "EN"
    lines: List[str] = []
    lines.append(
        i18n.t(L, "OBJ_ROOT").format(root=info["root_name"], par=info["parent_object"])
    )
    yn = i18n.t(L, "STRUCT_YES") if info["in_scene_collection_direct"] else i18n.t(L, "STRUCT_NO")
    lines.append(i18n.t(L, "OBJ_SCENE_MEM").format(yesno=yn))
    lines.append(
        i18n.t(L, "OBJ_SUBTREE").format(n=info["object_count"], d=info["max_depth"])
    )
    bt = info["by_type"]
    if not isinstance(bt, Counter):
        bt = Counter()
    if bt:
        parts = [f"{t}:{n}" for t, n in sorted(bt.items(), key=lambda x: (-x[1], x[0]))]
        tail = "…" if len(parts) > 10 else ""
        lines.append(
            i18n.t(L, "OBJ_TYPES").format(parts=", ".join(parts[:10]) + tail)
        )
    lines.append(i18n.t(L, "OBJ_SIG").format(sig=info["sig8"]))
    return lines
