"""Build plates as Bambu Studio project 3MF, so they open already colored.

Bambu Studio only reads a filament per part from its own project format; a plain 3MF loads as geometry
("not from Bambu Lab") and every part lands on filament 1. So each printed part is one object, each color body
one part of it, and Metadata/model_settings.config gives every part its filament (AMS slot).
Metadata/project_settings.config comes from bambu_project_settings.config, saved by Bambu Studio itself: A1 0.4,
0.20mm Standard, filaments 1 gray PETG, 2 brown PETG, 3 white PLA. Bambu Studio needs it to open a project.
"""
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np
from build123d import Shape

from hotrain.params import Params

SETTINGS = Path(__file__).with_name("bambu_project_settings.config")
VERSION = "02.08.04.57"  # Bambu Studio that wrote the settings template (the user's install)
NS = 'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" ' \
     'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" ' \
     'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"'
IDENTITY = "1 0 0 0 1 0 0 0 1 0 0 0"


def filament(p: Params, name: str) -> int:
    """Filament for a body: brown wood, white ceiling cleats, gray for everything else."""
    if name.endswith("_wood"):
        return p.filament_brown
    if name.startswith("ceiling_anchor"):
        return p.filament_white
    return p.filament_gray


def mesh(shape: Shape, tol: float = 0.01, angular: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """Watertight triangle mesh: OCC tessellates each face separately, so merge coincident vertices."""
    verts, tris = shape.tessellate(tol, angular)
    v = np.array([(q.X, q.Y, q.Z) for q in verts])
    _, first, idx = np.unique(np.round(v / 1e-4).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    t = idx.ravel()[np.array(tris)]
    t = t[(t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])]
    return v[first], t


def _uuid(*key) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "hotrain/" + "/".join(map(str, key))))


def _object_file(parts: list[tuple[str, Shape, int]], key: str) -> str:
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {NS}>',
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>', " <resources>"]
    for i, (_, shape, _) in enumerate(parts, start=1):
        v, t = mesh(shape)
        out.append(f'  <object id="{i}" p:UUID="{_uuid(key, i)}" type="model">\n   <mesh>\n    <vertices>')
        out += [f'     <vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x, y, z in v]
        out.append("    </vertices>\n    <triangles>")
        out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t]
        out.append("    </triangles>\n   </mesh>\n  </object>")
    out += [" </resources>", " <build/>", "</model>"]
    return "\n".join(out)


def write(path: Path, objects: list[tuple[str, list[tuple[str, Shape, int]]]]) -> None:
    """objects: (name, [(part name, shape in plate coordinates, filament), ...]); one plate per file."""
    model = [f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {NS}>',
             f' <metadata name="Application">BambuStudio-{VERSION}</metadata>',
             ' <metadata name="BambuStudio:3mfVersion">1</metadata>', " <resources>"]
    rels, files, build_items = [], {}, []
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    plate = ["  <plate>", '    <metadata key="plater_id" value="1"/>', '    <metadata key="plater_name" value=""/>',
             '    <metadata key="locked" value="false"/>']
    for k, (name, parts) in enumerate(objects, start=1):
        oid, fname = 2 * k, f"/3D/Objects/object_{k}.model"
        files[fname[1:]] = _object_file(parts, f"{path.name}/{k}")
        rels.append(f' <Relationship Target="{fname}" Id="rel-{k}" '
                    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>')
        model.append(f'  <object id="{oid}" p:UUID="{_uuid(path.name, k)}" type="model">\n   <components>')
        model += [f'    <component p:path="{fname}" objectid="{i}" p:UUID="{_uuid(path.name, k, "c", i)}" '
                  f'transform="{IDENTITY}"/>' for i in range(1, len(parts) + 1)]
        model.append("   </components>\n  </object>")
        build_items.append(f'  <item objectid="{oid}" p:UUID="{_uuid(path.name, k, "item")}" '
                           f'transform="{IDENTITY}" printable="1"/>')
        cfg += [f'  <object id="{oid}">', f'    <metadata key="name" value={quoteattr(name)}/>',
                f'    <metadata key="extruder" value="{parts[0][2]}"/>']
        for i, (pname, _, fil) in enumerate(parts, start=1):
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
        z.writestr("Metadata/project_settings.config", SETTINGS.read_text())
