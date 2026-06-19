# Data Provenance

This repository packages a 100-sample subset derived from Text2CAD v1.1 for geometry evaluation.

## Sample Subset

- Source dataset: Text2CAD v1.1 local public dataset copy.
- Subset name: Text2CAD random100 v1.1.
- Sample count: 100.
- Original sampling seed: `20260610`.
- One originally sampled CAD id, `00780606`, failed native DeepCAD STEP export in the prepared local subset and was replaced by verified candidate `00206843`.

## Reference Policy

The default evaluator uses sequence-derived reference geometry reconstructed from:

```text
data/reference_sequence_gt/sequence_files/deepcad_cad_json/
```

These JSON files are converted to meshes with the upstream Text2CAD/CadSeqProc code at evaluation time and used as the evaluation reference.

The upstream Text2CAD repository is not redistributed in this package. Pass a local Text2CAD checkout to the evaluator with `--text2cad-root`.

## Prompt Text

Prompt text is released under:

```text
data/prompts/
```

The files include the available prompt levels for each sample:

- `abstract`
- `description`
- `beginner`
- `intermediate`
- `expert`
- `all_level_data`
- `nli_data`

The `intermediate` and `expert` fields are the main prompt levels used by the reproduced generation workflows.

## Local Generated Results

To evaluate a local generated STL output, pair it with the matching packaged sequence JSON:

```text
data/reference_sequence_gt/sequence_files/deepcad_cad_json/{index}_{cad_id}.json
/path/to/generated/{index}_{cad_id}.stl
```

and pass both files to:

```bash
python evaluation_code/evaluate.py \
  --reference-json data/reference_sequence_gt/sequence_files/deepcad_cad_json/001_00702684.json \
  --generated-stl /path/to/generated/001_00702684.stl \
  --output-dir evaluation_outputs/example_001 \
  --text2cad-root /path/to/Text2CAD
```


## Evaluation Outputs

The evaluator writes `pair_metrics.csv`, `metrics.xlsx`, and `metric_run_metadata.json` under the selected output directory.

## License Note

The upstream Text2CAD GitHub repository and HuggingFace dataset identify the Text2CAD materials as `CC BY-NC-SA 4.0`. This release follows that license for dataset-derived materials. The evaluation code is separately MIT-licensed under `evaluation_code/LICENSE`.
