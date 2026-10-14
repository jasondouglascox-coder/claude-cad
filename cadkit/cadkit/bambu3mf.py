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


def mesh(shape: Shape, tol: float = 0.01, angular: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """Watertight triangle mesh: OCC tessellates each face separately, so merge coincident vertices."""
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


def write(path: Path, objects: list[tuple[str, list[tuple[str, Shape, int]]]], settings: Path = SETTINGS) -> None:
    """objects: (name, [(part name, shape in bed coordinates, filament number), ...]); one plate per file."""
    model = [f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {NS}>',
             f' <metadata name="Application">BambuStudio-{VERSION}</metadata>',
             ' <metadata name="BambuStudio:3mfVersion">1</metadata>', " <resources>"]
    rels, files, build_items = [], {}, []
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    plate = ["  <plate>", '    <metadata key="plater_id" value="1"/>', '    <metadata key="plater_name" value=""/>',
             '    <metadata key="locked" value="false"/>']
    last = 0  # one id sequence for meshes and objects across the package, as Bambu Studio writes it: it keys
    #           meshes by id alone, so a repeated id makes it reuse another object's mesh
    for k, (name, parts) in enumerate(objects, start=1):
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
                           f'transform="{IDENTITY}" printable="1"/>')
        cfg += [f'  <object id="{oid}">', f'    <metadata key="name" value={quoteattr(name)}/>',
                f'    <metadata key="extruder" value="{parts[0][2]}"/>']
        for i, (pname, _, fil) in zip(ids, parts):
            cfg += [f'    <part id="{i}" subtype="normal_part">', f'      <metadata key="name" value={quoteattr(pname)}/>',
                    f'      <metadata key="extruder" value="{fil}"/>', "    </part>"]
        cfg.append("  </object>")
        plate += ["    <model_instance>", f'      <metadata key="object_id" value="{oid}"/>',
                  '      <metadata key="instance_id" value="0"/>', f'      <metadata key="identify_id" value="{k}"/>',
                  "    </model_instance>"]
    model += [" </resources>", f' <build p:UUID="{_uuid(path.name, "build")}">'] + build_items + [" </build>", "</model>"]
    cfg += plate + ["  </plate>", "</config>"]
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
        z.writestr("Metadata/project_settings.config", Path(settings).read_text())


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
        parts = {_meta(pt)["name"]: int(_meta(pt).get("extruder", meta["extruder"])) for pt in o.findall("part")}
        out.append((meta["name"], int(meta["extruder"]), parts))
    return out


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
    """Sorted [(object name, sorted part sizes (dx, dy, dz, triangles))]: placement-independent, so a file and its
    Bambu Studio round trip should match (to 0.1 mm: Bambu saves 32-bit floats)."""
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
