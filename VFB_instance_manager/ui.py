from __future__ import annotations

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import Menu, Operator, Panel, PropertyGroup, UIList

from . import collection_instances
from . import core
from . import i18n
from . import instance_stats
from . import object_hierarchy
from . import object_instance_replace
from . import part_row_pack
from . import structure_match
from . import unified_results

COLOR_MASTER = (1.0, 0.0, 0.0, 1.0)
COLOR_INSTANCE = (0.55, 0.15, 0.95, 1.0)


def _tx_label(layout, text: str, **kw):
    try:
        return layout.label(text=text, translate=False, **kw)
    except TypeError:
        return layout.label(text=text, **kw)


def _tx_prop(layout, data, prop: str, **kw):
    try:
        return layout.prop(data, prop, translate=False, **kw)
    except TypeError:
        return layout.prop(data, prop, **kw)


def _tx_operator(layout, op_id: str, **kw):
    try:
        return layout.operator(op_id, translate=False, **kw)
    except TypeError:
        return layout.operator(op_id, **kw)


def _tx_menu(layout, menu_name: str, *, text: str, **kw):
    try:
        return layout.menu(menu_name, text=text, translate=False, **kw)
    except TypeError:
        return layout.menu(menu_name, text=text, **kw)


def _tx_disclosure_prop(layout, data, prop: str, **kw):
    """Fold header: chevron-style ▼ / ▶ (TRIA), not checkbox toggle."""
    opened = bool(getattr(data, prop, False))
    kw = dict(kw)
    kw.pop("toggle", None)
    kw["icon"] = "TRIA_DOWN" if opened else "TRIA_RIGHT"
    kw.setdefault("emboss", False)
    try:
        return layout.prop(data, prop, translate=False, **kw)
    except TypeError:
        return layout.prop(data, prop, **kw)


def _layout_sub_column(layout, *, gutter: float = 0.05):
    """Narrow left gutter so nested blocks read as children of the section above."""
    sp = layout.split(factor=gutter)
    sp.column()
    return sp.column()


def _unified_collection_master(scene: bpy.types.Scene, props, row) -> bpy.types.Collection | None:
    m = core.inst_mgr_pg_str(row, "master_coll_name")
    if m:
        return bpy.data.collections.get(m)
    return bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))


def _unified_object_master(scene: bpy.types.Scene, props, row) -> bpy.types.Object | None:
    m = core.inst_mgr_pg_str(row, "master_root_name")
    if m:
        o = bpy.data.objects.get(m)
        return object_hierarchy.root_object(o) if o else None
    o = bpy.data.objects.get(core.inst_mgr_pg_str(props, "ref_object_name"))
    return object_hierarchy.root_object(o) if o else None


def _equiv_counts_formatted(context: bpy.types.Context, cc: int, oc: int) -> str:
    lang = i18n.get_lang(context)
    dash = i18n.t(lang, "DASH")
    nc = str(cc) if cc >= 0 else dash
    no = str(oc) if oc >= 0 else dash
    return i18n.t(lang, "EQUIV_COUNTS_LINE").format(nc=nc, no=no)


def _resolve_master(
    scene: bpy.types.Scene,
    fingerprint: str,
    objects: list,
) -> bpy.types.Object:
    """Resolve master: mesh ID prop > overrides > first by name."""
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


def _restore_viewport_colors(scene: bpy.types.Scene) -> None:
    for item in scene.inst_mgr_color_backups:
        obj = bpy.data.objects.get(item.obj_name)
        if obj:
            obj.color = (
                item.color[0],
                item.color[1],
                item.color[2],
                item.color[3],
            )
    scene.inst_mgr_color_backups.clear()


def _backup_object_color(scene: bpy.types.Scene, obj: bpy.types.Object) -> None:
    for item in scene.inst_mgr_color_backups:
        if item.obj_name == obj.name:
            return
    b = scene.inst_mgr_color_backups.add()
    b.obj_name = obj.name
    c = obj.color
    b.color = (c[0], c[1], c[2], c[3])


def _unified_list_nonempty(scene: bpy.types.Scene) -> bool:
    return len(scene.inst_mgr_unified_results) > 0


def _unified_has_row_kind(scene: bpy.types.Scene, kind: str) -> bool:
    for row in scene.inst_mgr_unified_results:
        if row.row_kind == kind:
            return True
    return False


def _merge_show_collection_inst(scene: bpy.types.Scene, props) -> bool:
    """合并区：仅当当前分析模式会产出集合同构行且列表里确有 COLLECTION 行时显示。"""
    m = props.unified_analysis_type
    if m in ("OBJECT_DUPES", "ALL_OBJ_DUPES", "MESH_SCENE"):
        return False
    return _unified_has_row_kind(scene, "COLLECTION")


def _merge_show_object_inst(scene: bpy.types.Scene, props) -> bool:
    """合并区：仅当当前分析模式会产出物体根行且列表里确有 OBJECT_ROOT 行时显示。"""
    m = props.unified_analysis_type
    if m in ("COLLECTION_DUPES", "ALL_COLL_DUPES", "MESH_SCENE"):
        return False
    return _unified_has_row_kind(scene, "OBJECT_ROOT")


def _workflow_merge_ref_parts(props) -> bool:
    """参考集合页 + 「参考集合内零件」：合并区对应零件（简化 + 网格打包子集合）。"""
    return (
        props.reference_tab == "COLLECTION"
        and props.unified_analysis_type == "PARTS_IN_REF"
        and bool(core.inst_mgr_pg_str(props, "ref_collection_name"))
    )


def _parts_in_ref_destructive_row(row) -> bool:
    """Simplify / pack in PARTS_IN_REF may delete geometry or collections."""
    if row.row_kind in ("COLLECTION", "OBJECT_ROOT"):
        return True
    if row.row_kind == "MESH_GEOM":
        return True
    if row.row_kind == "SHARED_DATA" and getattr(row, "data_block_type", "") == "MESH":
        return True
    return False


def _link_objects_shared_data(objs: list) -> tuple:
    """Link all objects to the first object's data block by name. Returns (master, linked_count)."""
    if len(objs) < 2:
        raise RuntimeError("Not enough group members")
    sorted_objs = sorted(objs, key=lambda o: o.name)
    m = sorted_objs[0]
    data = m.data
    if data is None:
        raise RuntimeError("Master has no data block")
    linked = 0
    for obj in sorted_objs[1:]:
        if obj.data is data:
            continue
        obj.data = data
        linked += 1
    return m, linked


def _highlight_unified_row(context: bpy.types.Context, scene: bpy.types.Scene, idx: int) -> str:
    rows = scene.inst_mgr_unified_results
    if idx < 0 or idx >= len(rows):
        raise RuntimeError("Invalid row")
    row = rows[idx]
    objs = unified_results.resolve_row_objects(row)
    objs = [o for o in objs if o.name in context.view_layer.objects]
    if not objs:
        raise RuntimeError("No visible objects in row")

    _restore_viewport_colors(scene)

    if row.row_kind == "COLLECTION":
        dark, light = structure_match.GROUP_PALETTE[idx % len(structure_match.GROUP_PALETTE)]
        use = light if idx % 2 == 0 else dark
        for o in objs:
            _backup_object_color(scene, o)
            o.color = use
        return f"Collection row [{row.coll_name}]: colored {len(objs)} objects"

    if row.row_kind == "SHARED_DATA":
        master = sorted(objs, key=lambda o: o.name)[0]
        for o in objs:
            _backup_object_color(scene, o)
            o.color = COLOR_MASTER if o is master else COLOR_INSTANCE
        return (
            f"[{row.data_block_type}] shared [{row.data_block_name}]: "
            f"master [{master.name}] red, others purple, {len(objs)} objects"
        )

    if row.row_kind == "MESH_GEOM":
        master = _resolve_master(scene, row.fp_hash or "", objs)
        for o in objs:
            _backup_object_color(scene, o)
            o.color = COLOR_MASTER if o is master else COLOR_INSTANCE
        return f"Mesh dupes: master [{master.name}] red, others purple, {len(objs)} objects"

    if row.row_kind == "OBJECT_ROOT":
        dark, light = structure_match.GROUP_PALETTE[idx % len(structure_match.GROUP_PALETTE)]
        use = light if idx % 2 == 0 else dark
        for o in objs:
            _backup_object_color(scene, o)
            o.color = use
        return f"Object-root row [{row.root_object_name}]: colored {len(objs)} objects"

    raise RuntimeError(f"Unknown row kind {row.row_kind}")


# ---------------------------------------------------------------------------
# Analysis storage (one entry per group)
# ---------------------------------------------------------------------------


class INST_MGR_PG_Member(PropertyGroup):
    name: StringProperty(name="Object name")


class INST_MGR_PG_StatInstancer(PropertyGroup):
    """One collection-instance empty name for a stats row."""

    name: StringProperty(name="Instance empty")


class INST_MGR_PG_InstanceStatRow(PropertyGroup):
    row_kind: StringProperty(name="Type", default="")
    master_name: StringProperty(name="Master", default="")
    instance_count: IntProperty(name="Instance count", default=0)
    instancers: CollectionProperty(type=INST_MGR_PG_StatInstancer)


class INST_MGR_PG_ColorBackup(PropertyGroup):
    obj_name: StringProperty(name="Object")
    color: FloatVectorProperty(name="Original color", size=4, subtype="COLOR", default=(0.8, 0.8, 0.8, 1.0))


class INST_MGR_PG_MasterOverride(PropertyGroup):
    fingerprint: StringProperty(name="Fingerprint")
    master_name: StringProperty(name="Master object")


class INST_MGR_PG_Group(PropertyGroup):
    fingerprint: StringProperty(name="Fingerprint")
    scope_label: StringProperty(name="Scope", default="")
    master_name: StringProperty(name="Master object")
    count: IntProperty(name="Count", default=0)
    members: CollectionProperty(type=INST_MGR_PG_Member)


class INST_MGR_PG_UnifiedRow(PropertyGroup):
    """Unified list row: collection / object root / shared data / mesh geometry."""

    row_kind: StringProperty(name="Type", default="")
    title: StringProperty(name="Title", default="")
    coll_name: StringProperty(name="Collection name", default="")
    root_object_name: StringProperty(name="Duplicate root", default="")
    master_coll_name: StringProperty(
        name="Master collection",
        default="",
        description="No-reference mode: instance target collection for this row",
    )
    master_root_name: StringProperty(
        name="Master root object",
        default="",
        description="No-reference mode: instance target root for this row",
    )
    fp_hash: StringProperty(name="Geometry fingerprint", default="")
    data_block_name: StringProperty(name="Data-block name", default="")
    data_block_type: StringProperty(name="Data type", default="")
    members: CollectionProperty(type=INST_MGR_PG_Member)


def _clear_groups(scene: bpy.types.Scene) -> None:
    scene.inst_mgr_groups.clear()


def _add_group(
    scene: bpy.types.Scene,
    fp: str,
    objs: list,
    scope_label: str = "",
) -> None:
    g = scene.inst_mgr_groups.add()
    g.fingerprint = fp
    g.scope_label = scope_label
    sorted_objs = sorted(objs, key=lambda o: o.name)
    g.master_name = sorted_objs[0].name
    g.count = len(sorted_objs)
    for o in sorted_objs:
        m = g.members.add()
        m.name = o.name


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------


class INST_MGR_OT_Analyze(Operator):
    bl_idname = "inst_mgr.analyze"
    bl_label = "Analyze duplicate meshes"
    bl_description = "Scan by geometry fingerprint (meshes only, skip linked data)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props
        _clear_groups(scene)

        if props.scope == "PER_COLLECTION_TREE":
            rows = core.group_by_fingerprint_per_collection(context, only_mesh=props.only_mesh)
            for coll_name, fp, objs in rows:
                _add_group(scene, fp, objs, scope_label=coll_name)
        else:
            objs = core.iter_mesh_objects(context, props.scope, only_mesh=props.only_mesh)
            buckets = core.group_by_fingerprint(objs)
            for fp, group in sorted(buckets.items(), key=lambda x: -len(x[1])):
                label = props.scope if props.scope != "SELECTED" else "SELECTED"
                _add_group(scene, fp, group, scope_label=label)

        self.report({"INFO"}, f"Found {len(scene.inst_mgr_groups)} duplicate mesh groups")
        scene.inst_mgr_group_index = min(
            scene.inst_mgr_group_index,
            max(0, len(scene.inst_mgr_groups) - 1),
        )
        return {"FINISHED"}


