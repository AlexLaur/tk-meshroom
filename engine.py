# -*- coding: utf-8 -*-
#
# - engine.py -
#
# Copyright (c) 2025 Alexandre Laurette
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Your use of the Shotgun Pipeline Toolkit is governed by the applicable
# license agreement between you and Autodesk / Shotgun.
#


__author__ = "Laurette Alexandre"

import os
import sgtk
import tank

import meshroom

from tank.util import is_windows, is_linux, is_macos


def _patch_pyside6_for_tank():
    try:
        from PySide6 import QtWebEngineWidgets, QtWebEngineCore
    except ImportError:
        import PySide6

        class QtWebEngineCore:
            QWebEnginePage = None
            QWebEngineProfile = None

        PySide6.QtWebEngineCore = QtWebEngineCore
        PySide6.QtWebEngineWidgets = None


_patch_pyside6_for_tank()


def update_engine_context():
    engine = tank.platform.current_engine()

    if not engine:
        # If we don't have an engine for some reason then we don't have
        # anything to do.
        return

    if not engine.has_ui:
        # How to get the filepath of the pipeline whithout the UiInsance ?
        return

    engine.logger.debug("Updating engine context...")
    scene_path = meshroom.ui.uiInstance.activeProject.graph.filepath

    if not scene_path:
        engine.logger.info("No scene path. No need to change the context.")
        return

    scene_path = os.path.abspath(scene_path)

    # we are going to try to figure out the context based on the
    # active document
    current_ctx = engine.context

    try:
        # and construct the new context for this path:
        tk = sgtk.sgtk_from_path(scene_path)
    except tank.TankError:
        # could not detect context from path, will use the project context
        # for menus if it exists
        message = (
            "Flow Production Tracking Meshroom Engine could not detect "
            "the context from the active document. "
            f"FPTR menus will be stay in the current context '{current_ctx}'."
        )
        engine.logger.error(message)
        return

    new_ctx = tk.context_from_path(scene_path, current_ctx)

    if not new_ctx:
        project_name = engine.context.project.get("name")
        project_ctx = tk.context_from_entity_dictionary(current_ctx)
        message = (
            "Could not extract a context from the current active project "
            f"path, so we revert to the current project '{project_name}' context: '{project_ctx}'."
        )
        engine.logger.warning(message)
        return

    # Only change if the context is different
    if new_ctx != current_ctx:
        try:
            engine.change_context(new_ctx)
            engine.logger.info("Context changed.")
        except tank.TankError:
            message = (
                "Flow Production Tracking Meshroom Engine could not change "
                "context from the active document. FPTR menu will be disabled."
            )
            engine.logger.error(message)
            engine.create_shotgun_menu(disabled=True)


