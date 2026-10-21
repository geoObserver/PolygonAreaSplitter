# -*- coding: utf-8 -*-
def classFactory(iface):
    from .polygon_area_splitter import PolygonAreaSplitter
    return PolygonAreaSplitter(iface)
