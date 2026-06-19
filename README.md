# Text2CAD Random-100 Public Generation and Evaluation Package

This package contains the public inputs, lightweight runner code, reference files, and evaluation code used for the selected 100 Text2CAD v1.1 samples.

## Package Contents

- `data/prompts/`: prompt text for the 100 samples at all available language levels.
- `data/reference_sequence_gt/`: sequence ground-truth files used to reconstruct reference geometry.
- `code/text2cad/`: lightweight scripts that prepare Text2CAD prompt/config files and call an external official Text2CAD checkout.
- `code/cadcoder/`: minimal inference runner that adapts external prompts for `gudo7208/CAD-Coder` and exports the generated CadQuery outputs to STEP/STL.
- `evaluation_code/`: open per-pair evaluation entry point, metric definitions, and Python requirements.
- `DATA_PROVENANCE.md`: subset provenance, reference policy, and release notes.

## Evaluation

The evaluator computes the per-sample metrics used in the public table for one generated STL and one packaged reference sequence JSON:

- CD
- Solid IoU

Reference meshes are reconstructed from:

```text
data/reference_sequence_gt/sequence_files/deepcad_cad_json/
```

using the upstream Text2CAD/CadSeqProc code.

Install the Python dependencies:

```bash
conda create -n text2cad_eval python=3.10
conda activate text2cad_eval
conda install -c conda-forge pythonocc-core
pip install -r evaluation_code/requirements.txt
pip install loguru
```

Clone the upstream Text2CAD repository separately and pass its path with `--text2cad-root`:

```bash
git clone https://github.com/SadilKhan/Text2CAD.git /path/to/Text2CAD
```

Run the evaluator on a generated STL and the matching packaged sequence JSON:

```bash
python evaluation_code/evaluate.py \
  --reference-json data/reference_sequence_gt/sequence_files/deepcad_cad_json/001_00702684.json \
  --generated-stl /path/to/generated/001_00702684.stl \
  --output-dir evaluation_outputs/example_001 \
  --text2cad-root /path/to/Text2CAD
```

The script writes `pair_metrics.csv`, `metrics.xlsx`, and run metadata under the chosen output directory. Dataset-level Valid/Total, CD mean/median, and Solid IoU mean/median are obtained by aggregating per-sample outputs over the generated STL files being evaluated.

## Text2CAD/CadSeqProc Dependency

Reference mesh reconstruction depends on the upstream Text2CAD `CadSeqProc` module. The evaluator imports:

```python
from CadSeqProc.cad_sequence import CADSequence
from CadSeqProc.utility.macro import MAX_CAD_SEQUENCE_LENGTH, N_BIT
```

and uses `CADSequence.json_to_vec(...)` and `CADSequence.from_vec(...).create_cad_model().create_mesh()` to reconstruct reference meshes from the packaged sequence JSON files.

For evaluation, the Text2CAD source checkout is needed for `CadSeqProc`; the Text2CAD checkpoint and dataset files are only needed if you also rerun the Text2CAD baseline generation workflow.

## Generation Runners

### Text2CAD Baseline

See `code/text2cad/README.md` for the runnable Text2CAD wrapper workflow. The official Text2CAD source code, dataset files, and checkpoint must be obtained separately according to their license and distribution terms.

### CAD-Coder Baseline

See `code/cadcoder/README.md` for the CAD-Coder runner workflow. The complete `gudo7208/CAD-Coder` model must be obtained separately. The included helper `scripts/build_text2cad_random100_jsonl_from_prompts_csv.py` converts this package's `data/prompts/prompts.csv` into the CAD-Coder JSONL input format.

Note that there are multiple projects named "CAD-Coder". This package is for the text-to-CAD CadQuery model `gudo7208/CAD-Coder`.

## Upstream Resources

This package depends on upstream projects and models that must be downloaded separately:

| Component | What to download | Upstream link |
| --- | --- | --- |
| Text2CAD source code | Official Text2CAD repository | https://github.com/SadilKhan/Text2CAD |
| Text2CAD data | Text2CAD Hugging Face dataset page | https://huggingface.co/datasets/SadilKhan/Text2CAD |
| CAD-Coder complete model | `gudo7208/CAD-Coder` Hugging Face model repository | https://huggingface.co/gudo7208/CAD-Coder |
| CAD-Coder dataset format reference | CAD-Coder Hugging Face dataset page, used only as a reference for input/prompt formatting | https://huggingface.co/datasets/gudo7208/CAD-Coder |

## Release Scope

This is a compact reproduction package, not a complete standalone redistribution of the upstream projects.

Included:

- the selected random-100 prompts;
- sequence-ground-truth reference files for the same 100 samples;
- wrapper scripts for preparing Text2CAD inference inputs;
- runner scripts for preparing and running CAD-Coder baseline generation;
- an evaluation script for computing per-sample CD and Solid IoU.

Not included:

- official Text2CAD source code or checkpoints;
- CAD-Coder model files;
- generated geometry outputs.

Text2CAD baseline generation was run in a Windows environment. CAD-Coder baseline generation was run on a Linux server environment.