class INST_MGR_OT_UnifiedAnalyze(Operator):
    bl_idname = "inst_mgr.unified_analyze"
    bl_label = "Analyze duplicate groups"
    bl_description = (
        "Fill the list: (1) root collections matching reference; "
        "(2) root objects matching reference; "
        "(3) parts in reference collection; (4) scene mesh geometry only; "
        "(5) no-reference: all duplicate roots by signature"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props
        if props.unified_analysis_type not in unified_results.allowed_unified_modes(
            props.reference_tab
        ):
            self.report({"WARNING"}, i18n.tr(context, "ERR_ANALYSIS_MODE"))
            return {"CANCELLED"}
        mode = props.unified_analysis_type
        if mode == "COLLECTION_DUPES":
            n, err = unified_results.analyze_collection_dupes(scene, context)
        elif mode == "OBJECT_DUPES":
            n, err = unified_results.analyze_object_dupes(scene, context)
        elif mode == "PARTS_IN_REF":
            n, err = unified_results.analyze_parts_in_ref(scene, context)
        elif mode == "ALL_COLL_DUPES":
            n, err = unified_results.analyze_all_collection_clusters(scene, context)
        elif mode == "ALL_OBJ_DUPES":
            n, err = unified_results.analyze_all_object_root_clusters(scene, context)
        else:
            n, err = unified_results.analyze_mesh_scene_legacy(scene, context)
        if err:
            self.report({"WARNING"}, err)
            return {"CANCELLED"}
        scene.inst_mgr_unified_index = min(
            scene.inst_mgr_unified_index,
            max(0, n - 1),
        )
        self.report({"INFO"}, f"Duplicate rows: {n}")
        if (
            mode == "COLLECTION_DUPES"
            and n == 0
            and props.collection_equiv_scope == "SCENE_ROOT"
        ):
            ref = bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))
            sc = scene.collection
            if ref is not None and collection_instances.find_parent_collection(ref, scene) != sc:
                self.report({"INFO"}, i18n.tr(context, "HINT_COLL_TRY_SAME_PARENT"))
        return {"FINISHED"}


class INST_MGR_OT_Clear(Operator):
    bl_idname = "inst_mgr.clear"
    bl_label = "Clear results"
    bl_options = {"REGISTER"}

    def execute(self, context):
        scene = context.scene
        _clear_groups(scene)
        scene.inst_mgr_group_index = 0
        unified_results.clear_unified(scene)
        return {"FINISHED"}


class INST_MGR_OT_SelectGroup(Operator):
    bl_idname = "inst_mgr.select_group"
    bl_label = "Select current row/group"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty(default=-1)

    def execute(self, context):
        scene = context.scene
        if _unified_list_nonempty(scene):
            idx = self.index if self.index >= 0 else scene.inst_mgr_unified_index
            rows = scene.inst_mgr_unified_results
            if idx < 0 or idx >= len(rows):
                self.report({"WARNING"}, "Invalid row index")
                return {"CANCELLED"}
            row = rows[idx]
            bpy.ops.object.select_all(action="DESELECT")
            found = 0
            active_obj = None
            for m in row.members:
                obj = bpy.data.objects.get(m.name)
                if obj and obj.name in context.view_layer.objects:
                    obj.select_set(True)
                    found += 1
                    if active_obj is None:
                        active_obj = obj
            if row.row_kind == "MESH_GEOM" and row.fp_hash:
                master = None
                objs = unified_results.resolve_row_objects(row)
                objs = [o for o in objs if o.type == "MESH"]
                if objs:
                    try:
                        master = _resolve_master(scene, row.fp_hash, objs)
                    except RuntimeError:
                        master = None
                if master and master.name in context.view_layer.objects:
                    context.view_layer.objects.active = master
                elif active_obj:
                    context.view_layer.objects.active = active_obj
            elif row.row_kind == "OBJECT_ROOT" and row.root_object_name:
                root_o = bpy.data.objects.get(row.root_object_name)
                if root_o and root_o.name in context.view_layer.objects:
                    context.view_layer.objects.active = root_o
                elif active_obj:
                    context.view_layer.objects.active = active_obj
            elif active_obj:
                context.view_layer.objects.active = active_obj
            self.report({"INFO"}, f"Selected {found} object(s)")
            return {"FINISHED"}

        idx = self.index if self.index >= 0 else scene.inst_mgr_group_index
        if idx < 0 or idx >= len(scene.inst_mgr_groups):
            self.report({"WARNING"}, "Invalid group index")
            return {"CANCELLED"}
        grp = scene.inst_mgr_groups[idx]
        bpy.ops.object.select_all(action="DESELECT")
        found = 0
        for m in grp.members:
            obj = bpy.data.objects.get(m.name)
            if obj and obj.name in context.view_layer.objects:
                obj.select_set(True)
                found += 1
        if found:
            last = bpy.data.objects.get(grp.master_name)
            if last and last.name in context.view_layer.objects:
                context.view_layer.objects.active = last
        self.report({"INFO"}, f"Selected {found} object(s)")
        return {"FINISHED"}


class INST_MGR_OT_SelectBatch(Operator):
    bl_idname = "inst_mgr.select_batch"
    bl_label = "Select batch of rows/groups"
    bl_description = "From current index, select members of the next N rows or groups"
    bl_options = {"REGISTER", "UNDO"}

    count: IntProperty(name="Count", default=10, min=1, max=500)

    def execute(self, context):
        scene = context.scene
        if _unified_list_nonempty(scene):
            start = scene.inst_mgr_unified_index
            rows = scene.inst_mgr_unified_results
            bpy.ops.object.select_all(action="DESELECT")
            total = 0
            for i in range(start, min(start + self.count, len(rows))):
                row = rows[i]
                for m in row.members:
                    obj = bpy.data.objects.get(m.name)
                    if obj and obj.name in context.view_layer.objects:
                        obj.select_set(True)
                        total += 1
            self.report(
                {"INFO"},
                f"Selected {total} object(s) ({min(self.count, len(rows) - start)} row(s))",
            )
            return {"FINISHED"}

        start = scene.inst_mgr_group_index
        groups = scene.inst_mgr_groups
        if not groups:
            self.report({"WARNING"}, "Run analyze first")
            return {"CANCELLED"}
        bpy.ops.object.select_all(action="DESELECT")
        total = 0
        for i in range(start, min(start + self.count, len(groups))):
            grp = groups[i]
            for m in grp.members:
                obj = bpy.data.objects.get(m.name)
                if obj and obj.name in context.view_layer.objects:
                    obj.select_set(True)
                    total += 1
        self.report({"INFO"}, f"Selected {total} object(s) ({min(self.count, len(groups) - start)} group(s))")
        return {"FINISHED"}


class INST_MGR_OT_IndexDelta(Operator):
    bl_idname = "inst_mgr.index_delta"
    bl_label = "Cycle row/group index"
    bl_options = {"REGISTER"}

    delta: IntProperty(default=1)

    def execute(self, context):
        scene = context.scene
        if _unified_list_nonempty(scene):
            n = len(scene.inst_mgr_unified_results)
            if n == 0:
                return {"CANCELLED"}
            scene.inst_mgr_unified_index = (scene.inst_mgr_unified_index + self.delta) % n
            return {"FINISHED"}
        n = len(scene.inst_mgr_groups)
        if n == 0:
            return {"CANCELLED"}
        scene.inst_mgr_group_index = (scene.inst_mgr_group_index + self.delta) % n
        return {"FINISHED"}


class INST_MGR_OT_MergeActiveGroup(Operator):
    bl_idname = "inst_mgr.merge_active_group"
    bl_label = "Simplify active row (mesh / shared data / instance)"
    bl_description = (
        "Reference parts mode: collection dupes → collection instance + group next to ref; "
        "mesh rows → object instances in a sibling group; other shared data → link data block. "
        "Other modes: collection/object row → instance; mesh → link data"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        scene = context.scene
        if _unified_list_nonempty(scene):
            idx = scene.inst_mgr_unified_index
            if 0 <= idx < len(scene.inst_mgr_unified_results):
                row = scene.inst_mgr_unified_results[idx]
                props = scene.inst_mgr_props
                if _workflow_merge_ref_parts(props) and _parts_in_ref_destructive_row(row):
                    return context.window_manager.invoke_confirm(self, event)
                rk = row.row_kind
                if rk in ("COLLECTION", "OBJECT_ROOT"):
                    return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props

        if _unified_list_nonempty(scene):
            idx = scene.inst_mgr_unified_index
            rows = scene.inst_mgr_unified_results
            if idx < 0 or idx >= len(rows):
                self.report({"WARNING"}, "Invalid row")
                return {"CANCELLED"}
            row = rows[idx]

            if _workflow_merge_ref_parts(props):
                ref_coll = bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))
                if ref_coll is None:
                    self.report({"WARNING"}, i18n.tr(context, "ERR_NO_REF_COLL"))
                    return {"CANCELLED"}
                if row.row_kind == "COLLECTION":
                    master_coll = _unified_collection_master(scene, props, row)
                    dup = bpy.data.collections.get(row.coll_name)
                    if master_coll is None or dup is None:
                        self.report({"WARNING"}, "Missing master collection or row collection")
                        return {"CANCELLED"}
                    try:
                        collection_instances.replace_duplicate_collection_with_instance(
                            master_coll,
                            dup,
                            scene=scene,
                            auto_organize_master_instances=True,
                        )
                    except Exception as e:
                        self.report({"ERROR"}, str(e))
                        return {"CANCELLED"}
                    self.report({"INFO"}, f"Replaced [{dup.name}] with collection instance of [{master_coll.name}]")
                    return {"FINISHED"}
                if row.row_kind == "SHARED_DATA":
                    objs = unified_results.resolve_row_objects(row)
                    objs = [o for o in objs if o.data is not None]
                    if len(objs) < 2:
                        self.report({"WARNING"}, "Not enough members or non-data objects")
                        return {"CANCELLED"}
                    if getattr(row, "data_block_type", "") == "MESH":
                        if not part_row_pack.row_supports_mesh_pack(row):
                            self.report({"WARNING"}, i18n.tr(context, "ERR_PACK_ROW_KIND"))
                            return {"CANCELLED"}
                        ok, msg = part_row_pack.pack_mesh_row_into_subcollection_collection_instance(
                            scene, ref_coll, row, idx
                        )
                        if not ok:
                            self.report({"WARNING"}, i18n.tr(context, msg))
                            return {"CANCELLED"}
                        self.report(
                            {"INFO"},
                            i18n.tr(context, "INFO_PACK_ROW").format(name=msg),
                        )
                        return {"FINISHED"}
                    try:
                        master, linked = _link_objects_shared_data(objs)
                    except Exception as e:
                        self.report({"ERROR"}, str(e))
                        return {"CANCELLED"}
                    self.report(
                        {"INFO"},
                        f"Merged shared data: master [{master.name}], relinked {linked} object(s)",
                    )
                    return {"FINISHED"}
                if row.row_kind == "MESH_GEOM":
                    ok, msg = part_row_pack.pack_mesh_row_into_subcollection_collection_instance(
                        scene, ref_coll, row, idx
                    )
                    if not ok:
                        self.report({"WARNING"}, i18n.tr(context, msg))
                        return {"CANCELLED"}
                    self.report(
                        {"INFO"},
                        i18n.tr(context, "INFO_PACK_ROW").format(name=msg),
                    )
                    return {"FINISHED"}
                self.report({"WARNING"}, "Unknown row type")
                return {"CANCELLED"}

            if row.row_kind == "COLLECTION":
                ref = _unified_collection_master(scene, props, row)
                dup = bpy.data.collections.get(row.coll_name)
                if ref is None or dup is None:
                    self.report({"WARNING"}, "Missing master collection or row collection")
                    return {"CANCELLED"}
                try:
                    collection_instances.replace_duplicate_collection_with_instance(
                        ref,
                        dup,
                        scene=scene,
                        auto_organize_master_instances=props.auto_organize_master_instances,
                    )
                except Exception as e:
                    self.report({"ERROR"}, str(e))
                    return {"CANCELLED"}
                self.report({"INFO"}, f"Replaced [{dup.name}] with collection instance of [{ref.name}]")
                return {"FINISHED"}

            if row.row_kind == "OBJECT_ROOT":
                mo = _unified_object_master(scene, props, row)
                dup = bpy.data.objects.get(row.root_object_name)
                if mo is None or dup is None:
                    self.report({"WARNING"}, "Missing master root or duplicate root")
                    return {"CANCELLED"}
                try:
                    object_instance_replace.replace_duplicate_object_root_with_instance(
                        mo,
                        object_hierarchy.root_object(dup),
                        scene=scene,
                        auto_organize_master_instances=props.auto_organize_master_instances,
                    )
                except Exception as e:
                    self.report({"ERROR"}, str(e))
                    return {"CANCELLED"}
                self.report(
                    {"INFO"},
                    f"Replaced [{row.root_object_name}] with collection instance of [{object_hierarchy.root_object(mo).name}]",
                )
                return {"FINISHED"}

            if row.row_kind == "SHARED_DATA":
                objs = unified_results.resolve_row_objects(row)
                objs = [o for o in objs if o.data is not None]
                if len(objs) < 2:
                    self.report({"WARNING"}, "Not enough members or non-data objects")
                    return {"CANCELLED"}
                try:
                    master, linked = _link_objects_shared_data(objs)
                except Exception as e:
                    self.report({"ERROR"}, str(e))
                    return {"CANCELLED"}
                self.report(
                    {"INFO"},
                    f"Merged shared data: master [{master.name}], relinked {linked} object(s)",
                )
                return {"FINISHED"}

            if row.row_kind == "MESH_GEOM":
                objs = []
                for m in row.members:
                    obj = bpy.data.objects.get(m.name)
                    if obj and obj.type == "MESH":
                        objs.append(obj)
                if len(objs) < 2:
                    self.report({"WARNING"}, "Not enough group members")
                    return {"CANCELLED"}
                master = _resolve_master(scene, row.fp_hash, objs)
                master, linked = core.merge_group_to_linked_data(objs, master=master)
                self.report({"INFO"}, f"Linked mesh: master [{master.name}], relinked {linked}")
                return {"FINISHED"}

            self.report({"WARNING"}, "Unknown row type")
            return {"CANCELLED"}

        idx = scene.inst_mgr_group_index
        if idx < 0 or idx >= len(scene.inst_mgr_groups):
            self.report({"WARNING"}, "Invalid group")
            return {"CANCELLED"}
        grp = scene.inst_mgr_groups[idx]
        objs = []
        for m in grp.members:
            obj = bpy.data.objects.get(m.name)
            if obj and obj.type == "MESH":
                objs.append(obj)
        if len(objs) < 2:
            self.report({"WARNING"}, "Not enough group members")
            return {"CANCELLED"}
        master = _resolve_master(scene, grp.fingerprint, objs)
        master, linked = core.merge_group_to_linked_data(objs, master=master)
        self.report({"INFO"}, f"Linked mesh: master [{master.name}], relinked {linked}")
        return {"FINISHED"}


