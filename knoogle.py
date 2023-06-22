# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
********************************************************************

* QGis-Plugin Knoogle

********************************************************************

* Date                 : 2023-06-21
* Copyright            : (C) 2023 by Ludwig Kniprath
* Email                : ludwig at kni minus online dot de

********************************************************************

this program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

********************************************************************
"""

import os, qgis, webbrowser, math
from PyQt5 import QtCore, QtGui, QtWidgets


class Knoogle:
    def __init__(self, iface: qgis.gui.QgisInterface):
        """standard-to-implement-function for plugins, Constructor for the Plugin.
        Triggered on open QGis
        :param iface: interface to running QGis-App
        """
        # Rev. 2023-06-22
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        """"standard-to_implement-function for plugins: adapt/extend GUI triggered by plugin-activation or project-open"""
        # Rev. 2023-06-22
        # create action that will be run by the plugin
        self.action = QtWidgets.QAction(
            QtGui.QIcon(f"{self.plugin_dir}/icons/Google_Maps_icon_(2020).svg"),
            "Canvas-Click => Google Maps with three variants",
            self.iface.mainWindow()
        )

        self.action.setCheckable(True)

        # add plugin to menu
        self.iface.addPluginToMenu("Knoogle", self.action)

        # add icon to plugin in toolbar and menu
        self.iface.addToolBarIcon(self.action)

        # connect action
        self.action.triggered.connect(self.run)

        # MapTool, already prepared before call
        self.map_tool = Knoogletool(self.iface)

    def unload(self):
        """Actions to run when the plugin is unloaded"""
        # Rev. 2023-06-22
        # remove menu and icon
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("Knoogle", self.action)
        if self.iface.mapCanvas().mapTool() == self.map_tool:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)

        # unload dialog and temporal graphics
        self.map_tool.unload()
        del self.map_tool

    def run(self):
        """Main-Action, triggered by click on Toolbar/Menu"""
        # Rev. 2023-06-22
        self.iface.mapCanvas().setMapTool(self.map_tool)


