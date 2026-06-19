from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree


CADSequence = None
MAX_CAD_SEQUENCE_LENGTH = None
N_BIT = None


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, sheets: dict[str, list[dict]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False)


def normalize_mesh_scale_only(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh = mesh.copy()
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    scale = float(np.max(vertices) - np.min(vertices))
    if scale > 0:
        mesh.vertices = vertices / scale
    return mesh


def configure_text2cad(text2cad_root: Path | None) -> None:
    global CADSequence, MAX_CAD_SEQUENCE_LENGTH, N_BIT
    if CADSequence is not None:
        return

    candidates: list[Path] = []
    if text2cad_root is not None:
        candidates.append(text2cad_root)
    env_root = os.environ.get("TEXT2CAD_ROOT")
    if env_root:
        candidates.append(Path(env_root))

    for root in candidates:
        sys.path.append(str(root))
        sys.path.append(str(root / "Cad_VLM"))

    try:
        from CadSeqProc.cad_sequence import CADSequence as _CADSequence
        from CadSeqProc.utility.macro import MAX_CAD_SEQUENCE_LENGTH as _MAX_CAD_SEQUENCE_LENGTH
        from CadSeqProc.utility.macro import N_BIT as _N_BIT
    except ModuleNotFoundError as exc:
        hint = (
            "Text2CAD/CadSeqProc is required to reconstruct reference meshes from the packaged "
            "sequence JSON files. Clone the upstream Text2CAD project and pass --text2cad-root PATH, "
            "or set TEXT2CAD_ROOT."
        )
        raise ModuleNotFoundError(hint) from exc

    CADSequence = _CADSequence
    MAX_CAD_SEQUENCE_LENGTH = _MAX_CAD_SEQUENCE_LENGTH
    N_BIT = _N_BIT


def load_sequence_json_mesh(path: Path) -> trimesh.Trimesh:
    if CADSequence is None or MAX_CAD_SEQUENCE_LENGTH is None or N_BIT is None:
        raise RuntimeError("Text2CAD/CadSeqProc is not configured")
    data = json.loads(path.read_text(encoding="utf-8"))
    _, cad_vec, _, _ = CADSequence.json_to_vec(
        data=data,
        bit=N_BIT,
        padding=True,
        max_cad_seq_len=MAX_CAD_SEQUENCE_LENGTH,
    )
    vec = cad_vec.numpy() if hasattr(cad_vec, "numpy") else np.asarray(cad_vec)
    cad = CADSequence.from_vec(vec, bit=N_BIT, post_processing=True).create_cad_model().create_mesh()
    mesh = cad.mesh
    if mesh is None or mesh.is_empty or len(mesh.faces) == 0:
        raise RuntimeError(f"empty sequence mesh: {path}")
    return normalize_mesh_scale_only(mesh)


def load_stl_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(str(path), force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if mesh.is_empty or len(mesh.faces) == 0:
        raise RuntimeError(f"empty mesh: {path}")
    return normalize_mesh_scale_only(mesh)


def sample_surface_points(mesh: trimesh.Trimesh, n_points: int, seed: int) -> np.ndarray:
    np.random.seed(seed)
    points, _ = trimesh.sample.sample_surface(mesh, n_points)
    return np.asarray(points, dtype=np.float64)


def downsample(points: np.ndarray, max_points: int, rng: np.random.Generator) -> np.ndarray:
    if len(points) <= max_points:
        return points.copy()
    indices = rng.choice(len(points), size=max_points, replace=False)
    return points[indices].copy()


def kabsch(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    src_centroid = source.mean(axis=0)
    tgt_centroid = target.mean(axis=0)
    src_centered = source - src_centroid
    tgt_centered = target - tgt_centroid
    h = src_centered.T @ tgt_centered
    u, _, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = tgt_centroid - src_centroid @ r.T
    return r, t


def apply_transform_points(points: np.ndarray, r: np.ndarray, t: np.ndarray) -> np.ndarray:
    return points @ r.T + t


def apply_transform_mesh(mesh: trimesh.Trimesh, r: np.ndarray, t: np.ndarray) -> trimesh.Trimesh:
    aligned = mesh.copy()
    aligned.vertices = apply_transform_points(np.asarray(aligned.vertices, dtype=np.float64), r, t)
    return aligned


def rigid_icp_transform(
    source_eval: np.ndarray,
    target_eval: np.ndarray,
    *,
    iterations: int,
    tolerance: float,
    icp_points: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, float, int]:
    rng = np.random.default_rng(seed)
    source = downsample(source_eval, icp_points, rng)
    target = downsample(target_eval, icp_points, rng)

    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    transformed = source - source_center + target_center
    total_r = np.eye(3)
    total_t = target_center - source_center
    prev_error = np.inf

    for iteration in range(iterations):
        tree = cKDTree(target)
        distances, indices = tree.query(transformed)
        matched = target[indices]
        r, t = kabsch(transformed, matched)
        transformed = apply_transform_points(transformed, r, t)
        total_r = r @ total_r
        total_t = t + total_t @ r.T
        mean_error = float(np.mean(distances))
        if abs(prev_error - mean_error) < tolerance:
            break
        prev_error = mean_error

    return total_r, total_t, prev_error, iteration + 1


def chamfer_dist(a: np.ndarray, b: np.ndarray) -> float:
    b_tree = cKDTree(b)
    a_to_b, _ = b_tree.query(a)
    a_tree = cKDTree(a)
    b_to_a, _ = a_tree.query(b)
    return float(np.mean(np.square(a_to_b)) + np.mean(np.square(b_to_a)))


def voxel_indices(mesh: trimesh.Trimesh, pitch: float, mins: np.ndarray, resolution: int) -> set[tuple[int, int, int]]:
    vox = mesh.voxelized(pitch).fill()
    points = np.asarray(vox.points, dtype=np.float64)
    if len(points) == 0:
        return set()
    coords = np.floor((points - mins) / pitch).astype(np.int64)
    coords = np.clip(coords, 0, resolution - 1)
    return set(map(tuple, coords))


def solid_mesh_iou(ref_mesh: trimesh.Trimesh, gen_mesh: trimesh.Trimesh, resolution: int) -> tuple[float, int, int]:
    bounds = np.vstack([ref_mesh.bounds, gen_mesh.bounds])
    mins = bounds.min(axis=0)
    maxs = bounds.max(axis=0)
    span = float(np.max(maxs - mins))
    if span <= 0:
        raise RuntimeError("degenerate union bounds")
    pitch = span / resolution
    ref_voxels = voxel_indices(ref_mesh, pitch, mins, resolution)
    gen_voxels = voxel_indices(gen_mesh, pitch, mins, resolution)
    intersection = len(ref_voxels & gen_voxels)
    union = len(ref_voxels | gen_voxels)
    return float(intersection / union) if union else 0.0, intersection, union


def infer_seed(reference_json: Path, seed: int | None) -> int:
    if seed is not None:
        return seed
    index_text = reference_json.stem.split("_", 1)[0]
    if index_text.isdigit():
        return 20260612 + int(index_text)
    return 20260612


def evaluate_pair(args: argparse.Namespace) -> dict:
    reference_json = args.reference_json.resolve()
    generated_stl = args.generated_stl.resolve()
    seed = infer_seed(reference_json, args.seed)

    row: dict = {
        "reference_json": str(reference_json),
        "generated_stl": str(generated_stl),
        "status": "valid",
        "cd_x1e3": "",
        "solid_iou_32": "",
        "error": "",
    }

    ref_mesh = load_sequence_json_mesh(reference_json)

    try:
        gen_mesh = load_stl_mesh(generated_stl)
        ref_eval_points = sample_surface_points(ref_mesh, args.points, seed)
        gen_eval_points = sample_surface_points(gen_mesh, args.points, seed + 17)
        r, t, _, icp_iterations_used = rigid_icp_transform(
            gen_eval_points,
            ref_eval_points,
            iterations=args.icp_iterations,
            tolerance=args.tolerance,
            icp_points=args.icp_points,
            seed=seed,
        )
        aligned_eval_points = apply_transform_points(gen_eval_points, r, t)
        aligned_mesh = apply_transform_mesh(gen_mesh, r, t)
        cd = chamfer_dist(ref_eval_points, aligned_eval_points) * 1000.0
        iou, intersection, union = solid_mesh_iou(ref_mesh, aligned_mesh, args.voxel_resolution)
        row.update(
            {
                "cd_x1e3": float(cd),
                "solid_iou_32": float(iou),
                "icp_iterations_used": icp_iterations_used,
                "solid_iou_intersection": intersection,
                "solid_iou_union": union,
            }
        )
    except Exception as exc:
        row["status"] = "invalid"
        row["error"] = f"{type(exc).__name__}: {exc}"

    return row


def write_outputs(output_dir: Path, row: dict, args: argparse.Namespace) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "pair_metrics.csv", [row])
    write_xlsx(output_dir / "metrics.xlsx", {"pair": [row]})
    metadata = {
        "metric_policy": "Reference geometry is reconstructed from packaged Text2CAD/DeepCAD sequence JSON with Text2CAD/CadSeqProc. The generated STL is scale-normalized and rigidly ICP-aligned before CD/IoU.",
        "parameters": {
            "reference_json": str(args.reference_json.resolve()),
            "generated_stl": str(args.generated_stl.resolve()),
            "text2cad_root": str(args.text2cad_root.resolve()) if args.text2cad_root else os.environ.get("TEXT2CAD_ROOT", ""),
            "points": args.points,
            "icp_points": args.icp_points,
            "icp_iterations": args.icp_iterations,
            "voxel_resolution": args.voxel_resolution,
            "tolerance": args.tolerance,
            "seed": infer_seed(args.reference_json.resolve(), args.seed),
        },
    }
    (output_dir / "metric_run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one generated STL against one packaged Text2CAD sequence JSON reference.")
    parser.add_argument("--reference-json", type=Path, required=True, help="Packaged sequence JSON reference file.")
    parser.add_argument("--generated-stl", type=Path, required=True, help="Generated STL file to evaluate.")
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation_outputs"))
    parser.add_argument(
        "--text2cad-root",
        type=Path,
        default=None,
        help="Path to an upstream Text2CAD checkout. Can also be provided with TEXT2CAD_ROOT.",
    )
    parser.add_argument("--points", type=int, default=8192)
    parser.add_argument("--icp-points", type=int, default=2048)
    parser.add_argument("--icp-iterations", type=int, default=50)
    parser.add_argument("--voxel-resolution", type=int, default=32)
    parser.add_argument("--tolerance", type=float, default=1e-7)
    parser.add_argument("--seed", type=int, default=None, help="Optional sampling seed. By default, the seed is inferred from the reference filename index.")
    args = parser.parse_args()

    configure_text2cad(args.text2cad_root)
    row = evaluate_pair(args)
    write_outputs(args.output_dir.resolve(), row, args)
    print(args.output_dir.resolve() / "pair_metrics.csv", flush=True)
    print(pd.DataFrame([row]).to_string(index=False), flush=True)
    if row["status"] != "valid":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
