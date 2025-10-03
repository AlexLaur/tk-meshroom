# -*- coding: utf-8 -*-

__author__ = "Laurette Alexandre"

import sgtk
import tank

import meshroom

from tank.util import is_windows, is_linux, is_macos


def _path_pyside6_for_tank():
    try:
        from PySide6 import QtWebEngineWidgets, QtWebEngineCore
    except ImportError:
        import PySide6

        class QtWebEngineCore:
            QWebEnginePage = None
            QWebEngineProfile = None

        PySide6.QtWebEngineCore = QtWebEngineCore
        PySide6.QtWebEngineWidgets = None


_path_pyside6_for_tank()


class MeshroomEngine(tank.platform.Engine):
    """
    Toolkit engine for Meshroom.
    """

    LONG_MENU_NAME = "Flow Production Tracking"
    SHORT_MENU_NAME = "FPTR"
    VERSION_OLDEST_COMPATIBLE = 2025

    def __init__(self, *args, **kwargs):
        super(MeshroomEngine, self).__init__(*args, **kwargs)

        self._menu_name = self.LONG_MENU_NAME

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
        return bool(meshroom.ui.uiInstance)

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

        if self.get_setting("use_short_menu_name", False):
            self._menu_name = self.SHORT_MENU_NAME

        if self.get_setting("automatic_context_switch", True):
            # need to watch some scene events in case the engine needs
            # rebuilding:
            self.logger.debug("Registered open and save callbacks.")

    def create_shotgun_menu(self):
        """
        Creates the main shotgun menu in meshroom.
        Note that this only creates the menu, not the child actions
        :return: bool
        """

        # only create the shotgun menu if not in batch mode and menu doesn't
        # already exist
        if self.has_ui:
            tk_meshroom = self.import_module("tk_meshroom")
            self._menu_generator = tk_meshroom.MenuGenerator(
                self, self._menu_name
            )
            self._menu_generator.create_menu()
            return True

        return False

    def display_menu(self, pos=None):
        """
        Shows the engine Shotgun menu.
        """
        pass

    def post_app_init(self):
        """
        Called when all apps have initialized
        """
        # self.create_shotgun_menu()
        pass

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
                # self.create_shotgun_menu()
                pass
