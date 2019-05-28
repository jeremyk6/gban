# -*- coding: utf-8 -*-

# Gban: geocode and reverse geocode in France using the BAN.
# Author: Jérémy Kalsron
#         jeremy.kalsron@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QUrl, QEventLoop
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import QAction, QActionGroup, QApplication, QDialogButtonBox, QInputDialog, QMessageBox

from qgis.core import (QgsWkbTypes, QgsCoordinateReferenceSystem, QgsCoordinateTransform, 
                        QgsNetworkContentFetcher, QgsPoint, QgsProject)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand

import json
import unicodedata

from . import resources
import os

class Gban:

    def __init__(self, iface):
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            os.path.dirname(__file__),
            'i18n',
            'gban_{}.qm'.format(locale))
        
        self.translator = None
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        self.exclusive = QActionGroup( self.iface.mainWindow() )

        self.actions = []
        self.menu = '&Gban'
        self.toolbar = self.iface.addToolBar('Gban')
        self.toolbar.setObjectName('Gban')
        
        #Select tool initialization
        self.tool = QgsMapToolEmitPoint(self.canvas)
        self.tool.canvasClicked.connect(self.doReverseGeocoding)
        self.tool.deactivated.connect(self.uncheckReverseGeocoding)

        self.rb = QgsRubberBand(self.iface.mapCanvas(), QgsWkbTypes.PointGeometry)
        self.rb.setColor( QColor(255, 0, 0) )
        self.rb.setWidth( 5 )
                                   
    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu('&Gban', action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar
        
    def tr(self, message):
        return QCoreApplication.translate('Gban', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        checkable=False,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        if checkable:
            self.exclusive.addAction( action )

        self.actions.append(action)

        return action

    def initGui(self):
        icon_path = ":/plugins/gban/resources/icon_geocode.png"
        self.add_action(
            icon_path,
            text=self.tr("Geocoding"),
            callback=self.geocoding,
            parent=self.iface.mainWindow()
        )
        icon_path = ":/plugins/gban/resources/icon_reversegeocode.png"
        self.add_action(
            icon_path,
            checkable = True,
            text=self.tr("Reverse geocoding"),
            callback=self.reverseGeocoding,
            parent=self.iface.mainWindow()
        )
        
    def geocoding(self):
        self.rb.reset(QgsWkbTypes.PointGeometry)
        address, ok = QInputDialog.getText(self.iface.mainWindow(), self.tr("Address"), self.tr("Input address to geocode:"))
        if ok and address:
            self.doGeocoding(address)
         
    def doGeocoding(self, address):
        address = unicodedata.normalize('NFKD', unicode(address))
        url = "http://api-adresse.data.gouv.fr/search/?q="+address.replace(" ", "%20")
        
        result = self.request(url)

        try:
            data = json.loads(result)
            features = data["features"]
            if len(features) > 0:
                feature_list = []
                for feature in features:
                    feature_list.append(feature["properties"]["label"]+" - "+str(round(feature["properties"]["score"]*100))+"%")
                feature, ok = QInputDialog.getItem(self.iface.mainWindow(), self.tr("Result"), "", feature_list)
                if ok:
                    index = feature_list.index(feature)
                    x = features[index]["geometry"]["coordinates"][0]
                    y = features[index]["geometry"]["coordinates"][1]
                    transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(4326), 
                                                        self.canvas.mapSettings().destinationCrs(), QgsProject().instance())
                    point = transform.transform(x, y)
                    self.rb.addPoint(point)
                    self.iface.mapCanvas().setCenter(point)
                    self.iface.mapCanvas().refresh()
            else:
                QMessageBox.information(self.iface.mainWindow(), self.tr("Result"), self.tr("No result."))
        except ValueError:
            QMessageBox.critical(self.iface.mainWindow(), self.tr("Error"), self.tr("An error occured. Check your network settings (proxy)."))

    
    def reverseGeocoding(self):
        self.canvas.setMapTool(self.tool)
        
    def doReverseGeocoding(self, point_orig):
        transform = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), 
                                            QgsCoordinateReferenceSystem(4326), QgsProject().instance())
        point = transform.transform(point_orig)
        url = "http://api-adresse.data.gouv.fr/reverse/?lon="+str(point.x())+"&lat="+str(point.y())

        result = self.request(url)

        try:
            data = json.loads(result)
            
            if len(data["features"]) > 0:
                address = data["features"][0]["properties"]["label"]
                clicked = QMessageBox.information(self.iface.mainWindow(), self.tr("Result"), address, QMessageBox.Ok, QMessageBox.Save)
                if clicked == QMessageBox.Save:
                    QApplication.clipboard().setText(address)
            else:
                QMessageBox.information(self.iface.mainWindow(), self.tr("Result"), self.tr("No result."))
        except ValueError:
            QMessageBox.critical(self.iface.mainWindow(), self.tr("Error"), self.tr("An error occured. Check your network settings (proxy)."))

    def uncheckReverseGeocoding(self):
        self.exclusive.checkedAction().setChecked(False)

    def request(self, url):
        ''' prepare the request and return the result of the reply
        '''
        fetcher = QgsNetworkContentFetcher()
        fetcher.fetchContent(QUrl(url))
        evloop = QEventLoop()
        fetcher.finished.connect(evloop.quit)
        evloop.exec_(QEventLoop.ExcludeUserInputEvents)
        return fetcher.contentAsString()