class Knoogletool(qgis.gui.QgsMapToolEmitPoint):
    """the MapTool-Class"""

    def __init__(self, iface: qgis.gui.QgisInterface):
        """constructor for the MapTool
        :param iface: interface to running QGis-App"""
        # Rev. 2023-06-22
        qgis.gui.QgsMapTool.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.cursor = QtCore.Qt.CrossCursor
        self.google_maps_url = "https://www.google.com/maps/@[_lon_],[_lat_],[_zoom_]z?entry=ttu"
        self.google_place_url = "https://www.google.com/maps/place/[_lon_],[_lat_]"
        # calculate route from...to and no zoom => show whole route instead of zoom to-point to current scale
        self.google_route_url = "https://www.google.com/maps/dir/[_lon_from_],[_lat_from_]/[_lon_to_],[_lat_to_]/@[_lon_to_],[_lat_to_]?entry=ttu"

        # registered Start-Point for tool_mode "routes"
        self.from_point = None

        # internal flag with currently three possible values
        # "maps" (default)
        # "places"
        # "routes"
        # "set_from_point" (special tool-mode for "routes")
        self.tool_mode = None

        # two temporal canvas-graphics
        # From-Point green box for tool_mode "routes"
        self.vm_from_point = qgis.gui.QgsVertexMarker(self.iface.mapCanvas())
        self.vm_from_point.setPenWidth(2)
        self.vm_from_point.setIconSize(10)
        self.vm_from_point.setIconType(3)
        self.vm_from_point.setColor(QtGui.QColor('#ff00ff00'))
        self.vm_from_point.setFillColor(QtGui.QColor('#00ffffff'))
        self.vm_from_point.hide()

        # To-Point red box for all tool_modes
        self.vm_to_point = qgis.gui.QgsVertexMarker(self.iface.mapCanvas())
        self.vm_to_point.setPenWidth(2)
        self.vm_to_point.setIconSize(10)
        self.vm_to_point.setIconType(3)
        self.vm_to_point.setColor(QtGui.QColor('#ffff0000'))
        self.vm_to_point.setFillColor(QtGui.QColor('#00ffffff'))
        self.vm_to_point.hide()

        # simple QT-Dialog for results and handling
        self.my_dialogue = KnoogleDialog(iface)
        self.my_dialogue.dialog_close.connect(self.s_dialog_close)
        self.iface.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.my_dialogue)
        self.my_dialogue.hide()
        intro = """
    This Plugin creates URLs for Google-Maps with points from QGis (click-coordinates transformed to EPSG 4326, lat/lon).<br/>
    These URLs are appended below, they can be opened (click) or copied to clipboard (context-menu).<br/>
    There are currently three kinds of Google-Maps-Hyperlinks implemented:
    <ol>
    <li>"Google-Maps" => Google-Maps centered on the clicked point, zoomed to the current scale.</li>
    <li>"Google-Places" => Google-Maps with marker, centered on the clicked point, zoomed to the current scale, mode for storing places to lists or calculate routes.</li>
    <li>"Google-Routes" => Google-Maps with route-calculations between two points, needs registered From-Point.</li>
    </ol>
    """
        self.my_dialogue.qlbl_result.setText(intro)

        self.my_dialogue.qpb_clear.clicked.connect(self.s_clear)
        self.my_dialogue.qpb_reset_from_point.clicked.connect(self.s_reset_from_point)
        self.my_dialogue.qpb_maps.clicked.connect(self.s_set_tool_mode_maps)
        self.my_dialogue.qpb_places.clicked.connect(self.s_set_tool_mode_places)
        self.my_dialogue.qpb_routes.clicked.connect(self.s_set_tool_mode_routes)

        self.s_set_tool_mode_maps()

    def s_set_tool_mode_maps(self):
        """set tool_mode to maps, checks/unchecks the three checkable buttons"""
        # Rev. 2023-06-22
        self.tool_mode = 'maps'
        self.my_dialogue.qpb_maps.setChecked(True)
        self.my_dialogue.qpb_places.setChecked(False)
        self.my_dialogue.qpb_routes.setChecked(False)

    def s_set_tool_mode_places(self):
        """set tool_mode to places, checks/unchecks the three checkable buttons"""
        # Rev. 2023-06-22
        self.tool_mode = 'places'
        self.my_dialogue.qpb_maps.setChecked(False)
        self.my_dialogue.qpb_places.setChecked(True)
        self.my_dialogue.qpb_routes.setChecked(False)

    def s_set_tool_mode_routes(self):
        """set tool_mode to 'routes',
        checks/unchecks the three checkable buttons,
        tool_mode 'set_from_point' and additional text, if no from_point registered yet"""
        # Rev. 2023-06-22
        if self.from_point is None:
            self.tool_mode = 'set_from_point'
            self.my_dialogue.qlbl_result.setText(f"{self.my_dialogue.qlbl_result.text()}Click on map to register From-Point...<br/><br/>")
        else:
            self.tool_mode = 'routes'

        self.my_dialogue.qpb_maps.setChecked(False)
        self.my_dialogue.qpb_places.setChecked(False)
        self.my_dialogue.qpb_routes.setChecked(True)

    def s_clear(self):
        """clears the contents and hides the temporal canvas-graphic"""
        # Rev. 2023-06-22
        self.my_dialogue.qlbl_result.clear()
        self.vm_to_point.hide()

    def s_reset_from_point(self):
        """set/reset the from_point for tool_mode 'routes'"""
        # Rev. 2023-06-22
        if self.from_point is not None:
            self.from_point = None
            self.vm_from_point.hide()
            self.my_dialogue.qlbl_result.setText(f"{self.my_dialogue.qlbl_result.text()}From-Point cleared, Click on map to register new one...<br/><br/>")
        else:
            self.my_dialogue.qlbl_result.setText(f"{self.my_dialogue.qlbl_result.text()}Click on map to set From-Point...<br/><br/>")

        self.tool_mode = 'set_from_point'

    def activate(self):
        """re-implemented, called when set as currently active map tool"""
        # Rev. 2023-06-22
        self.iface.mapCanvas().setCursor(self.cursor)
        self.my_dialogue.show()
        super().activate()

    def canvasReleaseEvent(self, event):
        """re-implemented main-function triggered on mouse-release
        dependent on tool_mode are different actions performed"""
        # Rev. 2023-06-22
        self.my_dialogue.show()

        #click-point in the current canvas-projection
        point_org = self.iface.mapCanvas().getCoordinateTransform().toMapCoordinates(event.x(), event.y())

        # Google requires WGS84-lon/lat-coordinates
        source_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        target_crs = qgis.core.QgsCoordinateReferenceSystem("EPSG:4326")
        tr = qgis.core.QgsCoordinateTransform(source_crs, target_crs, qgis.core.QgsProject.instance())
        point_wgs = tr.transform(point_org)

        if self.tool_mode == 'set_from_point':
            self.vm_from_point.setCenter(point_org)
            self.vm_from_point.show()
            self.from_point = point_wgs
            self.my_dialogue.qlbl_result.setText(f"{self.my_dialogue.qlbl_result.text()}New From-Point registered:<br/>&nbsp;&nbsp;&nbsp;lon: {self.from_point.x()}<br/>&nbsp;&nbsp;&nbsp;lat: {self.from_point.y()}<br/><br/>Further Click(s) on map will create Google-Maps-URLs for route-calculations...<br/><br/>")
            self.tool_mode = 'routes'
        elif self.tool_mode == 'routes':
            if self.from_point is not None:
                self.vm_to_point.setCenter(point_org)
                self.vm_to_point.show()
                google_url = self.google_route_url
                google_url = google_url.replace('[_lat_from_]', str(self.from_point.x()))
                google_url = google_url.replace('[_lon_from_]', str(self.from_point.y()))
                google_url = google_url.replace('[_lat_to_]', str(point_wgs.x()))
                google_url = google_url.replace('[_lon_to_]', str(point_wgs.y()))

                # formula taken from QGis-Plugin "zoom_level"
                zoom_level = 29.1402 - math.log2(self.iface.mapCanvas().scale())
                str_zoom_level = str(round(zoom_level, 2))
                google_url = google_url.replace('[_zoom_]', str_zoom_level)
                self.my_dialogue.qlbl_result.setText(f"{self.my_dialogue.qlbl_result.text()}Google-Route:<br/><a href='{google_url}'>{google_url}</a><br/><br/>")
            else:
                self.tool_mode = 'set_from_point'
                self.my_dialogue.qlbl_result.setText(f"{self.my_dialogue.qlbl_result.text()}Click on map to set From-Point...<br/><br/>")
        elif self.tool_mode == 'places':
            self.vm_to_point.setCenter(point_org)
            self.vm_to_point.show()
            google_url = self.google_place_url
            google_url = google_url.replace('[_lat_]', str(point_wgs.x()))
            google_url = google_url.replace('[_lon_]', str(point_wgs.y()))
            self.my_dialogue.qlbl_result.setText(f"{self.my_dialogue.qlbl_result.text()}Google-Places:<br/><a href='{google_url}'>{google_url}</a><br/><br/>")
        else:
            self.vm_to_point.setCenter(point_org)
            self.vm_to_point.show()
            google_url = self.google_maps_url
            # formula taken from QGis-Plugin "zoom_level"
            zoom_level = 29.1402 - math.log2(self.iface.mapCanvas().scale())
            str_zoom_level = str(round(zoom_level, 2))
            google_url = google_url.replace('[_zoom_]', str_zoom_level)
            google_url = google_url.replace('[_lat_]', str(point_wgs.x()))
            google_url = google_url.replace('[_lon_]', str(point_wgs.y()))
            self.my_dialogue.qlbl_result.setText(f"{self.my_dialogue.qlbl_result.text()}Google-Maps:<br/><a href='{google_url}'>{google_url}</a><br/><br/>")

    def s_dialog_close(self, visible):
        """slot for signal dialog_close, emitted on self.my_dialogue closeEvent
        change MapTool, hide canvas-graphics"""
        # Rev. 2023-04-28
        try:
            self.vm_from_point.hide()
            self.vm_to_point.hide()
            self.iface.actionPan().trigger()
        except Exception as e:
            # if called on unload and these Markers are already deleted
            # print(f"Expected exception in {gdp()}: \"{e}\"")
            pass

    def unload(self):
        """unloads the MapTool:
        remove canvas-graphics
        remove dialog
        triggered from plugin-unload
        """
        # Rev. 2023-06-22
        try:
            self.iface.mapCanvas().scene().removeItem(self.vm_from_point)
            del self.vm_from_point
            self.iface.mapCanvas().scene().removeItem(self.vm_to_point)
            del self.vm_to_point
            self.my_dialogue.close()
            del self.my_dialogue
        except Exception as e:
            # AttributeError: 'PolEvt' object has no attribute 'vm_pt_measure'
            # print(f"Expected exception in {gdp()}: \"{e}\"")
            pass

    def flags(self):
        """reimplemented:
        here: make ShiftModifier available for tool_mode 'select_features'
        default: zoom to the dragged rectangle when Shift-Key is holded
        see: https://gis.stackexchange.com/questions/449523/override-the-zoom-behaviour-of-qgsmaptoolextent"""
        # Rev. 2023-05-08
        return super().flags() & ~qgis.gui.QgsMapToolEmitPoint.AllowZoomRect


