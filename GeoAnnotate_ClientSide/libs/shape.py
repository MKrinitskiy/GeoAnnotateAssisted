#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from libs.lib import distance
from libs.ServiceDefs import enum
import sys
import numpy as np
import uuid
from .MCSlabel import *
from .MClabel import *
from datetime import datetime
from libs.ga_defs import *

DEFAULT_LINE_COLOR = QColor(0, 255, 0, 128)
DEFAULT_FILL_COLOR = QColor(255, 0, 0, 128)
DEFAULT_SELECT_LINE_COLOR = QColor(255, 255, 255)
DEFAULT_SELECT_FILL_COLOR = QColor(0, 128, 255, 155)
DEFAULT_VERTEX_FILL_COLOR = QColor(0, 255, 0, 255)
DEFAULT_HVERTEX_FILL_COLOR = QColor(255, 0, 0)
MIN_Y_LABEL = 10

shape_types = enum(['ellipse', 'circle', 'qllabel'])


class PointType(enum(['BasicPoint', 'AuxiliaryPoint'])):
    pass


class ShapePoint(object):
    def __init__(self,
                 pt: QPointF,
                 pointtype: PointType = PointType.BasicPoint,
                 basicpoint: "ShapePoint" = None):
        self.uid = str(uuid.uuid4())
        self.qtpoint = pt
        self.pointtype = pointtype
        if pointtype == PointType.BasicPoint:
            self.basicpointuid = None
        else:
            self.basicpointuid = basicpoint.uid
    
    def __init__(self,
                 pt: QPointF,
                 pointtype: PointType = PointType.BasicPoint,
                 basicpointuid: str = None):
        self.uid = str(uuid.uuid4())
        self.qtpoint = pt
        self.pointtype = pointtype
        if pointtype == PointType.BasicPoint:
            self.basicpointuid = None
        else:
            self.basicpointuid = basicpointuid

    def copy(self):
        return ShapePoint(self.qtpoint, self.pointtype, self.basicpointuid)

    def __add__(self, other: QPointF):
        return ShapePoint(self.qtpoint + other, self.pointtype, self.basicpointuid)
    
    def __sub__(self, other: QPointF):
        return ShapePoint(self.qtpoint - other, self.pointtype, self.basicpointuid)
    
    def __str__(self):
        return f'ShapePoint: {self.uid}, {self.qtpoint}, {self.pointtype}, {self.basicpointuid}'


