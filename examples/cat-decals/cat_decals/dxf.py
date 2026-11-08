"""DXF for Silhouette Studio: R12, every outline and hole a closed polyline (one cut each)."""
import logging

import ezdxf

from .shapes import pieces

logging.getLogger("ezdxf").setLevel(logging.ERROR)  # it warns on every R12 save that units aren't written


def write(path, shapes):
    """Shapes in inches."""
    doc = ezdxf.new("R12", units=0)  # R12 carries no units: the test square settles them
    msp = doc.modelspace()
    for s in shapes:
        for ring in (r for q in pieces(s) for r in (q.exterior, *q.interiors)):
            msp.add_polyline2d(ring.coords[:-1], close=True)
    doc.saveas(path)
