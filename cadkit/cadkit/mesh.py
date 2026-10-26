"""Triangle meshes, for designs past what B-rep booleans can fuse: dozens of freeform bodies overlapping at shallow
angles (a peony's petals) come out of OCC invalid, in pieces, or hang. Build each body as a mesh (from_shape, or
from_grids straight from your own point grids), union them exactly with manifold3d, and hand the Mesh to the
checks, renders and write_plates like a part. It has no B-rep, so no STEP: write_plates writes its plate as STL.

Needs the `mesh` extra (manifold3d).
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from build123d import Shape, Vector


@dataclass(frozen=True)
class Bounds:
    """The bounding box, with the parts of build123d's BoundBox the checks use."""
    min: Vector
    max: Vector

    @property
    def size(self) -> Vector:
        return self.max - self.min


class Mesh:
    """A closed triangle mesh: verts (n, 3), tris (m, 3) indices, counter-clockwise seen from outside."""

    def __init__(self, verts, tris, label: str = "", color=None):
        self.verts = np.asarray(verts, float)
        self.tris = np.asarray(tris, np.int64)
        self.label, self.color = label, color

    def _like(self, verts, tris) -> "Mesh":
        return Mesh(verts, tris, self.label, self.color)

    @classmethod
    def from_shape(cls, shape: Shape, tol: float = 0.01) -> "Mesh":
        from cadkit.bambu3mf import mesh
        v, t = mesh(shape, tol)
        m = cls(v, t, getattr(shape, "label", ""), getattr(shape, "color", None))
        return m if m._manifold().volume() >= 0 else m._like(v, t[:, ::-1])

    @classmethod
    def from_grids(cls, top: np.ndarray, under: np.ndarray, label: str = "") -> "Mesh":
        """A solid between two skins given as [column][row] point grids of the same shape, rows lined up: both
        skins, then strips joining their four edges. Either skin can be on top."""
        nc, nr, _ = top.shape
        t = np.arange(nc * nr).reshape(nc, nr)
        u = t + nc * nr
        a, b, c, d = t[:-1, :-1], t[1:, :-1], t[1:, 1:], t[:-1, 1:]
        quads = [(a, b, c, d), (u[:-1, :-1], u[:-1, 1:], u[1:, 1:], u[1:, :-1])]
        for i, s in ((0, 1), (nr - 1, -1)):  # foot and rim rows
            quads.append(tuple(x[:, None] for x in (t[:-1, i], u[:-1, i], u[1:, i], t[1:, i])[::s]))
        for j, s in ((0, -1), (nc - 1, 1)):  # the two side columns
            quads.append(tuple(x[None, :] for x in (t[j, :-1], u[j, :-1], u[j, 1:], t[j, 1:])[::s]))
        tris = []
        for p, q, r, s in quads:
            tris += [np.stack([p, q, r], -1).reshape(-1, 3), np.stack([p, r, s], -1).reshape(-1, 3)]
        m = cls(np.concatenate([top.reshape(-1, 3), under.reshape(-1, 3)]), np.concatenate(tris), label)
        return m if m._manifold().volume() >= 0 else m._like(m.verts, m.tris[:, ::-1])

    @classmethod
    def from_manifold(cls, man, label: str = "", color=None) -> "Mesh":
        g = man.to_mesh()
        return cls(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), label, color)

    def _manifold(self):
        import manifold3d as m3
        return m3.Manifold(m3.Mesh(vert_properties=self.verts.astype(np.float32),
                                   tri_verts=self.tris.astype(np.uint32)))

    @classmethod
    def union(cls, meshes: list["Mesh"], label: str = "", color=None) -> "Mesh":
        import manifold3d as m3
        man = m3.Manifold.batch_boolean([m._manifold() for m in meshes], m3.OpType.Add)
        return cls.from_manifold(man, label or meshes[0].label, color if color is not None else meshes[0].color)

    def _boolean(self, other, op: str) -> "Mesh":
        other = other if isinstance(other, Mesh) else Mesh.from_shape(other)
        a, b = self._manifold(), other._manifold()
        m = self.from_manifold({"+": a + b, "-": a - b, "&": a ^ b}[op])
        return self._like(m.verts, m.tris)

    def __add__(self, other) -> "Mesh":
        return self._boolean(other, "+")

    def __sub__(self, other) -> "Mesh":
        return self._boolean(other, "-")

    def __and__(self, other) -> "Mesh":
        return self._boolean(other, "&")

    def trimmed(self, z: float = 0.0) -> "Mesh":
        """Everything at or above height z (cut flat there: bodies sunk below the bed come out standing on it)."""
        m = self.from_manifold(self._manifold().trim_by_plane((0, 0, 1), z))
        return self._like(m.verts, m.tris)

    def simplify(self, tol: float = 1e-3) -> "Mesh":
        """Edges shorter than tol collapsed (and flat runs of triangles merged): the slivers a union leaves where
        faces nearly line up, which a vertex-rounding check (open_edges) or a slicer can see as holes. A collapse can
        lift a bed vertex by up to tol; those go back on the bed."""
        m = self.from_manifold(self._manifold().simplify(tol))
        verts = m.verts.copy()
        verts[np.abs(verts[:, 2]) < tol, 2] = 0.0
        return self._like(verts, m.tris)

    def translate(self, offset) -> "Mesh":
        return self._like(self.verts + np.asarray(tuple(offset), float), self.tris)

    def rotate_z(self, deg: float) -> "Mesh":
        c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
        return self._like(self.verts @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]), self.tris)

    @property
    def volume(self) -> float:
        return float(self._manifold().volume())

    @property
    def centroid(self) -> tuple[float, float, float]:
        """The centre of mass (uniform density): signed tetrahedra from the origin to each triangle."""
        t = self.triangles()
        v = np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2]))
        return tuple(float(c) for c in (t.sum(axis=1) * v[:, None]).sum(axis=0) / (4 * v.sum()))

    @property
    def is_valid(self) -> bool:
        import manifold3d as m3
        man = self._manifold()
        return man.status() == m3.Error.NoError and man.volume() > 0

    def solids(self) -> list["Mesh"]:
        """The separate pieces (one = it holds together)."""
        return [self.from_manifold(p, self.label, self.color) for p in self._manifold().decompose()]

    def drop_crumbs(self, min_volume: float = 1.0) -> "Mesh":
        """Without pieces smaller than min_volume mm^3: slivers a cut leaves where surfaces nearly touch."""
        import manifold3d as m3
        keep = [p for p in self._manifold().decompose() if p.volume() >= min_volume]
        m = self.from_manifold(m3.Manifold.compose(keep))
        return self._like(m.verts, m.tris)

    def bounding_box(self) -> Bounds:
        return Bounds(Vector(*self.verts.min(axis=0)), Vector(*self.verts.max(axis=0)))

    def triangles(self) -> np.ndarray:
        """(m, 3, 3): each triangle's corners."""
        return self.verts[self.tris]

    def write_stl(self, path: Path) -> None:
        tri = self.triangles().astype(np.float32)
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        rec = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
        rec["n"], rec["v"] = n, tri
        with open(path, "wb") as f:
            f.write(b"cadkit mesh".ljust(80, b" ") + np.uint32(len(tri)).tobytes() + rec.tobytes())


def triangles(shape, tol: float = 0.1) -> np.ndarray:
    """(m, 3, 3) triangles of a Mesh or any Shape (tessellated within tol)."""
    if isinstance(shape, Mesh):
        return shape.triangles()
    verts, idx = shape.tessellate(tol, 0.2)
    if not idx:
        return np.zeros((0, 3, 3))
    return np.array([(q.X, q.Y, q.Z) for q in verts])[np.array(idx)]
