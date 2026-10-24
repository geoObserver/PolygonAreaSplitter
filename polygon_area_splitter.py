# -*- coding: utf-8 -*-
"""
Polygon Area Splitter
Author: Mike Elstermann (#geoObserver)
https://geoobserver.de/qgis-plugins/

Kompatibel mit QGIS 3 (Qt5 / PyQt5) und QGIS 4 (Qt6 / PyQt6).

This file contains code generated with assistance from an AI.
No warranty is provided. Human review and modification performed by:
Mike Elstermann (#geoObserver).
"""

import math
import os

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateTransform,
    QgsExpression,
    QgsFeature,
    QgsFillSymbol,
    QgsField,
    QgsGeometry,
    QgsLineSymbol,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
)
from qgis.gui import QgsMapToolEmitPoint
from qgis.PyQt.QtCore import QMetaType, QVariant, Qt
from qgis.PyQt.QtGui import QColor, QFont, QIcon

try:
    from qgis.PyQt.QtGui import QAction          # QGIS 4 (Qt6)
except ImportError:
    from qgis.PyQt.QtWidgets import QAction      # QGIS 3 (Qt5)

from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QInputDialog,
    QLabel,
    QMessageBox,
    QRadioButton,
    QToolBar,
    QVBoxLayout,
)


SPLIT_FIELD = "split_id"
UNIT_FIELD = "area_unit"

