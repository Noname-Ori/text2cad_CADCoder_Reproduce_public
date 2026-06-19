# Evaluation Protocol

This document describes the metrics implemented in `evaluate.py` for this released Text2CAD random100 benchmark package.

The goal of the script is to provide a reproducible geometry-based evaluation for one local generated STL file against one packaged reference sequence JSON. It is not an official implementation of any external paper's evaluation pipeline.

## Reference Geometry

Each sample has a sequence-derived ground-truth mesh:

```text
data/reference_sequence_gt/sequence_files/deepcad_cad_json/{index}_{cad_id}.json
```

The evaluator reconstructs the reference mesh from this packaged Text2CAD/DeepCAD token sequence JSON using Text2CAD/CadSeqProc.

This step requires a separately cloned upstream Text2CAD repository. Pass its path with `--text2cad-root` so the evaluator can import `CadSeqProc.cad_sequence.CADSequence`.

Let the reference mesh be:

\[
R
\]

and let the generated mesh be:

\[
G.
\]

If the generated STL cannot be loaded as a non-empty mesh, the pair is marked invalid.

## Valid / Total

The released script reports whether the provided pair is valid. Dataset-level Valid / Total is obtained by counting valid per-pair results over the evaluated STL files.

## Normalization and ICP Alignment

Before geometric comparison, both reference and generated meshes are scale-normalized. The scale factor is the global coordinate range:

\[
s(M)=\max(V_M)-\min(V_M),
\]

where \(V_M\) denotes all mesh vertex coordinates flattened across the three axes. Mesh vertices are divided by \(s(M)\) when \(s(M)>0\).

For paired metrics, the generated mesh is rigidly aligned to its paired reference using ICP:

1. Sample 8192 surface points from both meshes.
2. Downsample to 2048 points for ICP correspondence estimation.
3. Initialize by translating the generated point-cloud centroid to the reference centroid.
4. Iterate nearest-neighbor matching and Kabsch rigid alignment.
5. Apply the final rigid transform to the generated points and mesh.

No ICP scaling is applied.

Default paired ICP parameters:

```text
points = 8192
icp_points = 2048
icp_iterations = 50
tolerance = 1e-7
```

## Chamfer Distance

Chamfer Distance measures paired surface distance after ICP alignment.

Given two point clouds \(P\) and \(Q\):

\[
\operatorname{CD}(P,Q)=
\frac{1}{|P|}\sum_{p\in P}\min_{q\in Q}\|p-q\|_2^2+
\frac{1}{|Q|}\sum_{q\in Q}\min_{p\in P}\|q-p\|_2^2.
\]

The per-pair output column is `cd_x1e3`, multiplied by \(10^3\). Dataset-level CD mean and median are obtained by aggregating `cd_x1e3` over valid pairs.

## Solid Mesh IoU

Solid IoU measures paired volumetric overlap after ICP alignment.

The aligned generated mesh and reference mesh are voxelized in a shared bounding box with a \(32^3\) grid. Let \(V_R\) and \(V_G\) be the occupied solid voxel sets:

\[
\operatorname{IoU}(R,G)=\frac{|V_R\cap V_G|}{|V_R\cup V_G|}.
\]

The per-pair output column is:

- `solid_iou_32`: per-sample IoU.

Dataset-level Solid IoU mean and median are obtained by aggregating `solid_iou_32` over valid pairs.

## Output Files

Running:

```bash
python evaluation_code/evaluate.py \
  --reference-json data/reference_sequence_gt/sequence_files/deepcad_cad_json/001_00702684.json \
  --generated-stl /path/to/generated/001_00702684.stl \
  --output-dir evaluation_outputs/example_001 \
  --text2cad-root /path/to/Text2CAD
```

creates:

- `pair_metrics.csv`
- `metrics.xlsx`
- `metric_run_metadata.json`

These generated outputs are written under the chosen output directory.
