#!/usr/bin/env python
#--!-- coding: utf8 --!--

import logging
from random import randint
import re
import tempfile
import webbrowser

from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt, QRect, QObject, QRegExp
from PyQt5.QtGui import QBrush, QIcon, QPainter, QColor, QImage, QPixmap
from PyQt5.QtWidgets import qApp
from path import Path

from manuskript import constants
from manuskript.enums import Outline


logger = logging.getLogger('manuskript')

# Used to detect multiple connections

AUC = Qt.AutoConnection | Qt.UniqueConnection
MW = None

def wordCount(text):
    return len(text.split())

def toInt(text):
    try:
        return int(text or 0)
    except ValueError:
        return 0

def toFloat(text):
    return float(text or 0.)

def toString(text):
    if text is None:
        return ''
    return str(text)

def drawProgress(painter, rect, progress, radius=0):
    from manuskript.ui import style as S
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(S.base)) # "#dddddd"
    painter.drawRoundedRect(rect, radius, radius)

    painter.setBrush(QBrush(colorFromProgress(progress)))

    r2 = QRect(rect)
    r2.setWidth(r2.width() * min(progress, 1))
    painter.drawRoundedRect(r2, radius, radius)

def colorFromProgress(progress):
    progress = toFloat(progress)
    if progress < 0.3:
        return QColor(Qt.red)
    elif progress < 0.8:
        return QColor(Qt.blue)
    elif progress > 1.2:
        return QColor("#FFA500")
    else:
        return QColor(Qt.darkGreen)

def mainWindow():
    # TODO: replace by a singleton in the MainWindow class
    global MW
    if not MW:
        for i in qApp.topLevelWidgets():
            if i.objectName() == "MainWindow":
                MW = i
                return MW
        return None
    else:
        return MW

def iconColor(icon):
    """Returns a QRgb from a QIcon, assuming its all the same color"""
    px = icon.pixmap(5, 5)
    return QColor(QImage(px).pixel(2, 2) if px.width() else Qt.transparent)

def iconFromColor(color):
    px = QPixmap(32, 32)
    px.fill(QColor(color))
    return QIcon(px)

def iconFromColorString(string):
    return iconFromColor(string)

THEME_ICONS = {
                "character":    "stock_people",
                "characters":   "stock_people",
                "plot":         "stock_shuffle",
                "plots":        "stock_shuffle",
                "world":        "emblem-web", #stock_timezone applications-internet
                "outline":      "gtk-index", #applications-versioncontrol
                "label":        "folder_color_picker",
                "status":       "applications-development",
                "text":         "view-text",
                "card":         "view-card",
                "outline":      "view-outline",
                "tree":         "view-list-tree",
                "spelling":     "tools-check-spelling"
            }

def themeIcon(name):
    "Returns an icon for the given name."
    return QIcon.fromTheme(THEME_ICONS.get(name, ""), fallback=QIcon())

