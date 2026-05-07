"""
Room 3D Blueprint Generator
Detects 1-meter rulers and wall edges to create 3D room blueprints
"""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from typing import Iterable

import cv2
import numpy as np
from fastapi import UploadFile

from ..schemas import ImageMeasurement, MeasureResponse, MeasurementObject


def _encode_png_data_url(image: np.ndarray) -> str:
    """Encode image as base64 PNG data URL"""
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode preview image.")
    return f"data:image/png;base64,{base64.b64encode(encoded.tobytes()).decode('ascii')}"


def _detect_meter_ruler(image: np.ndarray) -> tuple[float, list] | None:
    """
    Detect 1-meter ruler in image and return pixels_per_meter and ruler line endpoints
    
    Returns:
        (pixels_per_meter, [(x1, y1), (x2, y2)]) or None if not found
    """
    if image is None or image.size == 0:
        return None
        
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection for ruler (look for straight lines)
    edges = cv2.Canny(blurred, 50, 150)
    
    # Look for straight lines (ruler is straight)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=100,
        maxLineGap=10
    )
    
    if lines is None or len(lines) == 0:
        return None
    
    # Find the longest line (likely the ruler)
    longest_line = None
    max_length = 0
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length > max_length:
            max_length = length
            longest_line = ((x1, y1), (x2, y2))
    
    if longest_line is None or max_length < 100:  # Ruler must be at least 100 pixels long
        return None
    
    # The longest line is the ruler - convert pixels to meters
    # 1 meter = max_length pixels
    pixels_per_meter = max_length
    
    return pixels_per_meter, [longest_line[0], longest_line[1]]


def _detect_walls(image: np.ndarray) -> list[tuple]:
    """
    Detect wall edges in the image
    
    Returns:
        List of wall line segments [(x1, y1, x2, y2), ...]
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # Edge detection for walls
    edges = cv2.Canny(blurred, 50, 150)
    
    # Dilate to connect broken edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=2)
    
    # Find lines
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=50,
        minLineLength=50,
        maxLineGap=20
    )
    
    if lines is None:
        return []
    
    # Convert to simple format and filter
    wall_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        # Keep lines with significant length
        if length > 30:
            wall_lines.append((x1, y1, x2, y2))
    
    return wall_lines


def _line_length_px(line: tuple[int, int, int, int]) -> float:
    x1, y1, x2, y2 = line
    return float(np.hypot(x2 - x1, y2 - y1))


def _line_angle_deg(line: tuple[int, int, int, int]) -> float:
    x1, y1, x2, y2 = line
    angle = np.degrees(np.arctan2((y2 - y1), (x2 - x1)))
    return float(abs(angle))


def _select_room_edges(walls: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Keep only the longest representative lines to reduce noise."""
    if not walls:
        return []

    sorted_walls = sorted(walls, key=_line_length_px, reverse=True)
    selected: list[tuple[int, int, int, int]] = []
    for line in sorted_walls:
        angle = _line_angle_deg(line)
        length = _line_length_px(line)
        if length < 40:
            continue

        is_similar = False
        for kept in selected:
            kept_angle = _line_angle_deg(kept)
            kept_len = _line_length_px(kept)
            if abs(kept_angle - angle) < 7 and abs(kept_len - length) < 25:
                is_similar = True
                break

        if not is_similar:
            selected.append(line)

        if len(selected) >= 10:
            break

    return selected


def _find_corners(walls: list[tuple], image_shape: tuple) -> list[tuple]:
    """
    Find corner points where walls meet
    
    Returns:
        List of corner coordinates [(x, y), ...]
    """
    if len(walls) < 2:
        return []
    
    corners = []
    
    # Check intersections between lines
    for i, line1 in enumerate(walls):
        for line2 in walls[i + 1:]:
            # Convert lines to parametric form and find intersection
            x1, y1, x2, y2 = line1
            x3, y3, x4, y4 = line2
            
            denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(denom) < 1e-10:
                continue  # Lines are parallel
            
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
            
            px = x1 + t * (x2 - x1)
            py = y1 + t * (y2 - y1)
            
            # Check if intersection is within image bounds
            if 0 <= px < image_shape[1] and 0 <= py < image_shape[0]:
                # Avoid duplicate corners
                is_duplicate = False
                for cx, cy in corners:
                    if abs(cx - px) < 20 and abs(cy - py) < 20:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    corners.append((int(px), int(py)))
    
    # Add image corners as room corners
    h, w = image_shape[:2]
    corners.extend([(0, 0), (w, 0), (0, h), (w, h)])
    
    return corners


