from __future__ import annotations

import io
import zipfile
import base64
from typing import Optional


def _build_obj(length: float, width: float, height: float) -> str:
    # Box vertices (origin at one corner, floor at y=0)
    L = float(length)
    W = float(width)
    H = float(height)

    verts = [
        (0.0, 0.0, 0.0),
        (L, 0.0, 0.0),
        (L, 0.0, W),
        (0.0, 0.0, W),
        (0.0, H, 0.0),
        (L, H, 0.0),
        (L, H, W),
        (0.0, H, W),
    ]

    # Faces (1-based indices)
    faces = [
        (1, 2, 3, 4),  # floor
        (5, 8, 7, 6),  # ceiling
        (1, 5, 6, 2),  # front wall
        (2, 6, 7, 3),  # right wall
        (3, 7, 8, 4),  # back wall
        (4, 8, 5, 1),  # left wall
    ]

    lines = ["mtllib room.mtl", "usemtl RoomMat"]
    for x, y, z in verts:
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")

    # simple UVs (not truly mapped, but placeholders)
    uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for u, v in uvs:
        lines.append(f"vt {u:.6f} {v:.6f}")

    # normals (approx)
    normals = [(0, -1, 0), (0, 1, 0), (0, 0, -1), (1, 0, 0), (0, 0, 1), (-1, 0, 0)]
    for nx, ny, nz in normals:
        lines.append(f"vn {nx} {ny} {nz}")

    # write faces with vertex/uv/normal indices
    for i, f in enumerate(faces):
        # use repeating uv/normal indices for each quad
        v_indices = " ".join(str(idx) + "/" + str(((j % 4) + 1)) + "/" + str(i + 1) for j, idx in enumerate(f))
        lines.append(f"f {v_indices}")

    return "\n".join(lines) + "\n"


def _build_mtl(has_texture: bool) -> str:
    lines = ["newmtl RoomMat"]
    lines.append("Ka 0.200000 0.200000 0.200000")
    lines.append("Kd 0.800000 0.800000 0.800000")
    lines.append("Ks 0.000000 0.000000 0.000000")
    if has_texture:
        lines.append("map_Kd texture.png")
    return "\n".join(lines) + "\n"


def generate_room_box_zip(
    length_m: float, width_m: float, height_m: float, background_data_url: Optional[str] = None
) -> bytes:
    """Generate a ZIP containing a simple OBJ/MTL representation of a rectangular room.

    - length_m, width_m, height_m: dimensions in meters
    - background_data_url: optional data URL (e.g. 'data:image/png;base64,...') to include as texture.png

    Returns ZIP bytes.
    """
    obj_text = _build_obj(length_m, width_m, height_m)
    has_texture = bool(background_data_url)
    mtl_text = _build_mtl(has_texture)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("room.obj", obj_text)
        z.writestr("room.mtl", mtl_text)
        if has_texture:
            # expect data URL like 'data:image/png;base64,....'
            try:
                header, b64 = background_data_url.split(",", 1)
                texture_bytes = base64.b64decode(b64)
                z.writestr("texture.png", texture_bytes)
            except Exception:
                # if parsing fails, include nothing but still return obj/mtl
                pass

    return buf.getvalue()
