'''

@author: olivier.massot, 2018
'''
from appdirs import user_data_dir
from path import Path


DEBUG = False

APP_NAME = "manuskript" if not DEBUG else "manuskript_tests"
APP_WEBSITE = "www.theologeek.ch"

VERSION = "0.8.0"

MAIN_DIR = Path(__file__).parent.parent
MS_DIR = MAIN_DIR / 'manuskript'
ICONS_DIR = MAIN_DIR / "icons"

LOGGING_CONF_FILE = MS_DIR / 'logging.yaml'

USER_DATA_DIR = Path(user_data_dir(roaming=True))

SEARCHABLE_PATHS = [MAIN_DIR, USER_DATA_DIR]
