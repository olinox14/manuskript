#!/usr/bin/env python
# --!-- coding: utf8 --!--
import logging
import shutil
import subprocess

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QWidget
from path import Path

from manuskript.functions import mainWindow


logger = logging.getLogger('manuskript')

class basicExporter:

    name = ""
    description = ""
    exportTo = []
    cmd = ""
    customPath = Path()
    icon = ""
    absentTip = ""  # A tip displayed when exporter is absent.
    absentURL = ""  # URL to open if exporter is absent.

    def __init__(self):
        settings = QSettings()
        self.customPath = settings.value("Exporters/{}_customPath".format(self.name), Path())

    def setCustomPath(self, path):
        self.customPath = Path(path)
        settings = QSettings()
        settings.setValue("Exporters/{}_customPath".format(self.name), self.customPath)

    def getFormatByName(self, name):
        for f in self.exportTo:
            if f.name == name:
                return f

        return None

    def isValid(self):
        if self.path() != None:
            return 2
        elif self.customPath and self.customPath.exists():
            return 1
        else:
            return 0

    def version(self):
        return ""

    def path(self):
        return Path(shutil.which(self.cmd))

    def run(self, args):
        if self.isValid() == 2:
            run = self.cmd
        elif self.isValid() == 1:
            run = self.customPath
        else:
            logger.error("no command for %s", self.name)
            return
        r = subprocess.check_output([run] + args)  # timeout=.2
        return r.decode("utf-8")

        # Example of how to run a command
        #
        # cmdl = ['txt2tags', '-t', target, '--enc=utf-8', '--no-headers', '-o', '-', '-']
        #
        # cmd = subprocess.Popen(('echo', text), stdout=subprocess.PIPE)
        # try:
        #     output = subprocess.check_output(cmdl, stdin=cmd.stdout, stderr=subprocess.STDOUT)  # , cwd="/tmp"
        # except subprocess.CalledProcessError as e:
        #     print("Error!")
        #     return text
        # cmd.wait()
        #
        # return output.decode("utf-8")


class basicFormat:

    implemented = False
    InvalidBecause = ""
    requires = {
        "Settings": False,
        "Preview": False,
    }
    icon = ""

    def __init__(self, name, description="", icon=""):
        self.name = name
        self.description = description
        self.icon = icon

    @classmethod
    def settingsWidget(cls):
        return QWidget()

    @classmethod
    def previewWidget(cls):
        return QWidget()

    @classmethod
    def preview(cls, settingsWidget, previewWidget):
        pass

    @classmethod
    def export(cls, settingsWidget):
        pass

    @classmethod
    def shortcodes(cls):
        return [
            ("\n", "\\n")
        ]

    @classmethod
    def escapes(cls, text):
        for A, B in cls.shortcodes():
            text = text.replace(A, B)
        return text

    @classmethod
    def descapes(cls, text):
        """How do we call that?"""
        for A, B in cls.shortcodes():
            text = text.replace(B, A)
        return text

    @classmethod
    def isValid(cls):
        return True

    @classmethod
    def projectPath(cls):
        return Path(mainWindow().currentProject).abspath().parent

