#!/usr/bin/env python
# --!-- coding: utf8 --!--
from PyQt5.QtWidgets import QTextEdit, qApp

from manuskript.constants import ICONS_DIR
from manuskript.exporter.basic import basicExporter, basicFormat
from manuskript.exporter.manuskript.HTML import HTML
from manuskript.exporter.manuskript.markdown import markdown
from manuskript.exporter.manuskript.plainText import plainText


class manuskriptExporter(basicExporter):

    name = "Manuskript"
    description = qApp.translate("Export", "Default exporter, provides basic formats used by other exporters.")
    exportTo = [
        plainText(),
        markdown(),
        HTML(),
        basicFormat("OPML", icon="text-x-opml+xml")
    ]
    icon = ICONS_DIR / "Manuskript/icon-256px.png"

    @classmethod
    def isValid(cls):
        return True