class MeshroomEngine(tank.platform.Engine):
    """
    Toolkit engine for Meshroom.
    """

    LONG_MENU_NAME = "Flow Production Tracking"
    SHORT_MENU_NAME = "FPTR"
    VERSION_OLDEST_COMPATIBLE = 2025

    def __init__(self, *args, **kwargs):
        self._menu_name = self.LONG_MENU_NAME
        self._menu_generator = None

        super(MeshroomEngine, self).__init__(*args, **kwargs)

    @property
    def context_change_allowed(self):
        """
        Whether the engine allows a context change without the need for a restart.
        """
        return True

    @property
    def host_info(self):
        """
        :returns: A dictionary with information about the application hosting this engine.

        The returned dictionary is of the following form on success:

            {
                "name": "Meshroom",
                "version": "2025.1.0",
            }

        The returned dictionary is of following form on an error preventing
        the version identification.

            {
                "name": "Meshroom",
                "version: "unknown"
            }
        """

        host_info = {"name": "Meshroom", "version": meshroom.__version__}
        return host_info

    @property
    def has_ui(self):
        """
        Detect and return if meshroom is running in batch mode
        """
        if getattr(meshroom, "ui", None):
            return bool(getattr(meshroom.ui, "uiInstance", None))
        return False

    ##########################################################################################
    # init and destroy

    def pre_app_init(self):
        """
        Runs after the engine is set up but before any apps have been initialized.
        """
        pass

    def init_engine(self):
        """
        Initializes the Meshroom engine.
        """
        self.logger.debug("%s: Initializing...", self)

        # check that we are running an ok version of meshroom
        if not any([is_windows(), is_linux(), is_macos()]):
            raise tank.TankError(
                "The current platform is not supported! "
                "Supported platforms are Mac, Linux 64 and Windows 64."
            )

        # Check that there is a location on disk which corresponds to the context
        # The engine must have at least a Shotgun Project in the context to even start!
        if not self.context.project:
            raise tank.TankError(
                "The Meshroom engine needs at least a FPTR Project in the context "
                "in order to start! Your context: %s" % self.context
            )

        meshroom_version = self.host_info.get("version", "")
        major, minor, patch = map(int, meshroom_version.split("."))

        if major < self.VERSION_OLDEST_COMPATIBLE:
            # Older that the oldest known compatible version
            message = (
                "Flow Production Tracking is no longer compatible with "
                f"Meshroom versions older than {self.VERSION_OLDEST_COMPATIBLE}."
            )

            if self.has_ui:
                from PySide6 import (
                    QtWidgets,
                    QtCore,
                )  # TODO replace by tank.platform.qt

                dlg = QtWidgets.QMessageBox()
                dlg.setIcon(QtWidgets.QMessageBox.Critical)
                dlg.setText(message)
                dlg.setWindowTitle(
                    "Error - Flow Production Tracking Compatibility!"
                )
                dlg.setWindowFlags(
                    dlg.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
                )
                dlg.show()
                dlg.exec()

            raise sgtk.TankError(message)

        # TODO show compatibility warning for new versions
        # Read SGTK_COMPATIBILITY_DIALOG_SHOWN to know what to do

        # self._menu_name = self.LONG_MENU_NAME
        if self.get_setting("use_short_menu_name", False):
            self._menu_name = self.SHORT_MENU_NAME

        if self.get_setting("automatic_context_switch", True):
            # need to watch some scene events in case the engine needs
            # rebuilding:
            self.logger.debug("Registered open and save callbacks.")

    def post_app_init(self):
        """
        Called when all apps have initialized
        """
        if self.has_ui:
            meshroom.ui.uiInstance.activeProject.graphChanged.connect(
                update_engine_context
            )

            tk_meshroom = self.import_module("tk_meshroom")
            self._menu_generator = tk_meshroom.MenuGenerator(
                self, self._menu_name
            )

        self.create_shotgun_menu()

    def post_context_change(self, old_context, new_context):
        """
        Runs after a context change.

        :param old_context: The context being changed away from.
        :param new_context: The new context being changed to.
        """
        # restore the open log folder, it get's removed whenever the first time
        # a context is changed

        if self.get_setting("automatic_context_switch", True):
            # We need to stop watching, and then replace with a new watcher
            # that has a callback registered with the new context baked in.
            # This will ensure that the context_from_path call that occurs
            # after a File->Open receives an up-to-date "previous" context.
            self.logger.debug(
                "Registered new open and save callbacks before"
                " changing context."
            )

            # finally create the menu with the new context if needed
            if old_context != new_context:
                self.create_shotgun_menu()

            self.sgtk.execute_core_hook_method(
                tank.platform.constants.CONTEXT_CHANGE_HOOK,
                "post_context_change",
                previous_context=old_context,
                current_context=new_context,
            )

    def destroy_engine(self):
        self.logger.debug("%s: Destroying...", self)

        if self.has_ui:
            meshroom.ui.uiInstance.activeProject.graphChanged.disconnect(
                update_engine_context
            )

        self._menu_generator.destroy()

    def create_shotgun_menu(self, disabled=False):
        """
        Creates the main shotgun menu in meshroom.
        Note that this only creates the menu, not the child actions
        :return: bool
        """
        # only create the shotgun menu if not in batch mode and menu doesn't
        # already exist
        if self.has_ui and self._menu_generator:
            self._menu_generator.create_menu(disabled=disabled)
            return True
        return False
