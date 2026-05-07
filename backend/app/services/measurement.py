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
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode preview image.")
    return f"data:image/png;base64,{base64.b64encode(encoded.tobytes()).decode('ascii')}"


def _extract_object_contours(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 40, 140)
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = image.shape[0] * image.shape[1] * 0.004

    filtered = [contour for contour in contours if cv2.contourArea(contour) >= min_area]
    if not filtered:
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filtered = [contour for contour in contours if cv2.contourArea(contour) >= min_area]

    filtered.sort(key=cv2.contourArea, reverse=True)
    return filtered[:8]


def _resolve_scale(
    contours: list[np.ndarray], reference_width_cm: float | None = None, smallest_object_cm: float | None = None
) -> tuple[float, str]:
    """
    Resolve the scale (pixels per cm) using either:
    1. Manual reference width provided by user
    2. Estimated from smallest detected object (assuming it's 1-3cm)
    3. Fall back to error if nothing works
    """
    if reference_width_cm and reference_width_cm > 0 and contours:
        reference_contour = max(contours, key=cv2.contourArea)
        (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(reference_contour)
        reference_pixels = max(rect_w, rect_h)
        if reference_pixels > 0:
            return reference_pixels / reference_width_cm, "reference-width"

    # If we have info about a small object (coin/card), use it
    if smallest_object_cm and smallest_object_cm > 0 and contours:
        smallest_contour = min(contours, key=cv2.contourArea)
        (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(smallest_contour)
        smallest_pixels = max(rect_w, rect_h)
        if smallest_pixels > 0 and 5 < smallest_pixels / smallest_object_cm < 2000:
            return smallest_pixels / smallest_object_cm, "auto-detected-reference"

    raise ValueError(
        "Real-world measurements require a known scale. "
        "Either: (1) include a reference object like a coin or credit card, "
        "(2) enter one known real dimension from the image, or (3) upload a measurement from a ruler/scale."
    )


def _estimate_height_cm(length_cm: float, width_cm: float, contour_area_px: float, pixels_per_cm: float) -> float:
    if pixels_per_cm <= 0:
        return 0.0

    length_px = max(length_cm * pixels_per_cm, 1.0)
    width_px = max(width_cm * pixels_per_cm, 1.0)
    fill_ratio = float(np.clip(contour_area_px / (length_px * width_px), 0.0, 1.0))

    # A single image cannot infer depth exactly; this provides a conservative estimate.
    height_factor = float(np.clip(0.25 + (1.0 - fill_ratio) * 0.75, 0.2, 1.0))
    return round(min(length_cm, width_cm) * height_factor, 2)


def _build_isolated_preview(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    white_bg = np.full_like(image, 255)
    isolated = np.where(mask[:, :, None] == 255, image, white_bg)
    return isolated


def _build_background_preview(image: np.ndarray, object_mask: np.ndarray) -> np.ndarray:
    # Inpaint removes detected objects to show the scene background without them.
    return cv2.inpaint(image, object_mask, 7, cv2.INPAINT_TELEA)


def _is_circular(contour: np.ndarray) -> bool:
    """Check if a contour is approximately circular."""
    area = cv2.contourArea(contour)
    if area < 50:
        return False
    perimeter = cv2.arcLength(contour, True)
    if perimeter == 0:
        return False
    circularity = 4 * np.pi * area / (perimeter * perimeter)
    return circularity > 0.6


def _detect_reference_objects(
    contours: list[np.ndarray], pixels_per_cm: float, image_shape: tuple
) -> tuple[list[dict], dict | None]:
    """
    Detect if any contours match standard reference objects (coins, cards, door, sofa, TV, etc).
    Returns list of detected reference objects and best suggestion.
    """
    from ..schemas import DetectedObjectType

    REFERENCE_DATABASE = {
        "penny": {
            "diameter_cm": 1.905,
            "type": "coin",
            "tolerance": 0.25,
            "description": "US Penny (smallest, 1¢)",
            "emoji": "🪙",
        },
        "dime": {
            "diameter_cm": 1.791,
            "type": "coin",
            "tolerance": 0.25,
            "description": "US Dime",
            "emoji": "🪙",
        },
        "nickel": {
            "diameter_cm": 2.108,
            "type": "coin",
            "tolerance": 0.25,
            "description": "US Nickel",
            "emoji": "🪙",
        },
        "quarter": {
            "diameter_cm": 2.413,
            "type": "coin",
            "tolerance": 0.25,
            "description": "US Quarter",
            "emoji": "🪙",
        },
        "credit_card": {
            "width_cm": 8.56,
            "height_cm": 5.398,
            "type": "card",
            "tolerance": 0.15,
            "description": "Standard credit card",
            "emoji": "💳",
        },
        "passport": {
            "width_cm": 12.4,
            "height_cm": 8.8,
            "type": "card",
            "tolerance": 0.2,
            "description": "Passport size",
            "emoji": "🛂",
        },
        "door": {
            "height_cm": 210,
            "width_cm": 90,
            "tolerance": 0.2,
            "description": "Standard door height",
            "emoji": "🚪",
        },
        "sofa": {
            "width_cm": 200,
            "depth_cm": 85,
            "tolerance": 0.25,
            "description": "2-3 seater sofa width",
            "emoji": "🛋️",
        },
        "tv_55": {
            "width_cm": 122,
            "height_cm": 70,
            "tolerance": 0.15,
            "description": "55-inch TV screen",
            "emoji": "📺",
        },
        "table": {
            "height_cm": 75,
            "width_cm": 100,
            "tolerance": 0.2,
            "description": "Dining table height",
            "emoji": "🪑",
        },
    }

    detected = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 50:  # Skip very small contours
            continue

        (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(contour)
        obj_length_cm = max(rect_w, rect_h) / pixels_per_cm
        obj_width_cm = min(rect_w, rect_h) / pixels_per_cm
        is_circle = _is_circular(contour)

        # Try to match against standard objects
        for ref_type, ref_specs in REFERENCE_DATABASE.items():
            if ref_specs.get("type") == "coin" and is_circle:
                # Detect coins by diameter
                avg_diameter_cm = (obj_length_cm + obj_width_cm) / 2
                expected_diameter = ref_specs["diameter_cm"]
                diameter_match = abs(avg_diameter_cm - expected_diameter) / expected_diameter

                if diameter_match < ref_specs["tolerance"]:
                    detected.append(
                        {
                            "objectType": ref_type,
                            "confidence": max(0.7, 1.0 - diameter_match),
                            "standardDimension": expected_diameter,
                            "dimension": f"{expected_diameter} cm",
                            "reason": ref_specs["description"],
                        }
                    )

            elif ref_specs.get("type") == "card" and not is_circle:
                # Detect cards by aspect ratio
                width_match = abs(obj_length_cm - ref_specs["width_cm"]) / ref_specs["width_cm"]
                height_match = abs(obj_width_cm - ref_specs["height_cm"]) / ref_specs["height_cm"]

                if width_match < ref_specs["tolerance"] and height_match < ref_specs["tolerance"]:
                    detected.append(
                        {
                            "objectType": ref_type,
                            "confidence": max(0.7, 1.0 - (width_match + height_match) / 2),
                            "standardDimension": ref_specs["width_cm"],
                            "dimension": f"{ref_specs['width_cm']} cm × {ref_specs['height_cm']} cm",
                            "reason": ref_specs["description"],
                        }
                    )

            elif ref_type == "door":
                height_match = abs(obj_length_cm - ref_specs["height_cm"]) / ref_specs["height_cm"]
                width_match = abs(obj_width_cm - ref_specs["width_cm"]) / ref_specs["width_cm"]

                # Door is tall and narrow
                if height_match < ref_specs["tolerance"] and width_match < ref_specs["tolerance"]:
                    detected.append(
                        {
                            "objectType": "door",
                            "confidence": max(0.5, 1.0 - (height_match + width_match) / 2),
                            "standardDimension": ref_specs["height_cm"],
                            "dimension": f"{ref_specs['height_cm']} cm",
                            "reason": ref_specs["description"],
                        }
                    )

            elif ref_type == "sofa":
                width_match = abs(obj_length_cm - ref_specs["width_cm"]) / ref_specs["width_cm"]
                depth_match = abs(obj_width_cm - ref_specs["depth_cm"]) / ref_specs["depth_cm"]

                if width_match < ref_specs["tolerance"] and depth_match < ref_specs["tolerance"]:
                    detected.append(
                        {
                            "objectType": "sofa",
                            "confidence": max(0.5, 1.0 - (width_match + depth_match) / 2),
                            "standardDimension": ref_specs["width_cm"],
                            "dimension": f"{ref_specs['width_cm']} cm",
                            "reason": ref_specs["description"],
                        }
                    )

            elif ref_type == "tv_55":
                width_match = abs(obj_length_cm - ref_specs["width_cm"]) / ref_specs["width_cm"]
                height_match = abs(obj_width_cm - ref_specs["height_cm"]) / ref_specs["height_cm"]

                if width_match < ref_specs["tolerance"] and height_match < ref_specs["tolerance"]:
                    detected.append(
                        {
                            "objectType": "tv",
                            "confidence": max(0.5, 1.0 - (width_match + height_match) / 2),
                            "standardDimension": ref_specs["width_cm"],
                            "dimension": f"{ref_specs['width_cm']} cm",
                            "reason": ref_specs["description"],
                        }
                    )

    # Pick best match (highest confidence)
    best_match = max(detected, key=lambda x: x["confidence"]) if detected else None

    return detected, best_match


async def analyze_measurement(
    files: Iterable[UploadFile],
    project_name: str,
    reference_width_cm: float | None = None,
) -> MeasureResponse:
    from ..schemas import DetectedObjectType

    images: list[ImageMeasurement] = []

    for image_index, file in enumerate(files):
        content = await file.read()
        nparr = np.frombuffer(content, np.uint8)
        decoded = cv2.imdecode(nparr, cv2.COLOR_BGR2GRAY)

        if decoded is None:
            raise ValueError(f"Could not decode uploaded image: {file.filename}")

        contours = _extract_object_contours(decoded)
        
        # Estimate scale using a heuristic: assume smallest detected object might be ~2cm (e.g., coin)
        # This gives us a reasonable first guess
        pixels_per_cm = 1.0
        calibration_source = "unknown"
        
        if reference_width_cm and reference_width_cm > 0:
            # User provided manual scale
            if contours:
                reference_contour = max(contours, key=cv2.contourArea)
                (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(reference_contour)
                reference_pixels = max(rect_w, rect_h)
                if reference_pixels > 0:
                    pixels_per_cm = reference_pixels / reference_width_cm
                    calibration_source = "reference-width"
        else:
            # Try to auto-detect reference by finding small objects that match known sizes
            if contours:
                smallest_contour = min(contours, key=cv2.contourArea)
                (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(smallest_contour)
                smallest_pixels = max(rect_w, rect_h)
                
                # Assume smallest object is 1.5-2.5 cm (reasonable guess for coin/small card)
                if smallest_pixels > 0:
                    estimated_scale = smallest_pixels / 2.0  # Assume ~2cm
                    if 5 < estimated_scale < 2000:  # Sanity check
                        pixels_per_cm = estimated_scale
                        calibration_source = "auto-estimated"

        # Detect reference objects using calculated scale
        detected_refs, best_ref = _detect_reference_objects(contours, pixels_per_cm, decoded.shape)

        object_mask = np.zeros(decoded.shape[:2], dtype=np.uint8)
        objects: list[MeasurementObject] = []

        for object_index, contour in enumerate(contours):
            contour_area = cv2.contourArea(contour)
            if contour_area <= 0:
                continue

            current_mask = np.zeros(decoded.shape[:2], dtype=np.uint8)
            cv2.drawContours(current_mask, [contour], -1, 255, thickness=cv2.FILLED)
            object_mask = cv2.bitwise_or(object_mask, current_mask)

            (_, _), (rect_w, rect_h), _ = cv2.minAreaRect(contour)
            length_cm = round(max(rect_w, rect_h) / pixels_per_cm, 2)
            width_cm = round(min(rect_w, rect_h) / pixels_per_cm, 2)
            height_cm = _estimate_height_cm(length_cm, width_cm, contour_area, pixels_per_cm)

            isolated = _build_isolated_preview(decoded, current_mask)
            confidence = float(np.clip(0.55 + min(contour_area / (decoded.shape[0] * decoded.shape[1]), 0.35), 0.55, 0.95))

            objects.append(
                MeasurementObject(
                    id=f"{file.filename}-object-{object_index + 1}",
                    name=f"Object {object_index + 1}",
                    length=length_cm,
                    width=width_cm,
                    height=height_cm,
                    confidence=round(confidence, 2),
                    previewLabel="Isolated object on white background",
                    previewDataUrl=_encode_png_data_url(isolated),
                    isBackground=False,
                )
            )

        image_h, image_w = decoded.shape[:2]
        background_preview = _build_background_preview(decoded, object_mask)
        background = MeasurementObject(
            id=f"{file.filename}-background",
            name="Background",
            length=round(image_w / pixels_per_cm, 2),
            width=round(image_h / pixels_per_cm, 2),
            height=0.0,
            confidence=0.92 if contours else 0.45,
            previewLabel="Background without detected objects",
            previewDataUrl=_encode_png_data_url(background_preview),
            isBackground=True,
        )

        # Convert best_ref dict to DetectedObjectType if exists
        suggested_calibration = None
        if best_ref:
            suggested_calibration = DetectedObjectType(**best_ref)

        images.append(
            ImageMeasurement(
                imageName=file.filename,
                imageIndex=image_index,
                objects=objects,
                background=background,
                calibrationSource=calibration_source,
                pixelsPerCm=round(pixels_per_cm, 4),
                detectedReferenceObjects=[DetectedObjectType(**ref) for ref in detected_refs],
                suggestedCalibration=suggested_calibration,
            )
        )

    return MeasureResponse(
        measurementId=str(uuid.uuid4()),
        projectName=project_name,
        createdAt=datetime.now(timezone.utc),
        images=images,
    )