def _measure_walls(walls: list[tuple], pixels_per_meter: float) -> list[dict]:
    """
    Measure wall lengths in meters
    
    Returns:
        List of wall measurements [{length_m, start, end}, ...]
    """
    wall_measurements = []
    
    for x1, y1, x2, y2 in walls:
        length_px = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        length_m = length_px / pixels_per_meter
        
        wall_measurements.append({
            "length_m": round(length_m, 2),
            "start": (int(x1), int(y1)),
            "end": (int(x2), int(y2)),
            "pixels": int(length_px)
        })
    
    return wall_measurements


def _generate_floor_plan_json(
    walls_measurements: list[dict],
    corners: list[tuple],
    pixels_per_meter: float,
    image_shape: tuple
) -> dict:
    """Generate floor plan as JSON with measurements"""
    floor_plan = {
        "type": "floor_plan",
        "walls": walls_measurements,
        "corners": corners,
        "pixels_per_meter": pixels_per_meter,
        "image_dimensions": {
            "width": image_shape[1],
            "height": image_shape[0]
        },
        "scale_info": {
            "unit": "meters",
            "ruler_scale": "1 meter reference"
        }
    }
    
    return floor_plan


def _draw_blueprint_overlay(
    image: np.ndarray,
    walls: list[tuple],
    corners: list[tuple],
    ruler_line: list | None
) -> np.ndarray:
    """Draw detected walls and corners on image for visualization"""
    overlay = image.copy()
    
    # Draw ruler in green
    if ruler_line:
        (x1, y1), (x2, y2) = ruler_line
        cv2.line(overlay, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(overlay, "1m Ruler", (x1 + 10, y1 - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Draw walls in blue
    for x1, y1, x2, y2 in walls:
        cv2.line(overlay, (x1, y1), (x2, y2), (255, 0, 0), 2)
    
    # Draw corners in red
    for cx, cy in corners:
        cv2.circle(overlay, (cx, cy), 5, (0, 0, 255), -1)
    
    return overlay


def _estimate_room_dimensions(
    per_image_edges: list[list[tuple[int, int, int, int]]],
    pixels_per_meter_values: list[float],
) -> tuple[float, float, float]:
    """Estimate room length/width/height in meters from 3 image views."""
    primary_lengths_m: list[float] = []
    secondary_lengths_m: list[float] = []
    vertical_lengths_m: list[float] = []

    for edges, ppm in zip(per_image_edges, pixels_per_meter_values):
        if ppm <= 0 or not edges:
            continue

        lengths_m = sorted([_line_length_px(line) / ppm for line in edges], reverse=True)
        if lengths_m:
            primary_lengths_m.append(lengths_m[0])
        if len(lengths_m) > 1:
            secondary = next((val for val in lengths_m[1:] if abs(val - lengths_m[0]) > 0.2), lengths_m[1])
            secondary_lengths_m.append(secondary)

        for line in edges:
            x1, y1, x2, y2 = line
            if abs(y2 - y1) > abs(x2 - x1):
                vertical_lengths_m.append(_line_length_px(line) / ppm)

    if not primary_lengths_m:
        raise ValueError("Could not estimate room geometry from the uploaded images.")

    room_length_m = float(np.median(primary_lengths_m))
    if secondary_lengths_m:
        room_width_m = float(np.median(secondary_lengths_m))
    else:
        room_width_m = room_length_m * 0.75

    if vertical_lengths_m:
        room_height_m = float(np.percentile(vertical_lengths_m, 85))
    else:
        room_height_m = 2.7

    room_length_m = float(np.clip(room_length_m, 1.8, 20.0))
    room_width_m = float(np.clip(room_width_m, 1.5, 20.0))
    room_height_m = float(np.clip(room_height_m, 2.2, 4.0))

    if room_width_m > room_length_m:
        room_length_m, room_width_m = room_width_m, room_length_m

    return room_length_m, room_width_m, room_height_m


def _draw_room_3d_blueprint(length_m: float, width_m: float, height_m: float) -> np.ndarray:
    """Render a CAD-like single 3D blueprint from fused room dimensions."""
    canvas_h, canvas_w = 820, 1120
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

    # Deep blueprint background.
    top = np.array([104, 50, 8], dtype=np.float32)   # BGR
    bottom = np.array([144, 74, 14], dtype=np.float32)
    for y in range(canvas_h):
        t = y / max(1, canvas_h - 1)
        canvas[y, :] = (top * (1.0 - t) + bottom * t).astype(np.uint8)

    # Subtle technical grid.
    for x in range(0, canvas_w, 28):
        cv2.line(canvas, (x, 0), (x, canvas_h), (132, 76, 18), 1)
    for y in range(0, canvas_h, 28):
        cv2.line(canvas, (0, y), (canvas_w, y), (132, 76, 18), 1)

    # Border frame.
    cv2.rectangle(canvas, (10, 10), (canvas_w - 10, canvas_h - 10), (170, 112, 42), 2)
    cv2.rectangle(canvas, (18, 18), (canvas_w - 18, canvas_h - 18), (155, 100, 34), 1)

    # Keep proportions while fitting into canvas.
    max_px_x = 560
    max_px_y = 300
    max_px_h = 380
    scale_x = max_px_x / max(length_m, 0.1)
    scale_y = max_px_y / max(width_m, 0.1)
    scale_h = max_px_h / max(height_m, 0.1)
    scale = float(min(scale_x, scale_y, scale_h))

    lx = int(length_m * scale)
    ly = int(width_m * scale * 0.58)
    hz = int(height_m * scale * 0.82)

    origin = np.array([190, 690], dtype=np.int32)
    vx = np.array([1, 0], dtype=np.int32)
    vy = np.array([1, -1], dtype=np.int32)
    vz = np.array([0, -1], dtype=np.int32)

    p0 = origin
    p1 = origin + lx * vx
    p2 = p1 + ly * vy
    p3 = origin + ly * vy
    p4 = p0 + hz * vz
    p5 = p1 + hz * vz
    p6 = p2 + hz * vz
    p7 = p3 + hz * vz

    def pt(p: np.ndarray) -> tuple[int, int]:
        return int(p[0]), int(p[1])

    line_main = (246, 246, 246)
    line_soft = (210, 210, 210)
    line_dash = (170, 170, 170)

    # Base platform steps, similar to reference style.
    for i in range(4):
        o = i * 14
        a0 = p0 + np.array([-26 + o, 8 + o], dtype=np.int32)
        a1 = p1 + np.array([20 + o, 8 + o], dtype=np.int32)
        a2 = p2 + np.array([20 + o, 8 + o], dtype=np.int32)
        a3 = p3 + np.array([-26 + o, 8 + o], dtype=np.int32)
        for a, b in [(a0, a1), (a1, a2), (a2, a3), (a3, a0)]:
            cv2.line(canvas, pt(a), pt(b), line_soft, 1)

    # Outer room frame.
    for a, b in [(p0, p1), (p1, p2), (p2, p3), (p3, p0), (p4, p5), (p5, p6), (p6, p7), (p7, p4), (p0, p4), (p1, p5), (p2, p6), (p3, p7)]:
        cv2.line(canvas, pt(a), pt(b), line_main, 1)

    # Inner wall shell.
    inset = 24
    q0 = p0 + inset * vx + inset * vy
    q1 = p1 - inset * vx + inset * vy
    q2 = p2 - inset * vx - inset * vy
    q3 = p3 + inset * vx - inset * vy
    q4 = q0 + (hz - 18) * vz
    q5 = q1 + (hz - 18) * vz
    q6 = q2 + (hz - 18) * vz
    q7 = q3 + (hz - 18) * vz
    for a, b in [(q0, q1), (q1, q2), (q2, q3), (q3, q0), (q4, q5), (q5, q6), (q6, q7), (q7, q4), (q0, q4), (q1, q5), (q2, q6), (q3, q7)]:
        cv2.line(canvas, pt(a), pt(b), line_soft, 1)

    # Interior guide lines.
    cv2.line(canvas, pt(q0), pt(q6), line_dash, 1)
    cv2.line(canvas, pt(q1), pt(q7), line_dash, 1)

    # Four column-like pillars.
    def draw_column(base: np.ndarray, w: int, d: int, h: int) -> None:
        c0 = base
        c1 = base + w * vx
        c2 = c1 + d * vy
        c3 = base + d * vy
        c4 = c0 + h * vz
        c5 = c1 + h * vz
        c6 = c2 + h * vz
        c7 = c3 + h * vz
        for a, b in [(c0, c1), (c1, c2), (c2, c3), (c3, c0), (c4, c5), (c5, c6), (c6, c7), (c7, c4), (c0, c4), (c1, c5), (c2, c6), (c3, c7)]:
            cv2.line(canvas, pt(a), pt(b), line_main, 1)

    col_h = int(hz * 0.62)
    draw_column(p0 + np.array([78, -10], dtype=np.int32), 34, 30, col_h)
    draw_column(p0 + np.array([190, -32], dtype=np.int32), 34, 30, col_h)
    draw_column(p1 + np.array([-170, -42], dtype=np.int32), 34, 30, col_h)
    draw_column(p1 + np.array([-70, -60], dtype=np.int32), 34, 30, col_h)

    # Draw segmented extension/dimension line.
    def draw_dim(a: np.ndarray, b: np.ndarray, offset: np.ndarray, text: str, text_shift: tuple[int, int] = (0, -8)) -> None:
        pa = a + offset
        pb = b + offset
        cv2.line(canvas, pt(a), pt(pa), line_soft, 1)
        cv2.line(canvas, pt(b), pt(pb), line_soft, 1)
        cv2.line(canvas, pt(pa), pt(pb), line_main, 1)

        # Tick marks.
        tick = np.array([4, 4], dtype=np.int32)
        cv2.line(canvas, pt(pa - tick), pt(pa + tick), line_main, 1)
        cv2.line(canvas, pt(pb - tick), pt(pb + tick), line_main, 1)

        mid = (pa + pb) // 2
        cv2.putText(
            canvas,
            text,
            (int(mid[0] + text_shift[0]), int(mid[1] + text_shift[1])),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            line_main,
            1,
            cv2.LINE_AA,
        )

    length_cm = int(round(length_m * 100))
    width_cm = int(round(width_m * 100))
    height_cm = int(round(height_m * 100))

    draw_dim(p0, p1, np.array([0, 56], dtype=np.int32), f"{length_cm}")
    draw_dim(p1, p2, np.array([42, 10], dtype=np.int32), f"{width_cm}")
    draw_dim(p0, p4, np.array([-30, 0], dtype=np.int32), f"{height_cm}", text_shift=(-26, -6))

    # Additional reference labels.
    cv2.putText(canvas, "X1", (p4[0] - 42, p4[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, line_soft, 1, cv2.LINE_AA)
    cv2.putText(canvas, "X2", (p5[0] + 10, p5[1] + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, line_soft, 1, cv2.LINE_AA)
    cv2.putText(canvas, "X3", (p6[0] + 10, p6[1] + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, line_soft, 1, cv2.LINE_AA)
    cv2.putText(canvas, "X4", (q4[0] + 26, q4[1] + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.45, line_soft, 1, cv2.LINE_AA)

    cv2.putText(canvas, "COMBINED 3D ROOM BLUEPRINT", (42, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.78, line_main, 1, cv2.LINE_AA)
    cv2.putText(canvas, "fused from 3 photos using 1-meter rulers", (42, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.46, line_soft, 1, cv2.LINE_AA)

    return canvas


async def analyze_room_measurement(
    files: Iterable[UploadFile],
    project_name: str,
) -> MeasureResponse:
    """
    Analyze room photos with meter rulers to generate 3D blueprint
    
    Process:
    1. Validate all images have rulers
    2. Detect walls and edges
    3. Find corners
    4. Measure wall dimensions
    5. Generate room model
    """
    images: list[ImageMeasurement] = []
    file_list = list(files)

    if len(file_list) != 3:
        raise ValueError("Please upload exactly 3 images to generate a fused 3D room blueprint.")

    per_image_edges: list[list[tuple[int, int, int, int]]] = []
    pixels_per_meter_values: list[float] = []
    
    # Read and validate all images (ruler + wall edges)
    for image_index, file in enumerate(file_list, 1):
        content = await file.read()
        nparr = np.frombuffer(content, np.uint8)
        image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image_bgr is None:
            raise ValueError(f"Image {image_index} ({file.filename}): Could not read image file.")
        
        # Check if ruler is detected
        ruler_result = _detect_meter_ruler(image_bgr)
        if ruler_result is None:
            raise ValueError(
                f"❌ Image {image_index} ({file.filename}): **No ruler detected**\n\n"
                f"Ensure the 1-meter ruler is clearly visible in the image. "
                f"The ruler should be:\n"
                f"• Placed on the floor or against a wall\n"
                f"• Straight and horizontal/vertical\n"
                f"• Occupying at least 30% of image width"
            )
        
        pixels_per_meter, _ = ruler_result
        walls = _select_room_edges(_detect_walls(image_bgr))
        if len(walls) < 2:
            raise ValueError(
                f"Image {image_index} ({file.filename}): Could not detect enough wall edges. "
                "Capture clearer room boundaries and avoid motion blur."
            )

        per_image_edges.append(walls)
        pixels_per_meter_values.append(pixels_per_meter)

    room_length_m, room_width_m, room_height_m = _estimate_room_dimensions(per_image_edges, pixels_per_meter_values)
    avg_pixels_per_cm = float(np.mean(pixels_per_meter_values) / 100.0)

    blueprint_image = _draw_room_3d_blueprint(room_length_m, room_width_m, room_height_m)
    preview_data_url = _encode_png_data_url(blueprint_image)

    length_cm = round(room_length_m * 100, 1)
    width_cm = round(room_width_m * 100, 1)
    height_cm = round(room_height_m * 100, 1)

    objects: list[MeasurementObject] = [
        MeasurementObject(
            id="room-wall-a",
            name="Wall A",
            length=length_cm,
            width=20.0,
            height=height_cm,
            confidence=0.92,
            previewLabel=f"Primary wall: {length_cm} cm",
            previewDataUrl=preview_data_url,
            isBackground=False,
        ),
        MeasurementObject(
            id="room-wall-b",
            name="Wall B",
            length=width_cm,
            width=20.0,
            height=height_cm,
            confidence=0.92,
            previewLabel=f"Secondary wall: {width_cm} cm",
            previewDataUrl=preview_data_url,
            isBackground=False,
        ),
        MeasurementObject(
            id="room-wall-c",
            name="Wall C",
            length=length_cm,
            width=20.0,
            height=height_cm,
            confidence=0.90,
            previewLabel=f"Opposite primary wall: {length_cm} cm",
            previewDataUrl=preview_data_url,
            isBackground=False,
        ),
        MeasurementObject(
            id="room-wall-d",
            name="Wall D",
            length=width_cm,
            width=20.0,
            height=height_cm,
            confidence=0.90,
            previewLabel=f"Opposite secondary wall: {width_cm} cm",
            previewDataUrl=preview_data_url,
            isBackground=False,
        ),
    ]

    background = MeasurementObject(
        id="room-3d-blueprint",
        name="Combined 3D Room",
        length=length_cm,
        width=width_cm,
        height=height_cm,
        confidence=0.95,
        previewLabel="Fused from 3 ruler-calibrated images",
        previewDataUrl=preview_data_url,
        isBackground=True,
    )

    images.append(
        ImageMeasurement(
            imageName="combined-room-3d",
            imageIndex=0,
            objects=objects,
            background=background,
            calibrationSource="meter-ruler-3-views",
            pixelsPerCm=round(avg_pixels_per_cm, 4),
            detectedReferenceObjects=[],
            suggestedCalibration=None,
        )
    )
    
    return MeasureResponse(
        measurementId=str(uuid.uuid4()),
        projectName=project_name,
        createdAt=datetime.now(timezone.utc),
        images=images,
    )