class INST_MGR_OT_MergeAll(Operator):
    bl_idname = "inst_mgr.merge_all"
    bl_label = "Simplify / instance all rows"
    bl_description = (
        "Reference parts mode: per row use collection instance or mesh object-instances "
        "(sibling groups) or link non-mesh shared data. Other modes: mesh → link data; "
        "collection / object-root → instance (destructive)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        scene = context.scene
        if _unified_list_nonempty(scene):
            props = scene.inst_mgr_props
            if _workflow_merge_ref_parts(props):
                for row in scene.inst_mgr_unified_results:
                    if _parts_in_ref_destructive_row(row):
                        return context.window_manager.invoke_confirm(self, event)
            else:
                for row in scene.inst_mgr_unified_results:
                    if row.row_kind in ("COLLECTION", "OBJECT_ROOT"):
                        return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props

        if _unified_list_nonempty(scene):
            total_linked = 0
            total_coll = 0
            total_objroot = 0
            total_mesh_pack = 0
            coll_err = 0
            obj_err = 0
            pack_err = 0
            ref_coll = bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))
            parts_mode = _workflow_merge_ref_parts(props) and ref_coll is not None

            for i, row in enumerate(scene.inst_mgr_unified_results):
                if parts_mode:
                    if row.row_kind == "COLLECTION":
                        master_coll = _unified_collection_master(scene, props, row)
                        dup = bpy.data.collections.get(row.coll_name)
                        if master_coll is None or dup is None:
                            coll_err += 1
                            continue
                        try:
                            collection_instances.replace_duplicate_collection_with_instance(
                                master_coll,
                                dup,
                                scene=scene,
                                auto_organize_master_instances=True,
                            )
                            total_coll += 1
                        except Exception:
                            coll_err += 1
                        continue
                    if row.row_kind == "SHARED_DATA":
                        objs = unified_results.resolve_row_objects(row)
                        objs = [o for o in objs if o.data is not None]
                        if len(objs) < 2:
                            continue
                        if getattr(row, "data_block_type", "") == "MESH":
                            if not part_row_pack.row_supports_mesh_pack(row):
                                pack_err += 1
                                continue
                            ok, _msg = part_row_pack.pack_mesh_row_into_subcollection_collection_instance(
                                scene, ref_coll, row, i
                            )
                            if ok:
                                total_mesh_pack += 1
                            else:
                                pack_err += 1
                            continue
                        try:
                            _, linked = _link_objects_shared_data(objs)
                            total_linked += linked
                        except Exception:
                            pass
                        continue
                    if row.row_kind == "MESH_GEOM":
                        ok, _msg = part_row_pack.pack_mesh_row_into_subcollection_collection_instance(
                            scene, ref_coll, row, i
                        )
                        if ok:
                            total_mesh_pack += 1
                        else:
                            pack_err += 1
                        continue

                if row.row_kind == "COLLECTION":
                    master_coll = _unified_collection_master(scene, props, row)
                    dup = bpy.data.collections.get(row.coll_name)
                    if master_coll is None or dup is None:
                        coll_err += 1
                        continue
                    try:
                        collection_instances.replace_duplicate_collection_with_instance(
                            master_coll,
                            dup,
                            scene=scene,
                            auto_organize_master_instances=props.auto_organize_master_instances,
                        )
                        total_coll += 1
                    except Exception:
                        coll_err += 1
                    continue
                if row.row_kind == "OBJECT_ROOT":
                    mo = _unified_object_master(scene, props, row)
                    dup = bpy.data.objects.get(row.root_object_name)
                    if mo is None or dup is None:
                        obj_err += 1
                        continue
                    try:
                        object_instance_replace.replace_duplicate_object_root_with_instance(
                            mo,
                            object_hierarchy.root_object(dup),
                            scene=scene,
                            auto_organize_master_instances=props.auto_organize_master_instances,
                        )
                        total_objroot += 1
                    except Exception:
                        obj_err += 1
                    continue
                if row.row_kind == "SHARED_DATA":
                    objs = unified_results.resolve_row_objects(row)
                    objs = [o for o in objs if o.data is not None]
                    if len(objs) < 2:
                        continue
                    try:
                        _, linked = _link_objects_shared_data(objs)
                        total_linked += linked
                    except Exception:
                        pass
                    continue
                if row.row_kind == "MESH_GEOM":
                    objs = []
                    for m in row.members:
                        obj = bpy.data.objects.get(m.name)
                        if obj and obj.type == "MESH":
                            objs.append(obj)
                    if len(objs) < 2:
                        continue
                    master = _resolve_master(scene, row.fp_hash, objs)
                    _, linked = core.merge_group_to_linked_data(objs, master=master)
                    total_linked += linked
            if parts_mode:
                msg = (
                    f"Done (parts mode): {total_coll} collection row(s), "
                    f"{total_mesh_pack} mesh pack(s), {total_linked} shared relink(s)"
                )
                if coll_err or obj_err or pack_err:
                    msg += f"; errors: coll {coll_err}, roots {obj_err}, mesh pack {pack_err}"
            else:
                msg = (
                    f"Done: instanced {total_coll} coll. / {total_objroot} root row(s); "
                    f"relinked {total_linked} mesh/shared op(s)"
                )
                if coll_err or obj_err:
                    msg += f"; skipped/errors: coll {coll_err}, roots {obj_err}"
            self.report({"INFO"}, msg)
            return {"FINISHED"}

        groups = list(scene.inst_mgr_groups)
        if not groups:
            self.report({"WARNING"}, "Run analyze first")
            return {"CANCELLED"}
        total_linked = 0
        for grp in groups:
            objs = []
            for m in grp.members:
                obj = bpy.data.objects.get(m.name)
                if obj and obj.type == "MESH":
                    objs.append(obj)
            if len(objs) < 2:
                continue
            master = _resolve_master(scene, grp.fingerprint, objs)
            _, linked = core.merge_group_to_linked_data(objs, master=master)
            total_linked += linked
        self.report({"INFO"}, f"All groups done, relinked {total_linked} object(s)")
        return {"FINISHED"}


def _is_stale_vfb_instance_empty(obj: bpy.types.Object) -> bool:
    """CI_/OI_/VfbCI_ empties that are not a valid collection instance (shell leftovers)."""
    if obj.type != "EMPTY":
        return False
    if getattr(obj, "library", None) is not None:
        return False
    n = obj.name
    if not (n.startswith("CI_") or n.startswith("OI_") or n.startswith("VfbCI_")):
        return False
    if (
        getattr(obj, "instance_type", "NONE") == "COLLECTION"
        and getattr(obj, "instance_collection", None) is not None
    ):
        return False
    return True


class INST_MGR_OT_RemoveStaleInstanceEmpties(Operator):
    bl_idname = "inst_mgr.remove_stale_instance_empties"
    bl_label = "Remove stale instance empties"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def description(cls, context, properties):
        return i18n.tr(context, "OP_PURGE_STALE_EMPTY_TIP")

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        to_remove = [o for o in bpy.data.objects if _is_stale_vfb_instance_empty(o)]
        if not to_remove:
            self.report({"WARNING"}, i18n.tr(context, "WARN_PURGE_STALE_EMPTY_NONE"))
            return {"CANCELLED"}
        for o in to_remove:
            bpy.data.objects.remove(o, do_unlink=True)
        self.report(
            {"INFO"},
            i18n.tr(context, "INFO_PURGE_STALE_EMPTY").format(n=len(to_remove)),
        )
        return {"FINISHED"}


class INST_MGR_OT_PurgeOrphans(Operator):
    bl_idname = "inst_mgr.purge_orphans"
    bl_label = "Purge unused data"
    bl_description = "Remove unused mesh data etc. (careful)"
    bl_options = {"REGISTER"}

    def execute(self, context):
        bpy.ops.outliner.orphans_purge(
            do_local_ids=True,
            do_linked_ids=False,
            do_recursive=True,
        )
        self.report({"INFO"}, "Ran orphans_purge")
        return {"FINISHED"}


