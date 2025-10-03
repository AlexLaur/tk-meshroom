# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


class MenuGenerator(object):
    """
    Menu generation functionality for Meshroom
    """

    def __init__(self, engine, menu_handle):
        self._engine = engine
        self._menu_handle = menu_handle

    ###########################################################################
    # public methods

    def create_menu(self, *args):
        """
        Render the entire Shotgun menu.
        In order to have commands enable/disable themselves based on the
        enable_callback, re-create the menu items every time.
        """
        pass
