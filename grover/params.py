"""Every dimension of the keychain. Origin = badge center, +Y up (front view), mm."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    url: str = "https://groverandpals.com"
    font: str = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"

    # Colors (RGB 0-1) — Grover orange, banner yellow, white, site dark brown #3E2F27
    yellow: tuple = (0.965, 0.855, 0.110)
    orange: tuple = (0.910, 0.537, 0.169)
    white: tuple = (1.0, 1.0, 1.0)
    brown: tuple = (0.243, 0.184, 0.153)

    # Badge
    r_badge: float = 21.0  # outer ring radius
    r_disk: float = 14.5  # inner white disk radius
    tab_r: float = 5.0  # keyring tab
    tab_y: float = 23.5
    hole_r: float = 1.5  # 3 mm keyring hole through the ring at 12 o'clock
    hole_wall: float = 2.0  # plastic between the hole and the top edge

    # Banner: arched ribbon (annular sector) with swallowtail tails folded behind
    banner_cy: float = -51.0  # arc center y
    banner_r_out: float = 50.0
    banner_r_in: float = 41.6
    banner_half_angle: float = 28.0  # deg each side of vertical
    banner_text: str = "GROVER & PALS"
    banner_font_size: float = 5.0
    banner_text_r: float = 45.8  # text center radius
    tail_top: float = 3.4  # tails sit behind the banner (lower Z)

    # Outlines (brown bands inlaid in the top of a region)
    line_w: float = 0.55

    # Ring paw prints: angles from 12 o'clock, clockwise positive
    paw_angles: tuple = (0.0, 48.0, -48.0, 92.0, -92.0)
    paw_r: float = 17.8  # radius of paw centers
    paw_scale: float = 1.15

    # Grover
    cat_round: float = 1.2  # corner rounding of head/ears
    cat_dy: float = 7.0  # head sits high in the ring, paws over the banner
    cat_paw_x: float = 8.5

    # QR (back)
    qr_error: str = "m"
    qr_module: float = 0.85
    qr_quiet: float = 1.5  # quiet zone, in modules
    qr_y: float = 0.0  # panel center
    qr_corner: float = 1.5
    qr_grow: float = 0.02  # makes diagonal-touching modules overlap (manifold mesh)

    # Z levels (multiples of the 0.2 mm layer height)
    layer: float = 0.2
    back_t: float = 0.8  # QR/back-text inlay depth from the bed
    core_top: float = 2.2
    disk_top: float = 2.8
    ring_top: float = 3.2
    cat_top: float = 3.6
    banner_top: float = 4.0
    inlay_t: float = 0.4  # front detail inlay depth

    # Traced artwork (art/logo.svg)
    width: float = 50.0  # banner tip to tip
    px_mm: float = 20.0  # working raster resolution
    mode_sigma: float = 0.06  # mm, smooths anti-aliased edges
    zone_sigma: float = 0.15
    min_feature: float = 0.4  # mm, thinnest color patch kept
    min_line: float = 0.4  # mm, thinnest brown line kept
    min_areas: tuple = (("orange", 0.15), ("yellow", 0.1), ("white", 0.15), ("brown", 0.1))  # mm^2 specks absorbed
    line_reach: float = 0.5  # mm, linework joins the highest zone within this distance
    fringe: float = 0.25  # mm, zone strips thinner than this are anti-aliasing, not art
    min_zone_area: float = 1.0  # mm^2
    min_zone_width: float = 0.8  # mm, thinner relief zones are absorbed
    brown_shrink: float = 0.1  # mm, opens gaps between paw-print toes / letters
    paw_lift: float = 1.2  # mm, paws start this far above the banner's top arc
    paw_depth: float = 0.6  # mm, cat must hang this far over the banner to count as a paw
    zone_tops: tuple = (("disk", 2.8), ("ring", 3.2), ("tail", 3.4), ("cat", 3.6), ("banner", 4.0), ("paw", 4.4))

    @property
    def zone_top(self) -> dict:
        return dict(self.zone_tops)

    # Vectorizing
    vec_upsample: int = 4
    vec_smooth: float = 0.05  # mm gaussian before contouring
    vec_tol: float = 0.02  # mm polygon simplification
    vec_gap: float = 0.03  # mm overlap so neighbouring colors close up (higher priority wins)
    vec_min_area: float = 0.02  # mm^2

    # Bambu A1
    bed: float = 256.0
    bed_margin: float = 5.0


P = Params()
