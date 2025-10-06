# -*- coding: utf-8 -*-
#
# - __init__.py -
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
import traceback


def start_toolkit():
    try:
        import sgtk
    except Exception as error:
        print(
            "Flow Production Tracking: Could not import sgtk! "
            f"Disabling for now: {error}"
        )
        return

    # start up toolkit logging to file
    sgtk.LogManager().initialize_base_file_handler("tk-meshroom")
    logger = sgtk.LogManager.get_logger(__name__)

    # Get the name of the engine to start from the environment
    env_engine = os.environ.get("SGTK_ENGINE")
    if not env_engine:
        msg = "Flow Production Tracking: Missing required environment variable SGTK_ENGINE."
        logger.error(msg)
        return

    # Get the context load from the environment.
    env_context = os.environ.get("SGTK_CONTEXT")
    if not env_context:
        msg = "Flow Production Tracking: Missing required environment variable SGTK_CONTEXT."
        logger.error(msg)
        return

    try:
        # Deserialize the environment context
        context = sgtk.context.deserialize(env_context)
    except Exception as error:
        msg = (
            "Flow Production Tracking: Could not create context! "
            f"FPTR will be disabled. Details: {error}"
        )
        etype, value, tb = sys.exc_info()
        msg += "".join(traceback.format_exception(etype, value, tb))
        logger.error(msg)
        return

    try:
        # Start up the toolkit engine from the environment data
        logger.debug(
            f"Launching engine instance '{env_engine}' "
            f"for context {env_context}..."
        )

        # make sure the previous engine is removed
        engine = sgtk.platform.current_engine()
        if not engine:
            sgtk.platform.start_engine(env_engine, context.sgtk, context)
    except Exception as error:
        msg = (
            "Flow Production Tracking: Could not start engine. "
            f"Details: {error}"
        )
        etype, value, tb = sys.exc_info()
        msg += "".join(traceback.format_exception(etype, value, tb))
        logger.error(msg)
        return


from PySide6 import QtCore

# Execute when the Qt event loop is ready
# Fire up Toolkit and the environment engine when there's time.
QtCore.QTimer.singleShot(0, start_toolkit)
