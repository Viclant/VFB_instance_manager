"""
VFB_instance_manager — reference-driven collection / object-hierarchy instancing for Blender.

Copyright **Viclant**; **V.F.B** is the department responsible for this product area.
https://viclant.com

Repository folder, Blender module id, and distribution zip basename: ``VFB_instance_manager``.
"""

bl_info = {
    "name": "VFB Instance Manager",
    "author": "Viclant — V.F.B",
    "version": (1, 0, 1),
    "blender": (3, 3, 0),
    "location": "View3D > Sidebar (N) > VFB",
    "description": "Viclant / V.F.B — v1.0.1: reference-driven duplicate detection; collection-instance merging; mesh row packs; optional *_Master_and_Instances layout",
    "category": "Object",
    "doc_url": "https://viclant.com",
}

from . import prefs
from . import ui


def register():
    prefs.register()
    ui.register()


def unregister():
    ui.unregister()
    prefs.unregister()
