"""DXF for Silhouette Studio: R12, every outline and hole a closed polyline (one cut each)."""
import logging

import ezdxf

logging.getLogger("ezdxf").setLevel(logging.ERROR)  # it warns on every R12 save that units aren't written


def write(path, shapes):
    """Shapes in inches."""
    doc = ezdxf.new("R12", units=0)  # R12 carries no units: the test square settles them
    msp = doc.modelspace()
    for s in shapes:
        for ring in (s.exterior, *s.interiors):
            msp.add_polyline2d(ring.coords[:-1], close=True)
    doc.saveas(path)