TEXTS = {
    "title": {"de": "Polygon nach Fläche teilen", "en": "Divide a Polygon by Area"},
    "no_layer": {"de": "Bitte zuerst einen Polygonlayer aktivieren.",
                 "en": "Please activate a polygon layer first."},
    "not_vector": {
        "de": "Der aktive Layer ist kein Vektorlayer (z. B. Raster- oder Gruppenlayer).\n\nBitte einen Polygonlayer aktivieren.",
        "en": "The active layer is not a vector layer (e.g. raster or group layer).\n\nPlease activate a polygon layer."
    },
    "wrong_geometry": {
        "de": "Der aktive Layer ist ein {}.\n\nBitte einen Polygonlayer aktivieren.",
        "en": "The active layer is a {}.\n\nPlease activate a polygon layer."
    },
    "geom_point": {"de": "Punktlayer", "en": "point layer"},
    "geom_line": {"de": "Linienlayer", "en": "line layer"},
    "geom_none": {"de": "Layer ohne Geometrie", "en": "layer without geometry"},
    "select_one": {"de": "Bitte genau ein Polygon auswählen.",
                   "en": "Please select exactly one polygon."},
    "geographic_crs": {
        "de": "Der Layer verwendet ein geografisches Koordinatensystem.\n\nBitte verwenden Sie ein projiziertes Koordinatensystem mit Meter-Einheiten, beispielsweise EPSG:25832.",
        "en": "The layer uses a geographic coordinate reference system.\n\nPlease use a projected coordinate reference system with metre units, for example EPSG:25832."
    },
    "not_meters": {
        "de": "Die Koordinateneinheiten des Layers sind keine Meter.\n\nBitte verwenden Sie ein projiziertes Koordinatensystem mit Meter-Einheiten.",
        "en": "The layer's coordinate units are not metres.\n\nPlease use a projected coordinate reference system with metre units."
    },
    "empty_geometry": {"de": "Das ausgewählte Polygon besitzt keine gültige Geometrie.",
                       "en": "The selected polygon has no valid geometry."},
    "invalid_geometry": {"de": "Das ausgewählte Polygon ist geometrisch ungültig.",
                         "en": "The selected polygon has invalid geometry."},
    "target_prompt": {"de": "Gewünschte Teilfläche in {}:",
                      "en": "Target area in {}:"},
    "target_area_label": {"de": "Gewünschte Teilfläche:", "en": "Target area:"},
    "unit_m2": {"de": "Quadratmeter (m²)", "en": "Square metres (m²)"},
    "unit_ha": {"de": "Hektar (ha)", "en": "Hectares (ha)"},
    "split_result": {"de": "Split-ID: {}", "en": "Split ID: {}"},
    "field_failed": {"de": "Das Feld split_id konnte im vorhandenen Layer nicht angelegt werden.",
                     "en": "The field split_id could not be added to the existing layer."},
    "target_too_large": {
        "de": "Die gewünschte Teilfläche muss kleiner sein als die Gesamtfläche des Polygons.\n\nGesamtfläche: {:.2f} m²",
        "en": "The target area must be smaller than the total polygon area.\n\nTotal area: {:.2f} m²"
    },
    "click_edge": {
        "de": "Bitte auf die äußere Polygonkante klicken, zu der der Schnitt parallel verlaufen soll. (Esc oder Rechtsklick bricht ab)",
        "en": "Click an outer polygon edge to define the direction of the parallel cut. (Esc or right-click to cancel)"
    },
    "no_edge": {
        "de": "Keine Polygonkante in der Nähe des Klickpunkts gefunden.\n\nBitte direkt auf eine äußere Kante klicken.",
        "en": "No polygon edge found near the clicked point.\n\nPlease click directly on an outer boundary edge."
    },
    "side_unclear": {
        "de": "Die Seite des Polygons konnte an dieser Kante nicht eindeutig bestimmt werden.\n\nBitte eine andere äußere Kante wählen.",
        "en": "The polygon side at this edge could not be determined.\n\nPlease select another outer boundary edge."
    },
    "zero_edge": {"de": "Die gewählte Kante hat keine Länge.",
                  "en": "The selected edge has zero length."},
    "no_points": {"de": "Es wurden keine Polygonpunkte gefunden.",
                  "en": "No polygon vertices were found."},
    "cannot_bracket": {
        "de": "Die gewünschte Fläche lässt sich von dieser Kante aus nicht erreichen.\n\nBitte eine andere äußere Kante auswählen oder einen kleineren Flächenwert eingeben.",
        "en": "The requested area cannot be reached from this edge.\n\nPlease select another outer boundary edge or enter a smaller target area."
    },
    "calculation_failed": {"de": "Die Teilfläche konnte nicht berechnet werden.",
                           "en": "Could not calculate the target area."},
    "invalid_target": {"de": "Die berechnete Teilfläche ist geometrisch ungültig.",
                       "en": "The calculated target polygon has invalid geometry."},
    "invalid_remainder": {"de": "Die berechnete Restfläche ist geometrisch ungültig.",
                          "en": "The calculated remainder polygon has invalid geometry."},
    "area_mismatch": {
        "de": "Die Flächenbilanz stimmt nicht ausreichend überein.\n\nDie Ergebnisse wurden nicht übernommen.",
        "en": "The area balance does not match within the allowed tolerance.\n\nThe results have not been added."
    },
    "feature_failed": {"de": "Die Ergebnisfeatures konnten nicht vollständig angelegt werden.",
                       "en": "Could not create all output features."},
    "error": {"de": "Fehler bei der Polygonteilung:\n\n{}",
              "en": "Error while splitting the polygon:\n\n{}"},
    "complete": {"de": "Polygonteilung abgeschlossen",
                 "en": "Polygon Split Complete"},
    "results_added": {"de": "Die Ergebnisse wurden in einem neuen temporären Layer angelegt.",
                      "en": "The results have been added to a new temporary layer."},
    "area_note": {
        "de": "Hinweis: Die Flächen beziehen sich auf die Ebene des Koordinatensystems. Gegenüber der Geländefläche können sie je nach Lage um wenige Hundertstel Prozent abweichen.",
        "en": "Note: The areas refer to the plane of the coordinate reference system. Compared with the ground area they may differ by a few hundredths of a percent, depending on location."
    },
    "target_label": {"de": "Teilfläche", "en": "Target Area"},
    "remainder_label": {"de": "Restfläche", "en": "Remainder"},
    "output_layer": {"de": "Polygonteilung", "en": "Polygon Split"},
    "edge_layer": {"de": "Polygonbezugskanten", "en": "Polygon reference edges"},
    "output_incompatible": {"de": 'Der vorhandene Layer "Polygonteilung" passt nicht zum aktuellen Polygonlayer (Felder oder Koordinatensystem weichen ab). Die Ergebnisse wurden nicht hinzugefügt.', "en": 'The existing "Polygon Split" layer is incompatible with the current polygon layer (fields or CRS differ). No results were added.'},
    "edge_layer_incompatible": {"de": 'Der vorhandene Layer "Polygonbezugskanten" ist kein kompatibler Linienlayer im Koordinatensystem des Ursprungslayers.', "en": 'The existing "Polygon reference edges" layer is not a compatible line layer in the source layer CRS.'},
    "edge_feature_failed": {"de": "Die neue Bezugskante konnte nicht gespeichert werden.", "en": "The new reference edge could not be saved."},
    "target_result": {"de": "Teilfläche: {:.2f} m²", "en": "Target area: {:.2f} m²"},
    "requested_result": {"de": "Gewünscht: {:.2f} m²", "en": "Requested area: {:.2f} m²"},
    "deviation_result": {"de": "Abweichung: {:.2f} m²", "en": "Deviation: {:.2f} m²"},
    "remainder_result": {"de": "Restfläche: {:.2f} m²", "en": "Remainder: {:.2f} m²"},
    "toolbar": {"de": "geoObserver-Werkzeuge", "en": "geoObserver Tools"},
}


