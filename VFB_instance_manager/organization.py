"""
Optional post-step after creating a collection-instance empty: group the instance empty
and the master content under ``{Name}_Master_and_Instances``.

Pipeline (only when ``auto_organize_master_instances`` is True in the replace helpers):

**Step 1 — Resolve parent**  
Find the collection that should hold the new group as a **child**, so the group sits at the
**same hierarchy level as the master** (sibling to the master collection / master’s collection
context), not always under the scene root.

**Step 2 — Create or reuse group**  
Create (or reparent) ``{SanitizedName}_Master_and_Instances`` under that parent.

**Step 3 — Move instance + master into the group**  
- Collection-instance path: move the instance empty into the group’s object list; reparent the
  master collection under the group. Optional **TWIN** layout: under the duplicate’s original
  parent, ``VFB_* / Name_Source / Name_Instances`` (master under Source, empties under Instances).  
- Object-instance path (OI_ / ``_DedupeObj_*``): same group logic as above, or **TWIN** under
  the duplicate’s containing collection: ``VFB_* / Name_Source / Name_Instances`` (master or
  ``_DedupeObj_*`` under Source; OI_ empties under Instances).
"""

from __future__ import annotations

import re
from typing import List, Optional, Set, Tuple

import bpy


def read_collection_organize_layout(scene: Optional[bpy.types.Scene]) -> str:
    if scene is None:
        return "LEGACY"
    p = getattr(scene, "inst_mgr_props", None)
    if p is None:
        return "LEGACY"
    v = getattr(p, "collection_organize_layout", "LEGACY")
    return v if v in ("LEGACY", "TWIN") else "LEGACY"


MASTER_INST_SUFFIX = "_Master_and_Instances"

# ``VFB_* / {base}_Source / {base}_Instances`` layout (collection-instance organize).
TWIN_SOURCE_SUFFIX = "_Source"
TWIN_INST_SUFFIX = "_Instances"

# When user hides ``_DedupeObj_*`` from the outliner: store parent name so Show can restore.
DEDUPE_SOURCE_PREFIX = "_DedupeObj_"
DEDUPE_HIDE_PARENT_KEY = "inst_mgr_vfb_dedupe_hide_parent"


def _safe_base(name: str) -> str:
    s = re.sub(r"[^\w\-]", "_", str(name)).strip("_")[:50]
    return s or "Asset"


def _find_parent_collection(
    coll: bpy.types.Collection,
    scene: bpy.types.Scene,
) -> Optional[bpy.types.Collection]:
    sc = scene.collection
    for ch in sc.children:
        if ch == coll:
            return sc
    for parent in bpy.data.collections:
        if parent == coll:
            continue
        for ch in parent.children:
            if ch == coll:
                return parent
    return None


def pick_twin_anchor_for_object_dup(
    dup_collections: List[bpy.types.Collection],
    scene: bpy.types.Scene,
) -> bpy.types.Collection:
    """Parent collection for ``VFB_*`` when replacing object-root duplicates (OI_ path).

    Uses the deepest collection that held the duplicate, excluding scene root and inner organizer
    folders (``*_Master_and_Instances``, ``*_Source``, ``*_Instances``).
    """
    sc = scene.collection

    def _is_inner_organizer(n: str) -> bool:
        return (
            n.endswith(MASTER_INST_SUFFIX)
            or n.endswith(TWIN_SOURCE_SUFFIX)
            or n.endswith(TWIN_INST_SUFFIX)
        )

    candidates = [c for c in dup_collections if c != sc and not _is_inner_organizer(c.name)]
    if not candidates:
        candidates = [c for c in dup_collections if c != sc]
    if not candidates:
        return sc
    return max(candidates, key=lambda c: _collection_depth(c, scene))


def _collection_depth(coll: bpy.types.Collection, scene: bpy.types.Scene) -> int:
    d = 0
    p: Optional[bpy.types.Collection] = coll
    root = scene.collection
    while p is not None and p != root:
        par = _find_parent_collection(p, scene)
        if par is None:
            break
        d += 1
        p = par
    return d


