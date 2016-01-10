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
import pandas as pd
from matplotlib.ticker import FuncFormatter
from matplotlib import pyplot as plt

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
        self.openScenarioButton.hide()
        self.saveScenarioButton.hide()
        # self.openScenarioButton.clicked.connect(self.openScenario)
        # self.saveScenarioButton.clicked.connect(self.saveScenario)
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
        self.serviceAreaButton.clicked.connect(self.calculateServiceArea)
        self.bufferButton.clicked.connect(self.calculateBuffer)
        self.selectBufferButton.clicked.connect(self.selectFeaturesBuffer)
        self.makeIntersectionButton.clicked.connect(self.calculateIntersection)
        self.selectRangeButton.clicked.connect(self.selectFeaturesRange)
        self.expressionSelectButton.clicked.connect(self.selectFeaturesExpression)
        self.expressionFilterButton.clicked.connect(self.filterFeaturesExpression)
        self.assignButton.clicked.connect(self.assignFacility)
        self.clearAssignmentButton.clicked.connect(self.clearAssignment)

        # visualisation

        # reporting
        # self.featureCounterUpdateButton.hide()
        # self.saveMapButton.hide()
        # self.saveMapPathButton.hide()
        # self.featureCounterUpdateButton.clicked.connect(self.updateNumberFeatures)
        # self.saveMapButton.clicked.connect(self.saveMap)
        # self.saveMapPathButton.clicked.connect(self.selectFile)
        # self.updateAttribute.connect(self.extractAttributeSummary)

        # set current UI restrictions
        self.makeIntersectionButton.hide()

        # example_chart
        # add matplotlib Figure to chartFrame
        self.chart_figure = Figure()
        self.chart_subplot_radar = self.chart_figure.add_subplot(211, projection='polar')
        self.chart_subplot_bar = self.chart_figure.add_subplot(212)
        self.chart_figure.tight_layout()
        self.chart_canvas = FigureCanvas(self.chart_figure)
        self.chartLayout.addWidget(self.chart_canvas)

        # initialisation
        self.eventlayer = uf.getLegendLayerByName(self.iface, 'reports')
        self.hospitalLayer = uf.getLegendLayerByName(self.iface, 'hospital')
        self.firestationLayer = uf.getLegendLayerByName(self.iface, 'firestation')
        self.facility_name = ''
        self.event_source = self.eventlayer.selectedFeatures()
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
    def openScenario(self, filename=""):
        scenario_open = False
        scenario_file = os.path.join('/Users/jorge/github/GEO1005', 'sample_data', 'time_test.qgs')
        # check if file exists
        if os.path.isfile(scenario_file):
            self.iface.addProject(scenario_file)
            scenario_open = True
        else:
            last_dir = uf.getLastDir("SDSS")
            new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
            if new_file:
                self.iface.addProject(new_file)
                scenario_open = True
        if scenario_open:
            self.updateLayers()

    def saveScenario(self):
        self.iface.actionSaveProject()

    def updateLayers(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectLayerCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectLayerCombo.addItems(layer_names)
            self.setSelectedLayer()
            self.plotChart()
        else:
            self.clearChart()  # example_chart

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
            self.clearChart()
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
                ('fire_active_humanDmg', '"dmgType" LIKE fire AND "resolved" LIKE no AND "civilDmg"> 0',
                 filepath + 'fire_active_humanDmg.svg', None, 10),
                (
                'building_active_humanDmg', '"dmgType" LIKE \'building\' AND "resolved" LIKE \'no\' AND "civilDmg"> 0 ',
                filepath + 'building_active_humanDmg.svg', None, 10),
                ('tree_active_humanDmg', '"dmgType" LIKE \'tree\' AND "resolved" LIKE \'no\' AND "civilDmg"> 0 ',
                 filepath + 'tree_active_humanDmg.svg', None, 10),
                ('fire_active', '"dmgType" LIKE \'fire\' AND "resolved" LIKE \'no\' AND "civilDmg"= 0',
                 filepath + 'fire_active.svg', None, 8),
                ('building_active', '"dmgType" LIKE \'building\' AND "resolved" LIKE \'no\' AND "civilDmg"= 0 ',
                 filepath + 'building_active.svg', None, 8),
                ('tree_active', '"dmgType" LIKE \'tree\' AND "resolved" LIKE \'no\' AND "civilDmg"= 0',
                 filepath + 'tree_active.svg', None, 8),
                ('fire_resolved_humanDmg', '"dmgType" LIKE fire AND "resolved" LIKE yes AND "civilDmg"> 0',
                 filepath + 'fire_resolved_humanDmg.svg', None, 10),
                ('building_resolved_humanDmg',
                 '"dmgType" LIKE \'building\' AND "resolved" LIKE \'yes\' AND "civilDmg"> 0 ',
                 filepath + 'building_resolved_humanDmg.svg', None, 10),
                ('tree_resolved_humanDmg', '"dmgType" LIKE \'tree\' AND "resolved" LIKE \'yes\' AND "civilDmg"> 0 ',
                 filepath + 'tree_resolved_humanDmg.svg', None, 10),
                ('fire_resolved', '"dmgType" LIKE \'fire\' AND "resolved" LIKE \'yes\' AND "civilDmg"= 0',
                 filepath + 'fire_resolved.svg', None, 8),
                ('building_resolved', '"dmgType" LIKE \'building\' AND "resolved" LIKE \'yes\' AND "civilDmg"= 0 ',
                 filepath + 'building_resolved.svg', None, 8),
                ('tree_resolved', '"dmgType" LIKE \'tree\' AND "resolved" LIKE \'yes\' AND "civilDmg"= 0',
                 filepath + 'tree_resolved.svg', None, 8)
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
                    # self.insertReport(text)
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
        self.facility_name = ''
        if len(event) != 1:
            return
        else:
            civilDmg = event[0].attribute('civilDmg')
            if civilDmg == 0:
                # origin and destination must be in the set of tied_points
                self.buildNetwork(event, 'firestation')
                self.facility_name = 'firestation:'
                self.facility_name += self.shortestRoute(self.tied_points)
            else:
                self.buildNetwork(event, 'firestation')
                self.facility_name = 'firestation:'
                self.facility_name += self.shortestRoute(self.tied_points)
                self.buildNetwork(event, 'hospital')
                self.facility_name += ' hospital:'
                self.facility_name += self.shortestRoute(self.tied_points)
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
        if self.event_source:
            self.eventlayer.startEditing()
            self.event_source[0]['unitOnSite'] = self.facility_name
            self.eventlayer.updateFeature(self.event_source[0])
            self.eventlayer.commitChanges()

    def clearAssignment(self):
        features = self.eventlayer.selectedFeatures()
        self.eventlayer.startEditing()
        for feature in features:
            feature.setAttribute('unitOnSite', '')
            self.eventlayer.updateFeature(feature)
        self.eventlayer.commitChanges()

    def getServiceAreaCutoff(self):
        cutoff = self.serviceAreaCutoffEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0

    def calculateServiceArea(self):
        options = len(self.tied_points)
        if options > 0:
            # origin is given as an index in the tied_points list
            origin = random.randint(1, options - 1)
            cutoff_distance = self.getServiceAreaCutoff()
            if cutoff_distance == 0:
                return
            service_area = uf.calculateServiceArea(self.graph, self.tied_points, origin, cutoff_distance)
            # store the service area results in temporary layer called "Service_Area"
            area_layer = uf.getLegendLayerByName(self.iface, "Service_Area")
            # create one if it doesn't exist
            if not area_layer:
                attribs = ['cost']
                types = [QtCore.QVariant.Double]
                area_layer = uf.createTempLayer('Service_Area', 'POINT', self.network_layer.crs().postgisSrid(),
                                                attribs, types)
                uf.loadTempLayer(area_layer)
            # insert service area points
            geoms = []
            values = []
            for point in service_area.itervalues():
                # each point is a tuple with geometry and cost
                geoms.append(point[0])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([cutoff_distance])
            uf.insertTempFeatures(area_layer, geoms, values)
            self.refreshCanvas(area_layer)

    # buffer functions
    def getBufferCutoff(self):
        cutoff = self.bufferCutoffEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0

    def calculateBuffer(self):
        origins = self.getSelectedLayer().selectedFeatures()
        layer = self.getSelectedLayer()
        if origins > 0:
            cutoff_distance = self.getBufferCutoff()
            buffers = {}
            for point in origins:
                geom = point.geometry()
                buffers[point.id()] = geom.buffer(cutoff_distance, 12)
            # store the buffer results in temporary layer called "Buffers"
            buffer_layer = uf.getLegendLayerByName(self.iface, "Buffers")
            # create one if it doesn't exist
            if not buffer_layer:
                attribs = ['id', 'distance']
                types = [QtCore.QVariant.String, QtCore.QVariant.Double]
                buffer_layer = uf.createTempLayer('Buffers', 'POLYGON', layer.crs().postgisSrid(), attribs, types)
                uf.loadTempLayer(buffer_layer)
            # insert buffer polygons
            geoms = []
            values = []
            for buffer in buffers.iteritems():
                # each buffer has an id and a geometry
                geoms.append(buffer[1])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([buffer[0], cutoff_distance])
            uf.insertTempFeatures(buffer_layer, geoms, values)
            self.refreshCanvas(buffer_layer)

    def calculateIntersection(self):
        # use the buffer to cut from another layer
        cutter = uf.getLegendLayerByName(self.iface, "Buffers")
        # use the selected layer for cutting
        layer = self.getSelectedLayer()
        if cutter.featureCount() > 0:
            # get the intersections between the two layers
            intersections = uf.getFeaturesIntersections(layer, cutter)
            if intersections:
                # store the intersection geometries results in temporary layer called "Intersections"
                intersection_layer = uf.getLegendLayerByName(self.iface, "Intersections")
                # create one if it doesn't exist
                if not intersection_layer:
                    geom_type = intersections[0].type()
                    if geom_type == 1:
                        intersection_layer = uf.createTempLayer('Intersections', 'POINT', layer.crs().postgisSrid(), [],
                                                                [])
                    elif geom_type == 2:
                        intersection_layer = uf.createTempLayer('Intersections', 'LINESTRING',
                                                                layer.crs().postgisSrid(), [], [])
                    elif geom_type == 3:
                        intersection_layer = uf.createTempLayer('Intersections', 'POLYGON', layer.crs().postgisSrid(),
                                                                [], [])
                    uf.loadTempLayer(intersection_layer)
                # insert buffer polygons
                geoms = []
                values = []
                for intersect in intersections:
                    # each buffer has an id and a geometry
                    geoms.append(intersect)
                uf.insertTempFeatures(intersection_layer, geoms, values)
                self.refreshCanvas(intersection_layer)

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

    def selectFeaturesExpression(self):
        layer = self.getSelectedLayer()
        uf.selectFeaturesByExpression(layer, self.expressionEdit.text())

    def filterFeaturesExpression(self):
        layer = self.getSelectedLayer()
        uf.filterFeaturesByExpression(layer, self.expressionEdit.text())

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
        plot_layer = uf.getLegendLayerByName(self.iface, 'wind')  # in my case it is fixed to the wind layer
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
            speedBins = [60, 50]
            colors = ['#579443', '#0066FF']#, '#990000', '#FF4719', '#FFCC00', '#579443', '#0066FF']

            # number of total and zero-wind observations
            total = np.float(dataframe.shape[0])
            factor = 1
            units = 'kmh'

            calm = np.float(dataframe[dataframe[speedcol] == 0].shape[0])/total * 100

            # loop through the speed bins
            for spd, clr in zip(speedBins, colors):
                barLen = _get_wind_counts(dataframe, spd, speedcol, dircol, factor=factor)
                barLen = barLen/total
                barDir, barWidth = _convert_dir_to_left_radian(np.array(barLen.index))
                self.chart_subplot_radar.bar(barDir, barLen, width=barWidth, linewidth=0.50,
                        edgecolor=(0.25, 0.25, 0.25), color=clr, alpha=0.8,
                        label=r"<%d %s" % (spd, units))

            # format the plot's axes
            self.chart_subplot_radar.legend(loc='lower right', bbox_to_anchor=(1.10, -0.13), fontsize=8)
            self.chart_subplot_radar.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
            self.chart_subplot_radar.xaxis.grid(True, which='major', color='k', alpha=0.5)
            self.chart_subplot_radar.yaxis.grid(True, which='major', color='k', alpha=0.5)
            self.chart_subplot_radar.yaxis.set_major_formatter(FuncFormatter(_pct_fmt))
            #self.chart_subplot_radar.text(0.05, 0.95, 'Calm Winds: %0.1f%%' % calm)
            #if calm >= 0.1:
            #   self.chart_subplot_radar.set_ylim(ymin=np.floor(calm*10)/10.)

            # ======================
            # draw windspeed bar plot
            # x = time, y = wind speed
            self.chart_subplot_bar.cla()
            self.chart_subplot_bar.bar(starttime, speed, width=0.03)
            self.chart_subplot_bar.set_ylim(bottom=0, top=150)
            self.chart_subplot_bar.hlines(120, xmin=min(starttime), xmax=max(starttime), colors='r', \
                                          label='Withdraw all units')
            self.chart_subplot_bar.legend()

            hours = dates.HourLocator()
            hFmt = dates.DateFormatter('%H:%M')

            # labels = starttime.hour()

            self.chart_subplot_bar.xaxis.set_major_locator(hours)
            self.chart_subplot_bar.xaxis.set_major_formatter(hFmt)
            # self.chart_subplot_bar.autofmt_xdate()

            # self.chart_subplot_bar.set_xticks(ticks)
            # self.chart_subplot_bar.set_xticklabels(rotation = 70)

        # draw all the plots
        self.chart_canvas.draw()

    # example_chart
    def clearChart(self):
        self.chart_subplot_radar.cla()
        self.chart_subplot_bar.cla()
        self.chart_canvas.draw()

    #######
    #    Reporting functions
    #######
    # update a text edit field
    def updateNumberFeatures(self):
        layer = self.getSelectedLayer()
        if layer:
            count = layer.featureCount()
            self.featureCounterEdit.setText(str(count))

    # selecting a file for saving
    def selectFile(self):
        last_dir = uf.getLastDir("SDSS")
        path = QtGui.QFileDialog.getSaveFileName(self, "Save map file", last_dir, "PNG (*.png)")
        if path.strip() != "":
            path = unicode(path)
            uf.setLastDir(path, "SDSS")
            self.saveMapPathEdit.setText(path)

    # saving the current screen
    def saveMap(self):
        filename = self.saveMapPathEdit.text()
        if filename != '':
            self.canvas.saveAsImage(filename, None, "PNG")

    def extractAttributeSummary(self, attribute):
        # get summary of the attribute
        summary = []
        layer = self.getSelectedLayer()

        # send this to the table
        self.clearTable()
        self.updateTable(summary)

        # # report window functions
        # def updateReport(self, report):
        #     self.reportList.clear()
        #     self.reportList.addItems(report)
        #
        # def insertReport(self, item):
        #     self.reportList.insertItem(0, item)
        #
        # def clearReport(self):
        #     self.reportList.clear()

        # # table window functions
        # def updateTable(self, values):
        #     # takes a list of label / value pairs, can be tuples or lists. not dictionaries to control order
        #     self.statisticsTable.setHorizontalHeaderLabels(["Item", "Value"])
        #     self.statisticsTable.setRowCount(len(values))
        #     for i, item in enumerate(values):
        #         self.statisticsTable.setItem(i, 0, QtGui.QTableWidgetItem(str(item[0])))
        #         self.statisticsTable.setItem(i, 1, QtGui.QTableWidgetItem(str(item[1])))
        #     self.statisticsTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        #     self.statisticsTable.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        #     self.statisticsTable.resizeRowsToContents()
        #
        # def clearTable(self):
        #     self.statisticsTable.clear()
