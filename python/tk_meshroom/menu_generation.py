# -*- coding: utf-8 -*-
#
# - menu_generation.py -
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

import os
import sys
import sgtk
import meshroom

from typing import Callable, Optional
from tank.platform.qt6 import QtQuick, QtWidgets, QtCore, QtGui


class FPTRPersistentMenuBar(QtWidgets.QWidget):
    """Uggly hack to create a menu in top of Meshroom QML UI.
    It should be refacto to something more clear.
    """

    def __init__(self, menu_name, x_pos, y_pos, parent=None):
        super(FPTRPersistentMenuBar, self).__init__(parent)

        self._x = x_pos
        self._y = y_pos

        # Configure widget
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        # Create menubar
        menubar = QtWidgets.QMenuBar(self)
        self._fptr_menu = menubar.addMenu(menu_name)
        self.resize(menubar.sizeHint())

        self.move(x_pos, y_pos + 55)

        # Hide/Show and Move menu according to the main app
        app = QtWidgets.QApplication.instance()
        app.focusWindowChanged.connect(self._on_focus_window_changed)

        # Hide/Show menu according to the page inside Meshroom (Application.qml or Homepage.qml)
        root = app.engine.rootObjects()[0]
        stackview_obj = None
        for child in root.findChildren(QtCore.QObject):
            if "StackView" in child.metaObject().className():
                stackview_obj = child
                break

        if stackview_obj:
            stackview_obj.currentItemChanged.connect(
                self._on_stackview_current_item_changed
            )

    @property
    def menu(self) -> QtWidgets.QMenu:
        return self._fptr_menu

    @property
    def original_x(self) -> int:
        return self._x

    @property
    def original_y(self) -> int:
        return self._y

    def _on_focus_window_changed(self, focus_window):
        if not focus_window:
            # We lost focus, hide menu
            self.hide()
            return

        if not isinstance(focus_window, QtQuick.QQuickWindow):
            # It is not the main window, nothing to do
            return

        if not meshroom.ui.uiInstance.activeProject.active:
            # We are not in the Application.qml but Homepage.qml
            return

        self.show()

        # It is the main window, we need to move the menu to the right position
        self.move(self._x + focus_window.x(), self._y + focus_window.y())

    def _on_stackview_current_item_changed(self):
        # TODO should check on which page we are ?
        if self.isVisible():
            self.hide()
        else:
            self.show()


