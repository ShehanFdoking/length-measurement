"""
Depth-map fusion for 3D room reconstruction from 3 images.
- Uses MiDaS for depth estimation
- Fuses depth maps into a point cloud
- Generates mesh using marching cubes
- Exports GLB format
"""

from __future__ import annotations

import io
import tempfile
import os
from typing import Optional

import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
from skimage.measure import marching_cubes
import trimesh

# Disable interactive torch hub prompts
os.environ['TORCH_HOME'] = os.path.expanduser('~/.cache/torch')
os.environ['TORCHHUB_HOME'] = os.path.expanduser('~/.cache/torch/hub')

# Pre-trust MiDaS repo
def _setup_midas_trust():
    """Auto-trust MiDaS repo to avoid interactive prompts."""
    try:
        hub_dir = torch.hub.get_dir()
        whitelist_file = os.path.join(hub_dir, 'midas_trusted.txt')
        if not os.path.exists(whitelist_file):
            os.makedirs(hub_dir, exist_ok=True)
            with open(whitelist_file, 'w') as f:
                f.write('intel-isl/MiDaS\n')
    except Exception:
        pass

_setup_midas_trust()


def load_midas_model(device: str = "cpu") -> tuple:
    """Load MiDaS depth estimation model.
    
    Returns (model, transform) tuple.
    """
    try:
        # Use MiDaS small model (faster, lower VRAM)
        midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", pretrained=True)
        midas.eval()
        midas.to(device)
        
        # Load corresponding transform
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        transform = midas_transforms.small_transform
        
        return midas, transform, device
    except Exception as e:
        raise RuntimeError(f"Failed to load MiDaS model: {e}")


def estimate_depth(
    image_path_or_array: str | np.ndarray,
    model: torch.nn.Module,
    transform,
    device: str = "cpu",
) -> np.ndarray:
    """Estimate depth map from image using MiDaS.
    
    Args:
        image_path_or_array: file path or np.ndarray (H,W,3) uint8 BGR
        model: MiDaS model
        transform: MiDaS transform
        device: 'cpu' or 'cuda'
    
    Returns:
        Normalized depth map (H,W) float32, range [0, 1]
    """
    if isinstance(image_path_or_array, str):
        img = cv2.imread(image_path_or_array)
        if img is None:
            raise ValueError(f"Could not load image: {image_path_or_array}")
    else:
        img = image_path_or_array
    
    # Downsample for faster processing (MiDaS will upscale anyway)
    h, w = img.shape[:2]
    if max(h, w) > 640:
        scale = 640 / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        img = cv2.resize(img, (new_w, new_h))
        h, w = new_h, new_w
    
    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Apply MiDaS transform
    print(f"[3D] Running depth inference on {h}x{w} image...")
    input_batch = transform(img_rgb).to(device)
    
    with torch.no_grad():
        prediction = model(input_batch)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=(h, w),
            mode="bicubic",
            align_corners=False,
        ).squeeze()
    
    # Normalize depth to [0, 1]
    depth = prediction.cpu().numpy()
    depth_min, depth_max = depth.min(), depth.max()
    if depth_max > depth_min:
        depth = (depth - depth_min) / (depth_max - depth_min)
    else:
        depth = np.zeros_like(depth)
    
    print(f"[3D] Depth map shape: {depth.shape}")
    return depth.astype(np.float32)


def depth_to_pointcloud(
    depth: np.ndarray,
    image: np.ndarray,
    focal_length: float,
    principal_point: tuple[float, float] | None = None,
) -> np.ndarray:
    """Convert depth map to point cloud with color.
    
    Args:
        depth: (H,W) normalized depth map [0,1]
        image: (H,W,3) color image for texture
        focal_length: focal length in pixels (estimated from image height)
        principal_point: (cx, cy) or None (uses image center)
    
    Returns:
        Points array (N,3) in meters (scale assumes depth_max ~5m)
    """
    h, w = depth.shape
    
    if principal_point is None:
        cx, cy = w / 2.0, h / 2.0
    else:
        cx, cy = principal_point
    
    # Create coordinate grids
    x = np.arange(w) - cx
    y = np.arange(h) - cy
    xx, yy = np.meshgrid(x, y)
    
    # Scale depth to meters (assume normalized depth 0-1 maps to 0-5m)
    depth_meters = depth * 5.0
    
    # Back-project to 3D
    z = depth_meters
    x_3d = (xx * z) / focal_length
    y_3d = (yy * z) / focal_length
    
    # Stack into point cloud
    points = np.stack([x_3d, y_3d, z], axis=-1).reshape(-1, 3)
    
    # Filter out points too close or too far (invalid depth)
    mask = (z.flatten() > 0.1) & (z.flatten() < 10.0)
    points = points[mask]
    
    return points


