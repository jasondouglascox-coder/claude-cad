"""Every dimension of the keychain. Origin = ring center, +Y up (front view), mm."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    url: str = "https://groverandpals.com"

    # Colors (RGB 0-1) — Grover orange, banner yellow, white, site dark brown #3E2F27
    yellow: tuple = (0.965, 0.855, 0.110)
    orange: tuple = (0.910, 0.537, 0.169)
    white: tuple = (1.0, 1.0, 1.0)
    brown: tuple = (0.243, 0.184, 0.153)

    # Overall size: ribbon tip to tip
    width: float = 50.0

    # Keyring hole through the ring at 12 o'clock (replaces the top paw print)
    hole_r: float = 1.5
    hole_wall: float = 2.0  # plastic between the hole and the outer edge

    # Linework
    line_w: float = 0.5  # generated outline on the raised side of every relief step
    detail_gap: float = 0.45  # letters / paw prints keep this much clear space from outlines
    min_detail: float = 0.4  # mm, brown/white details thinner than this are dropped
    min_detail_area: float = 0.25  # mm^2
    eye_glint_min_r: float = 0.3
    eye_r_range: tuple = (1.2, 3.5)  # mm, round brown blobs this size in the face are eyes

    # Grover
    ear_keep: float = 7.0  # mm below the ear tips that keep sharp (unsmoothed) outlines
    cheek_smooth: float = 0.5  # mm round close/open on the rest of his outline
    ear_simplify: float = 0.6  # mm, ears may deviate this far from the art (fur jogs removed)
    ear_tip_trim: float = 1.5  # mm, hull vertices this close to the apex are dropped -> one sharp tip
    mouth_reach: float = 2.0  # mm around the nose where thin lines are mouth, not whiskers
    mouth_thicken: float = 0.12  # mm each side, so mouth lines reach a printable width

    # Fur patches (orange on Grover's white face)
    patch_close: float = 0.5  # mm, fills white fur strokes inside orange
    patch_open: float = 0.25  # mm, drops orange wisps
    min_patch_area: float = 0.8  # mm^2
    min_white_island: float = 1.5  # mm^2

    # QR (back)
    qr_error: str = "m"
    qr_module: float = 0.85
    qr_quiet: float = 1.5  # quiet zone, in modules
    qr_y: float = 0.0  # panel center (ring center)
    qr_corner: float = 1.5
    qr_grow: float = 0.02  # makes diagonal-touching modules overlap (manifold mesh)

    # Z levels (multiples of the 0.2 mm layer height)
    layer: float = 0.2
    back_t: float = 0.8  # QR inlay depth from the bed
    core_top: float = 2.2
    zone_tops: tuple = (("disk", 2.8), ("ring", 3.2), ("tail", 3.4), ("banner", 3.8), ("cat", 4.2))

    @property
    def zone_top(self) -> dict:
        return dict(self.zone_tops)

    # Tracing (art/logo.svg)
    px_mm: float = 40.0  # working raster resolution (source art is ~62 px/mm at 50 mm)
    mode_sigma: float = 0.03  # mm, smooths anti-aliased edges
    zone_sigma: float = 0.04
    fringe: float = 0.25  # mm, zone strips thinner than this are anti-aliasing, not art
    line_reach: float = 0.5  # mm, linework joins the highest zone within this distance
    min_zone_area: float = 1.0  # mm^2

    # Vectorizing
    vec_upsample: int = 2
    vec_smooth: float = 0.03  # mm gaussian before contouring
    vec_tol: float = 0.04  # mm Douglas-Peucker (keeps corners sharp)
    zone_hole_fill: float = 3.0  # mm^2, smaller holes in a traced zone are misclassified art
    zone_clean: float = 0.45  # mm mitred close/open on traced zone outlines
    underlap: float = 0.05  # lower zones extend under higher ones so nothing cracks open

    # Bambu A1
    bed: float = 256.0
    bed_margin: float = 5.0


P = Params()