class MenuGenerator(object):
    """
    Menu generation functionality for Meshroom.
    """

    def __init__(self, engine, menu_name):
        self._engine = engine
        self._menu_name = menu_name

        app = QtWidgets.QApplication.instance()
        self._meshroom_main_window = app.engine.rootObjects()[0]

        menubar = None
        for child in self._meshroom_main_window.findChildren(QtCore.QObject):
            if "MenuBar" in child.metaObject().className():
                menubar = child
                break

        x_pos = 238  # Magic number
        y_pos = 5  # Magic number
        if menubar:
            x_pos = menubar.x() + menubar.width()
            y_pos = menubar.y() + 5

        self._fptr_menu_widget = FPTRPersistentMenuBar(
            menu_name=menu_name, x_pos=x_pos, y_pos=y_pos
        )
        self._fptr_menu = self._fptr_menu_widget.menu

    ###########################################################################
    # public methods

    def destroy(self) -> None:
        self._fptr_menu_widget.deleteLater()

    def create_menu(self, disabled: bool = False) -> None:
        """Render the entire Shotgun menu.
        In order to have commands enable/disable themselves based on the
        enable_callback, re-create the menu items every time.

        :param disabled: Disabled the sgtk menu, defaults to False
        :type disabled: bool, optional
        """
        self._fptr_menu.clear()

        if disabled:
            self._fptr_menu.addMenu("Sgtk is disabled.")
            return

        context_menu = self._add_context_menu()

        self.add_divider(self._fptr_menu)

        # now enumerate all items and create menu objects for them
        menu_items = []
        for cmd_name, cmd_details in self._engine.commands.items():
            menu_items.append(AppCommand(cmd_name, self, cmd_details))

        # sort list of commands in name order
        menu_items.sort(key=lambda x: x.name)

        # now add favourites
        for fav in self._engine.get_setting("menu_favourites"):
            app_instance_name = fav["app_instance"]
            menu_name = fav["name"]

            # scan through all menu items
            for cmd in menu_items:
                if (
                    cmd.get_app_instance_name() == app_instance_name
                    and cmd.name == menu_name
                ):
                    cmd.add_command_to_menu(self._fptr_menu)
                    cmd.favourite = True

        # add menu divider
        self.add_divider(self._fptr_menu)

        # now go through all of the menu items.
        # separate them out into various sections
        commands_by_app = {}

        for cmd in menu_items:
            if cmd.get_type() == "context_menu":
                # context menu!
                cmd.add_command_to_menu(context_menu)

            else:
                # normal menu
                app_name = cmd.get_app_name()
                if app_name is None:
                    # un-parented app
                    app_name = "Other Items"
                if app_name not in commands_by_app:
                    commands_by_app[app_name] = []
                commands_by_app[app_name].append(cmd)

        # now add all apps to main menu
        self._add_app_menu(commands_by_app)

    def add_divider(self, parent_menu: QtWidgets.QMenu) -> QtGui.QAction:
        """Add a divider to the menu

        :param parent_menu: The menu on which to add divider
        :type parent_menu: QtWidgets.QMenu
        :return: The divider
        :rtype: QtGui.QAction
        """
        divider = QtGui.QAction(parent_menu)
        divider.setSeparator(True)
        parent_menu.addAction(divider)
        return divider

    def add_sub_menu(
        self, menu_name: str, parent_menu: QtWidgets.QMenu
    ) -> QtWidgets.QMenu:
        """Add a sub menu to the menu

        :param menu_name: The name of the menu
        :type menu_name: str
        :param parent_menu: The menu on which to add a sub menu
        :type parent_menu: QtWidgets.QMenu
        :return: The created sub menu
        :rtype: QtWidgets.QMenu
        """
        sub_menu = QtWidgets.QMenu(title=menu_name, parent=parent_menu)
        parent_menu.addMenu(sub_menu)
        return sub_menu

    def add_menu_item(
        self,
        name: str,
        parent_menu: QtWidgets.QMenu,
        callback: Callable,
        properties: dict = None,
    ) -> QtGui.QAction:
        """Add a menu item

        :param name: The name of the item
        :type name: str
        :param parent_menu: The menu on which to add the item
        :type parent_menu: QMenu
        :param callback: The callback to trigger
        :type callback: function
        :param properties: Some properties, defaults to None
        :type properties: dict, optional
        :return: The created item
        :rtype: QtGui.QAction
        """
        action = QtGui.QAction(name, parent_menu)
        parent_menu.addAction(action)
        if callback:
            action.triggered.connect(Callback(callback))

        if properties:
            if "tooltip" in properties:
                action.setTooltip(properties["tooltip"])
                action.setStatustip(properties["tooltip"])
            if "enable_callback" in properties:
                action.setEnabled(properties["enable_callback"]())
            if "checkable" in properties:
                action.setCheckable(True)
                action.setChecked(properties.get("checkable"))

        return action

    ###########################################################################
    # privates methods

    def _add_context_menu(self):
        """
        Adds a context menu which displays the current context
        """

        ctx = self._engine.context
        ctx_name = str(ctx)

        # create the menu object
        ctx_menu = self.add_sub_menu(ctx_name, self._fptr_menu)

        self.add_divider(ctx_menu)

        self.add_menu_item(
            "Jump to Flow Production Tracking", ctx_menu, self._jump_to_sg
        )

        # Add the menu item only when there are some file system locations.
        if ctx.filesystem_locations:
            self.add_menu_item(
                "Jump to File System", ctx_menu, self._jump_to_fs
            )

        # divider (apps may register entries below this divider)
        self.add_divider(ctx_menu)

        return ctx_menu

    def _add_app_menu(self, commands_by_app):
        """
        Add all apps to the main menu, process them one by one.
        """
        for app_name in sorted(commands_by_app.keys()):
            if len(commands_by_app[app_name]) > 1:
                # more than one menu entry fort his app
                # make a sub menu and put all items in the sub menu
                app_menu = self.add_sub_menu(app_name, self._fptr_menu)

                # get the list of menu cmds for this app
                cmds = commands_by_app[app_name]
                # make sure it is in alphabetical order
                cmds.sort(key=lambda x: x.name)

                for cmd in cmds:
                    cmd.add_command_to_menu(app_menu)
            else:
                # this app only has a single entry.
                # display that on the menu
                cmd_obj = commands_by_app[app_name][0]
                if not cmd_obj.favourite:
                    # skip favourites since they are already on the menu
                    cmd_obj.add_command_to_menu(self._fptr_menu)
        self.add_divider(self._fptr_menu)

    def _jump_to_sg(self):
        """
        Jump to shotgun, launch web browser
        :param state: The state of the menu item
        :return: None
        """
        url = self._engine.context.shotgun_url
        QtWidgets.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _jump_to_fs(self):
        """
        Jump from context to File system action.
        :param state: The state of the menu item
        :return: None
        """
        # launch one window for each location on disk
        paths = self._engine.context.filesystem_locations
        for disk_location in paths:
            # run the app
            if sgtk.util.is_linux():
                cmd = 'xdg-open "%s"' % disk_location
            elif sgtk.util.is_macos():
                cmd = 'open "%s"' % disk_location
            elif sgtk.util.is_windows():
                cmd = 'cmd.exe /C start "Folder" "%s"' % disk_location
            else:
                raise Exception(
                    "Platform '%s' is not supported." % sys.platform
                )

            exit_code = os.system(cmd)
            if exit_code != 0:
                self._engine.logger.error("Failed to launch '%s'!", cmd)


