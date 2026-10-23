"""Build plates as Bambu Studio project 3MF, so they open already colored.

Bambu Studio only reads a filament per part from its own project format. A plain 3MF loads as geometry ("The 3mf
is not from Bambu Lab, load geometry data and color data only") and every part lands on filament 1. So:

- each printed part is one object, each color body one part of it, and Metadata/model_settings.config gives every
  part its filament (AMS slot);
- Metadata/project_settings.config comes from a template Bambu Studio saved itself (bambu_a1_project_settings.config:
  A1 0.4 nozzle, 0.20mm Standard, filaments 1 gray PETG, 2 brown PETG, 3 white PLA, 4 blue PLA). Without it
  Bambu Studio's CLI crashes on the project. Pass your own with `settings=` (save any project from Bambu Studio,
  unzip it, take Metadata/project_settings.config);
- mesh and object ids run in ONE sequence across the whole package, as Bambu writes them. Bambu keys meshes by
  id alone, whatever file they're in: numbering each object file from 1 made three different ladders open as
  three copies of the first.

Check a file the way the slicer reads it with cadkit.bambu (round trip and slice through Bambu Studio's CLI).
"""
import json
import math
import uuid
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

import numpy as np
from build123d import Shape

SETTINGS = Path(__file__).with_name("bambu_a1_project_settings.config")
VERSION = "02.08.04.57"  # Bambu Studio that saved the settings template
NS = 'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" ' \
     'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" ' \
     'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"'
IDENTITY = "1 0 0 0 1 0 0 0 1 0 0 0"
BLOCKER = "support_blocker"  # a part's filament for a support blocker: not printed, no support generated inside it


def mesh(shape: Shape, tol: float = 0.01, angular: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """Watertight triangle mesh within tol mm of the true surface: OCC tessellates each face separately, so merge
    coincident vertices. Meshed here with an absolute deflection first: build123d's tessellate asks OCC for one
    relative to each edge's size, which let an 18° arc of a 550 mm radius stray 0.14 mm. A cadkit.mesh.Mesh is
    already one."""
    from cadkit.mesh import Mesh
    if isinstance(shape, Mesh):
        return shape.verts, shape.tris
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    BRepMesh_IncrementalMesh(shape.wrapped, tol, False, angular, True)
    verts, tris = shape.tessellate(tol, angular)
    v = np.array([(q.X, q.Y, q.Z) for q in verts])
    _, first, idx = np.unique(np.round(v / 1e-4).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    t = idx.ravel()[np.array(tris)]
    t = t[(t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])]
    return v[first], t


def _uuid(*key) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "cadkit/" + "/".join(map(str, key))))


def _object_file(parts: list[tuple[str, Shape, int]], ids: list[int], key: str) -> str:
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {NS}>',
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>', " <resources>"]
    for i, (_, shape, _) in zip(ids, parts):
        v, t = mesh(shape)
        out.append(f'  <object id="{i}" p:UUID="{_uuid(key, i)}" type="model">\n   <mesh>\n    <vertices>')
        out += [f'     <vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x, y, z in v]
        out.append("    </vertices>\n    <triangles>")
        out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t]
        out.append("    </triangles>\n   </mesh>\n  </object>")
    out += [" </resources>", " <build/>", "</model>"]
    return "\n".join(out)


# 4 long in the template but describing the bed, not one entry per filament
_NOT_PER_FILAMENT = {"printable_area", "head_wrap_detect_zone", "filament_self_index"}


