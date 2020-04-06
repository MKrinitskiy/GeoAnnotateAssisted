#!/usr/bin/python
# -*- coding: utf-8 -*-


try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from libs.lib import distance
import sys
import numpy as np
import uuid
from .MCSlabel import *
from datetime import datetime

DEFAULT_LINE_COLOR = QColor(0, 255, 0, 128)
DEFAULT_FILL_COLOR = QColor(255, 0, 0, 128)
DEFAULT_SELECT_LINE_COLOR = QColor(255, 255, 255)
DEFAULT_SELECT_FILL_COLOR = QColor(0, 128, 255, 155)
DEFAULT_VERTEX_FILL_COLOR = QColor(0, 255, 0, 255)
DEFAULT_HVERTEX_FILL_COLOR = QColor(255, 0, 0)
MIN_Y_LABEL = 10


class Shape(object):
    P_SQUARE, P_ROUND = range(2)

    MOVE_VERTEX, NEAR_VERTEX = range(2)

    # The following class variables influence the drawing
    # of _all_ shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR
    point_type = P_ROUND
    point_size = 8
    scale = 1.0

    # def __init__(self, label=None, paintLabel=False, parent_canvas = None, uid = None, dt = None):
    def __init__(self, label=None, paintLabel=False, parent_canvas=None):
        if label is None:
            # new shape
            # self.uid = str(uuid.uuid4()).replace('-', '')
            self.uid = str(uuid.uuid4())
            if 'curr_dt' in parent_canvas.parent.__dict__.keys():
                self.dt = parent_canvas.parent.curr_dt
            else:
                self.dt = datetime.now()
            self.label = MCSlabel('', self.uid, self.dt, None, None)
        elif isinstance(label, MCSlabel):
            self.label = label
            self.uid = label.uid
            self.dt = label.dt
        else:
            raise NotImplementedError()

        self.points = []
        self.latlonPoints = []
        self.selected = False
        self.paintLabel = paintLabel
        self.fill = False

        # mk
        self._painter = QPainter()
        self.parent_canvas = parent_canvas


        self._highlightIndex = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
        }

        self._closed = False

    def close(self):
        self._closed = True

    def reachMaxPoints(self):
        if len(self.points) >= 3:
            return True
        return False

    def addPoint(self, point, latlonPoint):
        if not self.reachMaxPoints():
            self.points.append(point)
            self.latlonPoints.append(latlonPoint)

    def popPoint(self, latlon = False):
        if self.points:
            if latlon:
                return self.latlonPoints.pop()
            else:
                return self.points.pop()
        return None

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

            if len(self.points)==1:
                xmin = min([p.x() for p in self.points])
                ymin = min([p.y() for p in self.points])
                xmax = max([p.x() for p in self.points])
                ymax = max([p.y() for p in self.points])
                rect = QRectF(QPointF(xmin, ymin), QPointF(xmax, ymax))
                self._painter.drawEllipse(rect)
            elif len(self.points)==2:
                xmin = min([p.x() for p in self.points])
                ymin = min([p.y() for p in self.points])
                xmax = max([p.x() for p in self.points])
                ymax = max([p.y() for p in self.points])
                rect = QRectF(QPointF(xmin, ymin), QPointF(xmax, ymax))
                self._painter.drawEllipse(rect)
            elif len(self.points) == 3:
                x0 = self.points[0].x()
                x1 = self.points[1].x()
                xc = 0.5*(x0 + x1)
                y0 = self.points[0].y()
                y1 = self.points[1].y()
                yc = 0.5 * (y0 + y1)
                dx = x1-x0
                dy = y1-y0

                # if dy == 0.:
                alpha_sign = 1.
                # else:
                #     alpha_sign = dy / np.abs(dy)

                if dx == 0.:
                    alpha_rad = np.pi/2.
                    alpha = alpha_sign*90.
                else:
                    tg_alpha = dy/dx
                    alpha_rad = np.arctan(tg_alpha)
                    alpha = alpha_sign*(alpha_rad/np.pi)*180.
                x_diameter = np.sqrt(dx*dx + dy*dy)
                a = x_diameter*0.5

                x2_centered = self.points[2].x() - xc
                y2_centered = self.points[2].y() - yc
                coords2_centered = np.asarray([[x2_centered],[y2_centered]])
                rotation_matrix = np.asarray([[np.cos(alpha_rad), np.sin(alpha_rad)],[-np.sin(alpha_rad), np.cos(alpha_rad)]])
                coords2_centered_rotated_inv = rotation_matrix.dot(coords2_centered)
                x2r = coords2_centered_rotated_inv[0]
                y2r = coords2_centered_rotated_inv[1]
                if a==0.:
                    b = np.abs(y2r)
                else:
                    if 4*(a*a) - 4*(x2r*x2r) - y2r*y2r <= 0.:
                        b = np.abs(y2r)
                    else:
                        b = np.abs(y2r)/np.sqrt(1. - (x2r*x2r)/(a*a))



                line_path = QPainterPath()
                vrtx_path = QPainterPath()
                line_path.moveTo(self.points[0])

                for i, p in enumerate(self.points):
                    line_path.lineTo(p)
                    self.drawVertex(vrtx_path, i)
                if self.isClosed():
                    line_path.lineTo(self.points[0])
                self._painter.drawPath(line_path)
                self._painter.drawPath(vrtx_path)
                self._painter.fillPath(vrtx_path, self.vertex_fill_color)

                rect = QRectF(QPointF(-a, -b), QPointF(a, b))
                self._painter.translate(xc, yc)
                self._painter.rotate(alpha)
                self._painter.drawEllipse(rect)



            # Draw text at the top-left
            # if self.paintLabel:
            #     min_x = sys.maxsize
            #     min_y = sys.maxsize
            #     for point in self.points:
            #         min_x = min(min_x, point.x())
            #         min_y = min(min_y, point.y())
            #     if min_x != sys.maxsize and min_y != sys.maxsize:
            #         font = QFont()
            #         font.setPointSize(8)
            #         font.setBold(True)
            #         self._painter.setFont(font)
            #         if (self.label == None):
            #             self.label = ""
            #         if (min_y < MIN_Y_LABEL):
            #             min_y += MIN_Y_LABEL
            #         self._painter.drawText(min_x, min_y, self.label)

            self._painter.end()





    def drawVertex(self, path, i):
        d = self.point_size / self.scale
        shape = self.point_type

        # TODO: perhaps convert latlonPoints to points in order to draw

        point = self.points[i]
        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self.vertex_fill_color = self.hvertex_fill_color
        else:
            self.vertex_fill_color = Shape.vertex_fill_color
        if shape == self.P_SQUARE:
            path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"



    def nearestVertex(self, point, epsilon):

        # TODO: perhaps convert latlonPoints to points

        for i, p in enumerate(self.points):
            if distance(p - point) <= epsilon:
                return i
        return None

    def containsPoint(self, point):
        return self.makePath().contains(point)

    def makePath(self):
        path = QPainterPath(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        return path

    def boundingRect(self):
        return self.makePath().boundingRect()

    def moveBy(self, offset):
        self.points = [p + offset for p in self.points]

    def moveVertexBy(self, i, offset):
        self.points[i] = self.points[i] + offset

    def highlightVertex(self, i, action):
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):
        self._highlightIndex = None

    def copy(self):
        shape = Shape(self.label, parent_canvas=self.parent_canvas)
        shape.points = [p for p in self.points]
        shape.latlonPoints = [p for p in self.latlonPoints]
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
        return len(self.points)

    def __getitem__(self, key):
        return self.points[key]

    def __setitem__(self, key, value):
        self.points[key] = value