def randomColor(mix=QColor(0,0,0,255)):
    """Generates a random color. If mix (QColor) is given, mixes the random color and mix."""
    return QColor(*[(randint(0, 255) + v) // 2 for v in mix.getRgb()[:3]], mix.alpha())

def mixColors(col1, col2, k=.5):
    if not 0 <= k <= 1:
        raise ValueError('k shall be between 0 et 1')
    r1, g1, b1, _ = QColor(col1).getRgb()
    r2, g2, b2, _ = QColor(col2).getRgb()
    return QColor(r1 * k + r2 * (1 - k),
                  g1 * k + g2 * (1 - k),
                  b1  *k + b2 * (1 - k))

def outlineItemColors(item):
    """Takes an OutlineItem and returns a dict of colors."""
    from manuskript.ui import style as S

    colors = {}
    
    mw = mainWindow()
    POV = item.data(Outline.POV)
    lbl = item.data(Outline.label)
    pg = item.data(Outline.goalPercentage)
    
    colors["POV"] = next((iconColor(mw.mdlCharacter.icon(i)) \
                          for i in range(mw.mdlCharacter.rowCount()) \
                          if mw.mdlCharacter.ID(i) == POV)) if POV else QColor(Qt.transparent)

    colors["Label"] = iconColor(mw.mdlLabels.item(toInt(lbl)).icon()) if lbl else QColor(Qt.transparent)

    colors["Progress"] = colorFromProgress(pg)

    colors["Compile"] = mixColors(QColor(S.text), QColor(S.window)) if str(item.compile()) == "0" else QColor(Qt.transparent)

    return colors

def colorifyPixmap(pixmap, color):
    # FIXME: ugly
    p = QPainter(pixmap)
    p.setCompositionMode(p.CompositionMode_Overlay)
    p.fillRect(pixmap.rect(), color)
    return pixmap

def writablePath():
    p = constants.USER_DATA_DIR
    p.mkdir_p()
    return p

def allPaths():
    return [constants.MAIN_DIR, writablePath()]

def tempFile(name):
    # FIXME: better use the native TemporaryFile object from tempfile lib
    return Path(tempfile.gettempdir()) / name

def totalObjects():
    return len(mainWindow().findChildren(QObject))

def printObjects():
    logger.debug("Objects count: %s", str(totalObjects()))

def findWidgetsOfClass(cls):
    """
    Returns all widgets, children of MainWindow, whose class is cls.
    @param cls: a class
    @return: list of QWidgets
    """
    return mainWindow().findChildren(cls, QRegExp())

def findBackground(filename):
    """
    Returns the full path to a background file of name filename within resources folders.
    """
    return findFirstFile(re.escape(filename), "resources/backgrounds")

def findFirstFile(regex, subpath="resources"):
    """
    Returns full path of first file matching regular expression regex within folder path
    """
    try:
        return next((f for dir_ in allPaths() for f in Path(dir_ / subpath).walkfiles() if re.match(regex, f) or re.match(regex, f.name)))
    except StopIteration:
        raise FileNotFoundError(r"No file matches the regex '{}'".format(regex))

CUSTOM_ICONS_CANDIDATES = [
                            "text-plain",
                            "gnome-settings",
                            "applications-internet",
                            "applications-debugging",
                            "applications-development",
                            "system-help",
                            "info",
                            "dialog-question",
                            "dialog-warning",
                            "stock_timezone",
                            "stock_people",
                            "stock_shuffle",
                            "gtk-index",
                            "folder_color_picker",
                            "applications-versioncontrol",
                            "stock_home",
                            "stock_trash_empty",
                            "stock_trash_full",
                            "stock_yes",
                            "stock_no",
                            "stock_notes",
                            "stock_calendar",
                            "stock_mic",
                            'stock_score-lowest', 'stock_score-lower', 'stock_score-low', 'stock_score-normal', 'stock_score-high', 'stock_score-higher', 'stock_score-highest',
                            "stock_task",
                            "stock_refresh",
                            "application-community",
                            "applications-chat",
                            "application-menu",
                            "applications-education",
                            "applications-science",
                            "applications-puzzles",
                            "applications-roleplaying",
                            "applications-sports",
                            "applications-libraries",
                            "applications-publishing",
                            "applications-development",
                            "applications-games",
                            "applications-boardgames",
                            "applications-geography",
                            "applications-physics",
                            "package_multimedia",
                            "media-flash",
                            "media-optical",
                            "media-floppy",
                            "media-playback-start",
                            "media-playback-pause",
                            "media-playback-stop",
                            "media-playback-record",
                            "media-playback-start-rtl",
                            "media-eject",
                            "document-save",
                            "gohome",
                            'purple-folder', 'yellow-folder', 'red-folder', 'custom-folder', 'grey-folder', 'blue-folder', 'default-folder', 'pink-folder', 'orange-folder', 'green-folder', 'brown-folder',
                            'folder-home', 'folder-remote', 'folder-music', 'folder-saved-search', 'folder-projects', 'folder-sound', 'folder-publicshare', 'folder-pictures', 'folder-saved-search-alt', 'folder-tag',
                            'calendar-01', 'calendar-02', 'calendar-03', 'calendar-04', 'calendar-05', 'calendar-06', 'calendar-07', 'calendar-08', 'calendar-09', 'calendar-10',
                            'arrow-down', 'arrow-left', 'arrow-right', 'arrow-up', 'arrow-down-double', 'arrow-left-double', 'arrow-right-double', 'arrow-up-double',
                            'emblem-added', 'emblem-checked', 'emblem-downloads', 'emblem-dropbox-syncing', 'emblem-danger', 'emblem-development', 'emblem-dropbox-app', 'emblem-art', 'emblem-camera', 'emblem-dropbox-selsync', 'emblem-insync-des-error', 'emblem-insync-error', 'emblem-generic', 'emblem-favorites', 'emblem-error', 'emblem-dropbox-uptodate', 'emblem-marketing', 'emblem-money', 'emblem-music', 'emblem-noread', 'emblem-people', 'emblem-personal', 'emblem-sound', 'emblem-shared', 'emblem-sales', 'emblem-presentation', 'emblem-plan', 'emblem-system', 'emblem-urgent', 'emblem-videos', 'emblem-web',
                            'face-angel', 'face-clown', 'face-angry', 'face-cool', 'face-devilish', 'face-sick', 'face-sleeping', 'face-uncertain', 'face-monkey', 'face-ninja', 'face-pirate', 'face-glasses', 'face-in-love', 'face-confused',
                            'feed-marked-symbolic', 'feed-non-starred', 'feed-starred', 'feed-unmarked-symbolic',
                            'notification-new-symbolic',
                            ]
    
def customIcons():
    """
    Returns a list of possible customIcons. String from theme.
    """
    return sorted(CUSTOM_ICONS_CANDIDATES)

def statusMessage(message, duration=5000, importance=1):
    """
    Shows a message in MainWindow's status bar.
    Importance: 0 = low, 1 = normal, 2 = important, 3 = critical.
    """
    from manuskript.ui import style as S
    MW.statusBar().hide()
    MW.statusLabel.setText(message)
    
    colors = ["color:{};".format(S.textLighter),
              "color:{};".format(S.textLight),
              "color:{}; font-weight: bold;".format(S.text),
              "color:red; font-weight: bold;"]
    MW.statusLabel.setStyleSheet(colors[importance])
    MW.statusLabel.adjustSize()
    g = MW.statusLabel.geometry()
    s = MW.layout().spacing() / 2
    g.setLeft(s)
    g.moveBottom(MW.mapFromGlobal(MW.geometry().bottomLeft()).y() - s)
    MW.statusLabel.setGeometry(g)
    MW.statusLabel.show()
    QTimer.singleShot(duration, MW.statusLabel.hide)

def openURL(url):
    """
    Opens url (string) in browser using desktop default application.
    """
    webbrowser.open(url)

def inspect():
    """
    Debugging tool. Call it to see a stack of calls up to that point.
    """
    import inspect
    logger.debug("-----------------------")
    for s in inspect.stack()[1:]:
        logger.debug(" * {}:{} // {}".format(
            Path(s.filename).basename(),
            s.lineno,
            s.function))
        logger.debug("   " + "".join(s.code_context))
