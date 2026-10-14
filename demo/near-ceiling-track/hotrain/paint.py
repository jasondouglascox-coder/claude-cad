"""Two-color parts as ONE solid with painted faces.

A multi-color print part (corner deck, tie ladder) is modelled as wood + steel bodies so the printer files
can split it by color (one color change per print). For CAD it is one fused solid: `painted()` fuses the
bodies and records each face's color, `export_step()` writes those face colors into the STEP (so Onshape
shows one part with gray tie plates on brown ties), and `display_parts()` splits a placed painted part back
into colored bodies for viewers that only color whole shapes.
"""
from build123d import Color, Location, Part, Shape

_FACE_COLOR: dict[int, Color] = {}  # hash(face of a painted prototype) -> color
_PROTOS: list[tuple[Part, list[tuple[Part, Color]]]] = []  # (fused prototype, [(body, color)])


def _sample(face) -> tuple[float, float, float]:
    """A point inside the face (centroid of its first mesh triangle; the face center can fall in a hole)."""
    verts, tris = face.tessellate(0.05)
    a, b, c = (verts[i] for i in tris[0])
    return ((a.X + b.X + c.X) / 3, (a.Y + b.Y + c.Y) / 3, (a.Z + b.Z + c.Z) / 3)


def _boxes(body: Part) -> list:
    return [(s, s.bounding_box()) for s in body.solids()]


def _in(boxes: list, pt) -> bool:
    x, y, z = pt
    for s, bb in boxes:
        if bb.min.X - 1e-4 <= x <= bb.max.X + 1e-4 and bb.min.Y - 1e-4 <= y <= bb.max.Y + 1e-4 \
                and bb.min.Z - 1e-4 <= z <= bb.max.Z + 1e-4 and s.is_inside(pt, 1e-4):
            return True
    return False


def painted(base: Part, base_color: Color, accent: Part, accent_color: Color) -> Part:
    """Fuse base + accent into one solid; faces of the accent body get accent_color, the rest base_color."""
    fused = Part((base + accent).solids())
    fused.color = base_color
    boxes = _boxes(accent)
    for f in fused.faces():
        _FACE_COLOR[hash(f)] = accent_color if _in(boxes, _sample(f)) else base_color
    b, a = Part(base.solids()), Part(accent.solids())
    b.color, a.color = base_color, accent_color
    _PROTOS.append((fused, [(b, base_color), (a, accent_color)]))
    return fused


def face_color(face) -> Color | None:
    return _FACE_COLOR.get(hash(face))


def display_parts(part: Shape) -> list[tuple[Shape, Color]] | None:
    """If `part` is a placed copy of a painted prototype, its colored bodies placed the same way."""
    for proto, bodies in _PROTOS:
        if part.wrapped is not None and part.wrapped.IsPartner(proto.wrapped):
            loc = Location(part.wrapped.Location())
            return [(loc * b, c) for b, c in bodies]
    return None


def export_step(to_export: Shape, path: str) -> bool:
    """build123d's export_step, plus the painted face colors."""
    from build123d.exporters3d import _create_xde
    from build123d.build_enums import Unit
    from OCP.APIHeaderSection import APIHeaderSection_MakeHeader
    from OCP.IFSelect import IFSelect_ReturnStatus
    from OCP.Interface import Interface_Static
    from OCP.Message import Message, Message_Gravity
    from OCP.STEPCAFControl import STEPCAFControl_Controller, STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_Controller, STEPControl_StepModelType
    from build123d.build_enums import PrecisionMode
    from OCP.TCollection import TCollection_HAsciiString
    from OCP.TDF import TDF_ChildIterator
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
    from OCP.XSControl import XSControl_WorkSession
    from build123d import Face

    doc = _create_xde(to_export, Unit.MM, auto_naming=True)
    if _FACE_COLOR:
        shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
        color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
        it = TDF_ChildIterator(shape_tool.BaseLabel(), False)  # every shape definition
        while it.More():
            lab = it.Value()
            it.Next()
            if shape_tool.IsAssembly_s(lab) or not XCAFDoc_ShapeTool.IsShape_s(lab):
                continue
            shape = XCAFDoc_ShapeTool.GetShape_s(lab)
            exp = TopExp_Explorer(shape, TopAbs_FACE)
            while exp.More():
                col = _FACE_COLOR.get(hash(Face(exp.Current())))
                if col is not None:
                    sub = shape_tool.AddSubShape(lab, exp.Current())
                    if not sub.IsNull():
                        color_tool.SetColor(sub, col.wrapped, XCAFDoc_ColorType.XCAFDoc_ColorSurf)
                exp.Next()

    for printer in Message.DefaultMessenger_s().Printers():
        printer.SetTraceLevel(Message_Gravity.Message_Fail)
    writer = STEPCAFControl_Writer(XSControl_WorkSession(), False)
    writer.SetColorMode(True)
    writer.SetLayerMode(True)
    writer.SetNameMode(True)
    header = APIHeaderSection_MakeHeader(writer.Writer().Model())
    if not header.IsDone():
        header = APIHeaderSection_MakeHeader(0)
        header.Apply(writer.Writer().Model())
    if to_export.label:
        header.SetName(TCollection_HAsciiString(to_export.label))
    header.SetOriginatingSystem(TCollection_HAsciiString("build123d"))
    STEPCAFControl_Controller.Init_s()
    STEPControl_Controller.Init_s()
    Interface_Static.SetIVal_s("write.surfacecurve.mode", 1)
    Interface_Static.SetIVal_s("write.precision.mode", PrecisionMode.AVERAGE.value)
    writer.Transfer(doc, STEPControl_StepModelType.STEPControl_AsIs)
    if writer.Write(str(path)) != IFSelect_ReturnStatus.IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file {path}")
    return True