# ---------------------------------------------------------------------------
# Kompatibilitätshelfer (QGIS 3 / Qt5 und QGIS 4 / Qt6)
# ---------------------------------------------------------------------------

def _resolve(*candidates):
    """Gibt den ersten vorhandenen Attributwert zurück."""
    for candidate in candidates:
        try:
            return candidate()
        except AttributeError:
            continue
    raise AttributeError("Kein kompatibles Attribut gefunden.")


def _geom(name):
    """Geometrietyp, z. B. 'Polygon', 'Point', 'Line', 'Null'."""
    return _resolve(
        lambda: getattr(Qgis.GeometryType, name),
        lambda: getattr(QgsWkbTypes.GeometryType, name),
        lambda: getattr(QgsWkbTypes, name + "Geometry"),
    )


def _meter_unit():
    return _resolve(
        lambda: Qgis.DistanceUnit.Meters,
        lambda: QgsUnitTypes.DistanceMeters,
    )


def _info_level():
    return _resolve(
        lambda: Qgis.MessageLevel.Info,
        lambda: Qgis.Info,
    )


def _qtype_string():
    return _resolve(lambda: QMetaType.Type.QString, lambda: QVariant.String)


def _qtype_double():
    return _resolve(lambda: QMetaType.Type.Double, lambda: QVariant.Double)


def _qtype_longlong():
    return _resolve(lambda: QMetaType.Type.LongLong, lambda: QVariant.LongLong)


def _pixel_unit():
    return _resolve(lambda: Qgis.RenderUnit.Pixels, lambda: QgsUnitTypes.RenderPixels)


def _line_placement():
    return _resolve(
        lambda: Qgis.LabelPlacement.Line,
        lambda: QgsPalLayerSettings.Placement.Line,
        lambda: QgsPalLayerSettings.Line,
    )


def _ensure_field(layer, field):
    """Legt ein Feld an, falls es im Layer fehlt. True = Feld vorhanden."""
    if field.name() in [f.name() for f in layer.fields()]:
        return True
    provider = layer.dataProvider()
    if provider is None or not provider.addAttributes([field]):
        return False
    layer.updateFields()
    return True


def _horizontal_placement():
    return _resolve(
        lambda: Qgis.LabelPlacement.Horizontal,
        lambda: QgsPalLayerSettings.Placement.Horizontal,
        lambda: QgsPalLayerSettings.Horizontal,
    )


def _left_button():
    return _resolve(lambda: Qt.MouseButton.LeftButton, lambda: Qt.LeftButton)


def _right_button():
    return _resolve(lambda: Qt.MouseButton.RightButton, lambda: Qt.RightButton)


def _escape_key():
    return _resolve(lambda: Qt.Key.Key_Escape, lambda: Qt.Key_Escape)


def _event_pos(event):
    """Mausposition als QPoint, unabhängig von der Qt-Version."""
    try:
        return event.position().toPoint()
    except AttributeError:
        return event.pos()


# ---------------------------------------------------------------------------
# Map-Tool zum Auswählen der Kante
# ---------------------------------------------------------------------------

class EdgeClickTool(QgsMapToolEmitPoint):
    """Meldet genau einen Klick (Kartenpunkt) oder einen Abbruch (None)."""

    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self._callback = callback
        self._finished = False

    def _finish(self, point):
        if self._finished:
            return
        self._finished = True
        self._callback(point)

    def canvasReleaseEvent(self, event):
        if event.button() == _left_button():
            self._finish(self.toMapCoordinates(_event_pos(event)))
        elif event.button() == _right_button():
            self._finish(None)

    def keyPressEvent(self, event):
        if event.key() == _escape_key():
            self._finish(None)
        else:
            super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Hauptklasse
# ---------------------------------------------------------------------------

