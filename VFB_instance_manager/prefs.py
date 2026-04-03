"""Addon preferences: UI language (sidebar mirrors options)."""

from __future__ import annotations

import bpy
from bpy.props import EnumProperty
from bpy.types import AddonPreferences

from . import i18n


class INST_MGR_AP_Preferences(AddonPreferences):
    bl_idname = i18n.ADDON_ID

    language: EnumProperty(
        name="Language",
        description="Panel UI language (operator search stays English)",
        items=(
            ("EN", "English", ""),
            ("ZH", "中文", ""),
            (
                "OTHER",
                "Blender UI / 跟随界面",
                "Use Blender interface locale (Chinese UI → Chinese addon strings)",
            ),
        ),
        default="EN",
    )

    def draw(self, context):
        layout = self.layout
        lang = i18n.get_lang(context)
        if lang not in i18n.STRINGS:
            lang = "EN"

        def t(key: str) -> str:
            return i18n.t(lang, key)

        try:
            layout.label(text=i18n.ADDON_ID, translate=False)
            layout.label(text=t("PREFS_DISPLAY_TITLE"), translate=False)
        except TypeError:
            layout.label(text=i18n.ADDON_ID)
            layout.label(text=t("PREFS_DISPLAY_TITLE"))
        layout.separator()
        try:
            layout.label(text=t("PREFS_USE_SIDEBAR_SETTINGS"), translate=False)
        except TypeError:
            layout.label(text=t("PREFS_USE_SIDEBAR_SETTINGS"))


def register():
    bpy.utils.register_class(INST_MGR_AP_Preferences)
    try:
        from . import organization as org

        for scene in bpy.data.scenes:
            org.dedupe_show_all_sources(scene)
    except Exception:
        pass


def unregister():
    bpy.utils.unregister_class(INST_MGR_AP_Preferences)