def write_settings(path: Path, filaments: list[tuple[str, str]], base: Path = SETTINGS,
                   tower: tuple[float, float, float] | None = None, overrides: dict | None = None) -> Path:
    """Project settings for your own AMS set: filaments[i] = (type, "#RRGGBB") for slot i + 1. Each slot copies every
    per-filament setting (temperatures, speeds, preset id) from the first template slot of that type, then takes
    its color. The template's slot count stays (Bambu's flush matrix is sized for it).

    tower = (x, y, width): the prime tower's front-left corner on the bed and its width, for prints that leave no
    room at the template's spot (Bambu refuses to slice when the tower overlaps the print).

    overrides = {setting: value}: any project setting by its name in the template (supports, say), set last. A name
    the template doesn't have raises KeyError (a typo would otherwise be ignored by the slicer)."""
    cfg = json.loads(Path(base).read_text())
    types = cfg["filament_type"]
    n = len(types)
    if len(filaments) != n:
        raise ValueError(f"the template has {n} filaments; got {len(filaments)}")
    src = []
    for kind, _ in filaments:
        if kind not in types:
            raise ValueError(f"no {kind} slot in the template (it has {sorted(set(types))})")
        src.append(types.index(kind))
    for key, val in cfg.items():
        if isinstance(val, list) and len(val) == n and key not in _NOT_PER_FILAMENT:
            cfg[key] = [val[i] for i in src]
    for key in ("filament_colour", "filament_multi_colour"):
        cfg[key] = [c for _, c in filaments]
    if tower is not None:
        x, y, w = tower
        cfg["wipe_tower_x"], cfg["wipe_tower_y"], cfg["prime_tower_width"] = [str(x)], [str(y)], str(w)
    for key, val in (overrides or {}).items():
        if key not in cfg:
            raise KeyError(f"{key}: not a setting in {Path(base).name}")
        cfg[key] = val
    # Bambu Studio's window loads the presets and applies only what this names (process; each filament; printer),
    # so a setting left off it opens as the preset has it; the command-line slicer reads the whole file
    template = json.loads(Path(base).read_text())
    process = {"wipe_tower_x", "wipe_tower_y", "prime_tower_width"} | set(overrides or {})
    cfg["different_settings_to_system"] = [";".join(sorted(k for k in process if cfg[k] != template[k]))] + [""] * (n + 1)
    path = Path(path)
    path.write_text(json.dumps(cfg, indent=4))
    return path


def write(path: Path, objects: list[tuple[str, list[tuple[str, Shape, int]]]], settings: Path = SETTINGS) -> None:
    """objects: (name, [(part name, shape in bed coordinates, filament number), ...]); one plate per file. A part
    whose filament is BLOCKER is a support blocker (after the printed parts: the first part's filament is the
    object's)."""
    write_plates_project(path, [("", objects)], settings)


GRID = 1.2  # Bambu lays plates out every 1.2 beds, left to right then down (measured on a MakerWorld project)


def _bed(settings: Path) -> tuple[float, float]:
    pts = [tuple(float(v) for v in p.split("x")) for p in json.loads(Path(settings).read_text())["printable_area"]]
    return max(x for x, _ in pts), max(y for _, y in pts)


