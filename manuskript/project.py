'''

@author: olivier.massot, 2019
'''
from _collections import OrderedDict
import logging
import os
import re
import shutil
import string
from zipfile import BadZipFile
import zipfile

from PyQt5.QtCore import QObject, Qt, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QColor, QStandardItem
from lxml import etree as ET
from path import Path

from manuskript import constants
from manuskript.converters import HTML2PlainText
from manuskript.enums import Character, World, Plot, PlotStep, Outline
from manuskript.functions import iconColor, iconFromColorString
from manuskript.models import outlineItem
from manuskript.models.characterModel import characterModel, CharacterInfo
from manuskript.models.outlineModel import outlineModel
from manuskript.models.plotModel import plotModel
from manuskript.models.worldModel import worldModel


try:
    import zlib  # Used with zipfile for compression @UnusedImport
    COMPRESSION = zipfile.ZIP_DEFLATED
except:
    COMPRESSION = zipfile.ZIP_STORED

logger = logging.getLogger('manuskript')

cache = {}

class Project(QObject):
    """ A Manusckript writing project """
    version = None
    
    def __init__(self, filename=""):
        super().__init__()
        
        self.filename = Path(filename)
        self.settings = ""
        self.zipped = False
        
        self.mdlFlatData = QStandardItemModel(self)
        self.mdlCharacter = characterModel(self)
        # self.mdlPersosProxy = persosProxyModel(self)
        # self.mdlPersosInfos = QStandardItemModel(self)
        self.mdlLabels = QStandardItemModel(self)
        self.mdlStatus = QStandardItemModel(self)
        self.mdlPlots = plotModel(self)
        self.mdlOutline = outlineModel(self)
        self.mdlWorld = worldModel(self)
        
        self._loadingErrors = []
        self._savingErrors = []
    
    @property
    def name(self):
        return self.filename.name.stripext() or tr("My Project")
    
    @property
    def loadingErrors(self):
        return self._loadingErrors
    
    @property
    def savingErrors(self):
        return self._savingErrors
    
    @staticmethod
    def findVersionFromFile(filename):
        """ find the format version of the project file """
        try:
            zf = zipfile.ZipFile(filename)
            if "VERSION" in zf.namelist():
                return int(zf.read("VERSION"))
            elif "MANUSKRIPT" in zf.namelist():
                return int(zf.read("MANUSKRIPT"))
            else:
                return 0
        except zipfile.BadZipFile:
            with open(filename, "r") as f:
                return int(f.read())
    
    @staticmethod
    def isZipped(self, filename):
        try:
            zipfile.ZipFile(filename)
            return True
        except zipfile.BadZipFile:
            return False
        
    @classmethod
    def load(cls, filename):
        
        version = Project.findVersionFromFile(filename)
    
        logger.info("Loading: %s (format version: %s)", filename, version)
    
        if version == 0:
            return ProjectV0.load(filename)
            
        elif version == 1:
            return ProjectV1.load(filename)
        
        else:
            logger.critical("unknwown version: %s", version)
            return Project()
    
    def save(self, *args, **kwargs):
        """ reimplemented in the ProjectV0 et ProjectV1 subclasses """
        raise NotImplementedError()
        
    def save_as(self, filename, *args, **kwargs):
        self.filename = filename
        self.save(*args, **kwargs)