def step1_parent_same_layer_as_master_for_object_root(
    master_root: bpy.types.Object,
    scene: bpy.types.Scene,
) -> bpy.types.Collection:
    """Parent collection under which the group will be created (sibling layer to master)."""
    candidates = [
        c
        for c in master_root.users_collection
        if c != scene.collection and not c.name.endswith(MASTER_INST_SUFFIX)
    ]
    if not candidates:
        return scene.collection
    anchor = max(candidates, key=lambda c: _collection_depth(c, scene))
    par = _find_parent_collection(anchor, scene)
    return par if par is not None else scene.collection


def step1_parent_same_layer_as_master_collection(
    master_coll: bpy.types.Collection,
    scene: bpy.types.Scene,
) -> bpy.types.Collection:
    """Parent of the master collection = layer where the group sits next to the master."""
    par = _find_parent_collection(master_coll, scene)
    return par if par is not None else scene.collection


def ensure_master_instances_collection(
    scene: bpy.types.Scene,
    base_name: str,
    parent: bpy.types.Collection,
) -> bpy.types.Collection:
    """Step 2: create or reuse ``{base}_Master_and_Instances`` under ``parent``."""
    coll_name = f"{_safe_base(base_name)}{MASTER_INST_SUFFIX}"
    c = bpy.data.collections.get(coll_name)
    if c is None:
        c = bpy.data.collections.new(coll_name)
        try:
            parent.children.link(c)
        except RuntimeError:
            pass
        return c
    cur = _find_parent_collection(c, scene)
    if cur != parent:
        try:
            if cur is not None:
                cur.children.unlink(c)
        except Exception:
            pass
        try:
            names = {ch.name for ch in parent.children}
            if c.name not in names:
                parent.children.link(c)
        except RuntimeError:
            pass
    # Must sit in the scene tree or instances vanish from the viewport.
    if _find_parent_collection(c, scene) is None:
        try:
            scene.collection.children.link(c)
        except RuntimeError:
            pass
    return c


def _link_object(coll: bpy.types.Collection, obj: bpy.types.Object) -> None:
    try:
        if obj.name not in coll.objects:
            coll.objects.link(obj)
    except RuntimeError:
        pass


def _move_object_exclusive_to_collection(
    obj: bpy.types.Object,
    target: bpy.types.Collection,
) -> None:
    for col in list(obj.users_collection):
        if col != target:
            try:
                col.objects.unlink(obj)
            except RuntimeError:
                pass
    _link_object(target, obj)


def _move_collection_under_parent(
    coll: bpy.types.Collection,
    new_parent: bpy.types.Collection,
    scene: bpy.types.Scene,
) -> None:
    par = _find_parent_collection(coll, scene)
    try:
        if par is not None and par != new_parent:
            par.children.unlink(coll)
    except Exception:
        pass
    try:
        names = {ch.name for ch in new_parent.children}
        if coll.name not in names:
            new_parent.children.link(coll)
    except RuntimeError:
        pass


def _collection_is_or_contains(ancestor: bpy.types.Collection, coll: bpy.types.Collection) -> bool:
    if ancestor == coll:
        return True
    for ch in ancestor.children:
        if _collection_is_or_contains(ch, coll):
            return True
    return False


def _find_twin_triplet_for_master(
    anchor_parent: bpy.types.Collection,
    master_coll: bpy.types.Collection,
) -> Optional[Tuple[bpy.types.Collection, bpy.types.Collection, bpy.types.Collection]]:
    """Find existing ``VFB_*`` under ``anchor_parent`` whose Source subtree holds ``master_coll``."""
    for wrap in list(anchor_parent.children):
        if getattr(wrap, "library", None) is not None:
            continue
        if not wrap.name.startswith("VFB_"):
            continue
        src_bin: Optional[bpy.types.Collection] = None
        inst_bin: Optional[bpy.types.Collection] = None
        for sub in wrap.children:
            if sub.name.endswith(TWIN_SOURCE_SUFFIX):
                src_bin = sub
            elif sub.name.endswith(TWIN_INST_SUFFIX):
                inst_bin = sub
        if src_bin is None or inst_bin is None:
            continue
        if _collection_is_or_contains(src_bin, master_coll):
            return wrap, src_bin, inst_bin
    return None