class KnoogleDialog(QtWidgets.QDockWidget):
    """Dockale-Dialogue for QGis-Plugin Knoogle"""
    # Rev. 2023-05-03

    dialog_close = QtCore.pyqtSignal(bool)
    """own dialog-close-signal, emitted on closeEvent"""

    def __init__(self, iface: qgis.gui.QgisInterface, parent=None):
        """Constructor
        :param iface:
        :param parent: optional Qt-Parent-Element for Hierarchy
        """
        # Rev. 2023-05-03
        QtWidgets.QDockWidget.__init__(self, parent)
        self.setWindowTitle(self.tr("Knoogle: QGis -> Google-Maps "))

        # Application-Standard-Font
        base_font = QtGui.QFont()

        default_font_s = QtGui.QFont(base_font)
        default_font_s.setPointSize(8)

        main_wdg = QtWidgets.QWidget()
        main_wdg.setLayout(QtWidgets.QVBoxLayout())

        self.qlbl_result = QtWidgets.QLabel(self)
        self.qlbl_result.setStyleSheet("background-color: white;")
        self.qlbl_result.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.qlbl_result.setFont(default_font_s)
        self.qlbl_result.setWordWrap(True)
        self.qlbl_result.setToolTip("Click Hyperlinks to open Google in Default-Browser...")
        self.qlbl_result.linkActivated.connect(self.s_open_browser)
        self.qlbl_result.setTextFormat(QtCore.Qt.RichText)

        # make the QLabel scrollable for the long URLs
        qsa = QtWidgets.QScrollArea(self)
        qsa.setWidgetResizable(True)
        qsa.setWidget(self.qlbl_result)

        main_wdg.layout().addWidget(qsa)

        self.qpb_clear = QtWidgets.QPushButton(self.tr("Clear..."))
        self.qpb_clear.setToolTip(self.tr("Clear results"))
        main_wdg.layout().addWidget(self.qpb_clear)

        self.qpb_reset_from_point = QtWidgets.QPushButton(self.tr("Set From-Point..."))
        self.qpb_reset_from_point.setToolTip(self.tr("Set/Reset From-Point"))
        main_wdg.layout().addWidget(self.qpb_reset_from_point)

        sub_wdg = QtWidgets.QWidget()
        sub_wdg.setLayout(QtWidgets.QHBoxLayout())
        sub_wdg.layout().setContentsMargins(0, 0, 0, 0)
        sub_wdg.setFixedHeight(30)
        self.qpb_maps = QtWidgets.QPushButton(self.tr("Google-Maps"))
        self.qpb_maps.setToolTip(self.tr("Create Google-Maps-URL"))
        self.qpb_maps.setCheckable(True)
        sub_wdg.layout().addWidget(self.qpb_maps)
        self.qpb_places = QtWidgets.QPushButton(self.tr("Google-Places"))
        self.qpb_places.setToolTip(self.tr("Create Google-Places-URL"))
        self.qpb_places.setCheckable(True)
        sub_wdg.layout().addWidget(self.qpb_places)
        self.qpb_routes = QtWidgets.QPushButton(self.tr("Google-Routes"))
        self.qpb_routes.setToolTip(self.tr("Create Google-Routes-URL"))
        self.qpb_routes.setCheckable(True)
        sub_wdg.layout().addWidget(self.qpb_routes)
        main_wdg.layout().addWidget(sub_wdg)

        self.setWidget(main_wdg)

    def s_open_browser(self, url: str):
        """opens default-webbrowser with the clicked url in self.qlbl_result"""
        # Rev. 2023-06-22
        webbrowser.open(url, new=2, autoraise=True)
        
    def closeEvent(self, e: QtCore.QEvent):
        """reimplemented, emitts signal when closing this widget
        :param e: <PyQt5.QtGui.QCloseEvent object at ...>
        """
        # Rev. 2023-06-22
        self.dialog_close.emit(False)