class ProjectV0(Project):
    version = 0
    
    @classmethod
    def load(cls, filename):

        project = ProjectV0(filename)

        try:
            zf = zipfile.ZipFile(filename)
            project.zipped = True
            files = {Path(f).normpath(): zf.read(f) for f in zf.namelist()}
        except BadZipFile:
            files = {f.normpath(): f.text() for f in filename.walkfiles()}
        
        if "flatModel.xml" in files:
            cls.loadStandardItemModelXML(project.mdlFlatData, files["flatModel.xml"], fromString=True)
        else:
            project._loadingErrors.append("flatModel.xml")
    
        if "perso.xml" in files:
            project.loadStandardItemModelXMLForCharacters(project.mdlCharacter, files["perso.xml"])
        else:
            project._loadingErrors.append("perso.xml")
    
        if "world.xml" in files:
            cls.loadStandardItemModelXML(project.mdlWorld, files["world.xml"], fromString=True)
        else:
            project._loadingErrors.append("world.xml")
    
        if "labels.xml" in files:
            cls.loadStandardItemModelXML(project.mdlLabels, files["labels.xml"], fromString=True)
        else:
            project._loadingErrors.append("labels.xml")
    
        if "status.xml" in files:
            cls.loadStandardItemModelXML(project.mdlStatus, files["status.xml"], fromString=True)
        else:
            project._loadingErrors.append("status.xml")
    
        if "plots.xml" in files:
            cls.loadStandardItemModelXML(project.mdlPlots, files["plots.xml"], fromString=True)
        else:
            project._loadingErrors.append("plots.xml")
    
        if "outline.xml" in files:
            project.mdlOutline.loadFromXML(files["outline.xml"], fromString=True)
        else:
            project._loadingErrors.append("outline.xml")
    
        if "settings.pickle" in files:
            project.settings.load(files["settings.pickle"], fromString=True)
        else:
            project._loadingErrors.append("settings.pickle")
    
        return project
    
    def save(self, *args, **kwargs):
        files = [(self.saveStandardItemModelXML(self.mdlFlatData), "flatModel.xml"),
#                  (saveStandardItemModelXML(mw.mdlCharacter), "perso.xml")),
                 (self.saveStandardItemModelXML(self.mdlWorld), "world.xml"),
                 (self.saveStandardItemModelXML(self.mdlLabels), "labels.xml"),
                 (self.saveStandardItemModelXML(self.mdlStatus), "status.xml"),
                 (self.saveStandardItemModelXML(self.mdlPlots), "plots.xml"),
                 (self.mdlOutline.saveToXML(), "outline.xml"),
                 (self.settings.save(), "settings.pickle")
            ]
        logger.warning("file format 0 does not save characters !")
    
        zf = zipfile.ZipFile(self.filename, mode="w")
        
        for content, filename in files:
            zf.writestr(filename, content, compress_type=COMPRESSION)
    
        zf.close()
    
    def loadStandardItemModelXML(self, mdl, xml, fromString=False):
        """Load data to a QStandardItemModel mdl from xml.
        By default xml is a filename. If fromString=True, xml is a string containing the data."""
    
        if not fromString:
            try:
                _ = ET.parse(xml)
            except:
                logger.error("Failed.")
                return
        else:
            root = ET.fromstring(xml)
    
        # Header
        hLabels = []
        vLabels = []
        for l in root.find("header").find("horizontal").findall("label"):
            hLabels.append(l.attrib["text"])
        for l in root.find("header").find("vertical").findall("label"):
            vLabels.append(l.attrib["text"])
    
        # Populates with empty items
        for _ in enumerate(vLabels):
            row = []
            for _ in enumerate(hLabels):
                row.append(QStandardItem())
            mdl.appendRow(row)
    
        # Data
        data = root.find("data")
        self.loadItem(data, mdl)

    def loadItem(self, root, mdl, parent=QModelIndex()):
        for row in root:
            r = int(row.attrib["row"])
            for col in row:
                c = int(col.attrib["col"])
                item = mdl.itemFromIndex(mdl.index(r, c, parent))
                if not item:
                    item = QStandardItem()
                    mdl.itemFromIndex(parent).setChild(r, c, item)
    
                if col.text:
                    item.setText(col.text)
    
                if "color" in col.attrib:
                    item.setIcon(iconFromColorString(col.attrib["color"]))
    
                if len(col) != 0:
                    self.loadItem(col, mdl, mdl.indexFromItem(item))        
    
    @staticmethod
    def loadStandardItemModelXMLForCharacters(mdl, xml):
        """
        Loads a standardItemModel saved to XML by version 0, but for the new characterModel.
        @param mdl: characterModel
        @param xml: the content of the xml
        @return: nothing
        """
        root = ET.fromstring(xml)
        data = root.find("data")
    
        for row in data:
            char = Character(mdl)
    
            for col in row:
                c = int(col.attrib["col"])
    
                # Value
                if col.text:
                    char._data[c] = col.text
    
                # Color
                if "color" in col.attrib:
                    char.setColor(QColor(col.attrib["color"]))
    
                # Infos
                if len(col) != 0:
                    for rrow in col:
                        info = CharacterInfo(char)
                        for ccol in rrow:
                            cc = int(ccol.attrib["col"])
                            if cc == 11 and ccol.text:
                                info.description = ccol.text
                            if cc == 12 and ccol.text:
                                info.value = ccol.text
                        char.infos.append(info)
    
            mdl.characters.append(char)

    @staticmethod
    def saveStandardItemModelXML(mdl, xml=None):
        """Saves the given QStandardItemModel to XML.
        If xml (filename) is given, saves to xml. Otherwise returns as string."""
    
        root = ET.Element("model")
        root.attrib["version"] = constants.VERSION
    
        # Header
        header = ET.SubElement(root, "header")
        vHeader = ET.SubElement(header, "vertical")
        for x in range(mdl.rowCount()):
            vH = ET.SubElement(vHeader, "label")
            vH.attrib["row"] = str(x)
            vH.attrib["text"] = str(mdl.headerData(x, Qt.Vertical))
    
        hHeader = ET.SubElement(header, "horizontal")
        for y in range(mdl.columnCount()):
            hH = ET.SubElement(hHeader, "label")
            hH.attrib["row"] = str(y)
            hH.attrib["text"] = str(mdl.headerData(y, Qt.Horizontal))
    
        # Data
        data = ET.SubElement(root, "data")
        ProjectV0.saveItem(data, mdl)
    
        if xml:
            ET.ElementTree(root).write(xml, encoding="UTF-8", xml_declaration=True, pretty_print=True)
        else:
            return ET.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)

    @staticmethod
    def saveItem(root, mdl, parent=QModelIndex()):
        for x in range(mdl.rowCount(parent)):
            row = ET.SubElement(root, "row")
            row.attrib["row"] = str(x)
    
            for y in range(mdl.columnCount(parent)):
                col = ET.SubElement(row, "col")
                col.attrib["col"] = str(y)
                if mdl.data(mdl.index(x, y, parent), Qt.DecorationRole) != None:
                    color = iconColor(mdl.data(mdl.index(x, y, parent), Qt.DecorationRole)).name(QColor.HexArgb)
                    col.attrib["color"] = color if color != "#ff000000" else "#00000000"
                if mdl.data(mdl.index(x, y, parent)) != "":
                    col.text = mdl.data(mdl.index(x, y, parent))
                if mdl.hasChildren(mdl.index(x, y, parent)):
                    ProjectV0.saveItem(col, mdl, mdl.index(x, y, parent))