class Callback(object):
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *_):
        """
        Execute the callback deferred to avoid potential problems with the command resulting in the menu
        being deleted, e.g. if the context changes resulting in an engine restart! - this was causing a
        segmentation fault crash on Linux.

        :param _: Accepts any args so that a callback might throw at it.
        For example a menu callback will pass the menu state. We accept these and ignore them.
        """
        # note that we use a single shot timer instead of cmds.evalDeferred as we were experiencing
        # odd behaviour when the deferred command presented a modal dialog that then performed a file
        # operation that resulted in a QMessageBox being shown - the deferred command would then run
        # a second time, presumably from the event loop of the modal dialog from the first command!
        #
        # As the primary purpose of this method is to detach the executing code from the menu invocation,
        # using a singleShot timer achieves this without the odd behaviour exhibited by evalDeferred.

        # This logic is implemented in the plugin_logic.py Callback class.

        QtCore.QTimer.singleShot(0, self._execute_within_exception_trap)

    def _execute_within_exception_trap(self):
        """
        Execute the callback and log any exception that gets raised which may otherwise have been
        swallowed by the deferred execution of the callback.
        """
        try:
            self.callback()
        except Exception:
            current_engine = sgtk.platform.current_engine()
            current_engine.logger.exception(
                "An exception was raised from Toolkit"
            )


class AppCommand(Callback):
    """
    Wraps around a single command that you get from engine.commands
    """

    def __init__(
        self, name: str, parent: QtWidgets.QWidget, command_dict: dict
    ):
        self.name = name
        self.properties = command_dict["properties"] or {}
        self.favourite = False
        self._parent = parent

        super(AppCommand, self).__init__(command_dict["callback"])

    def get_app_name(self) -> Optional[str]:
        """
        Returns the name of the app that this command belongs to
        """
        if "app" in self.properties:
            return self.properties["app"].display_name
        return None

    def get_app_instance_name(self) -> Optional[str]:
        """
        Returns the name of the app instance, as defined in the environment.
        Returns None if not found.
        """
        if "app" not in self.properties:
            return None

        app_instance = self.properties["app"]
        engine = app_instance.engine

        for app_instance_name, app_instance_obj in engine.apps.items():
            if app_instance_obj == app_instance:
                # found our app!
                return app_instance_name

        return None

    def get_type(self) -> str:
        """
        returns the command type. Returns node, custom_pane or default
        """
        return self.properties.get("type", "default")

    def add_command_to_menu(self, menu: QtWidgets.QMenu) -> None:
        """Adds an app command to the menu

        :param menu: The menu on which to add
        :type menu: QtWidgets.QMenu
        """
        # create menu sub-tree
        parent_menu = menu

        parts = self.name.split("/")
        for item_label in parts[:-1]:
            # see if there is already a sub-menu item
            sub_menu = self._find_sub_menu_item(parent_menu, item_label)
            if sub_menu:
                # already have sub menu
                parent_menu = sub_menu
            else:
                parent_menu = self._parent.add_sub_menu(
                    item_label, parent_menu
                )

        self._parent.add_menu_item(
            parts[-1], parent_menu, self.callback, self.properties
        )

    def _find_sub_menu_item(
        self, menu: QtWidgets.QMenu, label: str
    ) -> Optional[str]:
        """
        Find the 'sub-menu' menu item with the given label
        """
        if menu.title() == label:
            return menu
        for action in menu.actions():
            submenu = action.menu()
            if submenu:
                if submenu.title() == label:
                    return submenu
                found = self._find_sub_menu_item(submenu, label)
                if found:
                    return found
        return None
