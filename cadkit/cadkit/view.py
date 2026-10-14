"""Send shapes to OCP CAD Viewer: no STEP translation, colors kept.

    uv run python -m ocp_viewer --port 3939      # once; open http://127.0.0.1:3939/viewer BEFORE sending

Only connected tabs receive a model. If a send seems to vanish (the tab still shows the old model), reload the tab
and send again; very large sends can drop the connection. From a phone on the same network, start the viewer with
--host <LAN IP> and set CADKIT_VIEWER_HOST to the same address.
"""
import os
from typing import Callable

from build123d import Color, Compound, Shape

from cadkit import paint

PORT = 3939


def host() -> str:
    return os.environ.get("CADKIT_VIEWER_HOST", "127.0.0.1")


def colored(items: list[tuple[str, Shape]], color_for: Callable[[str], Color], label: str = "model") -> Compound:
    """One Compound for the viewer: painted two-color parts split into colored bodies (viewers color whole shapes
    only), every other part colored by name."""
    kids = []
    for name, part in items:
        split = paint.display_parts(part)
        if split:
            for body, col in split:
                body.color = col
                kids.append(body)
            continue
        part.color = color_for(name)
        kids.append(part)
    return Compound(children=kids, label=label)


def show(shape: Shape, port: int = PORT) -> None:
    from ocp_viewer import set_port
    from ocp_viewer import show as ocp_show
    set_port(port, host())
    ocp_show(shape)
