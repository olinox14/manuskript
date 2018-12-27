# -*- coding: utf-8 -*-

import faulthandler
import logging.config
import sys
import traceback

from PyQt5.QtCore import QLocale, QTranslator, QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, qApp
from path import Path
import yaml

from manuskript import constants


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

__VERSION__ = constants.VERSION

def prepare():
    
    logger.info("Running manuskript version {}.".format(constants.VERSION))
    
    app = QApplication(sys.argv)
    app.setOrganizationName(constants.APP_NAME)
    app.setOrganizationDomain(constants.APP_WEBSITE)
    app.setApplicationName(constants.APP_NAME)
    app.setApplicationVersion(constants.VERSION)

    icon = QIcon()
    for i in [16, 32, 64, 128, 256, 512]:
        icon_file = constants.MAIN_DIR / "icons/Manuskript/icon-{}px.png".format(i)
        if icon_file.exists():
            icon.addFile(icon_file)
        else:
            logger.warning("%s does not exist", icon_file.name)
    app.setWindowIcon(icon)

    app.setStyle("Fusion")

    # Load style from QSettings
    settings = QSettings(app.organizationName(), app.applicationName())
    if settings.contains("applicationStyle"):
        style = settings.value("applicationStyle")
        app.setStyle(style)

    # Translation process
    locale = QLocale.system().name()

    appTranslator = QTranslator(app)    # By default: locale

    # Load translation from settings
    translation_file = ""
    if settings.contains("applicationTranslation"):
        translation_file = settings.value("applicationTranslation")
        logger.info("Found translation in settings:", translation_file)
    else:
        translation_file = "manuskript_{}.qm".format(locale)
        logger.info("No translation in settings, use: %s", translation_file)

    if appTranslator.load(constants.MAIN_DIR / "i18n" / translation_file):
        app.installTranslator(appTranslator)
        logger.info(app.tr("Loaded translation: {}.").format(translation_file))
    else:
        logger.warning(app.tr("No translator found or loaded for locale %s", locale))


    QIcon.setThemeSearchPaths(QIcon.themeSearchPaths() + [constants.ICONS_DIR])
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

    # Parse sys args
    args = sys.argv[1:]
    if args:
        project_path = Path(args[0])
        if project_path.ext == ".msk" and project_path.exists():
            MW._autoLoadProject = project_path.abspath()

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
