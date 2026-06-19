# Sequence-GT Reference Files

This folder contains the sequence-derived reference files for the selected 100 samples.

Reference policy:

- Reference geometry comes from the Text2CAD/DeepCAD token sequence.
- The evaluator reconstructs meshes from the packaged sequence JSON using upstream Text2CAD/CadSeqProc.

Contents:

- `sequence_files/deepcad_cad_json/`: token sequence JSON files used as the evaluation ground truth.
- `sequence_files/deepcad_cad_vec/`: matching H5 vector sequence files.
- `sequence_files/prompt_json/`: prompt JSON files for the same 100 samples.
- `sequence_gt_reference_manifest.csv`: one row per sample with relative packaged paths.

Evaluation uses the packaged Text2CAD/DeepCAD token sequence JSON with upstream Text2CAD/CadSeqProc.
