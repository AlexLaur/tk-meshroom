# -*- coding: utf-8 -*-
#
# - scene_operation.py -
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

from meshroom.ui import uiInstance

import sgtk
from sgtk.platform.qt6 import QtWidgets

HookClass = sgtk.get_hook_baseclass()


class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(
        self,
        operation,
        file_path,
        context,
        parent_action,
        file_version,
        read_only,
        **kwargs
    ):
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """
        if operation == "current_path":
            # return the current scene path
            return uiInstance.activeProject.graph.filepath

        elif operation == "prepare_new":
            # tk-multi-workfile doesn't popup the save windows when the user
            # click on the button "New File".
            # TODO: So create and save the scene from the context.
            pass

        elif operation == "open":
            # do new scene as Maya doesn't like opening
            # the scene it currently has open!
            uiInstance.activeProject.graph.load(file_path)

        elif operation == "save":
            # save the current scene:
            uiInstance.activeProject.graph.save()

        elif operation == "save_as":
            uiInstance.activeProject.saveAs(file_path)

        elif operation == "reset":
            if not uiInstance.activeProject.undoStack.clean:
                # Unsaved pipeline

                res = QtWidgets.QMessageBox.question(
                    None,
                    "Save your scene?",
                    "Your scene has unsaved changes. Save before proceeding?",
                    QtWidgets.QMessageBox.Yes
                    | QtWidgets.QMessageBox.No
                    | QtWidgets.QMessageBox.Cancel,
                )

                if res == QtWidgets.QMessageBox.Cancel:
                    return False
                elif res == QtWidgets.QMessageBox.No:
                    pass
                else:
                    if not uiInstance.activeProject.graph.filepath:
                        # Save as temp, really ?
                        uiInstance.activeProject.graph.saveAsTemp()
                    else:
                        uiInstance.activeProject.graph.save()

            uiInstance.activeProject.new()
            return True
