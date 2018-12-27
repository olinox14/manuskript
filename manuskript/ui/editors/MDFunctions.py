#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging


logger = logging.getLogger('manuskript')


def MDFormatSelection(editor, style):
    """
    Formats the current selection of ``editor`` in the format given by ``style``, 
    style being:
        0: bold
        1: italic
        2: code
    """
    logger.error("Formatting: %s", style)
    raise NotImplementedError()
    # FIXME