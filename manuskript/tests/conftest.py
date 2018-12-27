#!/usr/bin/env python
# --!-- coding: utf8 --!--

"""Fixtures."""

import pytest

from manuskript.constants import MAIN_DIR


@pytest.fixture
def MW():
    """
    Returns the mainWindow
    """
    from manuskript import functions as F
    MW = F.mainWindow()
    assert MW is not None
    assert MW == F.MW

    return MW

@pytest.fixture
def MWNoProject(MW):
    """
    Take the MainWindow and close andy possibly open project.
    """
    MW.closeProject()
    assert MW.currentProject is None
    return MW

@pytest.fixture
def MWEmptyProject(MW):
    """
    Creates a MainWindow and load an empty project.
    """
    import tempfile
    tf = tempfile.NamedTemporaryFile(suffix=".msk")

    MW.closeProject()
    assert MW.currentProject is None
    MW.welcome.createFile(tf.name, overwrite=True)
    assert MW.currentProject is not None
    return MW

    # If using with: @pytest.fixture(scope='session', autouse=True)
    # yield MW
    # # Properly destructed after. Otherwise: seg fault.
    # MW.deleteLater()

@pytest.fixture
def MWSampleProject(MW):
    """
    Creates a MainWindow and load a copy of the Acts sample project.
    """

    # Get the path of the first sample project. We assume it is here.
    spDir = MAIN_DIR / "sample-projects"
    lst = spDir.dirs()
    # We assume it's saved in folder, so there is a `name.msk` file and a
    # `name` folder.
    src = next((f for f in lst if f[-4:] == ".msk" and f[:-4] in lst))
    src = spDir / src
    # Copy to a temp file
    import tempfile
    tf = tempfile.NamedTemporaryFile(suffix=".msk")
    import shutil
    shutil.copyfile(src, tf.name)
    shutil.copytree(src[:-4], tf.name[:-4])
    MW.loadProject(tf.name)
    assert MW.currentProject is not None

    return MW
