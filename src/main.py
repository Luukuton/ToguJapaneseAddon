# -*- coding: utf-8 -*-
# 
import json
from os.path import dirname
from os.path import join, exists

import aqt.editor
import aqt.utils
from anki import Collection
from anki import sound
from anki.hooks import addHook, wrap
from aqt import mw
from aqt.main import AnkiQt
from aqt.qt import *
from aqt.utils import saveGeom, saveSplitter, showInfo
from aqt.webview import AnkiWebView

from . import reading
from .accentExporter import AccentExporter
from .accentsDictionary import AccentsDictionary
from .autoCSSJSHandling import AutoCSSJSHandler
from .exceptionDicts.adjustVerbs import adjustVerbs
from .exceptionDicts.adjustedDict import adjustedDict
from .exceptionDicts.conditionalYomi import conditionalYomi
from .exceptionDicts.counterDict import counterDict
from .exceptionDicts.dontCombineDict import dontCombineDict
from .exceptionDicts.exceptionDict import exceptionDict
from .exceptionDicts.ignoreVerbs import ignoreVerbs
from .exceptionDicts.parseWithMecab import parseWithMecab
from .exceptionDicts.potentialToKihonkei import potentialToKihonkei
from .exceptionDicts.readingOnlyDict import readingOnlyDict
from .exceptionDicts.sameYomiDifferentAccent import sameYomiDifferentAccent
from .exceptionDicts.separateVerbPhrase import separateVerbPhrase
from .exceptionDicts.separateWord import separateWord
from .exceptionDicts.skipList import skipList
from .exceptionDicts.suffixDict import suffixDict
from .exceptionDicts.verbToNoun import verbToNoun
from .gui import JSGui
from .massExporter import MassExporter
from .miutils import miInfo
from .models import MILanguageModels
from .userExceptionManager import UserExceptionManager

colArray = False

addon_path = dirname(__file__)
mecabReading = reading.MecabController()
mecabAccents = reading.MecabController()
UEManager = UserExceptionManager(mw, addon_path)  
AccentDict = AccentsDictionary(addon_path, counterDict, potentialToKihonkei, adjustedDict, conditionalYomi, readingOnlyDict, exceptionDict, sameYomiDifferentAccent, suffixDict)
mw.Exporter = AccentExporter(mw, aqt, UEManager, AccentDict, addon_path, adjustVerbs, separateWord, separateVerbPhrase, ignoreVerbs, dontCombineDict, skipList, parseWithMecab, verbToNoun)
MExporter = MassExporter(mw, mw.Exporter, addon_path)
mw.CSSJSHandler = AutoCSSJSHandler(mw, addon_path)
config = mw.addonManager.getConfig(__name__)
currentNote = False 
currentField = False
currentKey = False
mw.ToguJSSettings = None

languageModeler = MILanguageModels(mw)
addHook("profileLoaded", languageModeler.addModels)

def accentGraphCss():
    css = r" .accentsBlock{line-height:35px;} .museika{width:22px;height:22px;border-radius:50% ;border:1px #db4130 dashed} .pitch-box{position:relative} .pitch-box,.pitch-drop,.pitch-overbar{display:inline-block} .pitch-overbar{background-color:#db4130;height:1px;width:100% ;position:absolute;top:-3px;left:0} .pitch-drop{background-color:#db4130;height:6px;width:2px;position:absolute;top:-3px;right:-2px}"
    aqt.editor._html = aqt.editor._html.replace('</style>', css.replace('%', r'%%') + '</style>')
    
def shortcutCheck(x, key):
    if x == key:
        return False
    else:
        return True

def setupShortcuts(shortcuts, editor):
    if not checkProfile():
        return shortcuts
    config = mw.addonManager.getConfig(__name__)
    keys = [{"hotkey": "F2", "name": 'extra', 'function': lambda editor=editor: mw.Exporter.groupExport(editor)},
            {"hotkey": "F3", "name": 'extra', 'function': lambda editor=editor: mw.Exporter.individualExport(editor)},
            {"hotkey": "F4", "name": 'extra', 'function': lambda editor=editor: mw.Exporter.cleanField(editor)},
            {"hotkey": "F5", "name": 'extra', 'function': lambda editor=editor: UEManager.openAddMenu(editor)}]
    newKeys = shortcuts
    for key in keys:
        newKeys = list(filter(lambda x: shortcutCheck(x[0], key['hotkey']), newKeys))
        newKeys += [(key['hotkey'] , key['function'])]
    shortcuts.clear()
    shortcuts += newKeys
    return