class INST_MGR_OT_HighlightLinked(Operator):
    bl_idname = "inst_mgr.highlight_linked"
    bl_label = "Highlight linked (viewport color)"
    bl_description = (
        "From active mesh, same fingerprint or same mesh data; "
        "master red, others purple (Solid: Object color)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "Select a mesh object first")
            return {"CANCELLED"}
        fp, matches = core.objects_with_same_fingerprint(scene, obj)
        if not matches:
            self.report({"WARNING"}, "No linked meshes found")
            return {"CANCELLED"}

        _restore_viewport_colors(scene)

        master = _resolve_master(scene, fp or "", matches)
        for o in matches:
            if o.name not in context.view_layer.objects:
                continue
            b = scene.inst_mgr_color_backups.add()
            b.obj_name = o.name
            col = o.color
            b.color = (col[0], col[1], col[2], col[3])
            o.color = COLOR_MASTER if o is master else COLOR_INSTANCE

        self.report(
            {"INFO"},
            f"Highlighted {len(matches)}: master [{master.name}] (red), copies (purple). Solid Object color.",
        )
        return {"FINISHED"}


class INST_MGR_OT_HighlightCurrentRow(Operator):
    bl_idname = "inst_mgr.highlight_current_row"
    bl_label = "Highlight current row (viewport color)"
    bl_description = (
        "Color current row: collection / shared data (incl. lights) / mesh. "
        "Solid: Object color."
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        if not _unified_list_nonempty(scene):
            self.report({"WARNING"}, "Run Analyze duplicate groups first")
            return {"CANCELLED"}
        idx = scene.inst_mgr_unified_index
        try:
            msg = _highlight_unified_row(context, scene, idx)
        except RuntimeError as e:
            self.report({"WARNING"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class INST_MGR_OT_MergeAllCollectionRows(Operator):
    bl_idname = "inst_mgr.merge_all_collection_rows"
    bl_label = "Instance all: collection rows in list"
    bl_description = (
        "Each collection row: instance empty of row master (or reference) "
        "(destructive, save first)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props
        n = 0
        for row in list(scene.inst_mgr_unified_results):
            if row.row_kind != "COLLECTION":
                continue
            master_coll = _unified_collection_master(scene, props, row)
            dup = bpy.data.collections.get(row.coll_name)
            if master_coll is None or dup is None:
                continue
            try:
                collection_instances.replace_duplicate_collection_with_instance(
                    master_coll,
                    dup,
                    scene=scene,
                    auto_organize_master_instances=props.auto_organize_master_instances,
                )
                n += 1
            except Exception as e:
                self.report({"ERROR"}, f"{row.coll_name}: {e}")
                return {"CANCELLED"}
        if n == 0:
            self.report({"WARNING"}, "No collection rows with valid master/dup")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Instanced {n} collection row(s)")
        return {"FINISHED"}


class INST_MGR_OT_MergeAllObjectRootRows(Operator):
    bl_idname = "inst_mgr.merge_all_object_root_rows"
    bl_label = "Instance all: object-root rows in list"
    bl_description = (
        "Each object-root row: instance of row master root (or reference) "
        "(destructive, save first)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props
        n = 0
        for row in list(scene.inst_mgr_unified_results):
            if row.row_kind != "OBJECT_ROOT":
                continue
            mo = _unified_object_master(scene, props, row)
            dup = bpy.data.objects.get(row.root_object_name)
            if mo is None or dup is None:
                continue
            try:
                object_instance_replace.replace_duplicate_object_root_with_instance(
                    mo,
                    dup,
                    scene=scene,
                    auto_organize_master_instances=props.auto_organize_master_instances,
                )
                n += 1
            except Exception as e:
                self.report({"ERROR"}, f"{row.root_object_name}: {e}")
                return {"CANCELLED"}
        if n == 0:
            self.report({"WARNING"}, "No object-root rows with valid master/dup")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Instanced {n} object-root row(s)")
        return {"FINISHED"}


def _pack_current_mesh_row_coll_inst_exec(op, context):
    scene = context.scene
    props = scene.inst_mgr_props
    ref = bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))
    if ref is None:
        op.report({"WARNING"}, i18n.tr(context, "ERR_NO_REF_COLL"))
        return {"CANCELLED"}
    rows = scene.inst_mgr_unified_results
    idx = scene.inst_mgr_unified_index
    if idx < 0 or idx >= len(rows):
        op.report({"WARNING"}, "Invalid row index")
        return {"CANCELLED"}
    row = rows[idx]
    ok, msg = part_row_pack.pack_mesh_row_into_subcollection_collection_instance(
        scene, ref, row, idx
    )
    if not ok:
        op.report({"WARNING"}, i18n.tr(context, msg))
        return {"CANCELLED"}
    op.report({"INFO"}, i18n.tr(context, "INFO_PACK_ROW").format(name=msg))
    return {"FINISHED"}


def _pack_all_mesh_rows_coll_inst_exec(op, context):
    scene = context.scene
    props = scene.inst_mgr_props
    ref = bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))
    if ref is None:
        op.report({"WARNING"}, i18n.tr(context, "ERR_NO_REF_COLL"))
        return {"CANCELLED"}
    n, err = part_row_pack.pack_all_mesh_part_rows_collection_instance(scene, ref)
    if err is not None:
        if n == 0:
            op.report({"WARNING"}, i18n.tr(context, err))
            return {"CANCELLED"}
        op.report(
            {"WARNING"},
            i18n.tr(context, "ERR_PACK_PARTIAL").format(
                ok=n,
                why=i18n.tr(context, err),
            ),
        )
        return {"FINISHED"}
    op.report({"INFO"}, i18n.tr(context, "INFO_PACK_ALL").format(n=n))
    return {"FINISHED"}


class INST_MGR_OT_PackCurrentPartRowCollInst(Operator):
    bl_idname = "inst_mgr.pack_current_part_row_coll_inst"
    bl_label = "Pack current mesh row (collection instance)"
    bl_description = (
        "Mesh / shared-mesh row: child group under reference with _DedupeObj_* source and "
        "collection-instanced empties (works without OBJECT instancing on empties)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        return _pack_current_mesh_row_coll_inst_exec(self, context)


class INST_MGR_OT_PackAllPartRowsCollInst(Operator):
    bl_idname = "inst_mgr.pack_all_part_rows_coll_inst"
    bl_label = "Pack all mesh rows (collection instance)"
    bl_description = (
        "Each mesh row: child group under reference; collection-instance empties to _DedupeObj_*"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        return _pack_all_mesh_rows_coll_inst_exec(self, context)


class INST_MGR_OT_ClearHighlight(Operator):
    bl_idname = "inst_mgr.clear_highlight"
    bl_label = "Clear highlight"
    bl_description = "Restore colors from last highlight"
    bl_options = {"REGISTER"}

    def execute(self, context):
        _restore_viewport_colors(context.scene)
        return {"FINISHED"}


class INST_MGR_OT_SetMaster(Operator):
    bl_idname = "inst_mgr.set_master"
    bl_label = "Set as master object"
    bl_description = "Set active mesh as master for this fingerprint group"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if obj is None or obj.type != "MESH" or obj.data is None:
            self.report({"WARNING"}, "Select a mesh object as master")
            return {"CANCELLED"}

        fp = None
        if _unified_list_nonempty(scene):
            idx = scene.inst_mgr_unified_index
            if 0 <= idx < len(scene.inst_mgr_unified_results):
                row = scene.inst_mgr_unified_results[idx]
                if row.row_kind == "MESH_GEOM" and row.fp_hash:
                    names = {m.name for m in row.members}
                    if obj.name in names:
                        fp = row.fp_hash
        if fp is None:
            fp = core.mesh_fingerprint(obj.data)
        if not fp:
            self.report({"WARNING"}, "Could not compute mesh fingerprint")
            return {"CANCELLED"}

        found = False
        for ovr in scene.inst_mgr_master_overrides:
            if ovr.fingerprint == fp:
                ovr.master_name = obj.name
                found = True
                break
        if not found:
            ovr = scene.inst_mgr_master_overrides.add()
            ovr.fingerprint = fp
            ovr.master_name = obj.name

        users = core.objects_sharing_mesh_data(obj.data)
        if len(users) > 1 and obj.data:
            try:
                obj.data[core.MASTER_ID_PROP] = obj.name
            except Exception:
                pass

        self.report({"INFO"}, f"Recorded master [{obj.name}] (fp {fp[:8]}…)")
        return {"FINISHED"}


class INST_MGR_OT_CollectionAutoInstances(Operator):
    bl_idname = "inst_mgr.collection_auto_instances"
    bl_label = "Auto: duplicate asset collections → instances"
    bl_description = (
        "Under scene root, find sibling collections Base.NNN; keep lowest N as master, "
        "replace others with instance empties (save first)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        props = context.scene.inst_mgr_props
        try:
            replaced, _empties = collection_instances.auto_replace_all_duplicate_asset_collections(
                only_direct_child_of_scene_root=props.coll_inst_only_scene_root_children,
            )
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        if replaced == 0:
            self.report({"INFO"}, "No matching duplicates (expect Base.001 naming under scene root per settings)")
        else:
            self.report({"INFO"}, f"Replaced {replaced} duplicate collection(s) with instance empties")
        return {"FINISHED"}


class INST_MGR_OT_CollectionReplacePair(Operator):
    bl_idname = "inst_mgr.collection_replace_pair"
    bl_label = "Named master + duplicate → collection instance"
    bl_description = "Delete duplicate collection subtree, instance empty of master under same parent"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        props = context.scene.inst_mgr_props
        mname = core.inst_mgr_pg_str(props, "coll_inst_master_name")
        dname = core.inst_mgr_pg_str(props, "coll_inst_dup_name")
        if not mname or not dname:
            self.report({"WARNING"}, "Enter master and duplicate collection names")
            return {"CANCELLED"}
        master = bpy.data.collections.get(mname)
        dup = bpy.data.collections.get(dname)
        if master is None or dup is None:
            self.report({"WARNING"}, "Collection not found (name must match outliner)")
            return {"CANCELLED"}
        try:
            scene = context.scene
            props = scene.inst_mgr_props
            empty = collection_instances.replace_duplicate_collection_with_instance(
                master,
                dup,
                scene=scene,
                auto_organize_master_instances=props.auto_organize_master_instances,
            )
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Created instance [{empty.name}] → [{master.name}]")
        return {"FINISHED"}


def _update_equiv_collection_count(scene: bpy.types.Scene) -> None:
    props = scene.inst_mgr_props
    if props.reference_tab == "NONE":
        groups = structure_match.cluster_root_collections_by_signature(
            props.collection_equiv_scope,
            scene=scene,
        )
        scene.inst_mgr_equiv_collection_count = sum(max(0, len(g) - 1) for g in groups)
        return
    ref = bpy.data.collections.get(core.inst_mgr_pg_str(props, "ref_collection_name"))
    if ref is None:
        scene.inst_mgr_equiv_collection_count = -1
        return
    scene.inst_mgr_equiv_collection_count = len(
        structure_match.find_equivalent_root_collections(
            ref,
            scene=scene,
            mode=props.collection_equiv_scope,
        )
    )


def _update_equiv_object_count(scene: bpy.types.Scene) -> None:
    props = scene.inst_mgr_props
    if props.reference_tab == "NONE":
        groups = object_hierarchy.cluster_root_objects_by_signature(
            scene,
            props.collection_equiv_scope,
        )
        scene.inst_mgr_equiv_object_count = sum(max(0, len(g) - 1) for g in groups)
        return
    obj = bpy.data.objects.get(core.inst_mgr_pg_str(props, "ref_object_name"))
    if obj is None:
        scene.inst_mgr_equiv_object_count = -1
        return
    root = object_hierarchy.root_object(obj)
    scene.inst_mgr_equiv_object_count = len(
        object_hierarchy.find_equivalent_root_objects(
            root,
            scene,
            props.collection_equiv_scope,
        )
    )


def _refresh_all_equiv_counts(scene: bpy.types.Scene) -> None:
    _update_equiv_collection_count(scene)
    _update_equiv_object_count(scene)


def _scene_props_equiv_scope_update(self, context):
    scene = getattr(context, "scene", None)
    if scene is not None:
        _refresh_all_equiv_counts(scene)


class INST_MGR_OT_SetRefCollection(Operator):
    bl_idname = "inst_mgr.set_ref_collection"
    bl_label = "Set reference collection (outliner)"
    bl_description = (
        "Click a collection line in the outliner (active collection), "
        "then press to set name and refresh counts"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        c = context.collection
        if c is None:
            self.report({"WARNING"}, "Select a collection line in outliner (not only objects inside)")
            return {"CANCELLED"}
        scene = context.scene
        scene.inst_mgr_props.ref_collection_name = c.name
        _refresh_all_equiv_counts(scene)
        n = scene.inst_mgr_equiv_collection_count
        info = structure_match.summarize_collection_structure(c, scene=scene)
        oc = int(info["object_count"])
        self.report(
            {"INFO"},
            f"Reference [{c.name}] · subtree objects {oc} · other equiv. collections {max(0, n)} (scope)",
        )
        return {"FINISHED"}


class INST_MGR_OT_RefreshCollectionDupCount(Operator):
    bl_idname = "inst_mgr.refresh_collection_dup_count"
    bl_label = "Refresh equivalent counts (collections + objects)"
    bl_description = "Update both stats from reference names and search scope"
    bl_options = {"REGISTER"}

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props
        _refresh_all_equiv_counts(scene)
        nc = scene.inst_mgr_equiv_collection_count
        no = scene.inst_mgr_equiv_object_count
        self.report(
            {"INFO"},
            f"Other equiv. collections: {nc if nc >= 0 else '-'}  |  Other equiv. roots: {no if no >= 0 else '-'}",
        )
        return {"FINISHED"}


class INST_MGR_OT_SetRefObject(Operator):
    bl_idname = "inst_mgr.set_ref_object"
    bl_label = "Set reference object (active → root)"
    bl_description = "Active object in 3D or outliner; walks parents to root"
    bl_options = {"REGISTER"}

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({"WARNING"}, "Select an object (asset root or any child)")
            return {"CANCELLED"}
        scene = context.scene
        root = object_hierarchy.root_object(obj)
        scene.inst_mgr_props.ref_object_name = root.name
        _refresh_all_equiv_counts(scene)
        n = scene.inst_mgr_equiv_object_count
        info = object_hierarchy.summarize_object_subtree(root, scene)
        oc = int(info["object_count"])
        self.report(
            {"INFO"},
            f"Reference root [{root.name}] · subtree {oc} object(s) · other equiv. roots {max(0, n)} (scope)",
        )
        return {"FINISHED"}


class INST_MGR_OT_StructureHighlight(Operator):
    bl_idname = "inst_mgr.structure_highlight"
    bl_label = "Color by structure match"
    bl_description = (
        "Reference objects red; each equivalent collection gets a palette; "
        "instance empties light. Candidates follow Search scope"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props
        ref_name = core.inst_mgr_pg_str(props, "ref_collection_name")
        ref = bpy.data.collections.get(ref_name) if ref_name else context.collection
        if ref is None:
            self.report({"WARNING"}, "Set reference collection name or pick from outliner")
            return {"CANCELLED"}

        others = structure_match.find_equivalent_root_collections(
            ref,
            scene=scene,
            mode=props.collection_equiv_scope,
        )

        _restore_viewport_colors(scene)

        for o in structure_match.iter_objects_in_collection_deep(ref):
            if getattr(o, "library", None) is not None:
                continue
            _backup_object_color(scene, o)
            o.color = structure_match.REF_COLOR

        for gi, root in enumerate(others):
            dark, light = structure_match.GROUP_PALETTE[gi % len(structure_match.GROUP_PALETTE)]
            for o in structure_match.iter_objects_in_collection_deep(root):
                if getattr(o, "library", None) is not None:
                    continue
                _backup_object_color(scene, o)
                o.color = light if structure_match.is_collection_instance_empty(o) else dark

        scene.inst_mgr_equiv_collection_count = len(others)
        self.report(
            {"INFO"},
            f"[{ref.name}] red; {len(others)} equivalent root collection(s) colored.",
        )
        return {"FINISHED"}


class INST_MGR_OT_StructureRepoint(Operator):
    bl_idname = "inst_mgr.structure_repoint"
    bl_label = "Equivalent roots → instance to reference"
    bl_description = (
        "Each non-reference matching root: delete subtree, instance empty of reference "
        "(destructive, save first)"
    )
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        props = context.scene.inst_mgr_props
        ref_name = core.inst_mgr_pg_str(props, "ref_collection_name")
        ref = bpy.data.collections.get(ref_name) if ref_name else context.collection
        if ref is None:
            self.report({"WARNING"}, "Reference collection not found")
            return {"CANCELLED"}

        others = structure_match.find_equivalent_root_collections(
            ref,
            scene=context.scene,
            mode=props.collection_equiv_scope,
        )
        scene = context.scene
        n = 0
        for root in others:
            try:
                collection_instances.replace_duplicate_collection_with_instance(
                    ref,
                    root,
                    scene=scene,
                    auto_organize_master_instances=props.auto_organize_master_instances,
                )
                n += 1
            except Exception as e:
                self.report({"ERROR"}, f"{root.name}: {e}")
                return {"CANCELLED"}
        self.report({"INFO"}, f"Replaced {n} equivalent root collection(s) with instances of [{ref.name}]")
        return {"FINISHED"}


class INST_MGR_OT_RefreshInstanceStats(Operator):
    bl_idname = "inst_mgr.refresh_instance_stats"
    bl_label = "Refresh instance statistics"
    bl_description = "Rescan collection instances: masters with at least one instance empty"
    bl_options = {"REGISTER"}

    def execute(self, context):
        scene = context.scene
        props = scene.inst_mgr_props
        tab = getattr(props, "stats_tab", "SUMMARY")
        if not isinstance(tab, str):
            tab = "SUMMARY"
        n = instance_stats.rebuild_instance_stats(scene, tab)
        self.report({"INFO"}, f"Instance stats rows: {n}")
        return {"FINISHED"}


class INST_MGR_OT_SelectStatInstancers(Operator):
    bl_idname = "inst_mgr.select_stat_instancers"
    bl_label = "Select instance empties (stats row)"
    bl_description = "Select all collection-instance empties counted for the current stats row"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        idx = scene.inst_mgr_instance_stat_index
        rows = scene.inst_mgr_instance_stats
        if idx < 0 or idx >= len(rows):
            self.report({"WARNING"}, "Invalid stats row")
            return {"CANCELLED"}
        row = rows[idx]
        if row.row_kind == "SUMMARY":
            self.report({"WARNING"}, i18n.tr(context, "STATS_WARN_SUMMARY_SELECT"))
            return {"CANCELLED"}
        bpy.ops.object.select_all(action="DESELECT")
        found = 0
        last = None
        for it in row.instancers:
            ob = bpy.data.objects.get(it.name)
            if ob and ob.name in context.view_layer.objects:
                ob.select_set(True)
                found += 1
                last = ob
        if last:
            context.view_layer.objects.active = last
        self.report({"INFO"}, f"Selected {found} instance empties")
        return {"FINISHED"}


class INST_MGR_OT_SetReferenceTab(Operator):
    bl_idname = "inst_mgr.set_reference_tab"
    bl_label = "Set reference tab"
    bl_options = {"INTERNAL", "REGISTER"}

    tab: StringProperty(name="Tab", default="COLLECTION")

    def execute(self, context):
        if self.tab not in ("NONE", "COLLECTION", "OBJECT"):
            return {"CANCELLED"}
        context.scene.inst_mgr_props.reference_tab = self.tab
        return {"FINISHED"}


class INST_MGR_OT_SetUnifiedMode(Operator):
    bl_idname = "inst_mgr.set_unified_mode"
    bl_label = "Set analysis mode"
    bl_options = {"INTERNAL", "REGISTER"}

    mode: StringProperty(name="Mode", default="COLLECTION_DUPES")

    def execute(self, context):
        props = context.scene.inst_mgr_props
        if self.mode not in unified_results.allowed_unified_modes(props.reference_tab):
            return {"CANCELLED"}
        props.unified_analysis_type = self.mode
        return {"FINISHED"}


class INST_MGR_OT_SetEquivScope(Operator):
    bl_idname = "inst_mgr.set_equiv_scope"
    bl_label = "Set equivalent search scope"
    bl_options = {"INTERNAL", "REGISTER"}

    scope: StringProperty(name="Scope", default="SCENE_ROOT")

    def execute(self, context):
        if self.scope not in ("SCENE_ROOT", "SAME_PARENT", "ENTIRE_FILE"):
            return {"CANCELLED"}
        context.scene.inst_mgr_props.collection_equiv_scope = self.scope
        return {"FINISHED"}


class INST_MGR_OT_SetMeshScope(Operator):
    bl_idname = "inst_mgr.set_mesh_scope"
    bl_label = "Set mesh analysis scope"
    bl_options = {"INTERNAL", "REGISTER"}

    scope: StringProperty(name="Scope", default="SCENE")

    def execute(self, context):
        if self.scope not in ("SCENE", "VISIBLE_VIEW_LAYER", "SELECTED", "PER_COLLECTION_TREE"):
            return {"CANCELLED"}
        context.scene.inst_mgr_props.scope = self.scope
        return {"FINISHED"}


class INST_MGR_OT_SetStatsTab(Operator):
    bl_idname = "inst_mgr.set_stats_tab"
    bl_label = "Set statistics tab"
    bl_options = {"INTERNAL", "REGISTER"}

    tab: StringProperty(name="Tab", default="SUMMARY")

    def execute(self, context):
        if self.tab not in ("SUMMARY", "MASTERS", "BY_OBJECT"):
            return {"CANCELLED"}
        context.scene.inst_mgr_props.stats_tab = self.tab
        return {"FINISHED"}


class INST_MGR_MT_reference_tab(Menu):
    bl_label = "Reference tab"
    bl_idname = "INST_MGR_MT_reference_tab"

    def draw(self, context):
        layout = self.layout
        props = context.scene.inst_mgr_props
        layout.operator_context = "EXEC_DEFAULT"
        for ident, key in (
            ("NONE", "REF_TAB_NONE"),
            ("COLLECTION", "REF_TAB_COLL"),
            ("OBJECT", "REF_TAB_OBJ"),
        ):
            try:
                op = layout.operator(
                    "inst_mgr.set_reference_tab",
                    text=i18n.tr(context, key),
                    depress=(props.reference_tab == ident),
                )
            except TypeError:
                op = layout.operator(
                    "inst_mgr.set_reference_tab",
                    text=i18n.tr(context, key),
                )
            op.tab = ident


class INST_MGR_MT_equiv_scope(Menu):
    bl_label = "Equivalent scope"
    bl_idname = "INST_MGR_MT_equiv_scope"

    def draw(self, context):
        layout = self.layout
        props = context.scene.inst_mgr_props
        layout.operator_context = "EXEC_DEFAULT"
        for ident, key in (
            ("SCENE_ROOT", "EQ_SR_N"),
            ("SAME_PARENT", "EQ_SP_N"),
            ("ENTIRE_FILE", "EQ_EF_N"),
        ):
            try:
                op = layout.operator(
                    "inst_mgr.set_equiv_scope",
                    text=i18n.tr(context, key),
                    depress=(props.collection_equiv_scope == ident),
                )
            except TypeError:
                op = layout.operator(
                    "inst_mgr.set_equiv_scope",
                    text=i18n.tr(context, key),
                )
            op.scope = ident


class INST_MGR_MT_unified_analysis(Menu):
    bl_label = "Analysis mode"
    bl_idname = "INST_MGR_MT_unified_analysis"

    def draw(self, context):
        layout = self.layout
        props = context.scene.inst_mgr_props
        layout.operator_context = "EXEC_DEFAULT"
        for mid in unified_results.allowed_unified_modes(props.reference_tab):
            key = unified_results.unified_mode_label_key(mid)
            try:
                op = layout.operator(
                    "inst_mgr.set_unified_mode",
                    text=i18n.tr(context, key),
                    depress=(props.unified_analysis_type == mid),
                )
            except TypeError:
                op = layout.operator(
                    "inst_mgr.set_unified_mode",
                    text=i18n.tr(context, key),
                )
            op.mode = mid


class INST_MGR_MT_mesh_scope(Menu):
    bl_label = "Mesh scope"
    bl_idname = "INST_MGR_MT_mesh_scope"

    def draw(self, context):
        layout = self.layout
        props = context.scene.inst_mgr_props
        layout.operator_context = "EXEC_DEFAULT"
        for ident, key in (
            ("SCENE", "MS_SC_N"),
            ("VISIBLE_VIEW_LAYER", "MS_VL_N"),
            ("SELECTED", "MS_SE_N"),
            ("PER_COLLECTION_TREE", "MS_PC_N"),
        ):
            try:
                op = layout.operator(
                    "inst_mgr.set_mesh_scope",
                    text=i18n.tr(context, key),
                    depress=(props.scope == ident),
                )
            except TypeError:
                op = layout.operator(
                    "inst_mgr.set_mesh_scope",
                    text=i18n.tr(context, key),
                )
            op.scope = ident


class INST_MGR_MT_stats_tab(Menu):
    bl_label = "Statistics view"
    bl_idname = "INST_MGR_MT_stats_tab"

    def draw(self, context):
        layout = self.layout
        props = context.scene.inst_mgr_props
        layout.operator_context = "EXEC_DEFAULT"
        for ident, key in (
            ("SUMMARY", "STATS_TAB_SUMMARY_N"),
            ("MASTERS", "STATS_TAB_MASTERS_N"),
            ("BY_OBJECT", "STATS_TAB_BYOBJ_N"),
        ):
            try:
                op = layout.operator(
                    "inst_mgr.set_stats_tab",
                    text=i18n.tr(context, key),
                    depress=(props.stats_tab == ident),
                )
            except TypeError:
                op = layout.operator(
                    "inst_mgr.set_stats_tab",
                    text=i18n.tr(context, key),
                )
            op.tab = ident


# ---------------------------------------------------------------------------
# UI List
# ---------------------------------------------------------------------------


class INST_MGR_UL_Groups(UIList):
    bl_idname = "INST_MGR_UL_groups"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            scope = f"[{item.scope_label}] " if item.scope_label else ""
            row.label(
                text=f"{scope}{item.master_name} x{item.count}",
                icon="MESH_DATA",
            )
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon="MESH_DATA")


class INST_MGR_UL_UnifiedResults(UIList):
    bl_idname = "INST_MGR_UL_unified_results"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            ic = "OUTLINER_COLLECTION"
            if item.row_kind == "MESH_GEOM":
                ic = "MESH_DATA"
            elif item.row_kind == "SHARED_DATA":
                t = item.data_block_type
                if t == "LIGHT":
                    ic = "LIGHT"
                elif t == "CAMERA":
                    ic = "CAMERA_DATA"
                elif t == "MESH":
                    ic = "MESH_DATA"
                else:
                    ic = "OBJECT_DATA"
            elif item.row_kind == "OBJECT_ROOT":
                ic = "OUTLINER_OB_GROUP_INSTANCE"
            row.label(text=item.title or item.row_kind, icon=ic)
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon="BLANK1")


class INST_MGR_UL_instance_stats(UIList):
    bl_idname = "INST_MGR_UL_instance_stats"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            if item.row_kind == "SUMMARY":
                label = f"{i18n.tr(context, item.master_name)}: {item.instance_count}"
                try:
                    row.label(text=label, icon="LINENUMBERS_ON", translate=False)
                except TypeError:
                    row.label(text=label, icon="LINENUMBERS_ON")
                return
            ic = "OUTLINER_COLLECTION" if item.row_kind == "COLLECTION" else "OBJECT_DATA"
            tag = "C" if item.row_kind == "COLLECTION" else "O"
            label = f"[{tag}] {item.master_name} x{item.instance_count}"
            try:
                row.label(text=label, icon=ic, translate=False)
            except TypeError:
                row.label(text=label, icon=ic)
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon="BLANK1")


# ---------------------------------------------------------------------------
# Scene properties
# ---------------------------------------------------------------------------
# Blender 5.x: EnumProperty on PropertyGroup must use **module-global** static
# ``items`` tuples (no factory ``type()`` class — RNA enum registration fails).
# Item **labels** use i18n EN here; panel row labels still use ``i18n.tr()``.


def _inst_mgr_scene_enum_tuples(lang: str):
    t = i18n.t
    return (
        (
            ("SCENE", t(lang, "MS_SC_N"), t(lang, "MS_SC_D")),
            ("VISIBLE_VIEW_LAYER", t(lang, "MS_VL_N"), t(lang, "MS_VL_D")),
            ("SELECTED", t(lang, "MS_SE_N"), t(lang, "MS_SE_D")),
            ("PER_COLLECTION_TREE", t(lang, "MS_PC_N"), t(lang, "MS_PC_D")),
        ),
        (
            ("NONE", t(lang, "REF_TAB_NONE"), t(lang, "REF_TAB_NONE_D")),
            ("COLLECTION", t(lang, "REF_TAB_COLL"), ""),
            ("OBJECT", t(lang, "REF_TAB_OBJ"), ""),
        ),
        (
            ("SCENE_ROOT", t(lang, "EQ_SR_N"), t(lang, "EQ_SR_D")),
            ("SAME_PARENT", t(lang, "EQ_SP_N"), t(lang, "EQ_SP_D")),
            ("ENTIRE_FILE", t(lang, "EQ_EF_N"), t(lang, "EQ_EF_D")),
        ),
        (
            ("COLLECTION_DUPES", t(lang, "UA_CD_N"), t(lang, "UA_CD_D")),
            ("OBJECT_DUPES", t(lang, "UA_OD_N"), t(lang, "UA_OD_D")),
            ("PARTS_IN_REF", t(lang, "UA_PR_N"), t(lang, "UA_PR_D")),
            ("MESH_SCENE", t(lang, "UA_MS_N"), t(lang, "UA_MS_D")),
            ("ALL_COLL_DUPES", t(lang, "UA_AC_N"), t(lang, "UA_AC_D")),
            ("ALL_OBJ_DUPES", t(lang, "UA_AO_N"), t(lang, "UA_AO_D")),
        ),
    )


(
    INST_MGR_ENUM_MESH_SCOPE,
    INST_MGR_ENUM_REF_TAB,
    INST_MGR_ENUM_EQUIV_SCOPE,
    INST_MGR_ENUM_UNIFIED,
) = _inst_mgr_scene_enum_tuples("EN")


INST_MGR_ENUM_STATS_TAB = (
    ("SUMMARY", i18n.t("EN", "STATS_TAB_SUMMARY_N"), i18n.t("EN", "STATS_TAB_SUMMARY_D")),
    ("MASTERS", i18n.t("EN", "STATS_TAB_MASTERS_N"), i18n.t("EN", "STATS_TAB_MASTERS_D")),
    ("BY_OBJECT", i18n.t("EN", "STATS_TAB_BYOBJ_N"), i18n.t("EN", "STATS_TAB_BYOBJ_D")),
)

INST_MGR_ENUM_COL_ORG_LAYOUT = (
    (
        "LEGACY",
        "Legacy (single folder)",
        "One {Name}_Master_and_Instances next to the master collection",
    ),
    (
        "TWIN",
        "Packed (Source + Instances)",
        "VFB_* / Name_Source (master or _DedupeObj_*) + Name_Instances (CI_ or OI_ empties)",
    ),
)


def _reference_tab_update(self, context):
    alw = unified_results.allowed_unified_modes(self.reference_tab)
    if self.unified_analysis_type not in alw:
        self.unified_analysis_type = alw[0]
    scene = getattr(context, "scene", None)
    if scene is not None:
        _refresh_all_equiv_counts(scene)


def _scene_props_stats_tab_update(self, context):
    scene = getattr(context, "scene", None)
    if scene is None:
        return
    try:
        tab = getattr(self, "stats_tab", "SUMMARY")
        if not isinstance(tab, str):
            tab = "SUMMARY"
        instance_stats.rebuild_instance_stats(scene, tab)
    except Exception:
        pass


class INST_MGR_PG_SceneProps(PropertyGroup):
    only_mesh: BoolProperty(default=True, description="")
    scope: EnumProperty(items=INST_MGR_ENUM_MESH_SCOPE, default="SCENE")
    batch_size: IntProperty(default=10, min=1, max=500)
    coll_inst_only_scene_root_children: BoolProperty(default=True, description="")
    coll_inst_master_name: StringProperty(default="", description="")
    coll_inst_dup_name: StringProperty(default="", description="")
    ref_collection_name: StringProperty(default="", description="")
    ref_object_name: StringProperty(default="", description="")
    reference_tab: EnumProperty(
        items=INST_MGR_ENUM_REF_TAB,
        default="COLLECTION",
        update=_reference_tab_update,
    )
    reference_show_details: BoolProperty(default=False)
    reference_expand_collection_tools: BoolProperty(default=False, description="")
    reference_expand_equiv_block: BoolProperty(default=True, description="")
    reference_expand_pickers_block: BoolProperty(default=True, description="")
    reference_expand_coll_tools_inner: BoolProperty(default=True, description="")
    reference_expand_auto_inner: BoolProperty(default=True, description="")
    workflow_expand_quick_status: BoolProperty(
        default=True,
        description="Show collection / root / equiv summary in Analysis & merge",
    )
    workflow_expand_auto_organize_block: BoolProperty(default=True, description="")
    workflow_expand_wf_analysis: BoolProperty(default=True, description="")
    workflow_expand_wf_list: BoolProperty(default=True, description="")
    workflow_expand_wf_merge: BoolProperty(default=True, description="")
    workflow_expand_wf_nav: BoolProperty(default=True, description="")
    stats_expand_controls: BoolProperty(default=True, description="")
    stats_expand_list_block: BoolProperty(default=True, description="")
    stats_expand_options: BoolProperty(default=True, description="")
    auto_organize_master_instances: BoolProperty(default=True, description="")
    collection_organize_layout: EnumProperty(
        items=INST_MGR_ENUM_COL_ORG_LAYOUT,
        default="LEGACY",
    )
    stats_show_instancer_names: BoolProperty(default=False, description="")
    stats_tab: EnumProperty(
        items=INST_MGR_ENUM_STATS_TAB,
        default="SUMMARY",
        update=_scene_props_stats_tab_update,
    )
    collection_equiv_scope: EnumProperty(
        items=INST_MGR_ENUM_EQUIV_SCOPE,
        default="SAME_PARENT",
        update=_scene_props_equiv_scope_update,
    )
    unified_analysis_type: EnumProperty(
        items=INST_MGR_ENUM_UNIFIED,
        default="COLLECTION_DUPES",
    )


classes = (
    INST_MGR_PG_Member,
    INST_MGR_PG_StatInstancer,
    INST_MGR_PG_InstanceStatRow,
    INST_MGR_PG_ColorBackup,
    INST_MGR_PG_MasterOverride,
    INST_MGR_PG_Group,
    INST_MGR_PG_UnifiedRow,
    INST_MGR_PG_SceneProps,
    INST_MGR_UL_Groups,
    INST_MGR_UL_UnifiedResults,
    INST_MGR_UL_instance_stats,
    INST_MGR_OT_Analyze,
    INST_MGR_OT_UnifiedAnalyze,
    INST_MGR_OT_Clear,
    INST_MGR_OT_SelectGroup,
    INST_MGR_OT_SelectBatch,
    INST_MGR_OT_IndexDelta,
    INST_MGR_OT_MergeActiveGroup,
    INST_MGR_OT_MergeAll,
    INST_MGR_OT_RemoveStaleInstanceEmpties,
    INST_MGR_OT_PurgeOrphans,
    INST_MGR_OT_HighlightLinked,
    INST_MGR_OT_HighlightCurrentRow,
    INST_MGR_OT_MergeAllCollectionRows,
    INST_MGR_OT_MergeAllObjectRootRows,
    INST_MGR_OT_PackCurrentPartRowCollInst,
    INST_MGR_OT_PackAllPartRowsCollInst,
    INST_MGR_OT_ClearHighlight,
    INST_MGR_OT_SetMaster,
    INST_MGR_OT_CollectionAutoInstances,
    INST_MGR_OT_CollectionReplacePair,
    INST_MGR_OT_SetRefCollection,
    INST_MGR_OT_SetRefObject,
    INST_MGR_OT_RefreshCollectionDupCount,
    INST_MGR_OT_StructureHighlight,
    INST_MGR_OT_StructureRepoint,
    INST_MGR_OT_RefreshInstanceStats,
    INST_MGR_OT_SelectStatInstancers,
    INST_MGR_OT_SetReferenceTab,
    INST_MGR_OT_SetUnifiedMode,
    INST_MGR_OT_SetEquivScope,
    INST_MGR_OT_SetMeshScope,
    INST_MGR_OT_SetStatsTab,
    INST_MGR_MT_reference_tab,
    INST_MGR_MT_equiv_scope,
    INST_MGR_MT_unified_analysis,
    INST_MGR_MT_mesh_scope,
    INST_MGR_MT_stats_tab,
)


def register_props():
    bpy.types.Scene.inst_mgr_groups = CollectionProperty(type=INST_MGR_PG_Group)
    bpy.types.Scene.inst_mgr_group_index = IntProperty(name="Group index", default=0)
    bpy.types.Scene.inst_mgr_unified_results = CollectionProperty(type=INST_MGR_PG_UnifiedRow)
    bpy.types.Scene.inst_mgr_unified_index = IntProperty(
        name=" ",
        default=0,
        min=0,
        description="",
    )
    bpy.types.Scene.inst_mgr_props = bpy.props.PointerProperty(type=INST_MGR_PG_SceneProps)
    bpy.types.Scene.inst_mgr_color_backups = CollectionProperty(type=INST_MGR_PG_ColorBackup)
    bpy.types.Scene.inst_mgr_master_overrides = CollectionProperty(type=INST_MGR_PG_MasterOverride)
    bpy.types.Scene.inst_mgr_equiv_collection_count = IntProperty(
        name="Equiv. root collections",
        default=-1,
        description="-1 unknown; else count of other roots matching reference structure",
    )
    bpy.types.Scene.inst_mgr_equiv_object_count = IntProperty(
        name="Equiv. root objects",
        default=-1,
        description="-1 unknown; else count of other roots matching reference object",
    )
    bpy.types.Scene.inst_mgr_instance_stats = CollectionProperty(type=INST_MGR_PG_InstanceStatRow)
    bpy.types.Scene.inst_mgr_instance_stat_index = IntProperty(name="Instance stats row", default=0, min=0)


def unregister_props():
    del bpy.types.Scene.inst_mgr_instance_stat_index
    del bpy.types.Scene.inst_mgr_instance_stats
    del bpy.types.Scene.inst_mgr_equiv_object_count
    del bpy.types.Scene.inst_mgr_equiv_collection_count
    del bpy.types.Scene.inst_mgr_master_overrides
    del bpy.types.Scene.inst_mgr_color_backups
    del bpy.types.Scene.inst_mgr_props
    del bpy.types.Scene.inst_mgr_unified_index
    del bpy.types.Scene.inst_mgr_unified_results
    del bpy.types.Scene.inst_mgr_group_index
    del bpy.types.Scene.inst_mgr_groups


def _draw_reference_panel(layout, context, scene, props):
    """Foldable subpanel: tabs Collection | Object, optional details, shared scope & tools."""
    lang = i18n.get_lang(context)
    _tx_disclosure_prop(
        layout,
        props,
        "reference_expand_equiv_block",
        text=i18n.tr(context, "SECTION_EQUIV_COUNTS"),
    )
    if props.reference_expand_equiv_block:
        eqb = layout.box()
        _tx_prop(eqb, props, "reference_show_details", text=i18n.tr(context, "SHOW_DETAILS"))
        eqb.separator()
        es_row = eqb.row(align=True)
        _tx_label(es_row, text=i18n.tr(context, "PROP_EQ_SCOPE"))
        _es_keys = {
            "SCENE_ROOT": "EQ_SR_N",
            "SAME_PARENT": "EQ_SP_N",
            "ENTIRE_FILE": "EQ_EF_N",
        }
        _tx_menu(
            es_row,
            "INST_MGR_MT_equiv_scope",
            text=i18n.tr(context, _es_keys.get(props.collection_equiv_scope, "PROP_EQ_SCOPE")),
            icon="DOWNARROW_HLT",
        )
        _tx_operator(
            eqb,
            "inst_mgr.refresh_collection_dup_count",
            icon="FILE_REFRESH",
            text=i18n.tr(context, "OP_REFRESH_COUNTS"),
        )
        cnt_c = scene.inst_mgr_equiv_collection_count
        cnt_o = scene.inst_mgr_equiv_object_count
        _tx_label(
            eqb,
            text=_equiv_counts_formatted(context, cnt_c, cnt_o),
            icon="INFO",
        )
        if cnt_c == 0 or cnt_o == 0:
            hint = eqb.column(align=True)
            hint.scale_y = 0.85
            _tx_label(hint, text=i18n.tr(context, "HINT_ZERO"))

    layout.separator()
    rt_row = layout.row(align=True)
    _tx_label(rt_row, text=i18n.tr(context, "PROP_REF_TAB"))
    _rt_keys = {
        "NONE": "REF_TAB_NONE",
        "COLLECTION": "REF_TAB_COLL",
        "OBJECT": "REF_TAB_OBJ",
    }
    _tx_menu(
        rt_row,
        "INST_MGR_MT_reference_tab",
        text=i18n.tr(context, _rt_keys.get(props.reference_tab, "PROP_REF_TAB")),
        icon="DOWNARROW_HLT",
    )
    if props.reference_tab == "NONE":
        _tx_label(layout, text=i18n.tr(context, "REF_NONE_MODE_HINT"), icon="INFO")
    layout.separator()
    _tx_disclosure_prop(
        layout,
        props,
        "reference_expand_pickers_block",
        text=i18n.tr(context, "SECTION_REF_TARGET"),
    )
    if props.reference_expand_pickers_block:
        body = layout.column()
        if props.reference_tab == "NONE":
            pass
        elif props.reference_tab == "COLLECTION":
            box = body.box()
            row = box.row()
            row.scale_y = 1.15
            _tx_operator(
                row,
                "inst_mgr.set_ref_collection",
                icon="EYEDROPPER",
                text=i18n.tr(context, "OP_SET_REF_COLL"),
            )
            _tx_prop(box, props, "ref_collection_name", text=i18n.tr(context, "PROP_REF_COLL"))
            cn = core.inst_mgr_pg_str(props, "ref_collection_name")
            cref = bpy.data.collections.get(cn) if cn else None
            if cref is None:
                _tx_label(box, text=i18n.tr(context, "REF_NONE"), icon="ERROR")
            else:
                _tx_label(box, text=cref.name, icon="CHECKMARK")
                if props.reference_show_details:
                    for line in structure_match.format_structure_summary_lines(
                        structure_match.summarize_collection_structure(cref, scene=scene),
                        lang,
                    ):
                        _tx_label(box, text=line)
        else:
            box = body.box()
            row = box.row()
            row.scale_y = 1.15
            _tx_operator(
                row,
                "inst_mgr.set_ref_object",
                icon="EYEDROPPER",
                text=i18n.tr(context, "OP_SET_REF_OBJ"),
            )
            _tx_prop(box, props, "ref_object_name", text=i18n.tr(context, "PROP_REF_OBJ"))
            on = core.inst_mgr_pg_str(props, "ref_object_name")
            oref = bpy.data.objects.get(on) if on else None
            if oref is None:
                _tx_label(box, text=i18n.tr(context, "REF_NONE"), icon="ERROR")
            else:
                root = object_hierarchy.root_object(oref)
                _tx_label(box, text=root.name, icon="CHECKMARK")
                if props.reference_show_details:
                    for line in object_hierarchy.format_object_summary_lines(
                        object_hierarchy.summarize_object_subtree(root, scene),
                        lang,
                    ):
                        _tx_label(box, text=line)

    layout.separator()
    _tx_disclosure_prop(
        layout,
        props,
        "reference_expand_collection_tools",
        text=i18n.tr(context, "PROP_REF_ADV_TOOLS"),
    )
    if props.reference_expand_collection_tools:
        adv = layout.box()
        inner = _layout_sub_column(adv)
        _tx_disclosure_prop(
            inner,
            props,
            "reference_expand_coll_tools_inner",
            text=i18n.tr(context, "COLL_TOOLS"),
        )
        if props.reference_expand_coll_tools_inner:
            tools = inner.box()
            _tx_operator(
                tools,
                "inst_mgr.structure_highlight",
                icon="COLOR",
                text=i18n.tr(context, "OP_STRUCT_COLOR"),
            )
            _tx_operator(
                tools,
                "inst_mgr.structure_repoint",
                icon="LINKED",
                text=i18n.tr(context, "OP_STRUCT_INST"),
            )

        _tx_disclosure_prop(
            inner,
            props,
            "reference_expand_auto_inner",
            text=i18n.tr(context, "AUTO_NUM"),
        )
        if props.reference_expand_auto_inner:
            auto = inner.box()
            _tx_prop(
                auto,
                props,
                "coll_inst_only_scene_root_children",
                text=i18n.tr(context, "PROP_COLL_INST_ROOT"),
            )
            _tx_operator(
                auto,
                "inst_mgr.collection_auto_instances",
                icon="MOD_INSTANCE",
                text=i18n.tr(context, "OP_COLL_AUTO"),
            )
            _tx_prop(auto, props, "coll_inst_master_name", text=i18n.tr(context, "PROP_MASTER_COLL"))
            _tx_prop(auto, props, "coll_inst_dup_name", text=i18n.tr(context, "PROP_DUP_COLL"))
            _tx_operator(
                auto,
                "inst_mgr.collection_replace_pair",
                icon="ARROW_LEFTRIGHT",
                text=i18n.tr(context, "OP_COLL_PAIR"),
            )


class INST_MGR_PT_main(Panel):
    bl_label = " "
    bl_idname = "INST_MGR_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFB"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        _tx_label(self.layout, text=i18n.tr(context, "PANEL_MAIN"), icon="PLUGIN")

    def draw(self, context):
        layout = self.layout
        _tx_label(layout, text=i18n.tr(context, "MAIN_PANEL_HINT"), icon="INFO")


class INST_MGR_PT_reference(Panel):
    bl_label = " "
    bl_idname = "INST_MGR_PT_reference"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFB"
    bl_parent_id = "INST_MGR_PT_main"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 0

    def draw_header(self, context):
        _tx_label(self.layout, text=i18n.tr(context, "PANEL_REFERENCE"))

    def draw(self, context):
        _draw_reference_panel(
            self.layout,
            context,
            context.scene,
            context.scene.inst_mgr_props,
        )


class INST_MGR_PT_workflow(Panel):
    bl_label = " "
    bl_idname = "INST_MGR_PT_workflow"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFB"
    bl_parent_id = "INST_MGR_PT_main"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    def draw_header(self, context):
        _tx_label(self.layout, text=i18n.tr(context, "PANEL_WORKFLOW"))

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.inst_mgr_props

        _tx_disclosure_prop(
            layout,
            props,
            "workflow_expand_quick_status",
            text=i18n.tr(context, "REF_SUMMARY"),
        )
        if props.workflow_expand_quick_status:
            st = layout.box()
            cn = core.inst_mgr_pg_str(props, "ref_collection_name")
            cref = bpy.data.collections.get(cn) if cn else None
            on = core.inst_mgr_pg_str(props, "ref_object_name")
            oref = bpy.data.objects.get(on) if on else None
            root_disp = (
                object_hierarchy.root_object(oref).name
                if oref
                else i18n.tr(context, "REF_NONE")
            )
            _tx_label(
                st,
                text=f"{i18n.tr(context, 'REF_COLL_BOUND')}: "
                f"{cref.name if cref else i18n.tr(context, 'REF_NONE')}",
                icon="OUTLINER_COLLECTION",
            )
            _tx_label(
                st,
                text=f"{i18n.tr(context, 'REF_OBJ_BOUND')}: {root_disp}",
                icon="OBJECT_DATA",
            )
            cc, oc = scene.inst_mgr_equiv_collection_count, scene.inst_mgr_equiv_object_count
            _tx_label(
                st,
                text=_equiv_counts_formatted(context, cc, oc),
                icon="INFO",
            )

        _tx_disclosure_prop(
            layout,
            props,
            "workflow_expand_auto_organize_block",
            text=i18n.tr(context, "SECTION_AUTO_FOLDER"),
        )
        if props.workflow_expand_auto_organize_block:
            orgb = layout.box()
            _tx_prop(
                orgb,
                props,
                "auto_organize_master_instances",
                text=i18n.tr(context, "AUTO_ORGANIZE"),
            )
            _tx_label(orgb, text=i18n.tr(context, "AUTO_ORGANIZE_TIP"))
            col_org = orgb.column()
            col_org.enabled = bool(props.auto_organize_master_instances)
            _tx_prop(
                col_org,
                props,
                "collection_organize_layout",
                text=i18n.tr(context, "PROP_COL_ORG_LAYOUT"),
            )
            _tx_label(col_org, text=i18n.tr(context, "PROP_COL_ORG_LAYOUT_TIP"))

        layout.separator()
        wchain = layout.box()
        wcol = _layout_sub_column(wchain, gutter=0.04)
        _tx_disclosure_prop(
            wcol,
            props,
            "workflow_expand_wf_analysis",
            text=i18n.tr(context, "RESULTS"),
        )
        if props.workflow_expand_wf_analysis:
            ubox = wcol.box()
            _allowed_modes = unified_results.allowed_unified_modes(props.reference_tab)
            if props.unified_analysis_type not in _allowed_modes:
                props.unified_analysis_type = _allowed_modes[0]
            _tx_label(ubox, text=i18n.tr(context, "LIST_HINT"), icon="INFO")
            mode_row = ubox.row(align=True)
            _tx_label(mode_row, text=i18n.tr(context, "PROP_ANALYSIS_MODE"), icon="SETTINGS")
            _tx_menu(
                mode_row,
                "INST_MGR_MT_unified_analysis",
                text=i18n.tr(
                    context,
                    unified_results.unified_mode_label_key(props.unified_analysis_type),
                ),
                icon="DOWNARROW_HLT",
            )
            if props.unified_analysis_type == "MESH_SCENE":
                ms_row = ubox.row(align=True)
                _tx_label(ms_row, text=i18n.tr(context, "PROP_MESH_SCOPE"))
                _ms_keys = {
                    "SCENE": "MS_SC_N",
                    "VISIBLE_VIEW_LAYER": "MS_VL_N",
                    "SELECTED": "MS_SE_N",
                    "PER_COLLECTION_TREE": "MS_PC_N",
                }
                _tx_menu(
                    ms_row,
                    "INST_MGR_MT_mesh_scope",
                    text=i18n.tr(context, _ms_keys.get(props.scope, "PROP_MESH_SCOPE")),
                    icon="DOWNARROW_HLT",
                )
                _tx_prop(ubox, props, "only_mesh", text=i18n.tr(context, "PROP_ONLY_MESH"))
            row = ubox.row(align=True)
            row.operator(
                "inst_mgr.unified_analyze",
                icon="VIEWZOOM",
                text=i18n.tr(context, "OP_ANALYZE"),
            )
            row.operator(
                "inst_mgr.clear",
                icon="X",
                text=i18n.tr(context, "OP_CLEAR"),
            )
            n_rows = len(scene.inst_mgr_unified_results)
            _tx_label(
                ubox,
                text=i18n.tr(context, "RESULTS_DUP_GROUPS").format(n=n_rows),
                icon="INFO",
            )

        _tx_disclosure_prop(
            wcol,
            props,
            "workflow_expand_wf_list",
            text=i18n.tr(context, "SECTION_WF_LIST"),
        )
        if props.workflow_expand_wf_list:
            lbox = wcol.box()
            lbox.template_list(
                "INST_MGR_UL_unified_results",
                "",
                scene,
                "inst_mgr_unified_results",
                scene,
                "inst_mgr_unified_index",
                rows=5,
            )

        _tx_disclosure_prop(
            wcol,
            props,
            "workflow_expand_wf_merge",
            text=i18n.tr(context, "SECTION_WF_MERGE"),
        )
        if props.workflow_expand_wf_merge:
            mbox = wcol.box()
            if _workflow_merge_ref_parts(props):
                _tx_label(
                    mbox,
                    text=i18n.tr(context, "SECTION_MERGE_PARTS_IN_REF"),
                    icon="MESH_DATA",
                )
                colp = mbox.column(align=True)
                _tx_operator(
                    colp,
                    "inst_mgr.pack_current_part_row_coll_inst",
                    icon="OUTLINER_COLLECTION",
                    text=i18n.tr(context, "OP_PACK_CURRENT_MESH_ROW_CI"),
                )
                _tx_operator(
                    colp,
                    "inst_mgr.pack_all_part_rows_coll_inst",
                    icon="OUTLINER_OB_GROUP_INSTANCE",
                    text=i18n.tr(context, "OP_PACK_ALL_MESH_ROWS_CI"),
                )
            else:
                mbox.operator(
                    "inst_mgr.merge_active_group",
                    icon="LINKED",
                    text=i18n.tr(context, "OP_MERGE_ROW"),
                )
                mbox.operator(
                    "inst_mgr.merge_all",
                    icon="LINK_BLEND",
                    text=i18n.tr(context, "OP_MERGE_ALL"),
                )
                show_coll_inst = _merge_show_collection_inst(scene, props)
                show_obj_inst = _merge_show_object_inst(scene, props)
                if show_coll_inst or show_obj_inst:
                    mbox.separator()
                if show_coll_inst:
                    mbox.operator(
                        "inst_mgr.merge_all_collection_rows",
                        icon="OUTLINER_OB_GROUP_INSTANCE",
                        text=i18n.tr(context, "OP_MERGE_COLL_ALL"),
                    )
                if show_obj_inst:
                    mbox.operator(
                        "inst_mgr.merge_all_object_root_rows",
                        icon="EMPTY_AXIS",
                        text=i18n.tr(context, "OP_MERGE_OBJ_ALL"),
                    )

        _tx_disclosure_prop(
            wcol,
            props,
            "workflow_expand_wf_nav",
            text=i18n.tr(context, "SECTION_WF_NAV"),
        )
        if props.workflow_expand_wf_nav:
            nbox = wcol.box()
            row = nbox.row(align=True)
            row.operator("inst_mgr.index_delta", text="", icon="TRIA_LEFT").delta = -1
            row.operator("inst_mgr.index_delta", text="", icon="TRIA_RIGHT").delta = 1
            row.operator(
                "inst_mgr.select_group",
                icon="RESTRICT_SELECT_OFF",
                text=i18n.tr(context, "OP_SEL_GROUP"),
            )
            _tx_prop(nbox, props, "batch_size", text=i18n.tr(context, "PROP_BATCH"))
            row = nbox.row(align=True)
            op = row.operator(
                "inst_mgr.select_batch",
                icon="RESTRICT_SELECT_ON",
                text=i18n.tr(context, "OP_SEL_BATCH"),
            )
            op.count = props.batch_size
            nbox.operator(
                "inst_mgr.highlight_current_row",
                icon="HIDE_OFF",
                text=i18n.tr(context, "OP_HIGHLIGHT_ROW"),
            )
            row = nbox.row(align=True)
            row.operator(
                "inst_mgr.highlight_linked",
                icon="VIEW_PERSPECTIVE",
                text=i18n.tr(context, "OP_HIGHLIGHT_LINKED"),
            )
            row.operator(
                "inst_mgr.clear_highlight",
                icon="LOOP_BACK",
                text=i18n.tr(context, "OP_CLEAR_HI"),
            )
            row.operator(
                "inst_mgr.set_master",
                icon="PIVOT_CURSOR",
                text=i18n.tr(context, "OP_SET_MASTER"),
            )
            _tx_label(nbox, text=i18n.tr(context, "SOLID_HINT"))

        layout.separator()
        _tx_operator(
            layout,
            "inst_mgr.remove_stale_instance_empties",
            icon="EMPTY_AXIS",
            text=i18n.tr(context, "OP_PURGE_STALE_EMPTY"),
        )
        layout.operator(
            "inst_mgr.purge_orphans",
            icon="TRASH",
            text=i18n.tr(context, "OP_PURGE"),
        )


class INST_MGR_PT_instance_stats(Panel):
    bl_label = " "
    bl_idname = "INST_MGR_PT_instance_stats"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFB"
    bl_parent_id = "INST_MGR_PT_main"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 2

    def draw_header(self, context):
        _tx_label(self.layout, text=i18n.tr(context, "PANEL_INSTANCE_STATS"))

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.inst_mgr_props
        rows = scene.inst_mgr_instance_stats

        _tx_disclosure_prop(
            layout,
            props,
            "stats_expand_controls",
            text=i18n.tr(context, "SECTION_STATS_VIEW"),
        )
        if props.stats_expand_controls:
            cbox = layout.box()
            _tx_label(cbox, text=i18n.tr(context, "STATS_HINT"), icon="INFO")
            st_row = cbox.row(align=True)
            _tx_label(st_row, text=i18n.tr(context, "STATS_TAB"))
            _st_keys = {
                "SUMMARY": "STATS_TAB_SUMMARY_N",
                "MASTERS": "STATS_TAB_MASTERS_N",
                "BY_OBJECT": "STATS_TAB_BYOBJ_N",
            }
            _tx_menu(
                st_row,
                "INST_MGR_MT_stats_tab",
                text=i18n.tr(context, _st_keys.get(props.stats_tab, "STATS_TAB")),
                icon="DOWNARROW_HLT",
            )
            _tx_label(cbox, text=i18n.tr(context, "STATS_HINT_TABS"), icon="DOT")
            row = cbox.row(align=True)
            _tx_operator(
                row,
                "inst_mgr.refresh_instance_stats",
                icon="FILE_REFRESH",
                text=i18n.tr(context, "OP_REFRESH_STATS"),
            )
            _tx_label(
                cbox,
                text=f"{i18n.tr(context, 'STATS_ROWS')}: {len(rows)}",
                icon="OUTLINER_OB_GROUP_INSTANCE",
            )

        _tx_disclosure_prop(
            layout,
            props,
            "stats_expand_list_block",
            text=i18n.tr(context, "SECTION_STATS_LIST"),
        )
        if props.stats_expand_list_block:
            layout.template_list(
                "INST_MGR_UL_instance_stats",
                "",
                scene,
                "inst_mgr_instance_stats",
                scene,
                "inst_mgr_instance_stat_index",
                rows=6,
            )
            _tx_operator(
                layout,
                "inst_mgr.select_stat_instancers",
                icon="RESTRICT_SELECT_OFF",
                text=i18n.tr(context, "OP_SEL_STATS"),
            )

        _tx_disclosure_prop(
            layout,
            props,
            "stats_expand_options",
            text=i18n.tr(context, "SECTION_STATS_OPTS"),
        )
        if props.stats_expand_options:
            obox = layout.box()
            _tx_prop(
                obox,
                props,
                "stats_show_instancer_names",
                text=i18n.tr(context, "PROP_STATS_NAMES"),
            )
            idx = scene.inst_mgr_instance_stat_index
            if props.stats_tab == "SUMMARY":
                _tx_label(obox, text=i18n.tr(context, "STATS_SUM_HELP"), icon="INFO")
            elif props.stats_show_instancer_names and 0 <= idx < len(rows):
                r = rows[idx]
                if r.row_kind == "SUMMARY":
                    pass
                else:
                    dbox = obox.box()
                    _tx_label(
                        dbox,
                        text=f"{i18n.tr(context, 'STATS_DETAIL')}: {r.master_name} ({r.row_kind})",
                        icon="DOT",
                    )
                    col = dbox.column(align=True)
                    col.scale_y = 0.85
                    max_lines = 24
                    for i, it in enumerate(r.instancers):
                        if i >= max_lines:
                            _tx_label(col, text="...")
                            break
                        _tx_label(col, text=it.name)


class INST_MGR_PT_settings(Panel):
    bl_label = " "
    bl_idname = "INST_MGR_PT_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VFB"
    bl_parent_id = "INST_MGR_PT_main"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 99

    def draw_header(self, context):
        _tx_label(self.layout, text=i18n.tr(context, "PANEL_SETTINGS"))

    def draw(self, context):
        layout = self.layout
        try:
            ap = context.preferences.addons[i18n.ADDON_ID].preferences
        except Exception:
            _tx_label(layout, text=i18n.tr(context, "ERR_PREFS_ACCESS"), icon="ERROR")
            return
        _tx_prop(layout, ap, "language", text=i18n.tr(context, "LANGUAGE"))


_PANEL_CLASSES = (
    INST_MGR_PT_main,
    INST_MGR_PT_reference,
    INST_MGR_PT_workflow,
    INST_MGR_PT_instance_stats,
    INST_MGR_PT_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_props()
    for pcl in _PANEL_CLASSES:
        bpy.utils.register_class(pcl)


def unregister():
    for pcl in reversed(_PANEL_CLASSES):
        bpy.utils.unregister_class(pcl)
    unregister_props()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
