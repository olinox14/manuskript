#!/usr/bin/env python
# --!-- coding: utf8 --!--


import logging

from manuskript.converters import abstractConverter


try:
    import markdown as MD
except ImportError:
    MD = None

logger = logging.getLogger('manuskript')

class markdownConverter(abstractConverter):
    """
    Converter using python module markdown.
    """

    name = "python module markdown"

    @classmethod
    def isValid(self):
        return MD is not None

    @classmethod
    def convert(self, markdown):
        if not self.isValid:
            logger.error("markdownConverter is called but not valid.")
            return ""

        html = MD.markdown(markdown)
        return html
