from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DetectedObjectType(BaseModel):
    """Detected object type with standard reference dimension"""
    objectType: str  # e.g., "door", "sofa", "tv"
    confidence: float = Field(..., ge=0, le=1)
    standardDimension: float  # in cm (e.g., 210 for standard door height)
    dimension: str  # human readable (e.g., "210 cm")
    reason: str  # why this is a good reference


class MeasurementObject(BaseModel):
    id: str
    name: str
    length: float = Field(..., ge=0)
    width: float = Field(..., ge=0)
    height: float = Field(..., ge=0)
    confidence: float = Field(..., ge=0, le=1)
    previewLabel: str
    previewDataUrl: str | None = None
    isBackground: bool = False


class ImageMeasurement(BaseModel):
    imageName: str
    imageIndex: int
    objects: List[MeasurementObject]
    background: MeasurementObject
    calibrationSource: str
    pixelsPerCm: float = Field(..., gt=0)
    detectedReferenceObjects: List[DetectedObjectType] = []  # Auto-detected standard objects
    suggestedCalibration: Optional[DetectedObjectType] = None  # Best suggestion


class MeasureResponse(BaseModel):
    measurementId: str
    projectName: str
    createdAt: datetime
    images: List[ImageMeasurement]


class ProjectCreateRequest(BaseModel):
    name: str
    measurement: MeasureResponse
    selectedObjectIds: List[str]
    userId: Optional[str] = None


class ProjectRecord(BaseModel):
    id: str
    name: str
    createdAt: datetime
    measurementId: str
    selectedObjectIds: List[str]
    summary: MeasureResponse
    userId: Optional[str] = None
