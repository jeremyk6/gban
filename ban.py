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

from qgis.PyQt.QtCore import QUrl, QEventLoop

from qgis.core import QgsNetworkContentFetcher, QgsPointXY

import json
import unicodedata

def geocode(address):
    url = "http://api-adresse.data.gouv.fr/search/?q="+unicodedata.normalize('NFKD', unicode(address)).replace(" ", "%20")
    response = request(url)
    data = json.loads(response)
    features = data["features"]
    results = []
    for feature in features:
        results.append(
            {
                "address":feature["properties"]["label"],
                "score":round(feature["properties"]["score"]*100),
                "point":QgsPointXY(
                    feature["geometry"]["coordinates"][0],
                    feature["geometry"]["coordinates"][1]
                )
            }
        )
    return results

def reverseGeocode(point):
    url = "http://api-adresse.data.gouv.fr/reverse/?lon="+str(point.x())+"&lat="+str(point.y())
    response = request(url)
    data = json.loads(response)
    result = ""
    if len(data["features"]) > 0:
        result = data["features"][0]["properties"]["label"]
    return result

def request(url):
    fetcher = QgsNetworkContentFetcher()
    fetcher.fetchContent(QUrl(url))
    evloop = QEventLoop()
    fetcher.finished.connect(evloop.quit)
    evloop.exec_(QEventLoop.ExcludeUserInputEvents)
    return fetcher.contentAsString()
