from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import MeasureResponse, ProjectCreateRequest, ProjectRecord
from app.services.measurement import analyze_measurement
from app.services.storage import get_project, load_projects, save_project

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
    reference_width_cm: Annotated[float | None, Form()] = None,
    user_id: Annotated[str | None, Form()] = None,
) -> MeasureResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one image.")

    if len(files) > 3:
        raise HTTPException(status_code=400, detail="You can upload up to 3 images.")

    try:
        measurement = await analyze_measurement(
            files,
            project_name,
            reference_width_cm=reference_width_cm,
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
