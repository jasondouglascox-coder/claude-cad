"""uv run python -m grover.build [all|step|3mf|preview] [--out out]"""
import argparse
import json
import sys
import time
from pathlib import Path

from build123d import export_step

from cadkit import bambu3mf
from cadkit.export import ISO, write_svg

from . import back as B
from . import render as R
from .model import COLORS, bodies, keychain
from .params import P, Params
from .regions import design

OUT = Path(__file__).resolve().parent.parent / "out"


def settings_file(p: Params, out: Path) -> Path:
    """Bambu project settings from cadkit's A1 template, with this project's layer heights."""
    cfg = json.loads(Path(bambu3mf.SETTINGS).read_text())
    cfg["layer_height"] = str(p.printer.layer)
    cfg["initial_layer_print_height"] = str(p.printer.first)
    cfg["print_settings_id"] = f"{p.printer.layer:.2f}mm Optimal @BBL A1"
    path = out / "bambu_settings.config"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=4))
    return path


def step(out: Path):
    (out / "step").mkdir(parents=True, exist_ok=True)
    export_step(keychain(P), str(out / "step" / "grover_keychain.step"))


def three_mf(out: Path) -> Path:
    path = out / "plates" / "grover_keychain.3mf"
    path.parent.mkdir(parents=True, exist_ok=True)
    b = bodies(P)
    bambu3mf.write(path, [("grover_keychain", [(b[c].label, b[c], P.filaments[c]) for c in COLORS])],
                   settings=settings_file(P, out))
    return path


def preview(out: Path):
    d = design(P)
    pv = out / "preview"
    R.draw(R.front_layers(d), pv / "front.png", P, px_per_mm=20)
    panel, mods = B.qr_shapes(P, d.hole)
    R.draw([("brown", d.silhouette.difference(Point(*d.hole[:2]).buffer(d.hole[2]))),
            ("white", panel.difference(mods)), ("white", B.url_polys(P, d.hole, d.silhouette))],
           pv / "back.png", P, px_per_mm=20, mirror=True)
    write_svg(keychain(P), pv / "iso.svg", ISO)


from shapely.geometry import Point  # noqa: E402

TARGETS = {"step": step, "3mf": three_mf, "preview": preview}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="grover.build")
    ap.add_argument("targets", nargs="*", default=["all"])
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    names = list(TARGETS) if a.targets == ["all"] else a.targets
    for n in names:
        t = time.time()
        TARGETS[n](out)
        print(f"{n}: {time.time() - t:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