class ProjectV1(Project):
    version = 1
    
    characterMap = OrderedDict([
        (Character.name, "Name"),
        (Character.ID,   "ID"),
        (Character.importance, "Importance"),
        (Character.motivation, "Motivation"),
        (Character.goal, "Goal"),
        (Character.conflict, "Conflict"),
        (Character.epiphany, "Epiphany"),
        (Character.summarySentence, "Phrase Summary"),
        (Character.summaryPara, "Paragraph Summary"),
        (Character.summaryFull, "Full Summary"),
        (Character.notes, "Notes"),
    ])
        
    @classmethod
    def load(cls, filename):
        """
        Loads a project.
        @return: the loaded Project object
        """
        project = ProjectV1(filename)
    
        # Read file(s) and store everything in a dict
        try:
            zf = zipfile.ZipFile(filename)
            project.zipped = True
            logger.debug("Loading {} (zip)".format(filename))
            
            files = {Path(f).normpath(): zf.read(f) for f in zf.namelist()}
            
            for f in files:
                if f.ext not in [".xml", ".opml"]:
                    files[f] = files[f].decode("utf-8")
            
        except BadZipFile:
            logger.debug("Loading {} (folder)".format(filename))
            
            files = {f.normpath(): f.text(encoding=('utf-8' if f.ext in (".xml", "opml") else None)) 
                     for f in filename.walkfiles() if not f.name[0] == "."}
    
        # Sort files by keys
        files = OrderedDict(sorted(files.items()))
    
        # Settings
        if "settings.txt" in files:
            project.settings = files["settings.txt"]
        else:
            project._loadingErrors.append("settings.txt")

        # Labels
        mdl = project.mdlLabels
        mdl.appendRow(QStandardItem(""))  # Empty = No labels
        if "labels.txt" in files:
            logger.debug("Reading labels")
            for s in files["labels.txt"].split("\n"):
                if not s:
                    continue
    
                m = re.search(r"^(.*?):\s*(.*)$", s)
                txt, col = m.group(1), m.group(2)
                logger.debug("* Add status: {} ({})".format(txt, col))
                icon = iconFromColorString(col)
                mdl.appendRow(QStandardItem(icon, txt))
    
        else:
            project._loadingErrors.append("labels.txt")
    
        # Status
        mdl = project.mdlStatus
        mdl.appendRow(QStandardItem(""))  # Empty = No status
        if "status.txt" in files:
            logger.debug("Reading Status")
            for s in files["status.txt"].split("\n"):
                if not s:
                    continue
                logger.debug("* Add status: %s", s)
                mdl.appendRow(QStandardItem(s))
        else:
            project._loadingErrors.append("status.txt")
    
        # Infos
        mdl = project.mdlFlatData
        if "infos.txt" in files:
            logger.debug("Reading infos")
            md, body = ProjectV1.parseMMDFile(files["infos.txt"], asDict=True)
            names = ["Title", "Subtitle", "Serie", "Volume", "Genre", "License", "Author", "Email"]
            mdl.appendRow([QStandardItem(md.get(name, "")) for name in names])
        else:
            project._loadingErrors.append("infos.txt")
    
        # Summary
        mdl = project.mdlFlatData
        if "summary.txt" in files:
            logger.debug("Reading summary")
            md, body = ProjectV1.parseMMDFile(files["summary.txt"], asDict=True)
            names = ["Situation", "Sentence", "Paragraph", "Page", "Full"]
            mdl.appendRow([QStandardItem(md.get(name, "")) for name in names])
        else:
            project._loadingErrors.append("summary.txt")
    
        # Plots
        mdl = project.mdlPlots
        if "plots.xml" in files:
            logger.debug("Reading plots")
            root = ET.fromstring(files["plots.xml"])
    
            for plot in root:
                # Create row
                row = ProjectV1.getStandardItemRowFromXMLEnum(plot, Plot)
                logger.debug("* Add plot: %s", row[0].text())
    
                # Characters
                if row[Plot.characters].text():
                    IDs = row[Plot.characters].text().split(",")
                    item = QStandardItem()
                    for ID in IDs:
                        item.appendRow(QStandardItem(ID.strip()))
                    row[Plot.characters] = item
    
                # Subplots
                for step in plot:
                    row[Plot.steps].appendRow(
                        ProjectV1.getStandardItemRowFromXMLEnum(step, PlotStep)
                    )
    
                # Add row to the model
                mdl.appendRow(row)
        else:
            project._loadingErrors.append("plots.xml")
    
        # World
        mdl = project.mdlWorld
        if "world.opml" in files:
            logger.debug("Reading World")
            root = ET.fromstring(files["world.opml"])
            body = root.find("body")
    
            for outline in body:
                row = ProjectV1.getOutlineItem(outline, World)
                mdl.appendRow(row)
        else:
            project._loadingErrors.append("world.opml")
    
        # Characters
        mdl = project.mdlCharacter
        logger.debug("Reading Characters")
        for f in [f for f in files if "characters" in f]:
            md, body = ProjectV1.parseMMDFile(files[f])
            c = mdl.addCharacter()
            c.lastPath = f
    
            color_found = False
            for desc, val in md:
    
                # Base infos
                if desc in ProjectV1.characterMap.values():
                    key = [key for key, value in ProjectV1.characterMap.items() if value == desc][0]
                    index = c.index(key.value)
                    mdl.setData(index, val)
    
                # Character color
                elif desc == "Color" and not color_found:
                    c.setColor(QColor(val))
                    # We remember the first time we found "Color": it is the icon color.
                    # If "Color" comes a second time, it is a Character's info.
                    color_found = True
    
                # Character's infos
                else:
                    c.infos.append(CharacterInfo(c, desc, val))
    
            logger.debug("* Adds {} ({})".format(c.name(), c.ID()))
    
        # Texts
        # We read outline form the outline folder. If revisions are saved, then there's also a revisions.xml which contains
        # everything, but the outline folder takes precedence (in cases it's been edited outside of manuskript.
        mdl = project.mdlOutline
        logger.debug("Reading outline")
        outline = OrderedDict()
    
        # We create a structure of imbricated OrderedDict to store the whole tree.
        for f in [f for f in files if "outline" in f]:
            split = f.split(os.path.sep)[1:] # FIXME: use relpath instead of split
    
            last = ""
            parent = outline
            parentLastPath = Path("outline")
            for i in split:
                if last:
                    parent = parent[last]
                    parentLastPath = parentLastPath / last
                last = i
    
                if not i in parent:
                    # If not last item, then it is a folder
                    if i != split[-1]:
                        parent[i] = OrderedDict()
    
                    # If file, we store it
                    else:
                        parent[i] = files[f]
    
                    # We store f to add it later as lastPath
                    parent[i + ":lastPath"] = parentLastPath / i
    
        # We now just have to recursively add items.
        ProjectV1.addTextItems(mdl, outline)
    
        # Adds revisions
        if "revisions.xml" in files:
            root = ET.fromstring(files["revisions.xml"])
            ProjectV1.appendRevisions(mdl, root)
    
        # Check IDS
        mdl.rootItem.checkIDs()
        
        return project
    
    def save(self, *args, **kwargs):
        """
        Saves the project. If zip is False, the project is saved as a multitude of plain-text files for the most parts
        and some XML or zip? for settings and stuff.
        If zip is True, everything is saved as a single zipped file. Easier to carry around, but does not allow
        collaborative work, versioning, or third-party editing.
        @param zip: if True, saves as a single file. If False, saves as plain-text. If None, tries to determine based on
        settings.
        @return: True if successful, False otherwise.
        """
        logger.info("Saving to: %s", "zip" if self.zipped else "folder")
    
        # List of files to be written, removed and moved
        files, removes, moves = [], [], []
    
        # File format version
        files.append(("MANUSKRIPT", self.version))
    
        # General infos (book and author)
        # Saved in plain text, in infos.txt
        path = Path("infos.txt")
        content = ""
        for col, name in enumerate(["Title", "Subtitle", "Serie", "Volume", "Genre", "License", "Author", "Email"]):
            item = self.mdlFlatData.item(0, col)
            val = item.text().strip() if item else ""
            if not val:
                continue
            content += "{name}:{spaces}{value}\n".format(
                name=name,
                spaces=" " * (15 - len(name)),
                value=val
            )
        files.append((path, content))
    
        # Summary
        # In plain text, in summary.txt
        path = Path("summary.txt")
        content = ""
        for col, name in enumerate(["Situation", "Sentence", "Paragraph", "Page", "Full"]):
            item = self.mdlFlatData.item(1, col)
            val = item.text().strip() if item else ""
            if not val:
                continue
            content += self.formatMetaData(name, val, 12)
    
        files.append((path, content))
    
        # Label & Status
        # In plain text
        for mdl, path in [(self.mdlStatus, "status.txt"), (self.mdlLabels, "labels.txt")]:
    
            content = ""
    
            # We skip the first row, which is empty and transparent
            for i in range(1, mdl.rowCount()):
                color = ""
                if mdl.data(mdl.index(i, 0), Qt.DecorationRole) is not None:
                    color = iconColor(mdl.data(mdl.index(i, 0), Qt.DecorationRole)).name(QColor.HexRgb)
                    color = color if color != "#ff000000" else "#00000000"
    
                text = mdl.data(mdl.index(i, 0))
    
                if text:
                    content += "{name}{color}\n".format(
                        name=text,
                        color="" if color == "" else ":" + " " * (20 - len(text)) + color
                    )
    
            files.append((path, content))
    
        # Characters
        # In a character folder
        path = Path("characters") /  "{name}.txt"
        mdl = self.mdlCharacter
    
        # Review characters
        for c in mdl.characters:
    
            # Generates file's content
            content = ""
            
            for m in ProjectV1.characterMap:
                val = mdl.data(c.index(m.value)).strip()
                if val:
                    content += self.formatMetaData(ProjectV1.characterMap[m], val, 20)
    
            # Character's color:
            content += self.formatMetaData("Color", c.color().name(QColor.HexRgb), 20)
    
            # Character's infos
            for info in c.infos:
                content += self.formatMetaData(info.description, info.value, 20)
    
            # generate file's path
            cpath = path.format(name="{ID}-{slugName}".format(
                ID=c.ID(),
                slugName=self.slugify(c.name())
            ))
    
            # Has the character been renamed?
            if c.lastPath and cpath != c.lastPath:
                moves.append((c.lastPath, cpath))
    
            # Update character's path
            c.lastPath = cpath
    
            files.append((cpath, content))
    
        # Texts
        # In an outline folder
        mdl = self.mdlOutline
    
        # Go through the tree
        f, m, r = self.exportOutlineItem(mdl.rootItem)
        files += f
        moves += m
        removes += r
    
        # Writes revisions (if asked for)
        if kwargs.get("save_revisions", False):
            files.append(("revisions.xml", mdl.saveToXML()))
    
        # World
        # Either in an XML file, or in lots of plain texts?
        # More probably text, since there might be writing done in third-party.
        path = "world.opml"
        mdl = self.mdlWorld
    
        root = ET.Element("opml")
        root.attrib["version"] = "1.0"
        body = ET.SubElement(root, "body")
        self.addWorldItem(body, mdl)
        content = ET.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)
        files.append((path, content))
    
        # Plots
        # Either in XML or lots of plain texts?
        # More probably XML since there is not really a lot if writing to do (third-party)
        path = "plots.xml"
        mdl = self.mdlPlots
    
        root = ET.Element("root")
        self.addPlotItem(root, mdl)
        content = ET.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)
        files.append((path, content))
    
        # Settings
        # Saved in readable text (json) for easier versioning. But they mustn't be shared, it seems.
        files.append(("settings.txt", self.settings))
    
        # We check if the file exist and we have write access. If the file does
        # not exists, we check the parent folder, because it might be a new project.
        if self.filename.exists() and not self.filename.access(os.W_OK) or \
           not self.filename.exists() and not self.filename.parent.access(os.W_OK):
            logger.error("you don't have write access to save this project there.")
            return
    
        if self.zipped:
            # Save to zip
            zf = zipfile.ZipFile(self.filename, mode="w")
    
            for filename, content in files:
                zf.writestr(filename, content, compress_type=COMPRESSION)
    
            zf.close()
    
        else:
            # Save to plain text
            
            # Folder containing file: name of the project file (without .msk extension)
            dir_ = self.filename.parent
            foldername = self.name
            
            # Debug
            logger.info("Saving to folder %s", foldername)
    
            # If cache is empty (meaning we haven't loaded from disk), we wipe folder, just to be sure.
            if not cache:
                if Path(dir_ / foldername).exists():
                    shutil.rmtree(dir_ / foldername)
    
            # Moving files that have been renamed
            for old, new in moves:
    
                # Get full path
                oldPath = dir_ / foldername / old
                newPath = dir_ / foldername / new
    
                # Move the old file to the new place
                try:
                    oldPath.rename(newPath)
                    logger.debug("* Renaming/moving {} to {}".format(old, new))
                except FileNotFoundError:
                    # Maybe parent folder has been renamed
                    pass
    
                # Update cache
                cache2 = {}
                for f in cache:
                    f2 = f.replace(old, new)
                    if f2 != f:
                        logger.info("* Updating cache: %s %s", f, f2)
                    cache2[f2] = cache[f]
                cache = cache2
    
            # Writing files
            for path, content in files:
                filename = dir_ / foldername / path
                filename.parent.makedirs_p()
    
                # Check if content is in cache, and write if necessary
                if path not in cache or cache[path] != content:
                    logger.debug("* Writing file {} ({})".format(path, "not in cache" if path not in cache else "different"))
                    # mode = "w" + ("b" if type(content) == bytes else "")
                    if type(content) == bytes:
                        with open(filename, "wb") as f:
                            f.write(content)
                    else:
                        with open(filename, "w", encoding='utf8') as f:
                            f.write(content)
    
                    cache[path] = content
    
            # Removing phantoms
            for path in [p for p in cache if p not in [p for p, c in files]]:
                filename = dir_ / foldername / path
                logger.debug("* Removing", path)
    
                if filename.isdir():
                    shutil.rmtree(filename)
                else:  
                    filename.remove()
    
                # Clear cache
                cache.pop(path, 0)
    
            # Removing empty directories
            for root, dirs, files in Path(dir_ / foldername / "outline").walk():
                for d in dirs:
                    newDir = root / d
                    newDir.removedirs_p()
    
            # Write the project file's content
            with open(self, "w", encoding='utf8') as f:
                f.write(str(self.version))  # Format version number
    
    @staticmethod
    def formatMetaData(name, value, tabLength=10):

        # Multiline formatting
        if len(value.split("\n")) > 1:
            value = "\n".join([" " * (tabLength + 1) + l for l in value.split("\n")])[tabLength + 1:]
    
        # Avoid empty description (don't know how much MMD loves that)
        if name == "":
            name = "None"
    
        # Escapes ":" in name
        name = name.replace(":", "_.._")
    
        return "{name}:{spaces}{value}\n".format(
            name=name,
            spaces=" " * (tabLength - len(name)),
            value=value
        )

    @staticmethod
    def slugify(s):
        """
        A basic slug function, that escapes all spaces to "_" and all non letters/digits to "-".
        @param name: name to slugify (str)
        @return: str
        """
        return re.sub("\\W", "-", re.sub("\\s", "_", s))
    
    @staticmethod
    def exportOutlineItem(root):
        """
        Takes an outline item, and returns three lists:
        1. of (`filename`, `content`), representing the whole tree of files to be written, in multimarkdown.
        2. of (`filename`, `filename`) listing files to be moved
        3. of `filename`, representing files to be removed.
    
        @param root: OutlineItem
        @return: [(str, str)], [(str, str)], [str]
        """
        files, moves, removes = [], [], []
    
        k = 0
        for child in root.children():
            spath = Path.joinpath(*ProjectV1.outlineItemPath(child))
    
            k += 1
    
            # Has the item been renamed?
            lp = child._lastPath
            if lp and spath != lp:
                moves.append((lp, spath))
                logger.debug("%s has been renamed (%s → %s)", child.title(), lp, spath)
                logger.debug(" → We mark for moving: %s", lp)
    
            # Updates item last's path
            child._lastPath = spath
    
            # Generating content
            if child.type() == "folder":
                fpath = spath / "folder.txt"
                content = ProjectV1.outlineToMMD(child)
                files.append((fpath, content))
    
            elif child.type() == "md":
                content = ProjectV1.outlineToMMD(child)
                files.append((spath, content))
    
            else:
                logger.warning("Unknown type")
    
            f, m, r = ProjectV1.exportOutlineItem(child)
            files += f
            moves += m
            removes += r
    
        return files, moves, removes
    
    @staticmethod
    def addWorldItem(root, mdl, parent=QModelIndex()):
        """
        Lists elements in a world model and create an OPML xml file.
        @param root: an Etree element
        @param mdl:  a worldModel
        @param parent: the parent index in the world model
        @return: root, to which sub element have been added
        """
        # List every row (every world item)
        for x in range(mdl.rowCount(parent)):
    
            # For each row, create an outline item.
            outline = ET.SubElement(root, "outline")
            for y in range(mdl.columnCount(parent)):
    
                val = mdl.data(mdl.index(x, y, parent))
    
                if not val:
                    continue
    
                for w in World:
                    if y == w.value:
                        outline.attrib[w.name] = val
    
                if mdl.hasChildren(mdl.index(x, y, parent)):
                    ProjectV1.addWorldItem(outline, mdl, mdl.index(x, y, parent))
    
        return root

    @staticmethod
    def addPlotItem(root, mdl, parent=QModelIndex()):
        """
        Lists elements in a plot model and create an xml file.
        @param root: an Etree element
        @param mdl:  a plotModel
        @param parent: the parent index in the plot model
        @return: root, to which sub element have been added
        """
    
        # List every row (every plot item)
        for x in range(mdl.rowCount(parent)):
    
            # For each row, create an outline item.
            outline = ET.SubElement(root, "plot")
            for y in range(mdl.columnCount(parent)):
    
                index = mdl.index(x, y, parent)
                val = mdl.data(index)
    
                for w in Plot:
                    if y == w.value and val:
                        outline.attrib[w.name] = val
    
                # List characters as attrib
                if y == Plot.characters:
                    if mdl.hasChildren(index):
                        characters = []
                        for cX in range(mdl.rowCount(index)):
                            for cY in range(mdl.columnCount(index)):
                                cIndex = mdl.index(cX, cY, index)
                                characters.append(mdl.data(cIndex))
                        outline.attrib[Plot.characters.name] = ",".join(characters)
    
                    elif Plot.characters.name in outline.attrib:
                        outline.attrib.pop(Plot.characters.name)
    
                # List resolution steps as sub items
                elif y == Plot.steps:
                    if mdl.hasChildren(index):
                        for cX in range(mdl.rowCount(index)):
                            step = ET.SubElement(outline, "step")
                            for cY in range(mdl.columnCount(index)):
                                cIndex = mdl.index(cX, cY, index)
                                # If empty, returns None, which creates trouble later with lxml, so default to ""
                                val = mdl.data(cIndex) or ""
    
                                for w in PlotStep:
                                    if cY == w.value and w.name:
                                        step.attrib[w.name] = val
    
                    elif Plot.steps.name in outline.attrib:
                        outline.attrib.pop(Plot.steps.name)
    
        return root
    
    @staticmethod
    def getOutlineItem(item, enum):
        """
        Reads outline items from an opml file. Returns a row of QStandardItem, easy to add to a QStandardItemModel.
        @param item: etree item
        @param enum: enum to read keys from
        @return: [QStandardItem]
        """
        row = ProjectV1.getStandardItemRowFromXMLEnum(item, enum)
        logger.debug("* Add worldItem: %s", row[0].text())
        for child in item:
            sub = ProjectV1.getOutlineItem(child, enum)
            row[0].appendRow(sub)
    
        return row
    
    @staticmethod
    def outlineItemPath(item):
        """
        Returns the outlineItem file path (like the path where it will be written on the disk). As a list of folder's
        name. To be joined by os.path.join.
        @param item: outlineItem
        @return: list of folder's names
        """
        # Root item
        if not item.parent():
            return ["outline"]
        else:
            # Count the number of siblings for padding '0'
            siblings = item.parent().childCount()
    
            # We check if multiple items have the same name
            # If so, we add "-ID" to their name
            siblingsNames = [s.title() for s in item.parent().children()]
            if siblingsNames.count(item.title()) > 1:
                title = "{}-{}".format(item.title(), item.ID())
            else:
                title = item.title()
    
            name = "{ID}-{name}{ext}".format(
                ID=str(item.row()).zfill(len(str(siblings))),
                name=ProjectV1.slugify(title),
                ext="" if item.type() == "folder" else ".md"
            )
            return ProjectV1.outlineItemPath(item.parent()) + [name]

    @staticmethod
    def outlineFromMMD(text, parent):
        """
        Creates outlineItem from multimarkdown file.
        @param text: content of the file
        @param parent: appends item to parent (outlineItem)
        @return: outlineItem
        """
    
        item = outlineItem(parent=parent)
        md, body = ProjectV1.parseMMDFile(text, asDict=True)
    
        # Store metadata
        for k in md:
            if k in Outline.__members__:                              #@UndefinedVariable
                item.setData(Outline.__members__[k], str(md[k]))            #@UndefinedVariable
    
        # Store body
        item.setData(Outline.text, str(body))
    
        # Set file format to "md"
        # (Old version of manuskript had different file formats: text, t2t, html and md)
        # If file format is html, convert to plain text:
        if item.type() == "html":
            item.setData(Outline.text, HTML2PlainText(body))
        if item.type() in ["txt", "t2t", "html"]:
            item.setData(Outline.type, "md")
    
        return item

    @staticmethod
    def outlineToMMD(item):
        content = ""
    
        # We don't want to write some datas (computed)
        exclude = [Outline.wordCount, Outline.goal, Outline.goalPercentage, Outline.revisions, Outline.text]
        # We want to force some data even if they're empty
        force = [Outline.compile]
    
        for attrib in Outline:
            if attrib in exclude:
                continue
            val = item.data(attrib.value)
            if val or attrib in force:
                content += ProjectV1.formatMetaData(attrib.name, str(val), 15)
    
        content += "\n\n"
        content += item.data(Outline.text)
    
        return content

    @staticmethod
    def getStandardItemRowFromXMLEnum(item, enum):
        """
        Reads and etree item and creates a row of QStandardItems by cross-referencing an enum.
        Returns a list of QStandardItems that can be added to a QStandardItemModel by appendRow.
        @param item: the etree item
        @param enum: the enum
        @return: list of QStandardItems
        """
        row = []
        for _ in range(len(enum)):
            row.append(QStandardItem(""))
    
        for name in item.attrib:
            if name in enum.__members__:
                row[enum[name].value] = QStandardItem(item.attrib[name])
        return row

    @staticmethod
    def parseMMDFile(text, asDict=False):
        """
        Takes the content of a MultiMarkDown file (str) and returns:
        1. A list containing metadatas: (description, value) if asDict is False.
           If asDict is True, returns metadatas as an OrderedDict. Be aware that if multiple metadatas have the same description
           (which is stupid, but hey), they will be lost except the last one.
        2. The body of the file
        @param text: the content of the file
        @return: (list, str) or (OrderedDict, str)
        """
        md = []
        mdd = OrderedDict()
        body = []
        descr = ""
        val = ""
        inBody = False
        for s in text.split("\n"):
            if not inBody:
                m = re.match(r"^([^\s].*?):\s*(.*)$", s)
                if m:
                    # Commit last metadata
                    if descr:
                        if descr == "None":
                            descr = ""
                        md.append((descr, val))
                        mdd[descr] = val
                    descr = ""
                    val = ""
    
                    # Store new values
                    descr = m.group(1)
                    val = m.group(2)
    
                elif s[:4] == "    ":
                    val += "\n" + s.strip()
    
                elif s == "":
                    # End of metadatas
                    inBody = True
    
                    # Commit last metadata
                    if descr:
                        if descr == "None":
                            descr = ""
                        md.append((descr, val))
                        mdd[descr] = val
    
            else:
                body.append(s)
    
        # We remove the second empty line (since we save with two empty lines)
        if body and body[0] == "":
            body = body[1:]
    
        body = "\n".join(body)
    
        if not asDict:
            return md, body
        else:
            return mdd, body

    @staticmethod
    def addTextItems(mdl, odict, parent=None):
        """
        Adds a text / outline items from an OrderedDict.
        @param mdl: model to add to
        @param odict: OrderedDict
        @return: nothing
        """
        if parent is None:
            parent = mdl.rootItem
    
        for k in odict:
    
            # In case k is a folder:
            if type(odict[k]) == OrderedDict and "folder.txt" in odict[k]:
    
                # Adds folder
                logger.debug("{}* Adds {} to {} (folder)".format("  " * parent.level(), k, parent.title()))
                item = ProjectV1.outlineFromMMD(odict[k]["folder.txt"], parent=parent)
                item._lastPath = odict[k + ":lastPath"]
    
                # Read content
                ProjectV1.addTextItems(mdl, odict[k], parent=item)
    
            # k is not a folder
            elif type(odict[k]) == str and k != "folder.txt" and not ":lastPath" in k:
                logger.debug("{}* Adds {} to {} (file)".format("  " * parent.level(), k, parent.title()))
                item = ProjectV1.outlineFromMMD(odict[k], parent=parent)
                item._lastPath = odict[k + ":lastPath"]
    
            elif not ":lastPath" in k and k != "folder.txt":
                logger.warning("* Strange things in file %s", k)

    @staticmethod
    def appendRevisions(mdl, root):
        """
        Parse etree item to find outlineItem's with revisions, and adds them to model `mdl`.
        @param mdl: outlineModel
        @param root: etree
        @return: nothing
        """
        for child in root:
            # Recursively go through items
            if child.tag == "outlineItem":
                ProjectV1.appendRevisions(mdl, child)
    
            # Revision found.
            elif child.tag == "revision":
                # Get root's ID
                ID = root.attrib["ID"]
                if not ID:
                    logger.error("* Serious problem: no ID!")
                    continue
    
                # Find outline item in model
                item = mdl.getItemByID(ID)
                if not item:
                    logger.error("* Error: no item whose ID is", ID)
                    continue
    
                # Store revision
                logger.info("* Appends revision ({}) to {}".format(child.attrib["timestamp"], item.title()))
                item.appendRevision(child.attrib["timestamp"], child.attrib["text"])