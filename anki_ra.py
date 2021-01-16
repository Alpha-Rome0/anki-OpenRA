# -*- coding: utf-8 -*-
"""
Anki Add-on: Anki Quake 3
Gamify your Anki session using Quake3. Review cards to get ammunition, health and armor

uses some code from the Handy Answer Keys Shortcuts, by Vitalie Spinu
and Progress Bar, by Unknown author, SebastienGllmt, Glutanimate 

License: GNU AGPLv3 or later <https://www.gnu.org/licenses/agpl.html>
"""

### imports
### =======

from __future__ import unicode_literals

from anki.hooks import addHook, wrap, runHook
from anki import version as anki_version

from aqt.qt import *
from aqt import mw
from aqt.utils import tooltip
from aqt.reviewer import Reviewer


import PyQt4.QtCore

import struct

import math
import random
import json
import httplib
from threading import Thread
import time
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

### constants related to progress bar
### ---------------------------------

qtxt = "#f1ced1" # Percentage color, if text visible.
qbg = "#7d2029" # Background color of progress bar.
qfg = "#91131f" # Foreground color of progress bar.
qbr = 0 # Border radius (> 0 for rounded corners).

# optionally restricts progress bar width
maxWidth = ""  # (e.g. "5px". default: "")

orientationHV = Qt.Horizontal # Show bar horizontally (side to side). Use with top/bottom dockArea.
# orientationHV = Qt.Vertical # Show bar vertically (up and down). Use with right/left dockArea.

pbStyle = ""

dockArea = Qt.TopDockWidgetArea # Shows bar at the top. Use with horizontal orientation.

__version__ = '0.1'

def cardReview():
    multiplier = 1
    ease = mw.reviewer.card.factor / 1000.0
    if ease < 2.5:
        rn = random.random()
        if rn >= .98:
            multiplier = 10
        elif rn >= .9:
            multiplier = 5
        elif rn >= .75:
            multiplier = 2
        if multiplier > 1:
            parent = mw.app.activeWindow() or mw
            mb = QMessageBox(parent)
            mb.setText("{}x review!".format(multiplier))
            mb.exec_()
    send_request("/review", multiplier * 150 * max(0.1, -5.0 / 3 * ease + 31.0 / 6))

def send_request(uri, multiplier = 1):
    hdr = {
        "content-type": "text/plain",
        "multiplier": multiplier
        }
    try:
        conn = httplib.HTTPConnection('localhost:12345')
        conn.request('POST', uri, "", hdr)
        response = conn.getresponse()
        data = response.read() # same as r.text in 3.x
        update_bar(data)
    except:
        update_bar("Start the game!")

def answerCard(self, ease, _old):
    if ease != 1:
        cardReview()
    return _old(self, ease)
    

def keyHandler(self, evt, _old):
    key = unicode(evt.text())
    if key == "z":
        try:# throws an error on undo -> do -> undo pattern,  otherwise works fine
            mw.onUndo()
        except:
            pass
    elif key in ["q", "e",]: # allow answering with a and d keys, to keep fingers on WASD
        cnt = mw.col.sched.answerButtons(mw.reviewer.card) # Get button count
        isq = self.state == "question"
        if isq:
            return self._showAnswer()
        if key == "q":
            return self._answerCard(1)
        elif key == "e":
            return self._answerCard(cnt)
        else:
            return _old(self, evt)
    else:
        return _old(self, evt)    
        
## Set up variables for progress bar

failed = 0
progressBar = None
mx = 0

pbdStyle = QStyleFactory.create("%s" % (pbStyle)) # Don't touch.

#Defining palette in case needed for custom colors with themes.
palette = QPalette()
palette.setColor(QPalette.Base, QColor(qbg))
palette.setColor(QPalette.Highlight, QColor(qfg))
palette.setColor(QPalette.Button, QColor(qbg))
palette.setColor(QPalette.WindowText, QColor(qtxt))
palette.setColor(QPalette.Window, QColor(qbg))

if maxWidth:
    if orientationHV == Qt.Horizontal:
        restrictSize = "max-height: %s;" % maxWidth
    else:
        restrictSize = "max-width: %s;" % maxWidth
else:
    restrictSize = ""

def _dock(pb):
    """Dock for the progress bar. Giving it a blank title bar,
        making sure to set focus back to the reviewer."""
    dock = QDockWidget()
    tWidget = QWidget()
    dock.setObjectName("pbDock")
    dock.setWidget(pb)
    dock.setTitleBarWidget( tWidget )
    
    ## Note: if there is another widget already in this dock position, we have to add ourself to the list

    # first check existing widgets
    existing_widgets = [widget for widget in mw.findChildren(QDockWidget) if mw.dockWidgetArea(widget) == dockArea]

    # then add ourselves
    mw.addDockWidget(dockArea, dock)

    # stack with any existing widgets
    if len(existing_widgets) > 0:
        mw.setDockNestingEnabled(True)

        if dockArea == Qt.TopDockWidgetArea or dockArea == Qt.BottomDockWidgetArea:
            stack_method = Qt.Vertical
        if dockArea == Qt.LeftDockWidgetArea or dockArea == Qt.RightDockWidgetArea:
            stack_method = Qt.Horizontal
        mw.splitDockWidget(existing_widgets[0], dock, stack_method)

    if qbr > 0 or pbdStyle != None:
        # Matches background for round corners.
        # Also handles background for themes' percentage text.
        mw.setPalette(palette)
    mw.web.setFocus()
    return dock

    
def create_progressbar():    
    """Initialize and set parameters for progress bar, adding it to the dock."""

    progressBar = QProgressBar()
    progressBar.setTextVisible(True)
    progressBar.setValue(0)
    progressBar.setFormat("Start the game.")    
    progressBar.setOrientation(orientationHV)
    if pbdStyle == None:
        progressBar.setStyleSheet(
        '''
                    QProgressBar
                {
                    text-align:center;
                    color:%s;
                    background-color: %s;
                    border-radius: %dpx;
                    %s
                }
                    QProgressBar::chunk
                {
                    background-color: %s;
                    margin: 0px;
                    border-radius: %dpx;
                }
                ''' % (qtxt, qbg, qbr, restrictSize, qfg, qbr))
    else:
        progressBar.setStyle(pbdStyle)
        progressBar.setPalette(palette)
    _dock(progressBar)
    return progressBar
    
def setup_progressbar():
    global progressBar
    progressBar = create_progressbar()

def update_bar(cash):
    if progressBar:
        progressBar.setFormat("Cash: " + cash)

def refresh_loop():
    while True:
        send_request("/")
        time.sleep(1)

def start_up():
    thread = Thread(target = refresh_loop)
    thread.daemon = True
    thread.start()      


#addHook("showAnswer", cardReview)
addHook("profileLoaded", start_up)
addHook("profileLoaded", setup_progressbar)

Reviewer._answerCard = wrap(Reviewer._answerCard, answerCard, "around")
Reviewer._keyHandler = wrap(Reviewer._keyHandler, keyHandler, "around")

        

