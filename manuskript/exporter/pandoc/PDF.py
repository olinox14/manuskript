#!/usr/bin/env python
# --!-- coding: utf8 --!--
import shutil

from PyQt5.QtWidgets import qApp

from manuskript import constants
from manuskript.exporter.pandoc.abstractOutput import abstractOutput
from manuskript.ui.views.PDFViewer import PDFViewer


class PDF(abstractOutput):
    """PDF Viewer using PDF.js. Cf. https://github.com/mozilla/pdf.js/wiki/Setup-PDF.js-in-a-website"""

    name = "PDF"
    description = qApp.translate("Export", "Needs LaTeX to be installed.")
    InvalidBecause = qApp.translate("Export", """a valid LaTeX installation. Pandoc recommendations can be found on:
                     <a href="https://pandoc.org/installing.html">pandoc.org/installing.html</a>. If you want Unicode support, you need XeLaTeX.""")
    icon = "application-pdf"

    exportVarName = "lastPandocPDF"
    toFormat = "pdf"
    exportFilter = "PDF files (*.pdf);; Any files (*)"
    requires = {
        "Settings": True,
        "Preview": True,
    }

    def isValid(self):
        path = shutil.which("pdflatex") or shutil.which("xelatex")
        return path is not None

    def output(self, settingsWidget, outputfile=None):
        args = settingsWidget.runnableSettings()
        args.remove("--to=pdf")
        args.append("--to=latex")
        src = self.src(settingsWidget)
        return self.exporter.convert(src, args, outputfile)

    def previewWidget(self):
        return PDFViewer()

    def preview(self, settingsWidget, previewWidget):
        filename = constants.TEMP_DIR / "msk_pdfpreview.pdf"

        settingsWidget.writeSettings()
        _ = self.output(settingsWidget, outputfile=filename)

        previewWidget.loadPDF(filename)
