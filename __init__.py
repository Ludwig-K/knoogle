# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
********************************************************************

* Part of the QGis-Plugin knoogle:
* initializes and returns the plugin

********************************************************************

* Date                 : 2023-06-23
* Copyright            : (C) 2023 by Ludwig Kniprath
* Email                : ludwig at kni minus online dot de

********************************************************************

this program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

********************************************************************
"""
# Rev. 2023-06-23

from qgis._gui import QgisInterface

def classFactory(iface:QgisInterface):
    from .knoogle import Knoogle
    return Knoogle(iface)
