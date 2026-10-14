"""Fast local viewing in OCP CAD Viewer (no STEP export or translation).

From a phone on the home network: start the viewer with --host <LAN IP>, export HOTRAIN_VIEWER_HOST=<LAN IP>,
then open http://<LAN IP>:3939/viewer on the phone.

    uv run python -m ocp_viewer --port 3939      # once, leave it running; open http://127.0.0.1:3939/viewer
    uv run python -m hotrain.build show room      # or: run | inside | bridge | fit-test
"""
import os

from build123d import Compound, Shape

from hotrain import paint, assembly
from hotrain import corner_assembly as CA
from hotrain import corner_layout as CL
from hotrain import layout as L
from hotrain import room
from hotrain.params import Params

PORT = 3939


def _colored(items: list, label: str) -> Compound:
    kids = []
    for name, part in items:
        split = paint.display_parts(part)  # two-color parts show both colors
        if split:
            for body, col in split:
                body.color = col
                kids.append(body)
            continue
        part.color = room._color_for(name)
        kids.append(part)
    return Compound(children=kids, label=label)


def target(p: Params, name: str) -> Shape:
    """The model to show for a target name."""
    if name == "room":
        return room.make(p, display=True)
    if name == "run":
        return _colored(assembly.placed_parts(p, L.BAYS, L.RUN_ENDS), "run")
    if name in ("inside", "bridge"):
        c = CL.inside_corner() if name == "inside" else CL.bridge_corner()
        return _colored(CA.placed_parts(p, c) + CA.cables(p, c), f"{name}_corner")
    if name == "fit-test":
        from hotrain.parts import fit_test
        ft = fit_test.make(p)
        for s in ft.children:
            s.color = room.IRON
        return ft
    raise ValueError(f"unknown target {name!r}; choose from room, run, inside, bridge, fit-test")


def host() -> str:
    """Where the viewer listens. Set HOTRAIN_VIEWER_HOST to the Mac's LAN IP to view from a phone on the
    same network (start the viewer with the same --host)."""
    return os.environ.get("HOTRAIN_VIEWER_HOST", "127.0.0.1")


def show(p: Params, name: str, port: int = PORT) -> None:
    from ocp_viewer import set_port
    from ocp_viewer import show as ocp_show
    set_port(port, host())
    ocp_show(target(p, name))
