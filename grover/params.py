"""Every dimension of the keychain in one place (mm). Origin = ring center, +Y up in the front view."""
from dataclasses import dataclass
from pathlib import Path

from cadkit import Printer

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "art" / "logo.svg"
FONT = "Avenir Next"  # its Bold face: strokes that survive a 0.4 mm nozzle at 3.6 mm, narrow enough to fit


@dataclass(frozen=True)
class Params:
    qr_text: str = "HTTPS://GROVERANDPALS.COM"  # upper case: alphanumeric mode fits the smallest QR
    url: str = "groverandpals.com"

    # filaments: AMS slot per color, and display colors (RGB 0-1)
    filament: tuple = (("orange", 1), ("yellow", 2), ("white", 3), ("brown", 4))
    filament_type: str = "PLA"  # the same type in every slot; the plate's profile is built from it
    rgb: tuple = (("orange", (0.91, 0.54, 0.17)), ("yellow", (0.965, 0.855, 0.11)),
                  ("white", (1.0, 1.0, 1.0)), ("brown", (0.243, 0.184, 0.153)))

    # size
    width: float = 50.0  # ribbon tip to tip, sets the art scale
    figure_drop: float = 2.0  # cat + ribbon moved down from the logo position
    ear_clear: float = 1.5  # ear tips stay this far inside the ring's outer circle

    # keyring hole, replacing the top paw print
    hole_d: float = 3.5
    hole_wall: float = 2.0  # plastic between the hole and the outer edge
    hole_ring_w: float = 1.0  # brown ring around the hole, raised like a paw print; the chamfer eats hole_chamfer of it
    hole_chamfer: float = 0.4

    # ink and fills
    line_w: float = 0.5  # every thin stroke is re-drawn this wide
    ink_thick: float = 0.7  # marks at least this wide in the art keep their traced shape
    ink_min_src: float = 0.12  # strokes thinner than this in the art are dropped (the cat's outline is ~0.25)
    ink_min_len: float = 1.2  # mm, shorter stroke fragments (specks, ear tuft stubs) are dropped
    fill_min: float = 0.6  # fills narrower than this are dropped (ear tufts, fur wisps)
    min_island: float = 0.4  # mm^2, smaller fill pieces are dropped
    sliver: float = 0.4  # mm, fill slivers narrower than this (a nozzle width) join their neighbours
    pad_gap: float = 0.4  # mm, each ring paw print's pads back off until this much orange fits between them
    paw_print_scale: float = 1.25  # the logo's prints are small for a 5.8 mm ring
    eye_glint_min_d: float = 0.8  # one glint per eye, big enough to print as a dot
    spur: float = 0.35  # mm, skeleton branches shorter than this are spurs, not strokes
    whisker_zone: tuple = (2.0, 9.0, -3.2, 1.5)  # dx min, dx max, dy min, dy max from the nose: thin ink here is whiskers
    letter_smooth: float = 0.1  # mm, bumps on the traced letters smaller than this are smoothed away
    paw_print_step: float = 45.0  # degrees between ring paw prints (the 12 o'clock one is the hole)
    paw_min_area: float = 5.0  # mm^2, white blobs touching the ribbon between these sizes are the paws
    paw_max_area: float = 30.0
    paw_close: float = 0.7  # mm, gaps in the paw outline up to this wide don't join a paw to the chest
    cat_min_area: float = 20.0  # mm^2, smaller cat-colored blobs are stray pixels, not the cat
    letter_surround: float = 0.6  # a mark with this much ribbon around it is a letter
    circle_w: float = 0.5  # drawn ring/disc circles

    # layers: 0.2 mm (0.16 looked no better and cost 5 more swaps; set first_layer for profiles that differ)
    printer: Printer = Printer(layer=0.2)
    back_layers: int = 3  # QR / URL inlay depth (0.6: white opaque over brown)
    body_layers: int = 9  # back inlay + solid brown, to the top of the body (1.8)
    base_layers: int = 3  # white/orange base band (to 2.4)
    face_layers: int = 2  # ribbon, cat, ink (to 2.8)
    top_layers: int = 2  # paws, eyes, nose, letters (to 3.2)
    ring_ink_layers: int = 1  # ring circles, paw prints, hole ring above the base band (to 2.6)

    # back: QR panel and URL text
    qr_module: float = 0.9  # 2.25 nozzle widths; 1.0 left no room for the URL under the panel
    qr_quiet: int = 2  # modules of white around the code
    qr_corner: float = 1.5  # panel corner radius
    qr_gap: float = 0.6  # panel clear of the hole ring
    font: str = FONT
    text_size: float = 3.6  # em
    text_tracking: float = 0.45  # mm added between glyphs so the brown between them is a nozzle width
    text_gap: float = 0.8  # between the panel and the text
    text_margin: float = 1.0  # text clear of the silhouette edge

    # vectorizing
    vec_tol: float = 0.02  # mm, Douglas-Peucker
    vec_smooth: float = 0.05  # mm, blur before contouring

    def z(self, layers: int) -> float:
        """Top of layer `layers` (0 = the bed)."""
        return 0.0 if layers == 0 else round(self.printer.first + (layers - 1) * self.printer.layer, 6)

    @property
    def z_back(self) -> float:
        return self.z(self.back_layers)

    @property
    def z_body(self) -> float:
        return self.z(self.body_layers)

    @property
    def z_base(self) -> float:
        return self.z(self.body_layers + self.base_layers)

    @property
    def z_ring_ink(self) -> float:
        return self.z(self.body_layers + self.base_layers + self.ring_ink_layers)

    @property
    def z_face(self) -> float:
        return self.z(self.body_layers + self.base_layers + self.face_layers)

    @property
    def z_top(self) -> float:
        return self.z(self.body_layers + self.base_layers + self.face_layers + self.top_layers)

    @property
    def thickness(self) -> float:
        return self.z_top

    @property
    def filaments(self) -> dict:
        return dict(self.filament)

    @property
    def colors(self) -> dict:
        return dict(self.rgb)


P = Params()
