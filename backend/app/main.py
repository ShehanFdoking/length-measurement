from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from .schemas import MeasureResponse, ProjectCreateRequest, ProjectRecord
from .services.measurement_room import analyze_room_measurement
from .services.storage import get_project, load_projects, save_project
from .services.room_3d import generate_room_box_zip
from .services.room_3d_depth import generate_3d_room_from_depths
from pydantic import BaseModel
import io
from fastapi.responses import StreamingResponse, FileResponse

app = FastAPI(title="Length Lab API", version="1.0.0")

origins = [
    origin.strip()
    for origin in os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/measure", response_model=MeasureResponse)
async def measure_images(
    project_name: Annotated[str, Form(...)],
    files: Annotated[list[UploadFile], File(...)],
    user_id: Annotated[str | None, Form()] = None,
) -> MeasureResponse:
    if len(files) != 3:
        raise HTTPException(status_code=400, detail="Upload exactly 3 images to generate a single fused 3D room view.")

    try:
        measurement = await analyze_room_measurement(
            files,
            project_name,
        )
        return measurement
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/projects", response_model=list[ProjectRecord])
def list_projects() -> list[ProjectRecord]:
    return load_projects()


@app.get("/projects/{project_id}", response_model=ProjectRecord)
def read_project(project_id: str) -> ProjectRecord:
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@app.post("/projects", response_model=ProjectRecord)
def create_project(payload: ProjectCreateRequest) -> ProjectRecord:
    record = ProjectRecord(
        id=str(uuid.uuid4()),
        name=payload.name,
        createdAt=datetime.now(timezone.utc),
        measurementId=payload.measurement.measurementId,
        selectedObjectIds=payload.selectedObjectIds,
        summary=payload.measurement,
        userId=payload.userId,
    )
    return save_project(record)


class Room3DRequest(BaseModel):
    length_m: float
    width_m: float
    height_m: float
    backgroundDataUrl: str | None = None


@app.post("/measure/3d")
def measure_3d(payload: Room3DRequest):
    """Return a ZIP file containing a simple OBJ/MTL room mesh generated from dimensions.

    Accepts JSON with `length_m`, `width_m`, `height_m` and optional `backgroundDataUrl` (data URL).
    """
    zip_bytes = generate_room_box_zip(payload.length_m, payload.width_m, payload.height_m, payload.backgroundDataUrl)
    return StreamingResponse(io.BytesIO(zip_bytes), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=room3d.zip"})


@app.post("/measure/3d/depth")
async def measure_3d_depth(
    files: Annotated[list[UploadFile], File(...)],
    length_m: Annotated[float, Form(...)],
    width_m: Annotated[float, Form(...)],
    height_m: Annotated[float, Form(...)],
    device: Annotated[str, Form(...)] = "cpu",
):
    """Generate a 3D room model using MiDaS depth estimation + point cloud fusion.

    Accepts 3 images and room dimensions. Returns GLB file.
    Optional `device` parameter: "cpu" (default) or "cuda" for GPU acceleration.
    """
    if len(files) != 3:
        raise HTTPException(status_code=400, detail="Upload exactly 3 images for 3D depth fusion.")
    
    try:
        # Read image bytes
        image_bytes = []
        for file in files:
            content = await file.read()
            image_bytes.append(content)
        
        # Generate 3D model in thread pool to avoid blocking
        glb_bytes = await run_in_threadpool(
            generate_3d_room_from_depths,
            image_bytes,
            float(length_m),
            float(width_m),
            float(height_m),
            device,
        )
        
        return StreamingResponse(
            io.BytesIO(glb_bytes),
            media_type="model/gltf-binary",
            headers={"Content-Disposition": "attachment; filename=room3d.glb"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"3D generation failed: {str(exc)}") from exc
