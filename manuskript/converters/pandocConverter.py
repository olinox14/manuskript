#!/usr/bin/env python
# --!-- coding: utf8 --!--
import shutil
import subprocess

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import qApp, QMessageBox
from path import Path

from manuskript.converters import abstractConverter
from manuskript.functions import mainWindow


class pandocConverter(abstractConverter):

    name = "pandoc"
    cmd = "pandoc"

    @classmethod
    def isValid(cls):
        if cls.path() != None:
            return 2
        elif cls.customPath() and cls.customPath.exists():
            return 1
        else:
            return 0

    @classmethod
    def customPath(cls):
        return Path(QSettings().value("Exporters/{}_customPath".format(cls.name), ""))

    @classmethod
    def path(cls):
        return Path(shutil.which(cls.cmd))

    @classmethod
    def convert(cls, src, _from="markdown", to="html", args=None, outputfile=None):
        if not cls.isValid:
            print("ERROR: pandocConverter is called but not valid.")
            return ""

        cmd = [cls.runCmd()]

        cmd += ["--from={}".format(_from)]
        cmd += ["--to={}".format(to)]

        if args:
            cmd += args

        if outputfile:
            cmd.append("--output={}".format(outputfile))

        qApp.setOverrideCursor(QCursor(Qt.WaitCursor))

        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if not type(src) == bytes:
            src = src.encode("utf-8")  # assumes utf-8

        stdout, stderr = p.communicate(src)

        qApp.restoreOverrideCursor()

        if stderr:
            err = stderr.decode("utf-8")
            print(err)
            QMessageBox.critical(mainWindow().dialog,
                                 qApp.translate("Export", "Error"), err)
            return None

        return stdout.decode("utf-8")

    @classmethod
    def runCmd(cls):
        if cls.isValid() == 2:
            return cls.cmd
        elif cls.isValid() == 1:
            return cls.customPath