def _unique_vfb_wrapper_collection_name(safe_base: str) -> str:
    s = _safe_base(safe_base)[:40] or "Asset"
    name = f"VFB_{s}"[:62]
    j = 0
    cand = name
    while cand in bpy.data.collections:
        j += 1
        cand = f"{name}_{j:02d}"[:62]
    return cand


def _ensure_twin_wrapper_triplet(
    scene: bpy.types.Scene,
    anchor_parent: bpy.types.Collection,
    master_coll: bpy.types.Collection,
) -> Tuple[bpy.types.Collection, bpy.types.Collection, bpy.types.Collection]:
    found = _find_twin_triplet_for_master(anchor_parent, master_coll)
    if found is not None:
        return found
    safe = _safe_base(master_coll.name)
    wname = _unique_vfb_wrapper_collection_name(safe)
    wrap = bpy.data.collections.new(wname)
    src_bin = bpy.data.collections.new(f"{safe}{TWIN_SOURCE_SUFFIX}"[:62])
    inst_bin = bpy.data.collections.new(f"{safe}{TWIN_INST_SUFFIX}"[:62])
    try:
        anchor_parent.children.link(wrap)
        wrap.children.link(src_bin)
        wrap.children.link(inst_bin)
    except RuntimeError:
        pass
    _move_collection_under_parent(master_coll, src_bin, scene)
    return wrap, src_bin, inst_bin


def _collection_contains_object_recursive(
    coll: bpy.types.Collection,
    obj: bpy.types.Object,
) -> bool:
    for o in coll.objects:
        if o == obj:
            return True
    for ch in coll.children:
        if _collection_contains_object_recursive(ch, obj):
            return True
    return False


def _find_twin_triplet_for_object_root(
    anchor_parent: bpy.types.Collection,
    master_root: bpy.types.Object,
) -> Optional[Tuple[bpy.types.Collection, bpy.types.Collection, bpy.types.Collection]]:
    for wrap in list(anchor_parent.children):
        if getattr(wrap, "library", None) is not None:
            continue
        if not wrap.name.startswith("VFB_"):
            continue
        src_bin: Optional[bpy.types.Collection] = None
        inst_bin: Optional[bpy.types.Collection] = None
        for sub in wrap.children:
            if sub.name.endswith(TWIN_SOURCE_SUFFIX):
                src_bin = sub
            elif sub.name.endswith(TWIN_INST_SUFFIX):
                inst_bin = sub
        if src_bin is None or inst_bin is None:
            continue
        if _collection_contains_object_recursive(src_bin, master_root):
            return wrap, src_bin, inst_bin
    return None


def _ensure_twin_wrapper_triplet_object_root(
    scene: bpy.types.Scene,
    anchor_parent: bpy.types.Collection,
    master_root: bpy.types.Object,
) -> Tuple[bpy.types.Collection, bpy.types.Collection, bpy.types.Collection]:
    found = _find_twin_triplet_for_object_root(anchor_parent, master_root)
    if found is not None:
        return found
    safe = _safe_base(master_root.name)
    wname = _unique_vfb_wrapper_collection_name(safe)
    wrap = bpy.data.collections.new(wname)
    src_bin = bpy.data.collections.new(f"{safe}{TWIN_SOURCE_SUFFIX}"[:62])
    inst_bin = bpy.data.collections.new(f"{safe}{TWIN_INST_SUFFIX}"[:62])
    try:
        anchor_parent.children.link(wrap)
        wrap.children.link(src_bin)
        wrap.children.link(inst_bin)
    except RuntimeError:
        pass
    return wrap, src_bin, inst_bin


def step3_collection_path_place_instance_and_master(
    group: bpy.types.Collection,
    par: bpy.types.Collection,
    master_coll: bpy.types.Collection,
    empty: bpy.types.Object,
) -> None:
    """Step 3 (collection instance): empty → group.objects; master_coll → group child."""
    _move_object_exclusive_to_collection(empty, group)
    try:
        if master_coll.name in {ch.name for ch in par.children}:
            par.children.unlink(master_coll)
    except Exception:
        pass
    try:
        names = {ch.name for ch in group.children}
        if master_coll.name not in names:
            group.children.link(master_coll)
    except RuntimeError:
        pass