def setupButtons(righttopbtns, editor):
  if not checkProfile():
    return righttopbtns  
  editor._links["individualExport"] = lambda editor: mw.Exporter.individualExport(editor)
  editor._links["cleanField"] = lambda editor: mw.Exporter.cleanField(editor)
  editor._links["openUserExceptionsAdder"] = UEManager.openAddMenu
  iconPath = os.path.join(addon_path, "icons", "userexceptions.svg")
  righttopbtns.insert(0, editor._addButton(
                icon=iconPath,
                cmd='openUserExceptionsAdder',
                tip="Hotkey: F5",
                id=u"+"
            ))
  iconPath = os.path.join(addon_path, "icons", "saku.svg")
  righttopbtns.insert(0, editor._addButton(
                icon= iconPath,
                cmd='cleanField',
                tip="Hotkey: F4",
                id=u"削"
            ))
  iconPath = os.path.join(addon_path, "icons", "go.svg")
  righttopbtns.insert(0, editor._addButton(
                icon= iconPath,
                cmd='individualExport',
                tip="Hotkey: F3",
                id=u"語"
            ))  
  editor._links["groupExport"] = lambda editor: mw.Exporter.groupExport(editor)
  iconPath = os.path.join(addon_path, "icons", "bun.svg")
  righttopbtns.insert(0, editor._addButton(
                icon= iconPath,
                cmd='groupExport',
                tip="Hotkey: F2",
                id=u"文"
            ))
  return righttopbtns

def getConfig():
    return mw.addonManager.getConfig(__name__)

def checkProfile():
    config = getConfig()
    if mw.pm.name in config['Profiles'] or ('all' in config['Profiles'] or 'All' in config['Profiles'] or 'ALL' in config['Profiles']):
        return True
    return False

def setupMenu(browser):
    if not checkProfile():
        return
    a = QAction("Generate Readings/Accents/Audio", browser)
    a.triggered.connect(lambda: MExporter.onRegenerate(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)

       
def loadCollectionArray(self = None, b = None):
    global colArray
    colArray = {}
    loadAllProfileInformation()

def loadAllProfileInformation():
    global colArray
    for prof in mw.pm.profiles():
        cpath = join(mw.pm.base, prof,  'collection.anki2')
        try:
            tempCol = Collection(cpath)
            noteTypes = tempCol.models.all()
            tempCol.close()
            tempCol = None
            noteTypeDict = {}
            for note in noteTypes:
                noteTypeDict[note['name']] = {"cardTypes" : [], "fields" : []}
                for ct in note['tmpls']:
                    noteTypeDict[note['name']]["cardTypes"].append(ct['name'])
                for f in note['flds']:
                    noteTypeDict[note['name']]["fields"].append(f['name'])
            colArray[prof] = noteTypeDict
        except:
            miInfo('<b>Warning:</b><br>One of your profiles could not be loaded. This usually happens if you\'ve just created a new profile and are opening it for the first time.The issue should be fixed after restarting Anki.If it persists, then your profile is corrupted in some way.\n\nYou can fix this corruption by exporting your collection, importing it into a new profile, and then deleting your previous profile. <b>', level='wrn')

def openGui():
    if not mw.ToguJSSettings:
        mw.ToguJSSettings = JSGui(mw, colArray, languageModeler, openGui, mw.CSSJSHandler, UEManager)
    mw.ToguJSSettings.show()
    if mw.ToguJSSettings.windowState() == Qt.WindowMinimized:
            # Window is minimised. Restore it.
           mw.ToguJSSettings.setWindowState(Qt.WindowNoState)
    mw.ToguJSSettings.setFocus()
    mw.ToguJSSettings.activateWindow()

     
def setupGuiMenu():
    addMenu = False
    if not hasattr(mw, 'ToguMainMenu'):
        mw.ToguMainMenu = QMenu('Togu',  mw)
        addMenu = True
    if not hasattr(mw, 'ToguMenuSettings'):
        mw.ToguMenuSettings = []
    if not hasattr(mw, 'ToguMenuActions'):
        mw.ToguMenuActions = []

    setting = QAction("Japanese Settings", mw)
    setting.triggered.connect(openGui)
    mw.ToguMenuSettings.append(setting)
    action = QAction("Add Parsing Overwrite Rule", mw)
    action.triggered.connect(UEManager.openAddMenu)
    mw.ToguMenuActions.append(action)

    mw.ToguMainMenu.clear()
    for act in mw.ToguMenuSettings:
        mw.ToguMainMenu.addAction(act)
    mw.ToguMainMenu.addSeparator()
    for act in mw.ToguMenuActions:
        mw.ToguMainMenu.addAction(act)

    if addMenu:
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.ToguMainMenu)

setupGuiMenu()
AnkiQt.loadProfile = wrap(AnkiQt.loadProfile, loadCollectionArray, 'before')

def selectedText(page):    
    text = page.selectedText()
    if not text:
        return False
    else:
        return text

def addOverwriteRule(self):
    text = selectedText(self)
    if text:
        UEManager.openAddMenu(self, text)

def addToContextMenu(self, m):
    a = m.addAction("Add Rule")
    a.triggered.connect(self.addOverwriteRule)

