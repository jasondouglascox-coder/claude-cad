"""What to print: the fit-test plate first, then the colorizer (clip + block). All black."""
from cadkit.plates import Plate, pack
from sharpie_colorizer.params import P, Params
from sharpie_colorizer.parts import block, clip
from sharpie_colorizer.parts.fittest import fit_items


def colorizer_items(p: Params = P) -> list:
    return [("clip", clip.make(p)), ("block", block.make(p))]


def plates(p: Params = P) -> list[Plate]:
    out = []
    for name, items in (("fit_test", fit_items(p)), ("colorizer", colorizer_items(p))):
        out += [Plate(f"{name}_{n + 1}", 1, bed) for n, bed in enumerate(pack(items, p.printer))]
    return out
