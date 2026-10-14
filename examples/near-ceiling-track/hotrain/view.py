"""Fast local viewing in OCP CAD Viewer (no STEP export or translation), via cadkit.view.

From a phone on the home network: start the viewer with --host <LAN IP>, export CADKIT_VIEWER_HOST=<LAN IP>,
then open http://<LAN IP>:3939/viewer on the phone.

    uv run python -m ocp_viewer --port 3939      # once, leave it running; open http://127.0.0.1:3939/viewer
    uv run python -m hotrain.build show room      # or: run | inside | bridge | fit-test
"""
from build123d import Shape

from cadkit import view as cad_view
from cadkit.view import PORT, colored, host  # noqa: F401  (build prints the viewer address)
from hotrain import assembly
from hotrain import corner_assembly as CA
from hotrain import corner_layout as CL
from hotrain import layout as L
from hotrain import room
from hotrain.params import Params


def target(p: Params, name: str) -> Shape:
    """The model to show for a target name."""
    if name == "room":
        return room.make(p, display=True)
    if name == "run":
        return colored(assembly.placed_parts(p, L.BAYS, L.RUN_ENDS), room._color_for, "run")
    if name in ("inside", "bridge"):
        c = CL.inside_corner() if name == "inside" else CL.bridge_corner()
        return colored(CA.placed_parts(p, c) + CA.cables(p, c), room._color_for, f"{name}_corner")
    if name == "fit-test":
        from hotrain.parts import fit_test
        ft = fit_test.make(p)
        for s in ft.children:
            s.color = room.IRON
        return ft
    raise ValueError(f"unknown target {name!r}; choose from room, run, inside, bridge, fit-test")


def show(p: Params, name: str, port: int = PORT) -> None:
    cad_view.show(target(p, name), port)
