export type MeasurementObject = {
  id: string;
  name: string;
  length: number;
  width: number;
  height: number;
  confidence: number;
  isBackground?: boolean;
  previewLabel: string;
  previewDataUrl?: string | null;
  selected?: boolean;
};

export type ImageMeasurement = {
  imageName: string;
  imageIndex: number;
  objects: MeasurementObject[];
  background: MeasurementObject;
  calibrationSource: string;
  pixelsPerCm: number;
  detectedReferenceObjects?: Array<{
    objectType: string;
    confidence: number;
    standardDimension: number;
    dimension: string;
    reason: string;
  }>;
  suggestedCalibration?: {
    objectType: string;
    confidence: number;
    standardDimension: number;
    dimension: string;
    reason: string;
  };
};

export type MeasureResponse = {
  measurementId: string;
  projectName: string;
  createdAt: string;
  images: ImageMeasurement[];
};

export type ProjectRecord = {
  id: string;
  name: string;
  createdAt: string;
  measurementId: string;
  selectedObjectIds: string[];
  summary: MeasureResponse;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const raw = await response.text();
    try {
      const parsed = JSON.parse(raw) as { detail?: string };
      throw new Error(parsed.detail || raw || 'Request failed');
    } catch {
      throw new Error(raw || 'Request failed');
    }
  }
  return response.json() as Promise<T>;
}

export async function measureImages(payload: {
  projectName: string;
  files: File[];
  userId?: string;
}): Promise<MeasureResponse> {
  const formData = new FormData();
  formData.append('project_name', payload.projectName);
  if (payload.userId) {
    formData.append('user_id', payload.userId);
  }

  payload.files.slice(0, 3).forEach((file) => {
    formData.append('files', file);
  });

  const response = await fetch(`${apiBaseUrl}/measure`, {
    method: 'POST',
    body: formData
  });

  return parseResponse<MeasureResponse>(response);
}

export async function saveProject(payload: {
  name: string;
  measurement: MeasureResponse;
  selectedObjectIds: string[];
}): Promise<ProjectRecord> {
  const response = await fetch(`${apiBaseUrl}/projects`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  return parseResponse<ProjectRecord>(response);
}

export async function fetchProject(projectId: string): Promise<ProjectRecord> {
  const response = await fetch(`${apiBaseUrl}/projects/${projectId}`, {
    cache: 'no-store'
  });

  return parseResponse<ProjectRecord>(response);
}

export async function fetchProjects(): Promise<ProjectRecord[]> {
  const response = await fetch(`${apiBaseUrl}/projects`, {
    cache: 'no-store'
  });

  return parseResponse<ProjectRecord[]>(response);
}