def _unlink_object_from_collections_except(
    obj: bpy.types.Object,
    keep: Set[bpy.types.Collection],
) -> None:
    if getattr(obj, "library", None) is not None:
        return
    for col in list(obj.users_collection):
        if col in keep:
            continue
        try:
            col.objects.unlink(obj)
        except RuntimeError:
            pass


def step3_object_path_place_instance_and_master_data_coll(
    group: bpy.types.Collection,
    master_data_coll: bpy.types.Collection,
    empty: bpy.types.Object,
    scene: bpy.types.Scene,
    *,
    instance_bin: Optional[bpy.types.Collection] = None,
) -> None:
    """Keep ``master_data_coll`` as a child of ``group`` (nested ``_DedupeObj_*`` in outliner).

    If ``instance_bin`` (TWIN), the empty is placed there while master content uses ``group`` as Source."""
    inst_target = instance_bin if instance_bin is not None else group
    _move_object_exclusive_to_collection(empty, inst_target)
    if master_data_coll.name not in bpy.data.collections:
        return
    for obj in list(master_data_coll.objects):
        _unlink_object_from_collections_except(obj, {master_data_coll})
    _move_collection_under_parent(master_data_coll, group, scene)


def step3_object_path_place_object_instance_and_master(
    group: bpy.types.Collection,
    master_root: bpy.types.Object,
    empty: bpy.types.Object,
    *,
    instance_bin: Optional[bpy.types.Collection] = None,
) -> None:
    """Step 3 (OBJECT instance empty): empty + master mesh → group; strip other collection links.

    With ``instance_bin`` (TWIN), empty goes to Instances; ``group`` is Source (master object only)."""
    inst_target = instance_bin if instance_bin is not None else group
    _move_object_exclusive_to_collection(empty, inst_target)
    if getattr(master_root, "library", None) is not None:
        return
    keep = {group}
    _link_object(group, master_root)
    _unlink_object_from_collections_except(master_root, keep)


def after_collection_instance_empty(
    scene: bpy.types.Scene,
    master_coll: bpy.types.Collection,
    empty: bpy.types.Object,
    *,
    layout: str = "LEGACY",
    twin_anchor_parent: Optional[bpy.types.Collection] = None,
) -> None:
    """
    ``layout``:
    - ``LEGACY``: one ``*_Master_and_Instances`` beside the master (existing behaviour).
    - ``TWIN``: under ``twin_anchor_parent`` (duplicate's parent before delete, e.g. collection A),
      create or reuse ``VFB_* / {{name}}_Source / {{name}}_Instances``; master collection under
      Source; instance empties only under Instances.
    """
    if layout == "TWIN" and twin_anchor_parent is not None:
        wrap, src_bin, inst_bin = _ensure_twin_wrapper_triplet(
            scene, twin_anchor_parent, master_coll
        )
        if not _collection_is_or_contains(src_bin, master_coll):
            _move_collection_under_parent(master_coll, src_bin, scene)
        _move_object_exclusive_to_collection(empty, inst_bin)
        return
    par = step1_parent_same_layer_as_master_collection(master_coll, scene)
    group = ensure_master_instances_collection(scene, master_coll.name, par)
    step3_collection_path_place_instance_and_master(group, par, master_coll, empty)


