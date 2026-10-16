"""What to print: three plate designs (back quarter + 3 pins x4: 8 needed, 4 spare; front quarter with its orange
beads x4, seed head x1)."""
from cadkit.plates import Plate, pack
from sunflower.params import Params
from sunflower.parts import center, pin, quarter


def filament_for(p: Params):
    slots = {"back_quarter": p.slot_petals, "front_quarter": p.slot_petals, "front_beads": p.slot_beads,
             "pin": p.slot_pins,
             "center_black": p.slot_center, "center_brown": p.slot_seeds}
    return lambda name: slots[name.split("#")[0]]


def plans(p: Params) -> list[Plate]:
    snap = pin.make(p)
    kits = [("back_quarter", 4, [("back_quarter", quarter.make(p, "back")), ("pin#1", snap), ("pin#2", snap), ("pin#3", snap)]),
            ("front_quarter", 4, [("front_quarter", quarter.painted(p, "front"))]),
            ("seed_head", 1, [("center", center.make(p))])]
    out = []
    for name, qty, items in kits:
        beds = pack(items, p.printer)
        if len(beds) != 1:
            raise ValueError(f"{name} needs {len(beds)} beds; it should fit on one")
        out.append(Plate(name, qty, beds[0]))
    return out
