# -*- coding: utf-8 -*-

import faulthandler
import logging.config
import sys
import traceback

from PyQt5.QtCore import QLocale, QTranslator, QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, qApp, QMessageBox
from path import Path
import yaml

from manuskript.constants import MAIN_DIR
from manuskript.version import getVersion


faulthandler.enable()


# load logging configuration from 'logging.yaml'
with open(Path(__file__).parent / 'logging.yaml', 'rt') as f:
    logging.config.dictConfig(yaml.load(f))

logger = logging.getLogger('manuskript')

SYS_EXCEPT_HOOK = sys.excepthook
def _excepthook(typ, value, trace):
    """ Override the standard error handling to log any uncatched exception """
    QApplication.restoreOverrideCursor()
    logger.error("{}\n{}\n{}".format(typ.__name__, value, ''.join(traceback.format_tb(trace))))
    SYS_EXCEPT_HOOK(typ, value, trace)
sys.excepthook = _excepthook



def prepare(tests=False):
    app = QApplication(sys.argv)
    app.setOrganizationName("manuskript"+("_tests" if tests else ""))
    app.setOrganizationDomain("www.theologeek.ch")
    app.setApplicationName("manuskript"+("_tests" if tests else ""))
    app.setApplicationVersion(getVersion())

    logger.info("Running manuskript version {}.".format(getVersion()))
    icon = QIcon()
    for i in [16, 32, 64, 128, 256, 512]:
        icon.addFile(MAIN_DIR / "icons/Manuskript/icon-{}px.png".format(i))
    qApp.setWindowIcon(icon)

    app.setStyle("Fusion")

    # Load style from QSettings
    settings = QSettings(app.organizationName(), app.applicationName())
    if settings.contains("applicationStyle"):
        style = settings.value("applicationStyle")
        app.setStyle(style)

    # Translation process
    locale = QLocale.system().name()

    appTranslator = QTranslator(app)
    # By default: locale

    def extractLocale(filename):
        # len("manuskript_") = 13, len(".qm") = 3
        return filename[11:-3] if len(filename) >= 16 else ""

    def tryLoadTranslation(translation, source):
        if appTranslator.load(MAIN_DIR / "i18n" / translation):
            app.installTranslator(appTranslator)
            logger.info(app.tr("Loaded translation from {}: {}.").format(source, translation))
            return True
        else:
            logger.info(app.tr("Note: No translator found or loaded from {} for locale {}.").
                  format(source, extractLocale(translation)))
            return False

    # Load translation from settings
    translation = ""
    if settings.contains("applicationTranslation"):
        translation = settings.value("applicationTranslation")
        logger.info("Found translation in settings:", translation)

    if (translation != "" and not tryLoadTranslation(translation, "settings")) or translation == "":
        # load from settings failed or not set, fallback
        translation = "manuskript_{}.qm".format(locale)
        tryLoadTranslation(translation, "system locale")

    QIcon.setThemeSearchPaths(QIcon.themeSearchPaths() + [MAIN_DIR / "icons"])
    QIcon.setThemeName("NumixMsk")

    # Font siue
    if settings.contains("appFontSize"):
        f = qApp.font()
        f.setPointSize(settings.value("appFontSize", type=int))
        app.setFont(f)

    # Main window
    from manuskript.mainWindow import MainWindow

    MW = MainWindow()
    # We store the system default cursor flash time to be able to restore it
    # later if necessary
    MW._defaultCursorFlashTime = qApp.cursorFlashTime()

    # Command line project
    if len(sys.argv) > 1 and sys.argv[1][-4:] == ".msk":
        path = Path(sys.argv[1])
        if path.exists():
            MW._autoLoadProject = path.abspath()

    return app, MW

def launch(MW = None):
    if MW is None:
        from manuskript.functions import mainWindow
        MW = mainWindow()

    MW.show()

    qApp.exec_()
    qApp.deleteLater()

def run():
    """
    Run separates prepare and launch for two reasons:
    1. I've read somewhere it helps with potential segfault (see comment below)
    2. So that prepare can be used in tests, without running the whole thing
    """
    # Need to return and keep `app` otherwise it gets deleted.
    app, MW = prepare()     #@UnusedVariable
    # Separating launch to avoid segfault, so it seem.
    # Cf. http://stackoverflow.com/questions/12433491/is-this-pyqt-4-python-bug-or-wrongly-behaving-code
    launch(MW)

if __name__ == "__main__":
    run()