class PolygonAreaSplitter:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.toolbar = None
        self.map_tool = None
        self.previous_map_tool = None
        self._area_unit = "m²"
        self.language = self._get_language()

    @staticmethod
    def _get_language():
        try:
            locale = QgsApplication.locale()
            return "de" if str(locale).lower().startswith("de") else "en"
        except Exception:
            return "en"

    def tr(self, key, *args):
        text = TEXTS.get(key, {}).get(self.language, TEXTS.get(key, {}).get("en", key))
        return text.format(*args) if args else text

    def _warning(self, text):
        QMessageBox.warning(self.iface.mainWindow(), self.tr("title"), text)

    # -- GUI -----------------------------------------------------------------

    def initGui(self):
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(plugin_dir, "icon.svg")
        self.action = QAction(QIcon(icon_path), self.tr("title"), self.iface.mainWindow())
        self.action.setObjectName("polygonAreaSplitterAction")
        self.action.setToolTip(self.tr("title"))
        self.action.triggered.connect(self.run)
        self.iface.addPluginToVectorMenu(self.tr("title"), self.action)

        # Gemeinsame geoObserver-Werkzeugleiste wiederverwenden, falls vorhanden.
        main_window = self.iface.mainWindow()
        self.toolbar = main_window.findChild(QToolBar, "geoObserverTools")
        if self.toolbar is None:
            self.toolbar = main_window.addToolBar(self.tr("toolbar"))
            self.toolbar.setObjectName("geoObserverTools")

        self.toolbar.addAction(self.action)

    def unload(self):
        if self.map_tool is not None:
            self._restore_map_tool()

        if self.action:
            self.iface.removePluginVectorMenu(self.tr("title"), self.action)
            if self.toolbar:
                self.toolbar.removeAction(self.action)
            self.action = None

    def _restore_map_tool(self):
        canvas = self.iface.mapCanvas()
        if self.map_tool is not None:
            if self.previous_map_tool is not None:
                canvas.setMapTool(self.previous_map_tool)
            else:
                canvas.unsetMapTool(self.map_tool)
        self.map_tool = None
        self.previous_map_tool = None

    # -- Geometrie-Helfer ----------------------------------------------------

    @staticmethod
    def _outer_rings(geometry):
        if geometry.isMultipart():
            polygons = geometry.asMultiPolygon()
            return [poly[0] for poly in polygons if poly and poly[0]]
        polygon = geometry.asPolygon()
        return [polygon[0]] if polygon and polygon[0] else []

    @staticmethod
    def _all_ring_points(geometry):
        points = []
        for ring in PolygonAreaSplitter._outer_rings(geometry):
            points.extend(ring)
        return points

    @staticmethod
    def _point_segment_distance(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        if length2 == 0:
            return math.hypot(px - ax, py - ay)
        t = ((px - ax) * dx + (py - ay) * dy) / length2
        t = max(0.0, min(1.0, t))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def _nearest_edge(self, geometry, click_point, layer, canvas, tolerance_px=10):
        canvas_crs = canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(layer.crs(), canvas_crs, QgsProject.instance())
        map_to_pixel = canvas.mapSettings().mapToPixel()
        click_px = map_to_pixel.transform(click_point)
        best = None
        best_distance = float("inf")

        for ring in self._outer_rings(geometry):
            for i in range(len(ring) - 1):
                p1, p2 = QgsPointXY(ring[i]), QgsPointXY(ring[i + 1])
                c1 = transform.transform(p1)
                c2 = transform.transform(p2)
                s1 = map_to_pixel.transform(c1)
                s2 = map_to_pixel.transform(c2)
                distance = self._point_segment_distance(
                    click_px.x(), click_px.y(),
                    s1.x(), s1.y(), s2.x(), s2.y()
                )
                if distance < best_distance:
                    best_distance = distance
                    best = (ring, i, p1, p2)

        return best if best_distance <= tolerance_px else None

    @staticmethod
    def _point_local(origin, tx, ty, nx, ny, u, v):
        return QgsPointXY(
            origin.x() + u * tx + v * nx,
            origin.y() + u * ty + v * ny
        )

    def _half_plane(self, origin, tx, ty, nx, ny, u_min, u_max, v_min, v_max):
        points = [
            self._point_local(origin, tx, ty, nx, ny, u_min, v_min),
            self._point_local(origin, tx, ty, nx, ny, u_max, v_min),
            self._point_local(origin, tx, ty, nx, ny, u_max, v_max),
            self._point_local(origin, tx, ty, nx, ny, u_min, v_max),
        ]
        return QgsGeometry.fromPolygonXY([points + [points[0]]])

    def _split_at_offset(self, geometry, origin, tx, ty, nx, ny,
                         u_min, u_max, v_min, v_max, offset):
        margin = max(abs(u_max - u_min), abs(v_max - v_min), 1.0) * 3.0
        cutter = self._half_plane(
            origin, tx, ty, nx, ny,
            u_min - margin, u_max + margin,
            v_min - margin, offset
        )
        target = geometry.intersection(cutter)
        if target is None or target.isNull():
            return None, None
        remainder = geometry.difference(target)
        if remainder is None or remainder.isNull():
            return None, None
        return target, remainder

    @staticmethod
    def _unique_field_name(base, names):
        used = {name.lower() for name in names}
        name, i = base, 2
        while name.lower() in used:
            name = "{}_{}".format(base, i)
            i += 1
        return name

    def _geometry_name(self, geom_type):
        if geom_type == _geom("Point"):
            return self.tr("geom_point")
        if geom_type == _geom("Line"):
            return self.tr("geom_line")
        return self.tr("geom_none")

    def _set_labels(self, output, area_field):
        settings = QgsPalLayerSettings()
        area = QgsExpression.quotedColumnRef(area_field)
        unit = QgsExpression.quotedColumnRef(UNIT_FIELD)
        split = QgsExpression.quotedColumnRef(SPLIT_FIELD)
        settings.fieldName = (
            "format_number(CASE WHEN " + unit + " = 'ha' THEN " + area
            + " / 10000 ELSE " + area + " END, 2)"
            + " || ' ' || " + unit
            + " || ' [ID ' || " + split + " || ']'"
        )
        settings.isExpression = True
        settings.placement = _horizontal_placement()

        text_format = QgsTextFormat()
        text_format.setFont(QFont("Arial", 10))
        text_format.setSize(10)
        text_format.setColor(QColor(0, 0, 0))

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.0)
        buffer.setColor(QColor(255, 255, 255))
        text_format.setBuffer(buffer)

        settings.setFormat(text_format)
        output.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        output.setLabelsEnabled(True)

    def _highlight_edge(self, source_layer, p1, p2, split_id):
        """Sammelt alle verwendeten Bezugskanten in einem eigenen Layer."""
        project = QgsProject.instance()
        layer_name = self.tr("edge_layer")
        matches = project.mapLayersByName(layer_name)
        edge_layer = matches[0] if matches else None

        # Einen bereits vorhandenen Layer unter dem alten Namen weiterverwenden.
        if edge_layer is None:
            old_name = "Polygonbezugskante" if self.language == "de" else "Polygon reference edge"
            old_matches = project.mapLayersByName(old_name)
            if old_matches and isinstance(old_matches[0], QgsVectorLayer):
                edge_layer = old_matches[0]
                edge_layer.setName(layer_name)

        if edge_layer is not None:
            if (not isinstance(edge_layer, QgsVectorLayer)
                    or edge_layer.geometryType() != _geom("Line")
                    or edge_layer.crs() != source_layer.crs()):
                self._warning(self.tr("edge_layer_incompatible"))
                return
            if not _ensure_field(edge_layer, QgsField(SPLIT_FIELD, _qtype_longlong())):
                self._warning(self.tr("field_failed"))
                return
        else:
            edge_layer = QgsVectorLayer(
                "LineString?crs={}".format(source_layer.crs().authid()),
                layer_name, "memory"
            )
            edge_layer.dataProvider().addAttributes([
                QgsField("source_edge", _qtype_string(), len=40),
                QgsField(SPLIT_FIELD, _qtype_longlong()),
            ])
            edge_layer.updateFields()
            project.addMapLayer(edge_layer)

        # Stil und Beschriftung bei jedem Lauf setzen (auch für vorhandene Layer).
        edge_layer.renderer().setSymbol(self._edge_symbol())
        self._set_edge_labels(edge_layer)

        # Bestehende Kanten ausdrücklich erhalten und nur die neue ergänzen.
        provider = edge_layer.dataProvider()
        edge_feature = QgsFeature(edge_layer.fields())
        edge_feature.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(p1), QgsPointXY(p2)]))
        edge_feature.setAttribute("source_edge", "Bezugskante {}".format(edge_layer.featureCount() + 1))
        edge_feature.setAttribute(SPLIT_FIELD, split_id)
        success, _ = provider.addFeatures([edge_feature])
        if not success:
            self._warning(self.tr("edge_feature_failed"))
            return
        edge_layer.updateExtents()
        edge_layer.triggerRepaint()

    @staticmethod
    def _edge_symbol():
        """Cyan, 3 Pixel breite Bezugskante."""
        symbol = QgsLineSymbol.createSimple({
            "line_color": "0,127,127,255",
            "line_width": "3",
            "line_style": "solid"
        })
        symbol.setOutputUnit(_pixel_unit())
        return symbol

    @staticmethod
    def _set_edge_labels(edge_layer):
        """Beschriftet die Bezugskanten entlang der Linie mit der split_id."""
        settings = QgsPalLayerSettings()
        settings.fieldName = (
            "'[ID ' || " + QgsExpression.quotedColumnRef(SPLIT_FIELD) + " || ']'"
        )
        settings.isExpression = True
        settings.placement = _line_placement()

        text_format = QgsTextFormat()
        text_format.setFont(QFont("Arial", 10))
        text_format.setSize(10)
        text_format.setColor(QColor(0, 127, 127))

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.0)
        buffer.setColor(QColor(255, 255, 255))
        text_format.setBuffer(buffer)

        settings.setFormat(text_format)
        edge_layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        edge_layer.setLabelsEnabled(True)

    def _next_split_id(self):
        """Nächste freie split_id über Ergebnis- und Bezugskanten-Layer hinweg."""
        max_id = 0
        for name in (self.tr("output_layer"), self.tr("edge_layer")):
            for lyr in QgsProject.instance().mapLayersByName(name):
                if not isinstance(lyr, QgsVectorLayer):
                    continue
                if SPLIT_FIELD not in [f.name() for f in lyr.fields()]:
                    continue
                for feat in lyr.getFeatures():
                    value = feat[SPLIT_FIELD]
                    if value is not None:
                        max_id = max(max_id, int(value))
        return max_id + 1

    @staticmethod
    def _set_output_symbology(output):
        """Orange Füllung (#FF8000) mit 50 Prozent Transparenz."""
        symbol = QgsFillSymbol.createSimple({
            "color": "255,128,0,128",
            "outline_color": "255,128,0,255",
            "outline_width": "0.26",
            "outline_width_unit": "MM"
        })
        output.renderer().setSymbol(symbol)

    # -- Ablauf --------------------------------------------------------------

    def _ask_area(self, total_area):
        """Ein Dialog mit Flächeneingabe und Einheit (m² / ha).

        Liefert (Fläche in m², Einheit) oder None bei Abbruch.
        """
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle(self.tr("title"))
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(self.tr("target_area_label")))
        spin = QDoubleSpinBox(dialog)
        spin.setMinimumWidth(180)
        layout.addWidget(spin)

        radio_m2 = QRadioButton(self.tr("unit_m2"), dialog)
        radio_ha = QRadioButton(self.tr("unit_ha"), dialog)
        radio_m2.setChecked(True)
        layout.addWidget(radio_m2)
        layout.addWidget(radio_ha)

        ok_flag = _resolve(lambda: QDialogButtonBox.StandardButton.Ok,
                           lambda: QDialogButtonBox.Ok)
        cancel_flag = _resolve(lambda: QDialogButtonBox.StandardButton.Cancel,
                               lambda: QDialogButtonBox.Cancel)
        buttons = QDialogButtonBox(ok_flag | cancel_flag, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        state = {"ha": False}

        def configure(ha):
            # Aktuellen Wert in m² merken, dann in die neue Einheit umrechnen.
            value_m2 = spin.value() * (10000.0 if state["ha"] else 1.0)
            state["ha"] = ha
            factor = 10000.0 if ha else 1.0
            min_value = 0.01 / factor
            max_value = max(min_value, total_area / factor)
            spin.blockSignals(True)
            spin.setDecimals(6 if ha else 2)
            spin.setRange(min_value, max_value)
            spin.setValue(min(max(value_m2 / factor, min_value), max_value))
            spin.setSuffix(" ha" if ha else " m²")
            spin.blockSignals(False)

        configure(False)
        spin.setValue(total_area)
        radio_m2.toggled.connect(lambda checked: configure(False) if checked else None)
        radio_ha.toggled.connect(lambda checked: configure(True) if checked else None)

        accepted = _resolve(lambda: QDialog.DialogCode.Accepted, lambda: QDialog.Accepted)
        if dialog.exec() != accepted:
            return None
        if state["ha"]:
            return spin.value() * 10000.0, "ha"
        return spin.value(), "m²"

    def run(self):
        layer = self.iface.activeLayer()
        if layer is None:
            self._warning(self.tr("no_layer"))
            return

        # Nur Vektorlayer haben Geometrien (Raster- und Gruppenlayer abweisen).
        if not isinstance(layer, QgsVectorLayer):
            self._warning(self.tr("not_vector"))
            return

        geom_type = layer.geometryType()
        if geom_type != _geom("Polygon"):
            self._warning(self.tr("wrong_geometry", self._geometry_name(geom_type)))
            return

        selected = layer.selectedFeatures()
        if len(selected) != 1:
            self._warning(self.tr("select_one"))
            return
        if layer.crs().isGeographic():
            self._warning(self.tr("geographic_crs"))
            return
        if layer.crs().mapUnits() != _meter_unit():
            self._warning(self.tr("not_meters"))
            return

        source_feature = selected[0]
        source_geometry = QgsGeometry(source_feature.geometry())
        if source_geometry.isNull() or source_geometry.isEmpty():
            self._warning(self.tr("empty_geometry"))
            return
        if not source_geometry.isGeosValid():
            self._warning(self.tr("invalid_geometry"))
            return

        total_area = source_geometry.area()
        result = self._ask_area(total_area)
        if result is None:
            return
        target_area, self._area_unit = result

        if target_area >= total_area:
            self._warning(self.tr("target_too_large", total_area))
            return

        canvas = self.iface.mapCanvas()
        self.previous_map_tool = canvas.mapTool()

        def on_edge_selected(click_point):
            self._on_edge_selected(
                click_point, layer, source_feature, source_geometry,
                target_area, total_area
            )

        self.map_tool = EdgeClickTool(canvas, on_edge_selected)
        canvas.setMapTool(self.map_tool)
        self.iface.messageBar().pushMessage(
            self.tr("title"), self.tr("click_edge"),
            level=_info_level(), duration=8
        )

    def _on_edge_selected(self, click_point, layer, source_feature,
                          source_geometry, target_area, total_area):
        canvas = self.iface.mapCanvas()
        self._restore_map_tool()

        if click_point is None:
            return  # Vom Nutzer abgebrochen

        try:
            self._process_click(
                click_point, layer, source_feature, source_geometry,
                target_area, total_area, canvas
            )
        except Exception as exc:
            self._warning(self.tr("error", str(exc)))

    def _process_click(self, click_point, layer, source_feature, source_geometry,
                       target_area, total_area, canvas):
        edge = self._nearest_edge(source_geometry, click_point, layer, canvas)
        if edge is None:
            self._warning(self.tr("no_edge"))
            return

        _, _, p1, p2 = edge
        dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length == 0:
            self._warning(self.tr("zero_edge"))
            return

        tx, ty = dx / length, dy / length
        nx, ny = -ty, tx          # Normale: zeigt nach links der Kante
        origin = QgsPointXY(p1)

        # Innenseite bestimmen: Probepunkte beidseitig des Kantenmittelpunkts.
        bbox = source_geometry.boundingBox()
        scale = max(bbox.width(), bbox.height(), 1.0)
        probe = max(scale * 1e-6, 1e-4)
        mid_x = (p1.x() + p2.x()) / 2.0
        mid_y = (p1.y() + p2.y()) / 2.0
        left_inside = source_geometry.contains(QgsGeometry.fromPointXY(
            QgsPointXY(mid_x + nx * probe, mid_y + ny * probe)))
        right_inside = source_geometry.contains(QgsGeometry.fromPointXY(
            QgsPointXY(mid_x - nx * probe, mid_y - ny * probe)))

        if left_inside and not right_inside:
            pass
        elif right_inside and not left_inside:
            nx, ny = -nx, -ny
        else:
            self._warning(self.tr("side_unclear"))
            return

        points = self._all_ring_points(source_geometry)
        if not points:
            self._warning(self.tr("no_points"))
            return

        u_values, v_values = [], []
        for point in points:
            rx, ry = point.x() - origin.x(), point.y() - origin.y()
            u_values.append(rx * tx + ry * ty)
            v_values.append(rx * nx + ry * ny)

        u_min, u_max = min(u_values), max(u_values)
        v_min, v_max = min(v_values), max(v_values)
        margin = max(u_max - u_min, v_max - v_min, 1.0) * 3.0

        # Grenzen so wählen, dass der Schnitt am Start leer und am Ende
        # die gesamte Fläche umfasst.
        low = v_min - 0.5 * margin
        high = v_max + 0.5 * margin

        low_target, _ = self._split_at_offset(
            source_geometry, origin, tx, ty, nx, ny,
            u_min, u_max, v_min, v_max, low)
        high_target, _ = self._split_at_offset(
            source_geometry, origin, tx, ty, nx, ny,
            u_min, u_max, v_min, v_max, high)

        if low_target is None or high_target is None:
            self._warning(self.tr("calculation_failed"))
            return

        min_area = low_target.area()
        max_area = high_target.area()
        if target_area < min_area - 0.0001 or target_area > max_area + 0.0001:
            self._warning(self.tr("cannot_bracket"))
            return

        # Binäre Suche nach dem Schnittversatz mit der gewünschten Fläche.
        best_target = None
        best_remainder = None
        best_error = float("inf")
        lo, hi = low, high
        min_step = max(1e-9, scale * 1e-12)

        for _ in range(200):
            mid = (lo + hi) / 2.0
            target, remainder = self._split_at_offset(
                source_geometry, origin, tx, ty, nx, ny,
                u_min, u_max, v_min, v_max, mid)
            if target is None or remainder is None:
                self._warning(self.tr("calculation_failed"))
                return

            area = target.area()
            error = abs(area - target_area)
            if error < best_error:
                best_error = error
                best_target, best_remainder = target, remainder

            if error <= 0.0001 or (hi - lo) < min_step:
                break
            if area < target_area:
                lo = mid
            else:
                hi = mid

        if best_target is None or best_remainder is None:
            self._warning(self.tr("calculation_failed"))
            return
        if not best_target.isGeosValid():
            self._warning(self.tr("invalid_target"))
            return
        if not best_remainder.isGeosValid():
            self._warning(self.tr("invalid_remainder"))
            return

        target_area_result = best_target.area()
        remainder_area = best_remainder.area()
        area_tolerance = max(0.001, total_area * 1e-7)
        if abs(target_area_result + remainder_area - total_area) > area_tolerance:
            self._warning(self.tr("area_mismatch"))
            return

        split_id = self._next_split_id()

        # Vorhandenen Ergebnislayer wiederverwenden oder einmalig anlegen.
        project = QgsProject.instance()
        source_field_names = [field.name() for field in layer.fields() if field.name() != SPLIT_FIELD]
        part_field = self._unique_field_name("part_type", source_field_names)
        area_field = self._unique_field_name(
            "area_m2", source_field_names + [part_field]
        )
        matching_layers = project.mapLayersByName(self.tr("output_layer"))
        output = matching_layers[0] if matching_layers else None

        if output is not None:
            output_field_names = [field.name() for field in output.fields()]
            if (not isinstance(output, QgsVectorLayer)
                    or output.geometryType() != _geom("Polygon")
                    or output.crs() != layer.crs()
                    or not all(name in output_field_names for name in source_field_names)
                    or part_field not in output_field_names
                    or area_field not in output_field_names):
                self._warning(self.tr("output_incompatible"))
                return
            if not _ensure_field(output, QgsField(SPLIT_FIELD, _qtype_longlong())):
                self._warning(self.tr("field_failed"))
                return
            if not _ensure_field(output, QgsField(UNIT_FIELD, _qtype_string(), len=10)):
                self._warning(self.tr("field_failed"))
                return
        else:
            output = QgsVectorLayer(
                "MultiPolygon?crs={}".format(layer.crs().authid()),
                self.tr("output_layer"), "memory"
            )
            provider = output.dataProvider()
            provider.addAttributes([f for f in layer.fields() if f.name() != SPLIT_FIELD])
            provider.addAttributes([
                QgsField(part_field, _qtype_string(), len=30),
                QgsField(area_field, _qtype_double(), len=20, prec=2),
                QgsField(SPLIT_FIELD, _qtype_longlong()),
                QgsField(UNIT_FIELD, _qtype_string(), len=10),
            ])
            output.updateFields()

        results = [
            (best_target, self.tr("target_label"), target_area_result),
            (best_remainder, self.tr("remainder_label"), remainder_area),
        ]
        output_field_names = [field.name() for field in output.fields()]
        source_attributes = dict(zip([f.name() for f in layer.fields()], source_feature.attributes()))
        features = []
        for geometry, label, area in results:
            feature = QgsFeature(output.fields())
            result_geometry = QgsGeometry(geometry)
            if not result_geometry.isMultipart():
                result_geometry.convertToMultiType()
            feature.setGeometry(result_geometry)
            attributes = []
            for name in output_field_names:
                if name == part_field:
                    attributes.append(label)
                elif name == area_field:
                    attributes.append(area)
                elif name == SPLIT_FIELD:
                    attributes.append(split_id)
                elif name == UNIT_FIELD:
                    attributes.append(self._area_unit)
                else:
                    attributes.append(source_attributes.get(name))
            feature.setAttributes(attributes)
            features.append(feature)

        success, _ = output.dataProvider().addFeatures(features)
        if not success:
            self._warning(self.tr("feature_failed"))
            return

        output.updateExtents()
        self._set_labels(output, area_field)
        self._set_output_symbology(output)
        if not matching_layers:
            project.addMapLayer(output)

        # Die zuletzt verwendete Ursprungskante in einem eigenen Layer hervorheben.
        self._highlight_edge(layer, p1, p2, split_id)
        output.triggerRepaint()

        QMessageBox.information(
            self.iface.mainWindow(), self.tr("complete"),
            self.tr("results_added") + "\n\n"
            + self.tr("target_result", target_area_result) + "\n"
            + self.tr("requested_result", target_area) + "\n"
            + self.tr("deviation_result", abs(target_area_result - target_area)) + "\n"
            + self.tr("remainder_result", remainder_area) + "\n"
            + self.tr("split_result", split_id) + "\n\n"
            + self.tr("area_note")
        )
