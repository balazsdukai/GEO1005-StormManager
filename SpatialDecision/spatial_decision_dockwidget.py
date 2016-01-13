# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SpatialDecisionDockWidget
                                 A QGIS plugin
 This is a SDSS template for the GEO1005 course
                             -------------------
        begin                : 2015-11-02
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Jorge Gil, TU Delft
        email                : j.a.lopesgil@tudelft.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4 import QtGui, QtCore, uic
from qgis.core import *
from qgis.networkanalysis import *
# Initialize Qt resources from file resources.py
import resources
import os
import os.path
import random
from . import utility_functions as uf

# example_chart
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import dates
import datetime as dt
import numpy as np

import sys
import inspect
try:
    import pandas as pd
except ImportError, e:
    cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"external")))
    if cmd_subfolder not in sys.path:
        sys.path.insert(0, cmd_subfolder)
    import pandas as pd

from matplotlib.ticker import FuncFormatter
import math
from matplotlib import pyplot as plt
from matplotlib import colors
import matplotlib.cm as cm

FORM_CLASS, _ = uic.loadUiType(os.path.join(
        os.path.dirname(__file__), 'spatial_decision_dockwidget_base.ui'))


class SpatialDecisionDockWidget(QtGui.QDockWidget, FORM_CLASS):
    closingPlugin = QtCore.pyqtSignal()
    # custom signals
    updateAttribute = QtCore.pyqtSignal(str)

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(SpatialDecisionDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.canvas.setSelectionColor(QtGui.QColor(255, 0, 0))

        # set up GUI operation signals
        # data
        self.iface.projectRead.connect(self.updateLayers)
        self.iface.newProjectCreated.connect(self.updateLayers)
        self.selectLayerCombo.activated.connect(self.setSelectedLayer)
        self.selectAttributeCombo.activated.connect(self.setSelectedAttribute)
        self.showButton.clicked.connect(self.updateValueWidget)

        # signals
        self.canvas.renderStarting.connect(self.loadSymbols)
        self.canvas.selectionChanged.connect(self.updateValueWidget)

        # analysis
        self.graph = QgsGraph()
        self.tied_points = []
        self.shortestRouteButton.clicked.connect(self.calculateRoute)
        self.clearRouteButton.clicked.connect(self.deleteRoutes)
        self.assignButton.clicked.connect(self.assignFacility)
        self.clearAssignmentButton.clicked.connect(self.clearAssignment)
        self.changeStatusButton.clicked.connect(self.changeEventStatus)

        # visualisation

        # set current UI restrictions
        # initialisation
        self.eventlayer = uf.getLegendLayerByName(self.iface, 'Reports')
        self.hospitalLayer = uf.getLegendLayerByName(self.iface, 'Hospital')
        self.firestationLayer = uf.getLegendLayerByName(self.iface, 'Firestation')
        self.hospital_name=''
        self.firestation_name=''
        self.event_source=self.eventlayer.selectedFeatures()

        # example_chart
        # add matplotlib Figure to chartFrame
        self.chart_figure = Figure()
        self.chart_subplot_radar = self.chart_figure.add_subplot(211, projection='polar')
        self.chart_subplot_bar = self.chart_figure.add_subplot(212)
        self.chart_figure.tight_layout()
        self.chart_figure.text(0.05, 0.955, 'Data from:', fontsize = 12, horizontalalignment = 'left')
        self.chart_figure.text(0.05, 0.93, self.getWindDate(), fontsize = 12, fontweight='bold', horizontalalignment = 'left')
        self.chart_canvas = FigureCanvas(self.chart_figure)
        self.chartLayout.addWidget(self.chart_canvas)

        self.updateLayers()

        # run simple tests

    def closeEvent(self, event):
        # disconnect interface signals
        self.iface.projectRead.disconnect(self.updateLayers)
        self.iface.newProjectCreated.disconnect(self.updateLayers)

        self.closingPlugin.emit()
        event.accept()

    #######
    #   Data functions
    #######

    def updateLayers(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectLayerCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectLayerCombo.addItems(layer_names)
            self.setSelectedLayer()
            self.plotChart()
        #else:
        #    self.clearChart()  # example_chart

    def setSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface, layer_name)
        self.updateAttributes(layer)

    def getSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface, layer_name)
        return layer

    def updateAttributes(self, layer):
        self.selectAttributeCombo.clear()
        if layer:
            fields = uf.getFieldNames(layer)
            # self.clearChart()
            self.selectAttributeCombo.addItems(fields)
            # send list to the report list window
            # self.clearReport()
            # self.updateReport(fields)

    def setSelectedAttribute(self):
        field_name = self.selectAttributeCombo.currentText()
        self.updateAttribute.emit(field_name)

    def getSelectedAttribute(self):
        field_name = self.selectAttributeCombo.currentText()
        return field_name

    def getAllFeatures(self, layer):
        layer.selectAll()
        allFeatures = layer.selectedFeatures()
        layer.removeSelection()
        return allFeatures

    def loadSymbols(self):
        if (self.eventlayer):
            filepath = os.path.join(os.path.dirname(__file__), 'svg', '')
            event_rules = (
                ('fire_active_humanDmg', '"dmgType" LIKE fire AND "resolved" is\ "no" AND "civilDmg"> 0', filepath + 'fire_active_humanDmg.svg', None,10),
                ('building_active_humanDmg', '"dmgType" LIKE \'building\' AND "resolved" LIKE \'no\' AND "civilDmg"> 0 ', filepath + 'building_active_humanDmg.svg', None,10),
                ('tree_active_humanDmg', '"dmgType" LIKE \'tree\' AND "resolved" LIKE \'no\' AND "civilDmg"> 0 ', filepath + 'tree_active_humanDmg.svg', None,10),
                ('fire_active', '"dmgType" LIKE \'fire\' AND "resolved" LIKE \'no\' AND "civilDmg"= 0', filepath + 'fire_active.svg', None,8),
                ('building_active', '"dmgType" LIKE \'building\' AND "resolved" LIKE \'no\' AND "civilDmg"= 0 ', filepath + 'building_active.svg', None,8),
                ('tree_active', '"dmgType" LIKE \'tree\' AND "resolved" LIKE \'no\' AND "civilDmg"= 0', filepath + 'tree_active.svg', None,8),
                ('fire_resolved_humanDmg', '"dmgType" LIKE fire AND "resolved" LIKE yes AND "civilDmg"> 0', filepath + 'fire_resolved_humanDmg.svg', None,10),
                ('building_resolved_humanDmg', '"dmgType" LIKE \'building\' AND "resolved" LIKE \'yes\' AND "civilDmg"> 0 ', filepath + 'building_resolved_humanDmg.svg', None,10),
                ('tree_resolved_humanDmg', '"dmgType" LIKE \'tree\' AND "resolved" LIKE \'yes\' AND "civilDmg"> 0 ', filepath + 'tree_resolved_humanDmg.svg', None,10),
                ('fire_resolved', '"dmgType" LIKE \'fire\' AND "resolved" LIKE \'yes\' AND "civilDmg"= 0', filepath + 'fire_resolved.svg', None,8),
                ('building_resolved', '"dmgType" LIKE \'building\' AND "resolved" LIKE \'yes\' AND "civilDmg"= 0 ', filepath + 'building_resolved.svg', None,8),
                ('tree_resolved', '"dmgType" LIKE \'tree\' AND "resolved" LIKE \'yes\' AND "civilDmg"= 0', filepath + 'tree_resolved.svg', None,8)

            )
            symbol = QgsSymbolV2.defaultSymbol(self.eventlayer.geometryType())
            renderer = QgsRuleBasedRendererV2(symbol)
            root_rule = renderer.rootRule()

            for label, expression, path, scale, size in event_rules:
                # create a clone (i.e. a copy) of the default rule
                rule = root_rule.children()[0].clone()
                # set the label, expression and color
                rule.setLabel(label)
                rule.setFilterExpression(expression)
                symbol_layer = QgsSvgMarkerSymbolLayerV2()
                symbol_layer.setSize(size)
                symbol_layer.setPath(path)
                rule.symbol().appendSymbolLayer(symbol_layer)
                rule.symbol().deleteSymbolLayer(0)
                # set the scale limits if they have been specified
                if scale is not None:
                    rule.setScaleMinDenom(scale[0])
                    rule.setScaleMaxDenom(scale[1])
                # append the rule to the list of rules
                root_rule.appendChild(rule)

            # delete the default rule
            root_rule.removeChildAt(0)

            # apply the renderer to the layer
            self.eventlayer.setRendererV2(renderer)

        if (self.hospitalLayer):
            filepath = os.path.join(os.path.dirname(__file__), 'svg', '')
            hospital_rules = ('hospital', filepath + 'hospital.svg', None, 5)
            symbol = QgsSymbolV2.defaultSymbol(self.hospitalLayer.geometryType())
            renderer = QgsRuleBasedRendererV2(symbol)
            root_rule = renderer.rootRule()

            label, path, scale, size = hospital_rules
            # create a clone (i.e. a copy) of the default rule
            rule = root_rule.children()[0].clone()
            # set the label, expression and color
            rule.setLabel(label)
            # rule.setFilterExpression(expression)
            symbol_layer = QgsSvgMarkerSymbolLayerV2()
            symbol_layer.setSize(size)
            symbol_layer.setPath(path)
            rule.symbol().appendSymbolLayer(symbol_layer)
            rule.symbol().deleteSymbolLayer(0)
            # set the scale limits if they have been specified
            if scale is not None:
                rule.setScaleMinDenom(scale[0])
                rule.setScaleMaxDenom(scale[1])
            # append the rule to the list of rules
            root_rule.appendChild(rule)

            # delete the default rule
            root_rule.removeChildAt(0)

            # apply the renderer to the layer
            self.hospitalLayer.setRendererV2(renderer)

        if (self.firestationLayer):
            filepath = os.path.join(os.path.dirname(__file__), 'svg', '')
            firestation_rules = ('firestation', filepath + 'firestation.svg', None, 5)
            symbol = QgsSymbolV2.defaultSymbol(self.firestationLayer.geometryType())
            renderer = QgsRuleBasedRendererV2(symbol)
            root_rule = renderer.rootRule()

            label, path, scale, size = firestation_rules
            # create a clone (i.e. a copy) of the default rule
            rule = root_rule.children()[0].clone()
            # set the label, expression and color
            rule.setLabel(label)
            # rule.setFilterExpression(expression)
            symbol_layer = QgsSvgMarkerSymbolLayerV2()
            symbol_layer.setSize(size)
            symbol_layer.setPath(path)
            rule.symbol().appendSymbolLayer(symbol_layer)
            rule.symbol().deleteSymbolLayer(0)
            # set the scale limits if they have been specified
            if scale is not None:
                rule.setScaleMinDenom(scale[0])
                rule.setScaleMaxDenom(scale[1])
            # append the rule to the list of rules
            root_rule.appendChild(rule)

            # delete the default rule
            root_rule.removeChildAt(0)

            # apply the renderer to the layer
            self.firestationLayer.setRendererV2(renderer)

    #######
    #    Analysis functions
    #######

    # route functions
    def getNetwork(self):
        roads_layer = uf.getLegendLayerByName(self.iface, 'Roads')
        if roads_layer:
            # see if there is an obstacles layer to subtract roads from the network
            obstacles_layer = uf.getLegendLayerByName(self.iface, "Obstacles")
            if obstacles_layer:
                # retrieve roads outside obstacles (inside = False)
                features = uf.getFeaturesByIntersection(roads_layer, obstacles_layer, False)
                # add these roads to a new temporary layer
                road_network = uf.createTempLayer('Temp_Network', 'LINESTRING', roads_layer.crs().postgisSrid(), [], [])
                road_network.dataProvider().addFeatures(features)
            else:
                road_network = roads_layer
            return road_network
        else:
            return

    def buildNetwork(self, eventFeature, facilityName):
        self.network_layer = self.getNetwork()
        if self.network_layer:
            # get the points to be used as origin and destination
            # in this case gets the centroid of the selected features
            facilitylayer = uf.getLegendLayerByName(self.iface, facilityName)
            self.selected_sources = self.getAllFeatures(facilitylayer)
            self.event_source = eventFeature
            source_points = [feature.geometry().centroid().asPoint() for feature in self.event_source]
            source_points.extend([feature.geometry().centroid().asPoint() for feature in self.selected_sources])
            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
                # the tied points are the new source_points on the graph
                if self.graph and self.tied_points:
                    text = "network is built for %s points" % len(self.tied_points)
                    #self.insertReport(text)

        return

    def shortestRoute(self, tied_points):
        options = len(tied_points)
        if options > 1:
            # origin and destination are given as an index in the tied_points list
            origin = 0
            temp_lengh = 99999
            shortest_route = QgsFeature()
            for destination in range(1, options):
                # calculate the shortest path for the given origin and destination
                path = uf.calculateRouteDijkstra(self.graph, self.tied_points, origin, destination)
                # Get length of the geometry QgsGeometry.fromPolyline(path).length()
                # store the route results in temporary layer called "Routes"
                routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
                # create one if it doesn't exist
                if not routes_layer:
                    attribs = ['length']
                    types = [QtCore.QVariant.Double]
                    routes_layer = uf.createTempLayer('Routes', 'LINESTRING', self.network_layer.crs().postgisSrid(),
                                                      attribs, types)
                    uf.loadTempLayer(routes_layer)

                # insert route line
                provider = routes_layer.dataProvider()
                geometry_type = provider.geometryType()
                for i, geom in enumerate([path]):
                    fet = QgsFeature()
                    if geometry_type == 1:
                        fet.setGeometry(QgsGeometry.fromPoint(geom))
                    elif geometry_type == 2:
                        fet.setGeometry(QgsGeometry.fromPolyline(geom))
                        # in the case of polygons, instead of coordinates we insert the geometry
                    elif geometry_type == 3:
                        fet.setGeometry(geom)
                    route_length = fet.geometry().length()
                    if route_length < temp_lengh:
                        temp_lengh = route_length
                        shortest_route = fet
                        facility_name = self.selected_sources[destination - 1].attribute('name')
            shortest_route.setAttributes([route_length])
            provider.addFeatures([shortest_route])
            provider.updateExtents()
            return facility_name

    def calculateRoute(self):
        event = self.eventlayer.selectedFeatures()
        self.hospital_name=''
        self.firestation_name=''
        if len(event)!=1:
            return
        else:
            civilDmg = event[0].attribute('civilDmg')
            if civilDmg ==0 :
                # origin and destination must be in the set of tied_points
                self.buildNetwork(event,'Firestation')
                self.firestation_name=self.shortestRoute(self.tied_points)
            else:
                self.buildNetwork(event,'Firestation')
                self.firestation_name=self.shortestRoute(self.tied_points)
                self.buildNetwork(event,'Hospital')
                self.hospital_name=self.shortestRoute(self.tied_points)
            routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
            self.refreshCanvas(routes_layer)

    def deleteRoutes(self):
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        if routes_layer:
            ids = uf.getAllFeatureIds(routes_layer)
            routes_layer.startEditing()
            for id in ids:
                routes_layer.deleteFeature(id)
            routes_layer.commitChanges()

    def assignFacility(self):
        self.event_source=self.eventlayer.selectedFeatures()
        if len(self.event_source)!=1:
            return
        if isinstance(self.event_source[0]['unitOnSite'],QtCore.QPyNullVariant)==True:
            self.event_source[0]['unitOnSite']=''
        self.eventlayer.startEditing()
        firestationString=''
        hospitalString=''
        if self.event_source[0]['unitOnSite'].find('firestation:')!=-1 and self.event_source[0]['unitOnSite'].find('hospital:')!=-1:
            firestationString=self.event_source[0]['unitOnSite'].split(' hospital:')[0][12:]
            hospitalString=self.event_source[0]['unitOnSite'].split(' hospital:')[1]
        elif self.event_source[0]['unitOnSite'].find('firestation:')!=-1 and self.event_source[0]['unitOnSite'].find('hospital:')==-1:
            firestationString=self.event_source[0]['unitOnSite'].split('firestation:')[1]
        elif self.event_source[0]['unitOnSite'].find('firestation:')==-1 and self.event_source[0]['unitOnSite'].find('hospital:')!=-1:
            hospitalString=self.event_source[0]['unitOnSite'].split('hospital:')[1]
        firestationlist=[]
        hospitallist=[]
        for i in range(self.firestationLayer.selectedFeatureCount()):
            if firestationString.find(self.firestationLayer.selectedFeatures()[i].attribute('name'))==-1:
                firestationlist.append(self.firestationLayer.selectedFeatures()[i].attribute('name'))
        for i in range(self.hospitalLayer.selectedFeatureCount()):
            if hospitalString.find(self.hospitalLayer.selectedFeatures()[i].attribute('name'))==-1:
                hospitallist.append(self.hospitalLayer.selectedFeatures()[i].attribute('name'))
        delimiter=','
        self.event_source[0]['unitOnSite']=''
        firestationresult=[]
        hospitalresult=[]
        if firestationString+delimiter.join(firestationlist)+self.firestation_name!='':
            firestationresult.extend([firestationString])
            firestationresult.extend(firestationlist)
            if firestationString.find(self.firestation_name)==-1:
                firestationresult.extend([self.firestation_name])
            if '' in firestationresult:
                firestationresult.remove('')
            self.event_source[0]['unitOnSite']+='firestation:'+delimiter.join(firestationresult)
        if hospitalString+delimiter.join(hospitallist)+self.hospital_name!='':
            hospitalresult.extend([hospitalString])
            hospitalresult.extend(hospitallist)
            if hospitalString.find(self.hospital_name)==-1:
                hospitalresult.extend([self.hospital_name])
            if '' in hospitalresult:
                hospitalresult.remove('')
            self.event_source[0]['unitOnSite']+=' hospital:'+delimiter.join(hospitalresult)
        self.eventlayer.updateFeature(self.event_source[0])
        self.eventlayer.commitChanges()
        self.hospital_name=''
        self.firestation_name=''

    def clearAssignment(self):
        features = self.eventlayer.selectedFeatures()
        self.eventlayer.startEditing()
        for feature in features:
            feature.setAttribute('unitOnSite',QtCore.QPyNullVariant)
            self.eventlayer.updateFeature(feature)
        self.eventlayer.commitChanges()
    def changeEventStatus(self):
        self.event_source=self.eventlayer.selectedFeatures()
        if len(self.event_source)!=1:
            return
        else:
            self.eventlayer.startEditing()
            if self.event_source[0]['resolved']=='yes':
                self.event_source[0]['resolved']='no'
            else:
                self.event_source[0]['resolved']='yes'
            self.eventlayer.updateFeature(self.event_source[0])
            self.eventlayer.commitChanges()
            self.loadSymbols()
            self.canvas.refresh()
    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()

    # feature selection
    def selectFeaturesBuffer(self):
        layer = self.getSelectedLayer()
        buffer_layer = uf.getLegendLayerByName(self.iface, "Buffers")
        if buffer_layer and layer:
            uf.selectFeaturesByIntersection(layer, buffer_layer, True)

    def selectFeaturesRange(self):
        layer = self.getSelectedLayer()
        # for the range takes values from the service area (max) and buffer (min) text edits
        max = self.getServiceAreaCutoff()
        min = self.getBufferCutoff()
        if layer and max and min:
            # gets list of numeric fields in layer
            fields = uf.getNumericFields(layer)
            if fields:
                # selects features with values in the range
                uf.selectFeaturesByRangeValues(layer, fields[0].name(), min, max)

    #######
    #    Visualisation functions
    #######

    def updateValueWidget(self):
        """Retrieves selected feature attribute values and sends them to valueWidget"""
        self.valueWidget.clear()
        layer = self.getSelectedLayer()
        field_name = self.getSelectedAttribute()
        vals = uf.getFieldValues(layer, field_name, selection=True)
        attribute = map(str, vals[0])
        # if not attribute:
        #     attribute = 'NULL'
        self.valueWidget.addItems(attribute)

    # example_chart
    def plotChart(self):
        """
        Adapted from Jorge Gil.
        Returns
        -------
        Draws the maplotlib figures. The wind rose plot and the wind speed bar plot.
        """
        plot_layer = uf.getLegendLayerByName(self.iface, 'Wind')  # in my case it is fixed to the wind layer
        if plot_layer:
            starttime = uf.getAllFeatureValues(plot_layer, 'starttime')
            starttime = [dt.datetime.strptime(date, "%Y-%m-%d %H:%M:%S") for date in starttime]
            direction = uf.getAllFeatureValues(plot_layer, 'direction')
            speed = uf.getAllFeatureValues(plot_layer, 'speed')

            # ======================
            # From: https://github.com/phobson/python-metar/blob/master/metar/graphics.py
            # prepare and create the wind direction plot
            #     '''
            #     Plots a Wind Rose. Feed it a dataframe with 'speed'(kmh) and
            #     'direction' degrees clockwise from north (columns)
            #     '''
            self.chart_subplot_radar.cla()

            d = {'starttime': starttime, 'direction': uf.getAllFeatureValues(plot_layer, 'direction'),
                 'speed': uf.getAllFeatureValues(plot_layer, 'speed')
                 }
            dataframe = pd.DataFrame(d)
            speedcol='speed'
            dircol='direction'

            def _get_wind_counts(dataframe, maxSpeed, speedcol, dircol, factor=1):
                group = dataframe[dataframe[speedcol]*factor < maxSpeed].groupby(by=dircol)
                counts = group.size()
                return counts[counts.index != 0]

            def _convert_dir_to_left_radian(directions):
                N = directions.shape[0]
                barDir = directions * np.pi/180. - np.pi/N
                barWidth = [2 * np.pi / N]*N
                return barDir, barWidth

            def _pct_fmt(x, pos=0):
                return '%0.1f%%' % (100*x)

            # set up the axis
            self.chart_subplot_radar.xaxis.grid(True, which='major', linestyle='-', alpha='0.125', zorder=0)
            self.chart_subplot_radar.yaxis.grid(True, which='major', linestyle='-', alpha='0.125', zorder=0)
            self.chart_subplot_radar.set_theta_zero_location("N")
            self.chart_subplot_radar.set_theta_direction('clockwise')

            # speed bins and colors
            def _roundup(x):
                return int(math.ceil(x / 10.0)) * 10

            speedBins = list(sorted(set([_roundup(n) for n in speed])).__reversed__())
            norm = colors.Normalize(vmin=min(speedBins), vmax=max(speedBins)) # normalize the colors to the range of windspeed

            # number of total and zero-wind observations
            total = np.float(dataframe.shape[0])
            factor = 1
            units = 'kmh'
            # calm = np.float(dataframe[dataframe[speedcol] == 0].shape[0])/total * 100

            # loop through the speed bins
            for spd in speedBins:
                barLen = _get_wind_counts(dataframe, spd, speedcol, dircol, factor=factor)
                barLen = barLen/total
                barDir, barWidth = _convert_dir_to_left_radian(np.array(barLen.index))
                self.chart_subplot_radar.bar(barDir, barLen, width=barWidth, linewidth=0.50,
                        edgecolor=(0.25, 0.25, 0.25), color=cm.jet(norm(spd)), alpha=0.8,
                        label=r"<%d %s" % (spd, units))

            # format the plot's axes
            self.chart_subplot_radar.legend(loc='lower right', bbox_to_anchor=(1.25, -0.13), fontsize=8)
            self.chart_subplot_radar.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
            self.chart_subplot_radar.xaxis.grid(True, which='major', color='k', alpha=0.5)
            self.chart_subplot_radar.yaxis.grid(True, which='major', color='k', alpha=0.5)
            self.chart_subplot_radar.yaxis.set_major_formatter(FuncFormatter(_pct_fmt))
            # self.chart_subplot_radar.text(0.05, 0.95, 'Calm Winds: %0.1f%%' % calm)
            # if calm >= 0.1:
            #   self.chart_subplot_radar.set_ylim(ymin=np.floor(calm*10)/10.)

            # ======================
            # draw windspeed bar plot
            # x = time, y = wind speed
            self.chart_subplot_bar.cla()
            # loop through the speed bins
            norm = colors.Normalize(min(speed), max(speed))
            for spd, time in zip(speed, starttime):
                self.chart_subplot_bar.bar(time, spd, width=0.03, align = 'center',
                        edgecolor=(0.25, 0.25, 0.25), color=cm.jet(norm(spd)), alpha=0.8)
            self.chart_subplot_bar.set_ylim(bottom=0, top=150)

            # dangerous windspeed
            self.chart_subplot_bar.hlines(120, xmin=min(starttime), xmax=max(starttime), colors='r')
            self.chart_subplot_bar.annotate('safety hazard', xy=(.85, .82), xycoords='axes fraction',
                            horizontalalignment='center', verticalalignment='center', color = 'r')
            self.chart_subplot_bar.annotate('[kmh]', xy=(-0, 1), xycoords='axes fraction',
                            horizontalalignment='right', verticalalignment='bottom')

            # set x-axis labels
            labels = [time.strftime('%H:%M') for time in starttime]
            self.chart_subplot_bar.set_xticks(starttime)
            self.chart_subplot_bar.set_xticklabels(labels, rotation = 'vertical')

            # # Mark the current time with a vertical line — not implemented due to differring time between
            # # datetime.datetime.now().time() and the date range used in the simulation data. It would work with
            # # real-time dataset.
            # current_time = dt.datetime.now().time()
            # self.chart_subplot_bar.vlines(current_time, ymin=0, ymax=140, linestyles = 'dotted')

        # draw all the plots
        self.chart_canvas.draw()

    # example_chart
    def clearChart(self):
        self.chart_subplot_radar.cla()
        self.chart_subplot_bar.cla()
        self.chart_canvas.draw()

    def getWindDate(self):
        """
        Returns
        -------
        String. The date part of the first timestamp in the wind data.
        """
        layer = uf.getLegendLayerByName(self.iface, 'Wind')
        starttime = uf.getAllFeatureValues(layer, 'starttime')
        starttime = [dt.datetime.strptime(date, "%Y-%m-%d %H:%M:%S") for date in starttime]
        date = starttime[0].strftime('%Y-%m-%d')
        return date
