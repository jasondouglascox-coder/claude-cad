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
    width: float = 50.0  # the logo's ribbon tip to tip: sets the art scale (the tails then slide in, ribbon_slide)
    figure_drop: float = 2.0  # cat + ribbon moved down from the logo position
    ribbon_slide: float = 3.0  # mm each ribbon tail slides in toward the middle (v1's look)
    ear_clear: float = 1.5  # ear tips stay this far inside the ring's outer circle

    # keyring hole, replacing the top paw print
    hole_d: float = 3.5
    hole_wall: float = 2.0  # plastic between the hole and the outer edge
    hole_ring_w: float = 1.0  # brown ring around the hole, raised like a paw print; the chamfer eats hole_chamfer of it
    hole_chamfer: float = 0.4

    # ink and fills
    line_w: float = 0.5  # every thin stroke is re-drawn this wide
    whisker_w: float = 0.4  # whiskers: one nozzle width, as fine as a 0.4 nozzle prints solid
    ink_thick: float = 0.7  # marks at least this wide in the art keep their traced shape
    ink_min_src: float = 0.12  # strokes thinner than this in the art are dropped (the cat's outline is ~0.25)
    ink_min_len: float = 1.2  # mm, shorter stroke fragments (specks, ear tuft stubs) are dropped
    fill_min: float = 0.6  # fills narrower than this are dropped (ear tufts, fur wisps)
    min_island: float = 0.4  # mm^2, smaller fill pieces are dropped
    sliver: float = 0.4  # mm, fill slivers narrower than this (a nozzle width) join their neighbours
    pad_gap: float = 0.4  # mm, each ring paw print's pads back off until this much orange fits between them
    paw_print_scale: float = 1.25  # the logo's prints are small for a 5.8 mm ring
    eye_glint_min_d: float = 0.6  # glints big enough to print as dots (1.5 nozzle widths)
    spur: float = 0.35  # mm, skeleton branches shorter than this are spurs, not strokes
    whisker_zone: tuple = (0.0, 0.0, 0.0, 0.0)  # (dx min, dx max, dy min, dy max from the nose) to drop whiskers; empty keeps them
    letter_clear: float = 0.35  # mm, a raised letter keeps this far from the ribbon's outline
    counter_min_d: float = 0.55  # mm, a letter's counter opens to at least this (one yellow extrusion)
    letter_smooth: float = 0.1  # mm, bumps on the traced letters smaller than this are smoothed away
    paw_print_step: float = 45.0  # degrees between ring paw prints (the 12 o'clock one is the hole)
    paw_min_area: float = 5.0  # mm^2, white blobs touching the ribbon between these sizes are the paws
    paw_max_area: float = 30.0
    paw_close: float = 0.7  # mm, gaps in the paw outline up to this wide don't join a paw to the chest
    cat_min_area: float = 20.0  # mm^2, smaller cat-colored blobs are stray pixels, not the cat
    letter_surround: float = 0.6  # a mark with this much ribbon around it is a letter
    circle_w: float = 0.5  # drawn ring/disc circles

    # ears, drawn rather than traced (the traced outline had bumps where the art's fur and spurs met it): each ear's
    # outer arch, clockwise round the head from where it leaves the head's outline to where it rejoins it, and its
    # inner line, from the arch (its first point snaps onto it) down into the face; smooth curves through these
    # points, (x, y) mm in the logo's frame (before figure_drop)
    ear_arches: tuple = (
        ((-7.55, 6.65), (-7.84, 7.57), (-8.07, 8.51), (-8.27, 9.45), (-8.44, 10.39), (-8.58, 11.34), (-8.68, 12.30),
         (-8.74, 13.26), (-8.54, 14.20), (-7.80, 14.73), (-6.91, 14.42), (-6.07, 13.94), (-5.28, 13.40),
         (-4.56, 12.76), (-3.90, 12.05), (-3.23, 11.37), (-2.44, 10.84), (-1.50, 10.67)),
        ((2.50, 10.57), (3.10, 10.58), (3.71, 10.77), (4.22, 11.14), (4.68, 11.57), (5.12, 12.02), (5.58, 12.45),
         (6.06, 12.86), (6.55, 13.26), (7.05, 13.64), (7.57, 14.00), (8.11, 14.33), (8.62, 14.69), (9.17, 14.98),
         (9.63, 14.61), (9.83, 14.01), (9.91, 13.39), (9.93, 12.76), (9.95, 12.13), (9.95, 11.50), (9.93, 10.87),
         (9.86, 10.24), (9.76, 9.62), (9.64, 9.00), (9.47, 8.40), (9.24, 7.81), (9.15, 7.20), (9.06, 6.60)),
    )
    ear_lines: tuple = (
        ((-7.11, 14.47), (-5.83, 13.01), (-4.64, 11.49), (-3.54, 9.89), (-2.55, 8.25)),
        ((8.08, 14.38), (7.40, 13.25), (6.67, 12.16), (5.97, 11.04), (5.36, 9.88), (4.90, 8.65)),
    )
    ear_erase: tuple = (0.6, 0.45, 0.32)  # mm of traced ink erased outside an arch, inside it, round an inner line

    # eyes, drawn: per eye a smooth outline from its inner corner (where it comes to a point) round through these
    # points and back; the iris circle (x, y, r: brown, the rest inside the line_w rim is the white crescent); two
    # white glints (x, y, r). Fitted to the logo (the iris arc to the inner edge of its olive band), glints moved
    # until a nozzle of brown separates them from each other, the crescent and the rim. Logo frame, mm.
    eye_shapes: tuple = (
        ((-0.23, 4.05), (-0.72, 4.91), (-1.53, 5.48), (-2.53, 5.66), (-3.53, 5.41), (-4.22, 4.71), (-4.33, 3.76),
         (-3.80, 2.88), (-2.92, 2.39), (-1.94, 2.34), (-0.90, 2.51)),
        ((4.22, 2.58), (5.27, 2.52), (6.22, 2.69), (6.99, 3.31), (7.37, 4.25), (7.09, 5.14), (6.29, 5.70),
         (5.28, 5.81), (4.35, 5.50), (3.64, 4.85), (3.27, 3.93)),
    )
    eye_corners: tuple = ((-0.15, 2.60), (3.35, 2.72))
    eye_irises: tuple = ((-0.58, 4.21, 2.43), (3.17, 4.19, 2.68))
    eye_glints: tuple = (((-1.80, 4.60, 0.40), (-2.10, 3.50, 0.30)), ((4.80, 4.70, 0.40), (5.00, 3.58, 0.30)))
    # nose, mouth and whiskers, drawn (muzzle.py), fitted to the logo; logo frame, mm. The nose is a closed curve
    # (solid brown, raised); the rest are strokes a line wide, each a smooth curve through its points.
    nose: tuple = ((1.85, 0.02), (1.25, 0.30), (0.75, 0.80), (0.48, 1.40), (0.50, 1.85), (0.95, 2.00), (1.70, 2.02),
                   (2.45, 1.95), (2.85, 1.65), (2.85, 1.20), (2.55, 0.65), (2.20, 0.25))
    mouth: tuple = (
        ((1.86, 0.25), (1.82, -0.60), (1.76, -1.30)),  # philtrum
        ((1.76, -1.30), (1.20, -1.78), (0.40, -2.00), (-0.50, -1.95), (-1.40, -1.65), (-2.20, -1.10), (-2.65, -0.50),
         (-2.75, 0.00)),  # left lip, up into the muzzle
        ((1.76, -1.30), (2.40, -1.72), (3.30, -1.98), (4.30, -1.97), (4.90, -1.80), (5.30, -1.55)),  # right lip, a smile ending short of the whiskers
        ((0.40, -2.00), (0.50, -2.55), (0.95, -2.95), (1.70, -3.12), (2.45, -3.00), (2.95, -2.60), (3.20, -1.98)),  # mouth
    )
    whiskers: tuple = (  # the top ones from beside the nose, the lower pair a side fanning from a root in the
        # whisker pad (the white between nose and lip), each out to its tip
        ((0.00, -0.25), (-1.00, 0.35), (-2.50, 0.90), (-4.00, 1.15), (-6.00, 1.27), (-8.00, 1.03), (-10.15, 0.38)),
        ((-1.00, -0.75), (-2.00, -0.66), (-2.78, -0.57), (-3.50, -0.50), (-4.50, -0.55), (-5.30, -0.68)),
        ((-1.00, -0.75), (-1.60, -1.10), (-2.15, -1.62), (-2.85, -1.95), (-3.50, -2.27)),
        ((3.85, -0.45), (5.50, 0.35), (7.50, 0.88), (9.50, 1.15), (11.50, 1.20), (12.10, 1.15)),
        ((4.35, -1.05), (5.20, -0.80), (5.95, -0.62), (8.00, -0.35), (9.50, -0.40), (10.50, -0.50), (11.75, -0.85)),
        ((4.35, -1.05), (4.75, -1.55), (5.10, -2.05), (5.50, -2.50)),
    )
    tongue: str = "white"  # inside the mouth: "white", "orange", or "none" (no opening, just the smile)
    muzzle_zone: tuple = ((-3.30, -2.90), (5.40, -2.90), (5.40, -1.30), (6.10, -1.30), (6.10, 2.20),
                          (-3.30, 2.20))  # traced ink in here goes (it stops short of the right paw)
    muzzle_unlines: tuple = (  # traced lines that go though nothing is drawn on them (where a whisker was moved)
        ((4.25, -0.90), (6.00, -0.72), (8.00, -0.75), (9.50, -0.88), (10.50, -1.05), (11.75, -1.50)),
    )
    unline_erase: float = 0.5  # mm round an old path: the traced stroke wandered off it
    whisker_erase: float = 0.35  # mm along each stroke where the traced one goes (not near the face's outline,
    stroke_end_keep: float = 0.5  # nor this close to a stroke's outer end, where it meets a paw or an arm)
    # paws, drawn (paws.py), read off the logo: a closed outline (clockwise from the top left; the points at the
    # cusps between the toe lobes are where the toe lines start) and the toe lines' centerlines; logo frame, mm
    paw_outlines: tuple = (
        ((-8.65, -1.05), (-7.60, -0.97), (-6.40, -0.95), (-5.60, -1.00), (-4.90, -1.25), (-4.35, -1.75), (-4.02, -2.45), (-3.97, -3.20), (-4.12, -3.85), (-4.45, -4.40), (-4.95, -4.73), (-5.60, -4.50), (-5.85, -5.00), (-6.40, -5.45), (-7.00, -5.58), (-7.55, -5.45), (-7.88, -5.05), (-8.25, -5.50), (-9.00, -5.72), (-9.60, -5.62), (-10.00, -5.10), (-10.12, -4.30), (-10.05, -3.40), (-9.75, -2.55), (-9.25, -1.80)),
        ((6.60, -1.75), (7.30, -1.40), (8.20, -1.30), (9.40, -1.28), (10.40, -1.42), (11.10, -1.85), (11.60, -2.60), (11.85, -3.50), (11.85, -4.40), (11.65, -5.20), (11.25, -5.80), (10.70, -5.97), (10.10, -5.80), (9.62, -5.20), (9.20, -5.70), (8.60, -5.88), (8.05, -5.60), (7.75, -4.98), (7.30, -5.15), (6.60, -5.00), (6.15, -4.60), (5.98, -3.90), (6.05, -3.00), (6.25, -2.30)),
    )
    paw_toes: tuple = (
        (((-7.88, -4.80), (-7.92, -4.00), (-7.93, -3.05)), ((-5.66, -4.25), (-5.85, -3.55), (-6.10, -2.60))),
        (((7.80, -4.73), (7.95, -3.90), (8.15, -2.95)), ((9.66, -4.95), (9.87, -4.10), (10.13, -3.15))),
    )
    paw_top_clear: float = 0.45  # mm over a paw's top that's plain white (traced lines and shading go)
    paw_top_depth: float = 0.8  # mm down from a paw's top that counts as its top (its sides keep their lines)
    eye_tip_r: float = 0.08  # mm, the pointed inner corner is rounded this much
    eye_erase: float = 0.4  # mm round an eye's outline where the traced ink goes

    # layers: 0.2 mm (0.16 looked no better and cost 5 more swaps; set first_layer for profiles that differ)
    printer: Printer = Printer(layer=0.2)
    back_layers: int = 3  # QR / URL inlay depth (0.6: white opaque over brown)
    body_layers: int = 9  # back inlay + solid brown, to the top of the body (1.8)
    base_layers: int = 3  # white/orange base band (to 2.4)
    face_layers: int = 2  # ribbon, cat, ink (to 2.8)
    top_layers: int = 2  # paws, eyes, nose, letters (to 3.2)
    ring_ink_layers: int = 2  # ring circles, paw prints, hole ring above the base band (to 2.8, the face band's
    # height: the ring ink and the face's brown meet, and must be one shape to mesh cleanly)

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
    seam: float = 0.05  # mm, gaps up to this wide between neighbouring colors (each traced on its own) are closed
    base_sliver: float = 0.3  # mm, backdrop seen narrower than this between brown lines fills in (pad gaps are 0.4)
    base_tuck: float = 0.1  # mm, the base band's white/orange seam stays this far under the face band's edge

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