def after_object_instance_empty(
    scene: bpy.types.Scene,
    master_root: bpy.types.Object,
    empty: bpy.types.Object,
    *,
    master_data_coll: Optional[bpy.types.Collection] = None,
    layout: str = "LEGACY",
    twin_anchor_parent: Optional[bpy.types.Collection] = None,
) -> None:
    """
    ``layout`` / ``twin_anchor_parent``:
    - ``TWIN`` + anchor: under the collection that held the duplicate, reuse or create
      ``VFB_* / Name_Source / Name_Instances``; ``_DedupeObj_*`` or single master object under
      Source; OI_ empties under Instances.
    """
    if layout == "TWIN" and twin_anchor_parent is not None:
        if master_data_coll is not None:
            wrap, src_bin, inst_bin = _ensure_twin_wrapper_triplet(
                scene, twin_anchor_parent, master_data_coll
            )
            if not _collection_is_or_contains(src_bin, master_data_coll):
                _move_collection_under_parent(master_data_coll, src_bin, scene)
            step3_object_path_place_instance_and_master_data_coll(
                src_bin,
                master_data_coll,
                empty,
                scene,
                instance_bin=inst_bin,
            )
        else:
            _wrap, src_bin, inst_bin = _ensure_twin_wrapper_triplet_object_root(
                scene, twin_anchor_parent, master_root
            )
            step3_object_path_place_object_instance_and_master(
                src_bin, master_root, empty, instance_bin=inst_bin
            )
        return
    par = step1_parent_same_layer_as_master_for_object_root(master_root, scene)
    group = ensure_master_instances_collection(scene, master_root.name, par)
    if master_data_coll is not None:
        step3_object_path_place_instance_and_master_data_coll(
            group, master_data_coll, empty, scene
        )
    else:
        step3_object_path_place_object_instance_and_master(group, master_root, empty)


def iter_dedupe_source_collections():
    for c in bpy.data.collections:
        if c.name.startswith(DEDUPE_SOURCE_PREFIX):
            yield c


def dedupe_hide_folder_from_outliner(coll: bpy.types.Collection, scene: bpy.types.Scene) -> bool:
    """Remove ``_DedupeObj_*`` as a child folder only: duplicate-link its objects to the parent
    collection so they stay visible in the outliner; keep objects in ``coll`` so collection
    instances still resolve. Records parent on ``coll`` for :func:`dedupe_show_folder_in_outliner`."""
    par = _find_parent_collection(coll, scene)
    if par is None:
        return False
    for obj in list(coll.objects):
        if getattr(obj, "library", None) is not None:
            continue
        try:
            if obj.name not in par.objects:
                par.objects.link(obj)
        except RuntimeError:
            pass
    try:
        coll[DEDUPE_HIDE_PARENT_KEY] = par.name
    except Exception:
        pass
    try:
        par.children.unlink(coll)
        return True
    except RuntimeError:
        return False


def dedupe_show_folder_in_outliner(coll: bpy.types.Collection, scene: bpy.types.Scene) -> bool:
    """Reverse :func:`dedupe_hide_folder_from_outliner`, or link orphan ``_DedupeObj_*`` to scene root."""
    sc = scene.collection
    stored_name = None
    try:
        if DEDUPE_HIDE_PARENT_KEY in coll:
            stored_name = coll[DEDUPE_HIDE_PARENT_KEY]
    except Exception:
        stored_name = None

    if stored_name:
        par = bpy.data.collections.get(str(stored_name))
        if par is None:
            try:
                del coll[DEDUPE_HIDE_PARENT_KEY]
            except Exception:
                pass
            stored_name = None
        else:
            try:
                names = {ch.name for ch in par.children}
                if coll.name not in names:
                    par.children.link(coll)
                for obj in list(coll.objects):
                    if getattr(obj, "library", None) is not None:
                        continue
                    try:
                        if obj.name in par.objects:
                            par.objects.unlink(obj)
                    except RuntimeError:
                        pass
                try:
                    del coll[DEDUPE_HIDE_PARENT_KEY]
                except Exception:
                    pass
                return True
            except RuntimeError:
                return False

    if _find_parent_collection(coll, scene) is not None:
        return False
    try:
        if coll.name not in {ch.name for ch in sc.children}:
            sc.children.link(coll)
        return True
    except RuntimeError:
        return False


def dedupe_hide_all_sources(scene: bpy.types.Scene) -> int:
    n = 0
    for c in list(iter_dedupe_source_collections()):
        if dedupe_hide_folder_from_outliner(c, scene):
            n += 1
    return n


def dedupe_show_all_sources(scene: bpy.types.Scene) -> int:
    n = 0
    for c in list(iter_dedupe_source_collections()):
        if dedupe_show_folder_in_outliner(c, scene):
            n += 1
    return n
