"""
按集合子树结构（规范化集合名 + 物体类型 + 规范化物体名）匹配「同一套资产」，
用于参考集合高亮与其它副本分组配色。
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional, Tuple

import bpy

from . import core
from .collection_instances import find_parent_collection


def _normalize_object_name(name: str) -> str:
    return re.sub(r"\.\d+$", "", name)


def _normalize_collection_name(name: str) -> str:
    return re.sub(r"\.\d+$", "", name)


def collection_structure_signature(coll: bpy.types.Collection) -> str:
    """同构资产（忽略 .001/.002 等数字后缀）应得到相同签名。

    仅遍历集合层级与 ``collection.objects`` 直接成员；**集合实例空物体**记为 ``O:EMPTY:…``，
    不会展开 ``instance_collection`` 内物体。一侧全网格、一侧全实例空物体时签名会不同。
    """
    parts: List[str] = []

    def walk(c: bpy.types.Collection) -> None:
        parts.append(f"C:{_normalize_collection_name(c.name)}")
        for ch in sorted(c.children, key=lambda x: x.name):
            walk(ch)
        for o in sorted(c.objects, key=lambda x: x.name):
            parts.append(f"O:{o.type}:{_normalize_object_name(o.name)}")

    walk(coll)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def collection_flat_content_signature(
    coll: bpy.types.Collection,
    *,
    expand_collection_instances: bool = False,
) -> str:
    """子树内全部物体（忽略集合嵌套层级）的多重集签名；可选展开集合实例空物体内的物体。"""
    parts: List[str] = []
    ic_stack: set[int] = set()

    def walk_collection(c: bpy.types.Collection) -> None:
        for o in iter_objects_in_collection_deep(c):
            if getattr(o, "library", None) is not None:
                continue
            if expand_collection_instances and is_collection_instance_empty(o) and o.instance_collection:
                ic = o.instance_collection
                if getattr(ic, "library", None) is not None:
                    parts.append(f"EMPTY:{_normalize_object_name(o.name)}")
                    continue
                icid = id(ic)
                if icid in ic_stack:
                    parts.append(f"EMPTY:{_normalize_object_name(o.name)}|CYCLIC")
                    continue
                ic_stack.add(icid)
                try:
                    walk_collection(ic)
                finally:
                    ic_stack.discard(icid)
            else:
                parts.append(f"{o.type}:{_normalize_object_name(o.name)}")

    walk_collection(coll)
    parts.sort()
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def iter_objects_in_collection_deep(coll: bpy.types.Collection):
    yield from core._all_objects_in_collection(coll)


def is_collection_instance_empty(obj: bpy.types.Object) -> bool:
    return (
        obj.type == "EMPTY"
        and getattr(obj, "instance_type", "NONE") == "COLLECTION"
        and getattr(obj, "instance_collection", None) is not None
    )


def iter_duplicate_child_collection_pairs_in_subtree(
    root: bpy.types.Collection,
    scene: bpy.types.Scene,
):
    """Walk ``root`` and descendants; for each parent, find child collections with the same
    ``collection_structure_signature``. Yields ``(master, dup)`` with master first by name.

    Used for 「参考集合内零件」: duplicate *sub-collections* inside the reference subtree.
    """
    from collections import defaultdict, deque

    sc = scene.collection
    queue = deque([root])
    seen_parents = {root}
    while queue:
        parent = queue.popleft()
        children = [
            c
            for c in parent.children
            if getattr(c, "library", None) is None and c != sc
        ]
        by_sig: Dict[str, List[bpy.types.Collection]] = defaultdict(list)
        for ch in children:
            by_sig[collection_structure_signature(ch)].append(ch)
        for group in by_sig.values():
            if len(group) < 2:
                continue
            group = sorted(group, key=lambda x: x.name)
            m = group[0]
            for dup in group[1:]:
                yield m, dup
        for ch in children:
            if ch not in seen_parents:
                seen_parents.add(ch)
                queue.append(ch)


def cluster_root_collections_by_signature(
    mode: str,
    scene: Optional[bpy.types.Scene] = None,
) -> List[List[bpy.types.Collection]]:
    """
    Group root-level candidate collections by structure signature (same rules as search scope).
    Returns only groups with at least 2 members, each inner list sorted by name (master = [0]).
    """
    from collections import defaultdict

    if scene is None:
        scene = bpy.context.scene
    sc = scene.collection
    buckets: Dict[Tuple, List[bpy.types.Collection]] = defaultdict(list)
    if mode not in ("ENTIRE_FILE", "SCENE_ROOT", "SAME_PARENT"):
        mode = "SCENE_ROOT"

    for c in bpy.data.collections:
        if c == sc or getattr(c, "library", None) is not None:
            continue
        sig = collection_structure_signature(c)
        if mode == "ENTIRE_FILE":
            key = (sig,)
        elif mode == "SCENE_ROOT":
            if find_parent_collection(c, scene) != sc:
                continue
            key = (sig,)
        else:
            par = find_parent_collection(c, scene)
            if par is None:
                continue
            key = (par.name, sig)
        buckets[key].append(c)

    groups = [sorted(v, key=lambda x: x.name) for v in buckets.values() if len(v) >= 2]
    return sorted(groups, key=lambda g: g[0].name)


def _iter_equiv_collection_candidates(
    ref: bpy.types.Collection,
    sc: bpy.types.Collection,
    ref_parent: Optional[bpy.types.Collection],
    mode: str,
    scene: bpy.types.Scene,
) -> Iterable[bpy.types.Collection]:
    for c in bpy.data.collections:
        if c == ref or c == sc:
            continue
        if getattr(c, "library", None) is not None:
            continue
        if mode == "ENTIRE_FILE":
            pass
        elif mode == "SCENE_ROOT":
            if find_parent_collection(c, scene) != sc:
                continue
        else:
            if ref_parent is not None and find_parent_collection(c, scene) != ref_parent:
                continue
        yield c


def find_equivalent_root_collections(
    ref: bpy.types.Collection,
    *,
    scene: Optional[bpy.types.Scene] = None,
    only_direct_child_of_scene_root: Optional[bool] = None,
    mode: Optional[str] = None,
) -> List[bpy.types.Collection]:
    """
    与参考集合「同构」的其它集合（整棵子树签名一致，忽略 .001/.002 后缀）。

    若严格结构签名无匹配，则在同一候选范围内依次尝试：
    1) 规范化根集合名相同 + 子树物体 (type, 规范化名) 扁平多重集一致；
    2) 同上，且将集合实例空物体展开为其 ``instance_collection`` 内物体后再比扁平多重集。

    mode（推荐）：
    - SCENE_ROOT：仅「场景集合」的直接子集合（多份资产并排拖在场景根下）。
    - SAME_PARENT：与参考「同一父集合」下的兄弟（资产挂在一个父分组下）。
    - ENTIRE_FILE：整个 blend 内任意集合（副本在不同父级时仍能找到）。

    兼容旧参数 only_direct_child_of_scene_root：若 mode 为 None 则 True→SCENE_ROOT，False→SAME_PARENT。
    """
    if mode is None:
        if only_direct_child_of_scene_root is None:
            mode = "SCENE_ROOT"
        else:
            mode = "SCENE_ROOT" if only_direct_child_of_scene_root else "SAME_PARENT"
    if mode not in ("ENTIRE_FILE", "SCENE_ROOT", "SAME_PARENT"):
        mode = "SCENE_ROOT"

    if scene is None:
        scene = bpy.context.scene
    sig_ref = collection_structure_signature(ref)
    sc = scene.collection
    ref_parent = find_parent_collection(ref, scene)
    out: List[bpy.types.Collection] = []

    candidates = _iter_equiv_collection_candidates(ref, sc, ref_parent, mode, scene)
    for c in candidates:
        if collection_structure_signature(c) == sig_ref:
            out.append(c)
    if out:
        return sorted(out, key=lambda x: x.name)

    ref_norm = _normalize_collection_name(ref.name)
    sig_loose = collection_flat_content_signature(ref, expand_collection_instances=False)
    for c in _iter_equiv_collection_candidates(ref, sc, ref_parent, mode, scene):
        if _normalize_collection_name(c.name) != ref_norm:
            continue
        if collection_flat_content_signature(c, expand_collection_instances=False) == sig_loose:
            out.append(c)
    if out:
        return sorted(out, key=lambda x: x.name)

    sig_loose_inst = collection_flat_content_signature(ref, expand_collection_instances=True)
    for c in _iter_equiv_collection_candidates(ref, sc, ref_parent, mode, scene):
        if _normalize_collection_name(c.name) != ref_norm:
            continue
        if collection_flat_content_signature(c, expand_collection_instances=True) == sig_loose_inst:
            out.append(c)
    return sorted(out, key=lambda x: x.name)


def summarize_collection_structure(
    coll: bpy.types.Collection,
    scene: Optional[bpy.types.Scene] = None,
) -> Dict[str, object]:
    """用于面板展示：父级、是否场景根子项、子树物体数量按类型统计。"""

    def count_coll_subtree(c: bpy.types.Collection) -> int:
        return 1 + sum(count_coll_subtree(ch) for ch in c.children)

    if scene is None:
        scene = bpy.context.scene
    parent = find_parent_collection(coll, scene)
    sc = scene.collection
    objs = [
        o
        for o in iter_objects_in_collection_deep(coll)
        if getattr(o, "library", None) is None
    ]
    by_type = Counter(o.type for o in objs)
    n_coll_tree = count_coll_subtree(coll)
    return {
        "parent_name": parent.name if parent else "—",
        "is_direct_scene_child": parent == sc,
        "subcollections_in_tree": max(0, n_coll_tree - 1),
        "collections_total_in_tree": n_coll_tree,
        "object_count": len(objs),
        "by_type": by_type,
        "structure_sig8": collection_structure_signature(coll)[:8],
    }


def format_structure_summary_lines(info: Dict[str, object], lang: str = "EN") -> List[str]:
    """Outliner detail lines for the Reference panel (language from i18n)."""
    from . import i18n

    L = lang if lang in i18n.STRINGS else "EN"
    lines: List[str] = []
    yn = i18n.t(L, "STRUCT_YES") if info["is_direct_scene_child"] else i18n.t(L, "STRUCT_NO")
    lines.append(
        i18n.t(L, "STRUCT_PARENT").format(parent=info["parent_name"], yesno=yn)
    )
    lines.append(
        i18n.t(L, "STRUCT_SUBTREE").format(
            ncoll=info["collections_total_in_tree"],
            nobj=info["object_count"],
        )
    )
    bt = info["by_type"]
    if not isinstance(bt, Counter):
        bt = Counter()
    if bt:
        parts = [f"{t}:{n}" for t, n in sorted(bt.items(), key=lambda x: (-x[1], x[0]))]
        tail = "…" if len(parts) > 8 else ""
        lines.append(
            i18n.t(L, "STRUCT_TYPES").format(
                parts=", ".join(parts[:8]) + tail,
            )
        )
    lines.append(i18n.t(L, "STRUCT_SIG").format(sig=info["structure_sig8"]))
    return lines


# 与参考红色区分：每组 (深色「主内容」, 浅色「集合实例空物体」)
GROUP_PALETTE: List[Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]] = [
    ((0.0, 0.38, 0.12, 1.0), (0.45, 0.92, 0.55, 1.0)),
    ((0.28, 0.05, 0.52, 1.0), (0.72, 0.55, 0.98, 1.0)),
    ((0.0, 0.35, 0.55, 1.0), (0.45, 0.82, 0.95, 1.0)),
    ((0.55, 0.32, 0.0, 1.0), (0.98, 0.78, 0.35, 1.0)),
    ((0.48, 0.0, 0.22, 1.0), (0.95, 0.45, 0.55, 1.0)),
    ((0.2, 0.2, 0.45, 1.0), (0.65, 0.7, 0.95, 1.0)),
]

REF_COLOR = (1.0, 0.18, 0.18, 1.0)
