import logging
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
#from PyQt4.QtOpenGL import *

from libs.shape import Shape
from libs.lib import distance

CURSOR_DEFAULT = Qt.ArrowCursor
CURSOR_POINT = Qt.PointingHandCursor
CURSOR_DRAW = Qt.CrossCursor
CURSOR_MOVE = Qt.ClosedHandCursor
CURSOR_GRAB = Qt.OpenHandCursor


class Canvas(QWidget):
    zoomRequest = pyqtSignal(int)
    scrollRequest = pyqtSignal(int, int)
    newShape = pyqtSignal()
    selectionChanged = pyqtSignal(bool)
    shapeMoved = pyqtSignal()
    shapeMovesFinished = pyqtSignal()
    drawingPolygon = pyqtSignal(bool)

    CREATE, EDIT, CREATEELLIPSE, CREATEQLLABEL = list(range(4))

    epsilon = 11.0

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        # Initialise local state.
        if 'parent' in kwargs.keys():
            self.parent = kwargs['parent']

        self.shapes_points_count = 3
        if self.parent.label_types == 'MCS':
            self.shapes_points_count = 3
        elif self.parent.label_types == 'MC':
            self.shapes_points_count = 2
        elif self.parent.label_types == 'PL':
            self.shapes_points_count = 2
        elif self.parent.label_types == 'AMRC':
            self.shapes_points_count = 2
        elif self.parent.label_types == 'CS':
            self.shapes_points_count = 3
        elif self.parent.label_types == 'QLL':
            self.shapes_points_count = None

        self.mode = self.EDIT
        self.shapes = []
        self.currentShape = None
        self.selectedShape = None  # save the selected shape here
        # self.curr_dt = None

        self.selectedShapeCopy = None
        self.drawingLineColor = QColor(0, 0, 255)
        self.drawingRectColor = QColor(0, 0, 255) 
        # self.line = Shape(parent_canvas=self)
        self.prevPoint = QPointF()
        self.offsets = QPointF(), QPointF()
        self.scale = 1.0
        self.pixmap = QPixmap()
        self.visible = {}
        self._hideBackround = False
        self.hideBackround = False
        self.hShape = None
        self.hVertex = None
        self._painter = QPainter()
        self._cursor = CURSOR_DEFAULT
        # Menus:
        self.menus = (QMenu(), QMenu())
        # Set widget options.
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)
        self.verified = False

        self.logger = logging.getLogger(__name__)



    def setDrawingColor(self, qColor):
        self.drawingLineColor = qColor
        self.drawingRectColor = qColor

    def enterEvent(self, ev):
        self.overrideCursor(self._cursor)

    def leaveEvent(self, ev):
        self.restoreCursor()

    def focusOutEvent(self, ev):
        self.restoreCursor()

    def isVisible(self, shape):
        return self.visible.get(shape, True)

    def drawing(self):
        return self.mode == self.CREATE

    def drawing_ellipse(self):
        return self.mode == self.CREATEELLIPSE

    def drawing_qllabel(self):
        return self.mode == self.CREATEQLLABEL

    def editing(self):
        return self.mode == self.EDIT

    def setEditing(self, value=True):
        if value:
            if self.parent.label_types == 'QLL':
                self.mode = self.CREATEQLLABEL
            elif self.parent.label_types == 'MCS':
                self.mode = self.CREATEELLIPSE
            elif ((self.parent.label_types == 'MC') or (self.parent.label_types == 'PL') or (self.parent.label_types == 'AMRC')):
                self.mode = self.CREATE
            else:
                self.mode = self.EDIT
        else:
            if self.parent.label_types == 'QLL':
                self.mode = self.CREATEQLLABEL
            elif ((self.parent.label_types == 'MC') or (self.parent.label_types == 'PL') or (self.parent.label_types == 'AMRC')):
                self.mode = self.CREATEELLIPSE
            else:
                self.mode = self.CREATE

        if not value:  # Create
            self.unHighlight()
            self.deSelectShape()
        self.prevPoint = QPointF()
        self.repaint()

    def unHighlight(self):
        if self.hShape:
            self.hShape.highlightClear()
        self.hVertex = self.hShape = None

    def selectedVertex(self):
        return self.hVertex is not None

    def mouseMoveEvent(self, ev):
        """Update line with last point and current coordinates."""
        pos = self.transformPos(ev.pos())
        try:
            posLon,posLat = self.parent.basemaphelper.xy2latlon(pos.x(), pos.y())
        except:
            return
        posValue = self.parent.basemaphelper.xy2value(pos.x(), pos.y())
        self.parent.window().labelCoordinates.setText('lat: %.2f; lon: %.2f; value: %f' % (posLat, posLon, posValue))
        self.setToolTip('lat: %.2f; lon: %.2f; value: %s' % (posLat, posLon, posValue))


        self.mousePosLatLon = QPointF(posLon, posLat)

        if self.drawing_ellipse():
            return
        elif self.drawing():
            self.overrideCursor(CURSOR_DRAW)
            if self.currentShape:
                color = self.drawingLineColor
                if self.outOfPixmap(pos):
                    # Don't allow the user to draw outside the pixmap.
                    # Project the point to the pixmap's edges.
                    pos = self.intersectionPoint(self.currentShape[-1], pos)
                elif len(self.currentShape) > 1 and self.closeEnough(pos, self.currentShape[0]):
                    # Attract line to starting point and colorise to alert the
                    # user:
                    pos = self.currentShape[0]
                    color = self.currentShape.line_color
                    self.overrideCursor(CURSOR_POINT)
                    self.currentShape.highlightVertex(0, Shape.NEAR_VERTEX)
                # self.line[1] = pos
                # self.line.line_color = color
                self.prevPoint = QPointF()
                self.currentShape.highlightClear()
            else:
                self.prevPoint = pos
            self.repaint()
            return

        # Polygon copy moving.
        if Qt.RightButton & ev.buttons():
            if self.selectedShapeCopy and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShape(self.selectedShapeCopy, pos)
                self.repaint()
            elif self.selectedShape:
                self.selectedShapeCopy = self.selectedShape.copy()
                self.repaint()
            return

        # Polygon/Vertex moving.
        if Qt.LeftButton & ev.buttons():
            if self.selectedVertex():
                self.boundedMoveVertex(pos)
                self.shapeMoved.emit()
                self.repaint()
            elif self.selectedShape and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShape(self.selectedShape, pos)
                self.shapeMoved.emit()
                self.repaint()

            self.recalculateMovedLatlonPointsSelectedShape()
            return

        # Just hovering over the canvas, 2 posibilities:
        # - Highlight shapes
        # - Highlight vertex
        # Update shape/vertex fill and tooltip value accordingly.
        # self.setToolTip("Image")
        # self.setToolTip('X: %d; Y: %d' % (pos.x(), pos.y()))


        for shape in reversed([s for s in self.shapes if self.isVisible(s)]):
            # Look for a nearby vertex to highlight. If that fails,
            # check if we happen to be inside a shape.
            indexOfRegularVertex = shape.nearestVertex(pos, self.epsilon)
            indexOfWidthVertex = shape.nearestWidthVertex(pos, self.epsilon)
            if indexOfRegularVertex is not None:
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.hVertex, self.hShape = indexOfRegularVertex, shape
                shape.highlightVertex(indexOfRegularVertex, shape.MOVE_VERTEX)
                self.overrideCursor(CURSOR_POINT)
                self.setToolTip("Click & drag to move point")
                self.setStatusTip(self.toolTip())
                self.update()
                break
            elif indexOfWidthVertex is not None:
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.hVertex, self.hShape = indexOfWidthVertex, shape
                shape.highlightWidthVertex(indexOfWidthVertex, shape.MOVE_VERTEX)
                self.overrideCursor(CURSOR_POINT)
                self.setToolTip("Click & drag to move point")
                self.setStatusTip(self.toolTip())
                self.update()
                break
            elif shape.containsPoint(pos):
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.hVertex, self.hShape = None, shape
                self.setToolTip(
                    "Click & drag to move shape '%s'" % shape.label)
                self.setStatusTip(self.toolTip())
                self.overrideCursor(CURSOR_GRAB)
                self.update()
                break
        else:  # Nothing found, clear highlights, reset state.
            if self.hShape:
                self.hShape.highlightClear()
                self.update()
            self.hVertex, self.hShape = None, None
            self.overrideCursor(CURSOR_DEFAULT)

        self.recalculateMovedLatlonPointsSelectedShape()



    def mousePressEvent(self, ev):
        pos = self.transformPos(ev.pos())

        if ev.button() == Qt.LeftButton:
            if self.drawing() or self.drawing_ellipse() or self.drawing_qllabel():
                self.handleDrawing(pos)
            else:
                self.selectShapePoint(pos)
                self.prevPoint = pos
                self.repaint()
        elif ev.button() == Qt.RightButton and self.drawing_qllabel():
            self.finishDrawingQLLabel(pos)
        elif ev.button() == Qt.RightButton and self.editing():
            self.selectShapePoint(pos)
            self.prevPoint = pos
            self.repaint()

        self.recalculateMovedLatlonPointsSelectedShape()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.RightButton:
            menu = self.menus[bool(self.selectedShapeCopy)]
            self.restoreCursor()
            if not menu.exec_(self.mapToGlobal(ev.pos())) and self.selectedShapeCopy:
                # Cancel the move by deleting the shadow copy.
                self.selectedShapeCopy = None
                self.repaint()
        elif ev.button() == Qt.LeftButton and self.selectedShape:
            if self.selectedVertex():
                self.overrideCursor(CURSOR_POINT)
            else:
                self.overrideCursor(CURSOR_GRAB)
            self.shapeMovesFinished.emit()
        elif ev.button() == Qt.LeftButton:
            pos = self.transformPos(ev.pos())
            if self.drawing():
                self.handleDrawing(pos)

        self.recalculateMovedLatlonPointsSelectedShape()


    def endMove(self):
        assert self.selectedShape and self.selectedShapeCopy
        shape = self.selectedShapeCopy
        self.selectedShape.points = [p for p in shape.points]
        self.selectedShapeCopy = None
        self.recalculateMovedLatlonPointsSelectedShape()



    def hideBackroundShapes(self, value):
        self.hideBackround = value
        if self.selectedShape:
            # Only hide other shapes if there is a current selection.
            # Otherwise the user will not be able to select a shape.
            self.setHiding(True)
            self.repaint()

    def handleDrawing(self, pos: QPointF):
        if self.currentShape:
            posLon, posLat = self.parent.basemaphelper.xy2latlon(pos.x(), pos.y())
            qptLatLon = QPointF(posLon, posLat)
            
            
            if self.parent.label_types == 'QLL':
                widthkeypoint = pos + QPointF(20, 20)
                widthkeypointLon, widthkeypointLat = self.parent.basemaphelper.xy2latlon(widthkeypoint.x(), widthkeypoint.y())
                latlonWidthKeyPoint = QPointF(widthkeypointLat, widthkeypointLon)
                self.currentShape.addQLLpoint(pos, qptLatLon, widthkeypoint, latlonWidthKeyPoint)
            else:
                self.currentShape.addPoint(pos, qptLatLon)

            if len(self.currentShape) == self.shapes_points_count:
                self.currentShape.close()
                self.finalise()
        elif not self.outOfPixmap(pos):
            self.currentShape = Shape(parent_canvas=self)

            posLon, posLat = self.parent.basemaphelper.xy2latlon(pos.x(), pos.y())
            qptLatLon = QPointF(posLon, posLat)
            # self.current.addPoint(pos, self.transformToLatLon(pos, True))
            self.currentShape.addPoint(pos, qptLatLon)

            self.recalculateMovedLatlonPointsSelectedShape()

            self.update()
    

    def finishDrawingQLLabel(self, pos):
        self.currentShape.close()
        self.finalise()


    def setHiding(self, enable=True):
        self._hideBackround = self.hideBackround if enable else False

    def canCloseShape(self):
        if ((self.drawing() or self.drawing_qllabel() or self.drawing_ellipse()) and self.currentShape):
            if (self.shapes_points_count is None):
                return True
            else:
                return (len(self.currentShape) > self.shapes_points_count)
        return False

    def mouseDoubleClickEvent(self, ev):
        # We need at least 4 points here, since the mousePress handler
        # adds an extra one before this handler is called.
        if self.canCloseShape():
            # self.currentShape.popPoint()
            self.finalise()

    def selectShape(self, shape):
        self.deSelectShape()
        shape.selected = True
        self.selectedShape = shape
        self.setHiding()
        self.selectionChanged.emit(True)
        self.update()

    def selectShapePoint(self, point):
        """Select the first shape created which contains this point."""
        self.deSelectShape()
        if self.selectedVertex():  # A vertex is marked for selection.
            index, shape = self.hVertex, self.hShape
            shape.highlightVertex(index, shape.MOVE_VERTEX)
            self.selectShape(shape)
            return
        for shape in reversed(self.shapes):
            if self.isVisible(shape) and shape.containsPoint(point):
                self.selectShape(shape)
                self.calculateOffsets(shape, point)
                return

    def calculateOffsets(self, shape, point):
        rect = shape.boundingRect()
        x1 = rect.x() - point.x()
        y1 = rect.y() - point.y()
        x2 = (rect.x() + rect.width()) - point.x()
        y2 = (rect.y() + rect.height()) - point.y()
        self.offsets = QPointF(x1, y1), QPointF(x2, y2)

    def boundedMoveVertex(self, pos):
        index, shape = self.hVertex, self.hShape
        point = shape[index]
        if self.outOfPixmap(pos):
            pos = self.intersectionPoint(point, pos)

        shiftPos = pos - point
        shape.moveVertexBy(index, shiftPos)

    def boundedMoveShape(self, shape, pos):
        if self.outOfPixmap(pos):
            return False  # No need to move
        o1 = pos + self.offsets[0]
        if self.outOfPixmap(o1):
            pos -= QPointF(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets[1]
        if self.outOfPixmap(o2):
            pos += QPointF(min(0, self.pixmap.width() - o2.x()),
                           min(0, self.pixmap.height() - o2.y()))
        # The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason. XXX
        #self.calculateOffsets(self.selectedShape, pos)
        dp = pos - self.prevPoint
        if dp:
            shape.moveBy(dp)
            self.prevPoint = pos
            return True
        return False

    def deSelectShape(self):
        if self.selectedShape:
            self.selectedShape.selected = False
            self.selectedShape = None
            self.setHiding(False)
            self.selectionChanged.emit(False)
            self.update()

    def deleteSelected(self):
        if self.selectedShape:
            shape = self.selectedShape
            self.shapes.remove(self.selectedShape)
            self.selectedShape = None
            self.update()
            return shape

    def boundedShiftShape(self, shape):
        # Try to move in one direction, and if it fails in another.
        # Give up if both fail.
        point = shape[0]
        offset = QPointF(2.0, 2.0)
        self.calculateOffsets(shape, point)
        self.prevPoint = point
        if not self.boundedMoveShape(shape, point - offset):
            self.boundedMoveShape(shape, point + offset)

    def paintEvent(self, event):
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)

        p = self._painter
        p.begin(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        p.scale(self.scale, self.scale)
        p.translate(self.offsetToCenter())

        p.drawPixmap(0, 0, self.pixmap)
        Shape.scale = self.scale
        for shape in self.shapes:
            if (shape.selected or not self._hideBackround) and self.isVisible(shape):
                if shape.label_type == 'QLL': 
                    shape.fill = False
                else:
                    shape.fill = shape.selected or shape == self.hShape
                shape.paint()
        if self.currentShape:
            self.currentShape.paint()
        if self.selectedShapeCopy:
            # self.selectedShapeCopy.paint(p)
            self.selectedShapeCopy.paint()

        if self.drawing() and not self.prevPoint.isNull() and not self.outOfPixmap(self.prevPoint):
            p.setPen(QColor(0, 0, 0))
            p.drawLine(self.prevPoint.x(), 0, self.prevPoint.x(), self.pixmap.height())
            p.drawLine(0, self.prevPoint.y(), self.pixmap.width(), self.prevPoint.y())

        self.setAutoFillBackground(True)
        if self.verified:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(184, 239, 38, 128))
            self.setPalette(pal)
        else:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(232, 232, 232, 255))
            self.setPalette(pal)

        p.end()

    def transformPos(self, point):
        """Convert from widget-logical coordinates to painter-logical coordinates."""
        return point / self.scale - self.offsetToCenter()


    def transformToLatLon(self, PicturePoint, outputQPointF = False):
        lat,lon=0.,0.
        try:
            bmhelper = self.parent.window().basemaphelper
            # bm = bmhelper.bm
            x_pic,y_pic = PicturePoint.x(),PicturePoint.y()
            # for cylindrical projections ONLY
            lon = (x_pic/self.pixmap.width())*(bmhelper.urcrnrlon-bmhelper.llcrnrlon) + bmhelper.llcrnrlon
            lat = ((self.pixmap.height()-y_pic)/self.pixmap.height()) * (bmhelper.urcrnrlat - bmhelper.llcrnrlat) + bmhelper.llcrnrlat
        except:
            pass
        if outputQPointF:
            return QPointF(lon,lat)
        else:
            return lat,lon


    # def transformLatLonToPixmapCoordinates(self, lon, lat):
    #     x_pic,y_pic=0.,0.
    #     try:
    #         bmhelper = self.parent.window().basemaphelper
    #         # bm = bmhelper.bm
    #         pixmap_width = self.pixmap.width()
    #         pixmap_height = self.pixmap.height()
    #         # for cylindrical projections ONLY
    #         y_pic = pixmap_height*(1.-(lat-bmhelper.llcrnrlat)/(bmhelper.urcrnrlat - bmhelper.llcrnrlat))
    #         x_pic = pixmap_width*(lon-bmhelper.llcrnrlon)/(bmhelper.urcrnrlon-bmhelper.llcrnrlon)
    #     except:
    #         pass
    #     return x_pic,y_pic



    def recalculateMovedLatlonPointsSelectedShape(self):
        if self.selectedShape:
            self.selectedShape.latlonPoints = []
            for pt in self.selectedShape.points:
                # latlonPt = self.transformToLatLon(pt, outputQPointF=True)
                posLon, posLat = self.parent.basemaphelper.xy2latlon(pt.x(), pt.y())
                qptLatLon = QPointF(posLon, posLat)
                self.selectedShape.latlonPoints.append(qptLatLon)


    def offsetToCenter(self):
        s = self.scale
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * s, self.pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPointF(x, y)

    def outOfPixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w and 0 <= p.y() <= h)

    def finalise(self):
        assert self.currentShape
        if self.currentShape.points[0] == self.currentShape.points[-1]:
            self.currentShape = None
            self.drawingPolygon.emit(False)
            self.update()
            return

        self.currentShape.close()
        self.shapes.append(self.currentShape)
        self.currentShape = None
        self.setHiding(False)
        self.newShape.emit()
        self.update()
        self.mode = self.EDIT

    def closeEnough(self, p1, p2):
        return distance(p1 - p2) < self.epsilon

    def intersectionPoint(self, p1, p2):
        # Cycle through each image edge in clockwise fashion,
        # and find the one intersecting the current line segment.
        # http://paulbourke.net/geometry/lineline2d/
        size = self.pixmap.size()
        points = [(0, 0),
                  (size.width(), 0),
                  (size.width(), size.height()),
                  (0, size.height())]
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        d, i, (x, y) = min(self.intersectingEdges((x1, y1), (x2, y2), points))
        x3, y3 = points[i]
        x4, y4 = points[(i + 1) % 4]
        if (x, y) == (x1, y1):
            # Handle cases where previous point is on one of the edges.
            if x3 == x4:
                return QPointF(x3, min(max(0, y2), max(y3, y4)))
            else:  # y3 == y4
                return QPointF(min(max(0, x2), max(x3, x4)), y3)
        return QPointF(x, y)

    def intersectingEdges(self, x1y1, x2y2, points):
        """For each edge formed by `points', yield the intersection
        with the line segment `(x1,y1) - (x2,y2)`, if it exists.
        Also return the distance of `(x2,y2)' to the middle of the
        edge along with its index, so that the one closest can be chosen."""
        x1, y1 = x1y1
        x2, y2 = x2y2
        for i in range(4):
            x3, y3 = points[i]
            x4, y4 = points[(i + 1) % 4]
            denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
            nua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
            nub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
            if denom == 0:
                # This covers two cases:
                #   nua == nub == 0: Coincident
                #   otherwise: Parallel
                continue
            ua, ub = nua / denom, nub / denom
            if 0 <= ua <= 1 and 0 <= ub <= 1:
                x = x1 + ua * (x2 - x1)
                y = y1 + ua * (y2 - y1)
                m = QPointF((x3 + x4) / 2, (y3 + y4) / 2)
                d = distance(m - QPointF(x2, y2))
                yield d, i, (x, y)

    # These two, along with a call to adjustSize are required for the
    # scroll area.
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    def wheelEvent(self, ev):
        qt_version = 4 if hasattr(ev, "delta") else 5
        if qt_version == 4:
            if ev.orientation() == Qt.Vertical:
                v_delta = ev.delta()
                h_delta = 0
            else:
                h_delta = ev.delta()
                v_delta = 0
        else:
            delta = ev.angleDelta()
            h_delta = delta.x()
            v_delta = delta.y()

        mods = ev.modifiers()
        if Qt.ControlModifier == int(mods) and v_delta:
            self.zoomRequest.emit(v_delta)
        else:
            v_delta and self.scrollRequest.emit(v_delta, Qt.Vertical)
            h_delta and self.scrollRequest.emit(h_delta, Qt.Horizontal)
        ev.accept()

    def keyPressEvent(self, ev):
        key = ev.key()
        if key == Qt.Key_Escape and self.currentShape:
            self.logger.info('ESC press')
            self.currentShape = None
            self.drawingPolygon.emit(False)
            self.update()
        elif key == Qt.Key_Return and self.canCloseShape():
            self.finalise()
        elif key == Qt.Key_Left and self.selectedShape:
            self.moveOnePixel('Left')
        elif key == Qt.Key_Right and self.selectedShape:
            self.moveOnePixel('Right')
        elif key == Qt.Key_Up and self.selectedShape:
            self.moveOnePixel('Up')
        elif key == Qt.Key_Down and self.selectedShape:
            self.moveOnePixel('Down')

    def moveOnePixel(self, direction):
        if direction == 'Left' and not self.moveOutOfBound(QPointF(-1.0, 0)):
            for i in range(self.shapes_points_count):
                self.selectedShape.points[i] += QPointF(-1.0, 0)
        elif direction == 'Right' and not self.moveOutOfBound(QPointF(1.0, 0)):
            for i in range(self.shapes_points_count):
                self.selectedShape.points[i] += QPointF(1.0, 0)
        elif direction == 'Up' and not self.moveOutOfBound(QPointF(0, -1.0)):
            for i in range(self.shapes_points_count):
                self.selectedShape.points[i] += QPointF(0, -1.0)
        elif direction == 'Down' and not self.moveOutOfBound(QPointF(0, 1.0)):
            for i in range(self.shapes_points_count):
                self.selectedShape.points[i] += QPointF(0, 1.0)

        self.recalculateMovedLatlonPointsSelectedShape()

        self.shapeMoved.emit()
        self.repaint()

    def moveOutOfBound(self, step):
        points = [p1+p2 for p1, p2 in zip(self.selectedShape.points, [step]*4)]
        self.recalculateMovedLatlonPointsSelectedShape()
        return True in map(self.outOfPixmap, points)

    def setLastLabel(self, text, line_color  = None, fill_color = None):
        assert text
        self.shapes[-1].label.name = text
        if line_color:
            self.shapes[-1].line_color = line_color
        
        if fill_color:
            self.shapes[-1].fill_color = fill_color

        return self.shapes[-1]

    def resetAllLines(self):
        assert self.shapes
        self.currentShape = self.shapes.pop()
        self.currentShape.setOpen()
        
        self.drawingPolygon.emit(True)
        self.currentShape = None
        self.drawingPolygon.emit(False)
        self.update()

    def loadPixmap(self, pixmap, clearShapes = True):
        self.pixmap = pixmap
        if clearShapes:
            self.shapes = []
        self.repaint()

    def loadShapes(self, shapes, extend=False):
        if extend:
            self.shapes.extend(list(shapes))
        else:
            self.shapes = list(shapes)
        self.currentShape = None
        self.repaint()


    def loadBasemapShapes(self, bmShapes):
        self.bmShapes = list(bmShapes)


    def setShapeVisible(self, shape, value):
        self.visible[shape] = value
        self.repaint()


    def switchBasemapAndMainShapes(self):
        self.temporaryShapes = self.shapes
        self.selectedTemporaryShape = self.selectedShape
        self.shapes = self.bmShapes
        self.selectedShape = self.selectedBmShape
        self.currentShape = None
        self.repaint()

    def switchBackBasemapAndMainShapes(self):
        self.shapes = self.temporaryShapes
        self.selectedShape = self.selectedTemporaryShape
        self.currentShape = None
        self.repaint()


    def currentCursor(self):
        cursor = QApplication.overrideCursor()
        if cursor is not None:
            cursor = cursor.shape()
        return cursor

    def overrideCursor(self, cursor):
        self._cursor = cursor
        if self.currentCursor() is None:
            QApplication.setOverrideCursor(cursor)
        else:
            QApplication.changeOverrideCursor(cursor)

    def restoreCursor(self):
        QApplication.restoreOverrideCursor()

    def resetState(self):
        self.restoreCursor()
        self.pixmap = None
        self.update()
