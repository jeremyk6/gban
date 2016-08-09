# -*- coding: utf-8 -*-

from qgis.core import *
from qgis.gui import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
    
class selectPoint(QgsMapTool):
  def __init__(self,iface):
      canvas = iface.mapCanvas()
      QgsMapTool.__init__(self, canvas)
      return None

  def canvasReleaseEvent(self,e):
      if e.button() == Qt.LeftButton:
         cp = self.toMapCoordinates(QPoint(e.pos().x(), e.pos().y()))
         self.emit( SIGNAL("selectionDone"), cp)
  
  def reset(self):
    pass