def plate_offsets(n: int, bed: tuple[float, float]) -> list[tuple[float, float]]:
    """Where Bambu puts plates 1..n on its virtual bed: ceil(sqrt(n)) columns, rows going down."""
    cols = math.ceil(math.sqrt(n)) if n > 1 else 1
    return [((i % cols) * GRID * bed[0], -(i // cols) * GRID * bed[1]) for i in range(n)]


def _settings_for(settings: Path, n: int) -> str:
    """The project settings for n plates: Bambu keeps a prime-tower spot per plate, so every plate gets the first one
    (the corner cadkit.plates.pack keeps free). One plate: the file as it is."""
    text = Path(settings).read_text()
    if n == 1:
        return text
    cfg = json.loads(text)
    for key in ("wipe_tower_x", "wipe_tower_y"):
        if isinstance(cfg.get(key), list) and cfg[key]:
            cfg[key] = cfg[key][:1] * n
    return json.dumps(cfg, indent=4)


def write_plates_project(path: Path, plates: list[tuple[str, list]], settings: Path = SETTINGS) -> None:
    """One Bambu project with every plate: plates = [(plate name, objects as write() takes them)], each object in its
    plate's bed coordinates. Bambu opens it with a tab per plate; it's the file MakerWorld takes."""
    offsets = plate_offsets(len(plates), _bed(settings)) if len(plates) > 1 else [(0.0, 0.0)]
    model = [f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {NS}>',
             f' <metadata name="Application">BambuStudio-{VERSION}</metadata>',
             ' <metadata name="BambuStudio:3mfVersion">1</metadata>', " <resources>"]
    rels, files, build_items = [], {}, []
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    plate_cfg = []
    last, k = 0, 0  # one id sequence for meshes and objects across the package, as Bambu Studio writes it: it keys
    #                 meshes by id alone, so a repeated id makes it reuse another object's mesh
    for pi, ((pname, objects), (dx, dy)) in enumerate(zip(plates, offsets), start=1):
        place = IDENTITY if (dx, dy) == (0.0, 0.0) else f"1 0 0 0 1 0 0 0 1 {dx:g} {dy:g} 0"
        plate = ["  <plate>", f'    <metadata key="plater_id" value="{pi}"/>',
                 f'    <metadata key="plater_name" value={quoteattr(pname)}/>', '    <metadata key="locked" value="false"/>']
        for name, parts in objects:
            k += 1
            ids = list(range(last + 1, last + 1 + len(parts)))
            oid, last, fname = ids[-1] + 1, ids[-1] + 1, f"/3D/Objects/object_{k}.model"
            files[fname[1:]] = _object_file(parts, ids, f"{path.name}/{k}")
            rels.append(f' <Relationship Target="{fname}" Id="rel-{k}" '
                        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>')
            model.append(f'  <object id="{oid}" p:UUID="{_uuid(path.name, k)}" type="model">\n   <components>')
            model += [f'    <component p:path="{fname}" objectid="{i}" p:UUID="{_uuid(path.name, k, "c", i)}" '
                      f'transform="{IDENTITY}"/>' for i in ids]
            model.append("   </components>\n  </object>")
            build_items.append(f'  <item objectid="{oid}" p:UUID="{_uuid(path.name, k, "item")}" '
                               f'transform="{place}" printable="1"/>')
            cfg += [f'  <object id="{oid}">', f'    <metadata key="name" value={quoteattr(name)}/>',
                    f'    <metadata key="extruder" value="{parts[0][2]}"/>']
            for i, (part, _, fil) in zip(ids, parts):
                if fil == BLOCKER:
                    cfg += [f'    <part id="{i}" subtype="support_blocker">',
                            f'      <metadata key="name" value={quoteattr(part)}/>', "    </part>"]
                    continue
                cfg += [f'    <part id="{i}" subtype="normal_part">', f'      <metadata key="name" value={quoteattr(part)}/>',
                        f'      <metadata key="extruder" value="{fil}"/>', "    </part>"]
            cfg.append("  </object>")
            plate += ["    <model_instance>", f'      <metadata key="object_id" value="{oid}"/>',
                      '      <metadata key="instance_id" value="0"/>', f'      <metadata key="identify_id" value="{k}"/>',
                      "    </model_instance>"]
        plate_cfg += plate + ["  </plate>"]
    model += [" </resources>", f' <build p:UUID="{_uuid(path.name, "build")}">'] + build_items + [" </build>", "</model>"]
    cfg += plate_cfg + ["</config>"]
    rel_head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                   ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                   ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
                   '</Types>')
        z.writestr("_rels/.rels", rel_head + ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
                   'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>')
        z.writestr("3D/3dmodel.model", "\n".join(model))
        z.writestr("3D/_rels/3dmodel.model.rels", rel_head + "\n".join(rels) + "\n</Relationships>")
        for n, text in files.items():
            z.writestr(n, text)
        z.writestr("Metadata/model_settings.config", "\n".join(cfg))
        z.writestr("Metadata/project_settings.config", _settings_for(settings, len(plates)))


# ---- reading a 3MF back (tests, and checking what Bambu Studio saved) ---------------------------------------

CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def _meta(el) -> dict:
    return {m.get("key"): m.get("value") for m in el.findall("metadata")}


def read_filaments(path: Path) -> list[tuple[str, int, dict]]:
    """[(object name, object filament, {part name: filament})] from Metadata/model_settings.config. A part with no
    filament of its own uses the object's (Bambu Studio leaves it out of one-part objects)."""
    z = zipfile.ZipFile(path)
    out = []
    for o in ET.fromstring(z.read("Metadata/model_settings.config")).iter("object"):
        meta = _meta(o)
        parts = {_meta(pt)["name"]: int(_meta(pt).get("extruder", meta["extruder"])) for pt in o.findall("part")
                 if pt.get("subtype", "normal_part") == "normal_part"}
        out.append((meta["name"], int(meta["extruder"]), parts))
    return out


def read_blockers(path: Path) -> dict[str, list[str]]:
    """{object name: [its support blockers' part names]} for the objects that have any."""
    out = {}
    for o in ET.fromstring(zipfile.ZipFile(path).read("Metadata/model_settings.config")).iter("object"):
        names = [_meta(pt)["name"] for pt in o.findall("part") if pt.get("subtype") == "support_blocker"]
        if names:
            out[_meta(o)["name"]] = names
    return out


def _plates(path: Path) -> list[tuple[str, list[str]]]:
    """[(plate name, [object ids])] in plate order."""
    cfg = ET.fromstring(zipfile.ZipFile(path).read("Metadata/model_settings.config"))
    out = []
    for pl in cfg.iter("plate"):
        ids = [_meta(mi)["object_id"] for mi in pl.findall("model_instance")]
        out.append((int(_meta(pl)["plater_id"]), _meta(pl).get("plater_name", ""), ids))
    return [(name, ids) for _, name, ids in sorted(out)]


def read_plates(path: Path) -> list[tuple[str, list[str]]]:
    """[(plate name, [object names on it])], in plate order."""
    cfg = ET.fromstring(zipfile.ZipFile(path).read("Metadata/model_settings.config"))
    names = {o.get("id"): _meta(o)["name"] for o in cfg.iter("object")}
    return [(name, [names[i] for i in ids]) for name, ids in _plates(path)]


def read_plate_offsets(path: Path) -> list[tuple[str, tuple[float, float]]]:
    """[(plate name, (x, y) translation of its first object's build item)]: where the plate sits on Bambu's grid."""
    root = ET.fromstring(zipfile.ZipFile(path).read("3D/3dmodel.model"))
    move = {it.get("objectid"): [float(v) for v in it.get("transform").split()][9:11] for it in root.iter(f"{CORE}item")}
    return [(name, (round(move[ids[0]][0], 3), round(move[ids[0]][1], 3))) for name, ids in _plates(path)]


def read_meshes(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """{mesh object id: (vertices, triangles)} for every mesh in 3D/Objects/."""
    z = zipfile.ZipFile(path)
    out = {}
    for n in z.namelist():
        if n.startswith("3D/Objects/"):
            for o in ET.fromstring(z.read(n)).iter(f"{CORE}object"):
                v = np.array([(float(q.get("x")), float(q.get("y")), float(q.get("z"))) for q in o.iter(f"{CORE}vertex")])
                t = np.array([(int(q.get("v1")), int(q.get("v2")), int(q.get("v3"))) for q in o.iter(f"{CORE}triangle")])
                out[o.get("id")] = (v, t)
    return out


def object_sizes(path: Path, digits: int = 1) -> list[tuple[str, tuple]]:
    """Sorted [(object name, sorted part sizes (dx, dy, dz, triangles))], placement-independent. To compare two
    files, use same_objects (a tolerance), not == on these (rounding flips on boundary values)."""
    z = zipfile.ZipFile(path)
    names = {o.get("id"): _meta(o)["name"]
             for o in ET.fromstring(z.read("Metadata/model_settings.config")).iter("object")}
    sizes = {i: tuple(round(float(np.ptp(v[:, k])), digits) for k in range(3)) + (len(t),)
             for i, (v, t) in read_meshes(path).items()}
    out = []
    for o in ET.fromstring(z.read("3D/3dmodel.model")).iter(f"{CORE}object"):
        comps = [c.get("objectid") for c in o.iter(f"{CORE}component")]
        if comps:
            out.append((names[o.get("id")], tuple(sorted(sizes[c] for c in comps))))
    return sorted(out)


def _match(xs: list, ys: list, eq) -> bool:
    """Every x pairs with its own y under eq (greedy), and nothing is left over."""
    ys = list(ys)
    for x in xs:
        j = next((j for j, y in enumerate(ys) if eq(x, y)), None)
        if j is None:
            return False
        ys.pop(j)
    return not ys


def same_objects(a: Path, b: Path, tol: float = 0.01) -> bool:
    """Both files hold the same objects (by name), each with parts of the same size within tol mm and the same
    triangle count; placement doesn't matter. Use it to compare a file with its Bambu Studio round trip: Bambu saves
    32-bit floats, so exact or rounded sizes can differ (60.15 comes back as 60.149..., which rounds the other way)."""
    part = lambda p, q: p[3] == q[3] and all(abs(x - y) <= tol for x, y in zip(p[:3], q[:3]))
    return _match(object_sizes(a, digits=6), object_sizes(b, digits=6),
                  lambda x, y: x[0] == y[0] and _match(list(x[1]), list(y[1]), part))
