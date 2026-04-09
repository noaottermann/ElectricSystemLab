import os
from PyQt5.QtGui import QFont, QGuiApplication, QImage, QPainter, QPen, QColor, QPolygonF, QPainterPath
from PyQt5.QtCore import Qt, QPointF, QRectF

ROOT = os.path.dirname(__file__)
COMP = os.path.join(ROOT, "components")
CAT = os.path.join(ROOT, "categories")
FAM = os.path.join(ROOT, "components_families")

os.makedirs(COMP, exist_ok=True)
os.makedirs(CAT, exist_ok=True)
os.makedirs(FAM, exist_ok=True)

SIZE = 64
CENTER = SIZE / 2
CENTER_I = int(CENTER)
_APP = None


def _pen(width: float = 2.0) -> QPen:
    pen = QPen(QColor("#181818"), width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _pen_light(width: float = 1.4) -> QPen:
    pen = QPen(QColor("#181818"), width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _soft_color(hex_color: str) -> QColor:
    return QColor(hex_color)


def save_icon(path, draw_func):
    image = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    draw_func(painter)
    painter.end()
    if not image.save(path):
        raise RuntimeError(f"Failed to save icon: {path}")
    if not os.path.exists(path):
        raise RuntimeError(f"Icon not found after save: {path}")


def _leads(p, left_end: int, right_start: int):
    p.drawLine(8, CENTER_I, left_end, CENTER_I)
    p.drawLine(right_start, CENTER_I, SIZE - 8, CENTER_I)


def draw_wire(p):
    p.setPen(_pen())
    _leads(p, SIZE - 8, 8)
    p.setPen(QPen(QColor("#181818"), 3))
    p.drawPoint(8, CENTER_I)
    p.drawPoint(SIZE - 8, CENTER_I)


def draw_resistor(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    _leads(p, 20, SIZE - 20)
    rect = QRectF(20, CENTER - 7, SIZE - 40, 14)
    p.drawRoundedRect(rect, 3, 3)


def draw_capacitor(p):
    p.setPen(_pen())
    _leads(p, 22, SIZE - 22)
    p.drawLine(22, CENTER_I - 14, 22, CENTER_I + 14)
    p.drawLine(SIZE - 22, CENTER_I - 14, SIZE - 22, CENTER_I + 14)


def draw_inductor(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    radius = 5
    start_x = 17
    left_end = start_x
    right_start = start_x + 3 * (radius * 2)
    _leads(p, left_end, right_start)
    for i in range(3):
        x = start_x + i * (radius * 2)
        p.drawArc(x, CENTER_I - radius, radius * 2, radius * 2, 0, 180 * 16)


def draw_voltage_source_dc(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    _leads(p, 14, SIZE - 14)
    p.drawEllipse(QPointF(CENTER, CENTER), 18, 18)
    p.setPen(_pen_light())
    p.drawLine(CENTER_I - 12, CENTER_I, CENTER_I - 6, CENTER_I)
    p.drawLine(CENTER_I - 9, CENTER_I - 3, CENTER_I - 9, CENTER_I + 3)
    p.drawLine(CENTER_I + 6, CENTER_I, CENTER_I + 12, CENTER_I)


def draw_voltage_source_ac(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    _leads(p, 14, SIZE - 14)
    p.drawEllipse(QPointF(CENTER, CENTER), 18, 18)
    p.setPen(_pen_light())
    path = QPainterPath()
    path.moveTo(CENTER - 8, CENTER + 0)
    path.cubicTo(CENTER - 3, CENTER - 14, CENTER + 3, CENTER + 14, CENTER + 8, CENTER + 0)
    p.drawPath(path)


def draw_current_source_dc(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    _leads(p, 14, SIZE - 14)
    p.drawEllipse(QPointF(CENTER, CENTER), 18, 18)
    p.setPen(_pen_light())
    p.drawLine(CENTER_I - 6, CENTER_I, CENTER_I + 6, CENTER_I)
    p.drawLine(CENTER_I + 6, CENTER_I, CENTER_I + 2, CENTER_I - 3)
    p.drawLine(CENTER_I + 6, CENTER_I, CENTER_I + 2, CENTER_I + 3)


def draw_current_source_ac(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    _leads(p, 14, SIZE - 14)
    p.drawEllipse(QPointF(CENTER, CENTER), 18, 18)
    p.setPen(_pen_light())
    p.drawLine(CENTER_I - 6, CENTER_I + 6, CENTER_I + 6, CENTER_I + 6)
    p.drawLine(CENTER_I + 6, CENTER_I + 6, CENTER_I + 2, CENTER_I + 3)
    p.drawLine(CENTER_I + 6, CENTER_I + 6, CENTER_I + 2, CENTER_I + 9)
    path = QPainterPath()
    path.moveTo(CENTER - 8, CENTER - 5)
    path.cubicTo(CENTER - 3, CENTER - 19, CENTER + 3, CENTER + 9, CENTER + 8, CENTER - 5)
    p.drawPath(path)


def draw_dependent_source_vccs(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    _leads(p, 14, SIZE - 14)
    diamond = QPolygonF([
        QPointF(CENTER, CENTER - 18),
        QPointF(CENTER + 18, CENTER),
        QPointF(CENTER, CENTER + 18),
        QPointF(CENTER - 18, CENTER),
    ])
    p.drawPolygon(diamond)
    p.setPen(_pen_light())
    p.drawLine(CENTER_I - 10, CENTER_I, CENTER_I - 4, CENTER_I)
    p.drawLine(CENTER_I - 7, CENTER_I - 3, CENTER_I - 7, CENTER_I + 3)
    p.drawLine(CENTER_I + 4, CENTER_I, CENTER_I + 10, CENTER_I)


def draw_dependent_source_cccs(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    _leads(p, 14, SIZE - 14)
    diamond = QPolygonF([
        QPointF(CENTER, CENTER - 18),
        QPointF(CENTER + 18, CENTER),
        QPointF(CENTER, CENTER + 18),
        QPointF(CENTER - 18, CENTER),
    ])
    p.drawPolygon(diamond)
    p.setPen(_pen_light())
    p.drawLine(CENTER_I - 6, CENTER_I, CENTER_I + 6, CENTER_I)
    p.drawLine(CENTER_I + 6, CENTER_I, CENTER_I + 2, CENTER_I - 3)
    p.drawLine(CENTER_I + 6, CENTER_I, CENTER_I + 2, CENTER_I + 3)


def draw_diode(p):
    p.setPen(_pen())
    p.setBrush(Qt.NoBrush)
    _leads(p, 20, SIZE - 20)
    triangle = QPolygonF([
        QPointF(CENTER - 10, CENTER - 12),
        QPointF(CENTER + 6, CENTER),
        QPointF(CENTER - 10, CENTER + 12),
    ])
    p.drawPolygon(triangle)
    p.drawLine(CENTER_I + 8, CENTER_I - 12, CENTER_I + 8, CENTER_I + 12)


def draw_led(p):
    draw_diode(p)
    p.setPen(_pen_light())
    p.drawLine(CENTER_I + 12, CENTER_I - 8, CENTER_I + 20, CENTER_I - 16)
    p.drawLine(CENTER_I + 20, CENTER_I - 16, CENTER_I + 16, CENTER_I - 16)
    p.drawLine(CENTER_I + 20, CENTER_I - 16, CENTER_I + 20, CENTER_I - 12)
    p.drawLine(CENTER_I + 16, CENTER_I - 4, CENTER_I + 24, CENTER_I - 12)
    p.drawLine(CENTER_I + 24, CENTER_I - 12, CENTER_I + 20, CENTER_I - 12)
    p.drawLine(CENTER_I + 24, CENTER_I - 12, CENTER_I + 24, CENTER_I - 8)


def draw_category_base(p, color, label):
    rect = QRectF(0, 0, SIZE, SIZE)
    font = QFont("Segoe UI", 18)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QPen(_soft_color(color), 2))
    p.drawText(rect, Qt.AlignCenter, label)


def draw_category_connections(p):
    draw_category_base(p, "#7a6a3a", "N")


def draw_category_sources(p):
    draw_category_base(p, "#f25f5c", "S")


def draw_category_passive(p):
    draw_category_base(p, "#247ba0", "P")


def draw_category_nonlinear(p):
    draw_category_base(p, "#8b5cf6", "NL")


def main():
    global _APP
    app_instance = QGuiApplication.instance()
    if app_instance is None:
        _APP = QGuiApplication([])
    else:
        _APP = app_instance
    save_icon(os.path.join(COMP, "wire.png"), draw_wire)
    save_icon(os.path.join(COMP, "resistor.png"), draw_resistor)
    save_icon(os.path.join(COMP, "capacitor.png"), draw_capacitor)
    save_icon(os.path.join(COMP, "inductor.png"), draw_inductor)
    save_icon(os.path.join(COMP, "source_dc.png"), draw_voltage_source_dc)
    save_icon(os.path.join(COMP, "source_ac.png"), draw_voltage_source_ac)
    save_icon(os.path.join(COMP, "current_source_dc.png"), draw_current_source_dc)
    save_icon(os.path.join(COMP, "current_source_ac.png"), draw_current_source_ac)
    save_icon(os.path.join(COMP, "source_vccs.png"), draw_dependent_source_vccs)
    save_icon(os.path.join(COMP, "source_cccs.png"), draw_dependent_source_cccs)
    save_icon(os.path.join(COMP, "diode.png"), draw_diode)
    save_icon(os.path.join(COMP, "led.png"), draw_led)

    save_icon(os.path.join(CAT, "connections.png"), draw_category_connections)
    save_icon(os.path.join(CAT, "sources.png"), draw_category_sources)
    save_icon(os.path.join(CAT, "passive.png"), draw_category_passive)
    save_icon(os.path.join(CAT, "nonlinear.png"), draw_category_nonlinear)

    save_icon(os.path.join(FAM, "connections.png"), draw_category_connections)
    save_icon(os.path.join(FAM, "sources.png"), draw_category_sources)
    save_icon(os.path.join(FAM, "passive.png"), draw_category_passive)
    save_icon(os.path.join(FAM, "nonlinear.png"), draw_category_nonlinear)


if __name__ == "__main__":
    main()
