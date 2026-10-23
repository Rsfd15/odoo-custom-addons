"""Gráfica de rendimiento de la bomba (Fire Pump Performance Curve) en SVG.

No depende de librerías externas: el SVG se muestra igual en el formulario
de Odoo y en el PDF generado con wkhtmltopdf.
"""
import math
from xml.sax.saxutils import escape

FIELD_COLOR = "#1f2fa8"   # CAMPO (azul)
PLATE_COLOR = "#c0392b"   # PLACA (rojo)

WIDTH = 960
HEIGHT = 470
MARGIN_LEFT = 70
MARGIN_RIGHT = 25
MARGIN_TOP = 20
MARGIN_BOTTOM = 95


def _nice_step(span, target_ticks):
    """Paso "redondo" (1, 2, 2.5, 5 x 10^n) para dividir el eje."""
    if span <= 0:
        return 1
    raw = span / float(target_ticks)
    power = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 2.5, 5, 10):
        if raw <= factor * power:
            return factor * power
    return 10 * power


def _axis_max(value, target_ticks):
    step = _nice_step(value, target_ticks)
    return step * math.ceil(value / step), step


def _fmt(value):
    if abs(value - round(value)) < 1e-9:
        return "{:,.0f}".format(value)
    return "{:,.1f}".format(value)


def _marker(kind, x, y, color):
    if kind == "diamond":
        return (
            '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>'
            % (x, y - 5, x + 5, y, x, y + 5, x - 5, y, color)
        )
    return '<rect x="%.1f" y="%.1f" width="9" height="9" fill="%s"/>' % (x - 4.5, y - 4.5, color)


def performance_curve_svg(field_points, plate_points, title=None):
    """Devuelve el SVG de la curva.

    field_points / plate_points: listas de tuplas (caudal_gpm, presion_psi).
    """
    field_points = sorted(p for p in field_points if p[0] is not None and p[1] is not None)
    plate_points = sorted(p for p in plate_points if p[0] is not None and p[1] is not None)
    all_points = field_points + plate_points

    max_flow = max([p[0] for p in all_points] + [100])
    max_press = max([p[1] for p in all_points] + [10])
    x_max, x_step = _axis_max(max_flow * 1.05, 8)
    y_max, y_step = _axis_max(max_press * 1.10, 6)

    plot_w = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    plot_h = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM

    def sx(flow):
        return MARGIN_LEFT + flow / x_max * plot_w

    def sy(press):
        return MARGIN_TOP + plot_h - press / y_max * plot_h

    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" font-family="Arial">' % (WIDTH, HEIGHT, WIDTH, HEIGHT),
        '<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (WIDTH, HEIGHT),
        '<rect x="%d" y="%d" width="%d" height="%d" fill="#c8c8c8" stroke="#555" stroke-width="1"/>'
        % (MARGIN_LEFT, MARGIN_TOP, plot_w, plot_h),
    ]

    # Rejilla fina (5 divisiones por paso) y rejilla principal
    minor_x = x_step / 5.0
    minor_y = y_step / 2.0
    v = minor_x
    while v < x_max - 1e-9:
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#8a8a8a" stroke-width="0.5"/>'
                   % (sx(v), MARGIN_TOP, sx(v), MARGIN_TOP + plot_h))
        v += minor_x
    v = minor_y
    while v < y_max - 1e-9:
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#8a8a8a" stroke-width="0.5"/>'
                   % (MARGIN_LEFT, sy(v), MARGIN_LEFT + plot_w, sy(v)))
        v += minor_y

    # Etiquetas de los ejes
    v = 0.0
    while v <= x_max + 1e-9:
        out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#555" stroke-width="1"/>'
                   % (sx(v), MARGIN_TOP + plot_h, sx(v), MARGIN_TOP + plot_h + 5))
        out.append('<text x="%.1f" y="%d" font-size="12" text-anchor="middle">%s</text>'
                   % (sx(v), MARGIN_TOP + plot_h + 20, _fmt(v)))
        v += x_step
    v = 0.0
    while v <= y_max + 1e-9:
        out.append('<text x="%d" y="%.1f" font-size="12" text-anchor="end">%s</text>'
                   % (MARGIN_LEFT - 8, sy(v) + 4, _fmt(v)))
        v += y_step

    out.append('<text x="%.1f" y="%d" font-size="15" font-weight="bold" text-anchor="middle">'
               'Flow - (gpm)</text>' % (MARGIN_LEFT + plot_w / 2.0, MARGIN_TOP + plot_h + 45))
    out.append('<text x="20" y="%.1f" font-size="11" font-weight="bold" text-anchor="middle" '
               'transform="rotate(-90 20 %.1f)">Net Pressure - (psi)</text>'
               % (MARGIN_TOP + plot_h / 2.0, MARGIN_TOP + plot_h / 2.0))
    if title:
        out.append('<text x="%.1f" y="%d" font-size="13" font-weight="bold" text-anchor="middle">%s</text>'
                   % (MARGIN_LEFT + plot_w / 2.0, MARGIN_TOP - 5, escape(title)))

    # Curvas: primero PLACA (roja) y encima CAMPO (azul), como en el formato original
    for points, color, marker, width, label_dy in (
        (plate_points, PLATE_COLOR, "square", 2.5, 14),
        (field_points, FIELD_COLOR, "diamond", 1.5, -8),
    ):
        if not points:
            continue
        if len(points) > 1:
            path = " ".join("%.1f,%.1f" % (sx(f), sy(p)) for f, p in points)
            out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"/>'
                       % (path, color, width))
        for f, p in points:
            out.append(_marker(marker, sx(f), sy(p), color))
            out.append('<text x="%.1f" y="%.1f" font-size="11" fill="#222">%s</text>'
                       % (sx(f) + 7, sy(p) + label_dy, _fmt(round(p))))

    # Leyenda
    ly = HEIGHT - 22
    lx = MARGIN_LEFT + plot_w / 2.0 - 110
    out.append('<rect x="%.1f" y="%d" width="220" height="22" fill="#fff" stroke="#555" stroke-width="1"/>'
               % (lx, ly - 11))
    out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1.5"/>'
               % (lx + 12, ly, lx + 42, ly, FIELD_COLOR))
    out.append(_marker("diamond", lx + 27, ly, FIELD_COLOR))
    out.append('<text x="%.1f" y="%d" font-size="12">CAMPO</text>' % (lx + 48, ly + 4))
    out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="2.5"/>'
               % (lx + 118, ly, lx + 148, ly, PLATE_COLOR))
    out.append(_marker("square", lx + 133, ly, PLATE_COLOR))
    out.append('<text x="%.1f" y="%d" font-size="12">PLACA</text>' % (lx + 154, ly + 4))

    out.append("</svg>")
    return "".join(out)


def interpolate(points, flow):
    """Presión de la curva `points` en `flow` (interpolación lineal).

    Fuera del rango de la curva se extrapola con el último tramo solo hasta
    un 10 % más allá del caudal máximo; si no, devuelve None.
    """
    points = sorted(points)
    if not points or flow is None:
        return None
    if len(points) == 1:
        return points[0][1] if points[0][0] == flow else None
    for (f1, p1), (f2, p2) in zip(points, points[1:]):
        if f1 <= flow <= f2:
            if f2 == f1:
                return p1
            return p1 + (p2 - p1) * (flow - f1) / (f2 - f1)
    (f1, p1), (f2, p2) = points[-2], points[-1]
    if f2 < flow <= f2 * 1.10 and f2 != f1:
        return p1 + (p2 - p1) * (flow - f1) / (f2 - f1)
    return None
