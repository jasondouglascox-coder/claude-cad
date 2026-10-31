"""DXF for Silhouette Studio: R12, every outline and hole a closed polyline (one cut each)."""
import logging

import ezdxf

from .params import MM

logging.getLogger("ezdxf").setLevel(logging.ERROR)  # it warns on every R12 save that units aren't written


def write(path, shapes, units="in"):
    """Shapes are in inches; units 'mm' scales them, for when Studio reads the file as millimetres."""
    k = {"in": 1.0, "mm": MM}[units]
    doc = ezdxf.new("R12", units=0)  # R12 carries no units: the test square settles them
    msp = doc.modelspace()
    for s in shapes:
        for ring in (s.exterior, *s.interiors):
            msp.add_polyline2d([(x * k, y * k) for x, y in ring.coords[:-1]], close=True)
    doc.saveas(path)