class Shape(object):
    P_SQUARE, P_ROUND = range(2)

    MOVE_VERTEX, NEAR_VERTEX = range(2)

    # The following class variables influence the drawing
    # of _all_ shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    width_circles_color = DEFAULT_SELECT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR
    point_type = P_ROUND
    point_size = 8
    scale = 1.0

    # def __init__(self, label=None, paintLabel=False, parent_canvas = None, uid = None, dt = None):
    def __init__(self, label=None, paintLabel=False, parent_canvas=None):
        self.parent_canvas = parent_canvas
        self.label_type = self.parent_canvas.parent.label_types
        if label is None:
            self.uid = str(uuid.uuid4())
            if 'curr_dt' in parent_canvas.parent.__dict__.keys():
                self.dt = parent_canvas.parent.curr_dt
            else:
                self.dt = datetime.now()

            try:    
                if self.label_type == 'QLL':
                    self.label = self.parent_canvas.parent.label_class("", self.uid, self.dt, None, None, os.path.basename(parent_canvas.parent.filePath))
                else:
                    self.label = self.parent_canvas.parent.label_class("", self.uid, self.dt, None, None)
            except:
                self.label = None
                ReportException('./logs/error.log', None)
                return
        elif (isinstance(label, self.parent_canvas.parent.label_class)):
            self.label = label
            self.uid = label.uid
            self.dt = label.dt
        else:
            self.parent_canvas.logger.error(f'label is not an instance of {self.parent_canvas.parent.label_class}')
            raise NotImplementedError()

        if self.label_type == 'MCS':
            self.shape_type = shape_types.ellipse
        elif ((self.label_type == 'MC') | (self.label_type == 'PL')):
            self.shape_type = shape_types.circle
        elif (self.label_type == 'AMRC'):
            self.shape_type = shape_types.circle
        elif (self.label_type == 'CS'):
            self.shape_type = shape_types.ellipse
        elif (self.label_type == 'QLL'):
            self.shape_type = shape_types.qllabel

        self.points = {}
        self.points_uids = []


        self.latlonPoints = {}
        self.latlonPoints_uids = []

        self.selected = False
        self.paintLabel = paintLabel
        self.fill = False

        # mk
        self._painter = QPainter()

        self.shapes_points_count = 3
        if self.parent_canvas.parent.label_types == 'MCS':
            self.shapes_points_count = 3
        elif self.parent_canvas.parent.label_types == 'MC':
            self.shapes_points_count = 2
        elif self.parent_canvas.parent.label_types == 'PL':
            self.shapes_points_count = 2
        elif self.parent_canvas.parent.label_types == 'AMRC':
            self.shapes_points_count = 2
        elif self.parent_canvas.parent.label_types == 'CS':
            self.shapes_points_count = 3
        elif self.parent_canvas.parent.label_types == 'QLL':
            self.shapes_points_count = None

        self._highlightUID = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
        }

        self._closed = False

    def close(self):
        self._closed = True

    def reachMaxPoints(self):
        if self.shape_type == shape_types.qllabel:
            return False
        elif ((len(self.points) >= 3) and (self.shapes_points_count is not None)):
            return True
        return False

    def addPoint(self, point: QPointF, latlonPoint: QPointF):
        self.parent_canvas.logger.info(f'addPoint: {point}, {latlonPoint}')
        if not self.reachMaxPoints():
            shpt = ShapePoint(point)
            self.points[shpt.uid] = shpt
            self.points_uids.append(shpt.uid)
            self.addLatLonPoint(latlonPoint)
    
    def addLatLonPoint(self, latlonPoint: QPointF):
        self.parent_canvas.logger.info(f'addLatLonPoint: {latlonPoint}')
        llnpt = ShapePoint(latlonPoint)
        self.latlonPoints[llnpt.uid] = llnpt
        self.latlonPoints_uids.append(llnpt.uid)
    
    def addQLLpoint(self,
                     point: QPointF,
                     latlonPoint: QPointF,
                     auxiliarypoint: QPointF,
                     latlonAuxiliaryPoint: QPointF):
        self.parent_canvas.logger.info(f'addQLLpoint: {point}, {latlonPoint}, {auxiliarypoint}, {latlonAuxiliaryPoint}')
        if not self.reachMaxPoints():
            pt = ShapePoint(point)
            self.parent_canvas.logger.info(f'adding point: {pt}')
            self.points[pt.uid] = pt
            self.points_uids.append(pt.uid)
            self.parent_canvas.logger.info(f'added point: {pt}')
            self.addLatLonPoint(latlonPoint)
            auxpt = ShapePoint(auxiliarypoint, PointType.AuxiliaryPoint, pt.uid)
            self.parent_canvas.logger.info(f'adding auxiliary point: {auxpt}')
            self.points[auxpt.uid] = auxpt
            self.points_uids.append(auxpt.uid)
            self.parent_canvas.logger.info(f'added auxiliary point: {auxpt}')
            self.addLatLonPoint(latlonAuxiliaryPoint)


    def isClosed(self):
        return self._closed

    def setOpen(self):
        self._closed = False


    def paint(self):
        if self.points:
            # TODO: plot from latlonPoints not from points

            self._painter.begin(self.parent_canvas)
            self._painter.scale(self.parent_canvas.scale, self.parent_canvas.scale)
            self._painter.translate(self.parent_canvas.offsetToCenter())

            color = self.select_line_color if self.selected else self.line_color
            pen = QPen(color)
            # Try using integer sizes for smoother drawing(?)
            pen.setWidth(max(1, int(round(2.0 / self.scale))))
            self._painter.setPen(pen)

            if self.fill:
                color = self.select_fill_color if self.selected else self.fill_color
                self._painter.setBrush(color)

            if self.shape_type == shape_types.qllabel:               
                vrtx_path = QPainterPath()
                width_path = QPainterPath()

                line_path = QPainterPath()
                line_path.moveTo(self.points[self.points_uids[0]].qtpoint)
                basic_points_uids = [uid for uid in self.points_uids if self.points[uid].pointtype == PointType.BasicPoint]
                for ptuid in basic_points_uids[1:]:
                    line_path.lineTo(self.points[ptuid].qtpoint)
                    self.drawVertex(vrtx_path, self.points[ptuid])
                    try:
                        self.drawWidthCircle(width_path, vrtx_path, self.points[ptuid])
                    except:
                        self.parent_canvas.logger.error(f'drawWidthCircle: {self.points[ptuid]}')
                
                self._painter.drawPath(line_path)
                self._painter.drawPath(width_path)
                self._painter.drawPath(vrtx_path)
                self._painter.fillPath(vrtx_path, self.vertex_fill_color)
                self._painter.fillPath(width_path, self.width_circles_color)


            elif (self.shapes_points_count == len(self.points)):
                if self.shapes_points_count == 2:
                    x0 = self.points[self.points_uids[0]].qtpoint.x()
                    x1 = self.points[self.points_uids[1]].qtpoint.x()
                    xc = 0.5 * (x0 + x1)
                    y0 = self.points[self.points_uids[0]].qtpoint.y()
                    y1 = self.points[self.points_uids[1]].qtpoint.y()
                    yc = 0.5 * (y0 + y1)
                    dx = x1 - x0
                    dy = y1 - y0
                    diameter = np.sqrt(dx * dx + dy * dy)
                    r = diameter * 0.5

                    line_path = QPainterPath()
                    vrtx_path = QPainterPath()
                    line_path.moveTo(self.points[self.points_uids[0]].qtpoint)
                    basic_points_uids = [uid for uid in self.points_uids if self.points[uid].pointtype == PointType.BasicPoint]
                    for ptuid in basic_points_uids[1:]:
                        line_path.lineTo(self.points[ptuid].qtpoint)
                        self.drawVertex(vrtx_path, self.points[ptuid])
                    if self.isClosed():
                        line_path.lineTo(self.points[self.points_uids[0]].qtpoint)
                    self._painter.drawPath(line_path)
                    self._painter.drawPath(vrtx_path)
                    self._painter.fillPath(vrtx_path, self.vertex_fill_color)

                    square = QRectF(QPointF(-r, -r), QPointF(r, r))
                    self._painter.translate(xc, yc)
                    self._painter.drawEllipse(square)
                elif self.shapes_points_count == 3:
                    x0 = self.points[self.points_uids[0]].qtpoint.x()
                    x1 = self.points[self.points_uids[1]].qtpoint.x()
                    xc = 0.5 * (x0 + x1)
                    y0 = self.points[self.points_uids[0]].qtpoint.y()
                    y1 = self.points[self.points_uids[1]].qtpoint.y()
                    yc = 0.5 * (y0 + y1)
                    dx = x1 - x0
                    dy = y1 - y0

                    alpha_sign = 1.

                    if dx == 0.:
                        alpha_rad = np.pi / 2.
                        alpha = alpha_sign * 90.
                    else:
                        tg_alpha = dy / dx
                        alpha_rad = np.arctan(tg_alpha)
                        alpha = alpha_sign * (alpha_rad / np.pi) * 180.
                    x_diameter = np.sqrt(dx * dx + dy * dy)
                    a = x_diameter * 0.5

                    x2_centered = self.points[self.points_uids[2]].qtpoint.x() - xc
                    y2_centered = self.points[self.points_uids[2]].qtpoint.y() - yc
                    coords2_centered = np.asarray([[x2_centered], [y2_centered]])
                    rotation_matrix = np.asarray(
                        [[np.cos(alpha_rad), np.sin(alpha_rad)], [-np.sin(alpha_rad), np.cos(alpha_rad)]])
                    coords2_centered_rotated_inv = rotation_matrix.dot(coords2_centered)
                    x2r = coords2_centered_rotated_inv[0]
                    y2r = coords2_centered_rotated_inv[1]
                    if a == 0.:
                        b = np.abs(y2r)
                    else:
                        if 4 * (a * a) - 4 * (x2r * x2r) - y2r * y2r <= 0.:
                            b = np.abs(y2r)
                        else:
                            b = np.abs(y2r) / np.sqrt(1. - (x2r * x2r) / (a * a))

                    line_path = QPainterPath()
                    vrtx_path = QPainterPath()
                    line_path.moveTo(self.points[self.points_uids[0]].qtpoint)
                    basic_points_uids = [uid for uid in self.points_uids if self.points[uid].pointtype == PointType.BasicPoint]
                    for ptuid in basic_points_uids[1:]:
                        line_path.lineTo(self.points[ptuid].qtpoint)
                        self.drawVertex(vrtx_path, self.points[ptuid])
                    if self.isClosed():
                        line_path.lineTo(self.points[self.points_uids[0]].qtpoint)
                    self._painter.drawPath(line_path)
                    self._painter.drawPath(vrtx_path)
                    self._painter.fillPath(vrtx_path, self.vertex_fill_color)

                    rect = QRectF(QPointF(-a, -b), QPointF(a, b))
                    self._painter.translate(xc, yc)
                    self._painter.rotate(alpha)
                    self._painter.drawEllipse(rect)
            

            self._painter.end()


    def drawVertex(self, path, shpt: ShapePoint):
        d = self.point_size / self.scale

        # TODO: perhaps convert latlonPoints to points in order to draw

        point = shpt
        if shpt.uid == self._highlightUID:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        
        if self._highlightUID is not None:
            self.vertex_fill_color = self.hvertex_fill_color
        else:
            self.vertex_fill_color = Shape.vertex_fill_color

        if self.point_type == self.P_SQUARE:
            path.addRect(point.qtpoint.x() - d / 2, point.qtpoint.y() - d / 2, d, d)
        elif self.point_type == self.P_ROUND:
            path.addEllipse(point.qtpoint, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"
    

    def drawAuxiliaryVertex(self, path, shpt: ShapePoint):
        d = self.point_size / self.scale
        if shpt.uid == self._highlightUID:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        
        try:
            path.addEllipse(shpt.qtpoint, d / 2.0, d / 2.0)
        except:
            pass


    def drawWidthCircle(self, width_path, vrtx_path, shpt: ShapePoint):
        # TODO: perhaps convert latlonPoints to points in order to draw
        # 
        
        point = shpt
        auxpt = [pt for pt in self.points if (pt.pointtype == PointType.AuxiliaryPoint) and (pt.basicpointuid == shpt.uid)][0]
        self.drawAuxiliaryVertex(vrtx_path, auxpt)
        
        try:
            x0 = point.qtpoint.x()
            x1 = auxpt.qtpoint.x()
            y0 = point.qtpoint.y()
            y1 = auxpt.qtpoint.y()
            dx = x1 - x0
            dy = y1 - y0
            r = np.sqrt(dx * dx + dy * dy)

            width_path.addEllipse(QPointF(x0, y0), r, r)
        except:
            pass

        
    def nearestVertex(self, point, epsilon) -> str:

        # TODO: perhaps convert latlonPoints to points

        for ptuid in self.points_uids:
            if distance(self.points[ptuid].qtpoint - point) <= epsilon:
                return self.points[ptuid].uid
        return None
    
    

    def containsPoint(self, point):
        if self.shape_type == shape_types.ellipse:
            return self.makePath().contains(point)
        elif self.shape_type == shape_types.circle:
            x0 = self.points[self.points_uids[0]].qtpoint.x()
            x1 = self.points[self.points_uids[1]].qtpoint.x()
            xc = 0.5 * (x0 + x1)
            y0 = self.points[self.points_uids[0]].qtpoint.y()
            y1 = self.points[self.points_uids[1]].qtpoint.y()
            yc = 0.5 * (y0 + y1)
            dx = x1 - x0
            dy = y1 - y0
            diameter = np.sqrt(dx * dx + dy * dy)
            r = diameter * 0.5

            return ((point.qtpoint.x() - xc)**2 + (point.qtpoint.y() - yc)**2) <= r**2

    def makePath(self):
        path = QPainterPath(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        return path

    def boundingRect(self):
        return self.makePath().boundingRect()

    def moveBy(self, offset: QPointF):
        self.points = [self.points[uid] + offset for uid in self.points_uids]

    def moveVertexBy(self, uid: str, offset: QPointF):
        
        self.points[uid] = self.points[uid] + offset
        if self.points[uid].pointtype == PointType.BasicPoint:
            try:
                auxpt = [pt for auxuid,pt in self.points.items() if (pt.pointtype == PointType.AuxiliaryPoint) and (pt.basicpointuid == uid)][0]
                auxpt = auxpt + offset
            except:
                pass

    def highlightVertex(self, uid: str, action):
        self._highlightUID = uid
        self._highlightMode = action

    def highlightClear(self):
        self._highlightUID = None

    def copy(self):
        shape = Shape(self.label, parent_canvas=self.parent_canvas)
        shape.points = [p.copy() for p in self.points] # TODO: it is incorrect since uids are copied yet they should be unique
        shape.latlonPoints = [p.copy() for p in self.latlonPoints] # TODO: it is incorrect since uids are copied yet they should be unique
        shape.fill = self.fill
        shape.selected = self.selected
        shape._closed = self._closed
        if self.line_color != Shape.line_color:
            shape.line_color = self.line_color
        if self.fill_color != Shape.fill_color:
            shape.fill_color = self.fill_color
        shape.difficult = self.difficult
        shape.label = self.label
        return shape

    def __len__(self):
        return len([pt for uid,pt in self.points.items() if pt.pointtype == PointType.BasicPoint])

    def __getitem__(self, key):
        return self.points[key]
        

    def __setitem__(self, key, value):
        self.points[key] = value
