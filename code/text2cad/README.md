# Text2CAD Baseline Wrapper

These scripts prepare the selected 100 prompts for official Text2CAD inference and call an external Text2CAD checkout. They do not redistribute Text2CAD source code, model checkpoints, or generated outputs.

## Requirements

- A working official Text2CAD checkout:
  https://github.com/SadilKhan/Text2CAD
- The official Text2CAD checkpoint, obtained following the upstream Text2CAD
  repository instructions.
- Python dependencies required by the official Text2CAD project.
- A BERT-large-uncased model path or Hugging Face model name.
- The Text2CAD dataset, obtained from the upstream source:
  https://huggingface.co/datasets/SadilKhan/Text2CAD

Useful upstream references:

- Dataset page: https://huggingface.co/datasets/SadilKhan/Text2CAD
- Source code: https://github.com/SadilKhan/Text2CAD

This package only provides the selected random-100 prompts and small wrapper
scripts. It does not mirror the official Text2CAD repository, checkpoint, or
full dataset.

## Environment

This wrapper path was run in a Windows environment. The examples below use
PowerShell line continuation. On Linux, replace the backticks with backslashes.

## Prepare Inputs

From the repository root:

```powershell
python code/text2cad/prepare_text2cad_inputs.py `
  --root . `
  --prompt-level intermediate `
  --output-dir runs/text2cad/intermediate `
  --checkpoint-path C:/path/to/Text2CAD_1.0.pth `
  --bert-model-name-or-path google-bert/bert-large-uncased
```

This writes:

- `prompts.txt`
- `index_manifest.csv`
- `text2cad_inference.yaml`

The default generation hyperparameters match the previous Text2CAD baseline runs in this package: `batch_size=1`, `sampling_type=max`, and `nucleus_prob=0`.

## Run Inference

```powershell
python code/text2cad/run_text2cad_inference.py `
  --text2cad-root C:/path/to/Text2CAD `
  --config runs/text2cad/intermediate/text2cad_inference.yaml
```

To run expert-level prompts, change `--prompt-level expert` and use a separate output directory such as `runs/text2cad/expert`.
