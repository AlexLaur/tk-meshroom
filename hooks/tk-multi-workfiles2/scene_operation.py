# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# import meshroom

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
        # TODO Meshroom should provide a basic API to open, save...
        meshroom_api = QtWidgets.QApplication.instance()._activeProject

        if operation == "current_path":
            # return the current scene path
            return meshroom_api.graph.filepath

        elif operation == "prepare_new":
            # tk-multi-workfile doesn't popup the save windows when the user
            # click on the button "New File".
            # TODO: So create and save the scene from the context.
            pass

        elif operation == "open":
            # do new scene as Maya doesn't like opening
            # the scene it currently has open!
            meshroom_api.graph.load(file_path)

        elif operation == "save":
            # save the current scene:
            meshroom_api.graph.save()

        elif operation == "save_as":
            meshroom_api.saveAs(file_path)

        elif operation == "reset":
            if not meshroom_api.undoStack.clean:
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
                    if not meshroom_api.graph.filepath:
                        # Save as temp, really ?
                        meshroom_api.graph.saveAsTemp()
                    else:
                        meshroom_api.graph.save()

            meshroom_api.new()
            return True