def align_pointclouds(
    pcs: list[np.ndarray],
    max_correspondence_distance: float = 0.1,
) -> np.ndarray:
    """Simple point cloud alignment via merging and deduplication.
    
    For simplicity, this just merges point clouds and removes nearby duplicates.
    
    Args:
        pcs: list of (N,3) point clouds
        max_correspondence_distance: merge radius
    
    Returns:
        Merged and deduplicated point cloud (M,3)
    """
    # Simple merge: concatenate all point clouds
    merged = np.vstack(pcs) if pcs else np.zeros((0, 3))
    
    if merged.shape[0] == 0:
        return merged
    
    print(f"[3D] Merged {len(pcs)} clouds: {merged.shape[0]} total points")
    
    # Subsample for speed (keep only unique)
    # Use spatial hashing instead of pairwise distance for speed
    rounded = np.round(merged / max_correspondence_distance).astype(int)
    _, unique_idx = np.unique(rounded, axis=0, return_index=True)
    unique_points = merged[unique_idx]
    
    print(f"[3D] After dedup: {unique_points.shape[0]} points")
    return unique_points


def pointcloud_to_mesh(
    points: np.ndarray,
    grid_size: int = 32,  # Reduced from 64 for speed
) -> trimesh.Trimesh:
    """Generate mesh from point cloud using marching cubes.
    
    Args:
        points: (N,3) point cloud
        grid_size: resolution of voxel grid (default 32 for speed)
    
    Returns:
        trimesh.Trimesh object
    """
    if points.shape[0] < 10:
        # Not enough points; return empty mesh
        return trimesh.Trimesh(vertices=[], faces=[])
    
    # Create voxel grid
    min_pt = points.min(axis=0)
    max_pt = points.max(axis=0)
    
    # Pad bounds slightly
    pad = 0.1 * (max_pt - min_pt).max()
    min_pt -= pad
    max_pt += pad
    
    # Create 3D grid
    grid = np.zeros((grid_size, grid_size, grid_size), dtype=np.float32)
    
    # Rasterize points into grid (simple count, no Gaussian)
    scale = (grid_size - 1) / (max_pt - min_pt + 1e-6)
    indices = ((points - min_pt) * scale).astype(int)
    indices = np.clip(indices, 0, grid_size - 1)
    
    # Fast rasterization
    for idx in indices:
        grid[idx[0], idx[1], idx[2]] += 1.0
    
    print("[3D] Running marching cubes...")
    # Marching cubes
    try:
        result = marching_cubes(grid, level=grid.max() * 0.2)
        # Handle both old (2-value) and new (4-value) scikit-image returns
        if len(result) == 4:
            vertices, faces, normals, values = result
        else:
            vertices, faces = result
        
        # Transform vertices back to world coords
        vertices = vertices / scale + min_pt
        
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        mesh.remove_degenerate_faces()
        
        print(f"[3D] Mesh generated: {len(vertices)} vertices, {len(faces)} faces")
        return mesh
    except Exception as e:
        print(f"[3D] Marching cubes failed: {e}")
        return trimesh.Trimesh(vertices=[], faces=[])


def generate_3d_room_from_depths(
    image_bytes_list: list[bytes],
    room_length_m: float,
    room_width_m: float,
    room_height_m: float,
    device: str = "cpu",
) -> bytes:
    """Generate GLB mesh from 3 image depth maps.
    
    Args:
        image_bytes_list: list of 3 image byte buffers (JPEG/PNG)
        room_length_m, room_width_m, room_height_m: reference dimensions
        device: 'cpu' or 'cuda'
    
    Returns:
        GLB file bytes
    """
    if len(image_bytes_list) != 3:
        raise ValueError("Exactly 3 images required")
    
    print("[3D] Loading MiDaS model...")
    model, transform, dev = load_midas_model(device)
    
    print("[3D] Estimating depth maps...")
    point_clouds = []
    for i, img_bytes in enumerate(image_bytes_list):
        # Load image from bytes
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            print(f"[3D] Skipping image {i}: decode failed")
            continue
        
        # Estimate depth
        depth = estimate_depth(img, model, transform, device=dev)
        
        # Estimate focal length (simple heuristic)
        h, w = img.shape[:2]
        focal_length = w  # approx focal length
        
        # Back-project to 3D
        pc = depth_to_pointcloud(depth, img, focal_length)
        point_clouds.append(pc)
    
    if not point_clouds:
        raise ValueError("No valid images for 3D reconstruction")
    
    print(f"[3D] Aligning {len(point_clouds)} point clouds...")
    merged_pc = align_pointclouds(point_clouds)
    
    print(f"[3D] Merged cloud has {merged_pc.shape[0]} points")
    
    if merged_pc.shape[0] < 10:
        raise ValueError("Insufficient points after fusion")
    
    print("[3D] Generating mesh...")
    mesh = pointcloud_to_mesh(merged_pc, grid_size=64)
    
    # Apply room scale hint (scale mesh to match reference dimensions)
    if mesh.vertices.size > 0:
        mesh_extent = mesh.bounds[1] - mesh.bounds[0]
        target_extent = np.array([room_length_m, room_width_m, room_height_m])
        
        # Scale non-zero dimensions
        scale_factors = []
        for i in range(3):
            if mesh_extent[i] > 1e-3:
                scale_factors.append(target_extent[i] / mesh_extent[i])
            else:
                scale_factors.append(1.0)
        
        mesh.apply_scale(scale_factors)
    
    print("[3D] Exporting GLB...")
    
    # Export to GLB
    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
        mesh.export(f.name, file_type="glb")
        with open(f.name, "rb") as glb_file:
            glb_bytes = glb_file.read()
    
    return glb_bytes