AnkiWebView.addOverwriteRule = addOverwriteRule
addHook("EditorWebView.contextMenuEvent", addToContextMenu)
addHook("browser.setupMenus", setupMenu)
addHook("browser.setupMenus", setupMenu)
addHook("profileLoaded", UEManager.getUEList)
addHook("profileLoaded", accentGraphCss)
addHook("profileLoaded", mw.CSSJSHandler.injectWrapperElements)    
addHook("setupEditorButtons", setupButtons)
addHook("setupEditorShortcuts", setupShortcuts)

def supportAccept(self):
    if self.addon != os.path.basename(addon_path):
        ogAccept(self)
    txt = self.form.editor.toPlainText()
    try:
        new_conf = json.loads(txt)
    except Exception as e:
        showInfo(_("Invalid configuration: ") + repr(e))
        return
    if not isinstance(new_conf, dict):
        showInfo(_("Invalid configuration: top level object must be a map"))
        return
    if new_conf != self.conf:
        self.mgr.writeConfig(self.addon, new_conf)
        act = self.mgr.configUpdatedAction(self.addon)
        if act:
            act(new_conf)
        if not mw.CSSJSHandler.injectWrapperElements():
            return

    saveGeom(self, "addonconf")
    saveSplitter(self.form.splitter, "addonconf")
    self.hide()


ogAccept = aqt.addons.ConfigEditor.accept
aqt.addons.ConfigEditor.accept = supportAccept

def customFind(self, query, order=False, reverse=False):
    if 'nobr' in query:
        query = query.replace('nobr', '').replace('\n', '').replace('\r', '').strip()
        newquery = []
        for char in query:
            newquery.append(char)
        query = '*'.join(newquery)
    return ogFind(self, query, order)

ogFind = Collection.find_cards
Collection.find_cards = customFind

def getFieldName(fieldId, note):
    fields = mw.col.models.field_names(note.note_type())
    field = fields[int(fieldId)]
    return field


def bridgeReroute(self, cmd):
    if checkProfile():
        if cmd.startswith('textToJReading'):
            splitList = cmd.split(':||:||:')
            if self.note.id == int(splitList[3]):
                field = getFieldName(int(splitList[2]), self.note)
                mw.Exporter.finalizeGroupExport(self, splitList[1], field, self.note)
            return
        elif cmd.startswith('individualJExport'):
            splitList = cmd.split(':||:||:')
            if self.note.id == int(splitList[3]):
                field = getFieldName(splitList[2], self.note)
                mw.Exporter.finalizeIndividualExport(self, splitList[1], field, self.note)
            return
    ogReroute(self, cmd)
    
ogReroute = aqt.editor.Editor.onBridgeCmd 
aqt.editor.Editor.onBridgeCmd = bridgeReroute


def grabAudioForMultiReadingWord(word, yomi):
    idx = 0
    if word in AccentDict.dictionary:
        entry = AccentDict.dictionary[word]
        for term in entry:
            if term[1] == yomi:
                if term[4]:
                    try:
                        if term[4][idx]:
                            return term[4][idx][2]
                    except:
                        for a in term[4]:
                            if a[0] == mw.Exporter.dictParser.kaner(yomi):
                                return a[2]    
                        return term[4][0][2]
            idx+= 1
    return False


def grabAudioForMultiPitchWord(word, yomi, idx):
    if word in AccentDict.dictionary:
        entry = AccentDict.dictionary[word]
        for term in entry:  
            if term[1] == yomi:
                if term[4]:
                    if term[4][idx]:
                        return term[4][idx][2]   
    return False

def fetchAudioFromDict(word, yomi, idx):
    if idx == 100:
        return grabAudioForMultiReadingWord(word, yomi)
    else:
        return grabAudioForMultiPitchWord(word, yomi, idx)
    

def clickPlayAudio(cmd):

    splitList = cmd.split(';')
    path = fetchAudioFromDict(splitList[1],  splitList[2], int(splitList[3]))
    if path:
        path = join(addon_path, "user_files", 'accentAudio', path)
        if exists(path):
            sound.play(path)

def revBridgeReroute(self, cmd):
    if cmd.startswith('playAudio;'):
        if checkProfile() and getConfig()['PlayAudioOnClick'] == 'on':
            clickPlayAudio(cmd)
            return
    else:
        ogRevReroute(self, cmd)

ogRevReroute = aqt.reviewer.Reviewer._linkHandler 
aqt.reviewer.Reviewer._linkHandler = revBridgeReroute

def prevBridgeReroute(self, cmd):
    if cmd.startswith('playAudio;'):
        if checkProfile() and getConfig()['PlayAudioOnClick'] == 'on':
            clickPlayAudio(cmd)
            return
    else:
        ogAnkiWebBridge(self, cmd)



ogAnkiWebBridge = AnkiWebView._onBridgeCmd
AnkiWebView._onBridgeCmd = prevBridgeReroute

