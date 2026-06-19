# CAD-Coder Baseline Runner

Minimal scripts for running inference with `gudo7208/CAD-Coder` on external
text-to-CAD prompts.

This is not the official CAD-Coder repository. It only bridges external JSONL
prompts to the public `gudo7208/CAD-Coder` model and exports generated CadQuery
code to STEP/STL for downstream use.

- Complete model: https://huggingface.co/gudo7208/CAD-Coder
- Dataset format reference only, used to match input/prompt formatting: https://huggingface.co/datasets/gudo7208/CAD-Coder
- Paper: https://arxiv.org/abs/2505.19713

There are multiple projects named "CAD-Coder". This runner targets the
`gudo7208/CAD-Coder` text-to-CAD/CadQuery model.

```bibtex
@article{guan2025cadcoder,
  title={CAD-Coder: Text-to-CAD Generation with Chain-of-Thought and Geometric Reward},
  author={Guan, Yandong and Wang, Xilin and Ming, Xingxi and Zhang, Jing and Xu, Dong and Yu, Qian},
  journal={arXiv preprint arXiv:2505.19713},
  year={2025}
}
```

## Files

```text
scripts/run_gudo_cadcoder_text_generation.py
```

Runs model inference. It reads `prompt_for_generation`, applies a prompt
template, generates CadQuery code, and writes `merge.jsonl`.

```text
scripts/run_gudo_cadcoder_external_set.sh
```

Main entry point. It runs text generation, executes generated CadQuery, exports
STEP/STL, samples point clouds, and writes validity statistics.

```text
scripts/generate_model_cad.py
scripts/utils_generate_model.py
```

Execution/export utilities. They write generated code to Python files, execute
it, export STL/STEP, and generate point clouds.

```text
scripts/build_text2cad_level_jsonl.py
```

Optional helper for converting a Text2CAD manifest to this runner's JSONL
format using one prompt level, for example `intermediate` or `expert`.

```text
scripts/build_text2cad_random100_jsonl_from_prompts_csv.py
```

Helper for converting this package's `data/prompts/prompts.csv` directly into
the JSONL format expected by this CAD-Coder runner.

## Input Format

Each line in the input JSONL should look like:

```json
{
  "dataset": "example_set",
  "sample_id": "001",
  "prompt_for_generation": "Create a rectangular block with length 50 mm, width 30 mm, and height 20 mm."
}
```

Required:

- `prompt_for_generation`
- `sample_id`

Recommended:

- `dataset`
- `source_id`
- `prompt_level`

## Prompt Template

For Text2CAD `intermediate` and `expert` prompts, we used the short prompt style
observed in the CAD-Coder training/validation data:

```text
Please based on the following description, create a CAD-Query Code to generate a model:
{description}
```

Set it with:

```bash
PROMPT_TEMPLATE=gudo_train_short
```

The script records the exact prompt in `model_prompt`.

## Environment

The CAD-Coder reproduction path was run on a Linux server environment. The
shell entry point below is intended for Linux or WSL with conda available.

Install dependencies in a Python 3.10 environment:

```bash
conda create -n gudo_cadcoder python=3.10 -y
conda activate gudo_cadcoder
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision
pip install transformers==4.46.3 tokenizers==0.20.3 accelerate safetensors tqdm sentencepiece
conda install -c conda-forge cadquery -y
pip install trimesh plyfile pandas scipy
```

Download the complete model:

```bash
mkdir -p weights/gudo-CAD-Coder
hf download gudo7208/CAD-Coder --local-dir weights/gudo-CAD-Coder
```

If the Hugging Face CLI is not available, download the model files manually
from `https://huggingface.co/gudo7208/CAD-Coder` and place them under:

```text
code/cadcoder/weights/gudo-CAD-Coder/
```

## Run

Run one sample:

```bash
ENV_NAME=gudo_cadcoder MODEL=./weights/gudo-CAD-Coder \
PROMPT_TEMPLATE=gudo_train_short MAX_NEW_TOKENS=4096 \
  ./scripts/run_gudo_cadcoder_external_set.sh \
  data/examples/example_prompts.jsonl \
  example_set \
  1
```

Run all samples:

```bash
ENV_NAME=gudo_cadcoder MODEL=./weights/gudo-CAD-Coder \
PROMPT_TEMPLATE=gudo_train_short MAX_NEW_TOKENS=4096 \
  ./scripts/run_gudo_cadcoder_external_set.sh \
  data/examples/example_prompts.jsonl \
  example_set \
  all
```

Results are written to:

```text
inference/inference_results/gudo-CAD-Coder/<run_name>/
```

Important files:

```text
merge.jsonl
cad_gen_results.txt
results.csv
model_code/
model_step/
model_stl/
model_point_cloud_0/
```

## Build Text2CAD JSONL

### Option A: From This Package's `prompts.csv`

From the repository root:

```bash
python code/cadcoder/scripts/build_text2cad_random100_jsonl_from_prompts_csv.py \
  --prompts-csv data/prompts/prompts.csv \
  --reference-manifest data/reference_sequence_gt/sequence_gt_reference_manifest.csv \
  --output-root code/cadcoder/data/text2cad_random_100_v1_1_intermediate \
  --dataset-name text2cad_random_100_v1_1_intermediate \
  --level intermediate
```

This writes:

```text
code/cadcoder/data/text2cad_random_100_v1_1_intermediate/text2cad_random_100_v1_1_intermediate_prompts.jsonl
code/cadcoder/data/text2cad_random_100_v1_1_intermediate/manifest_for_cadcoder.json
```

Then run from `code/cadcoder/`:

```bash
ENV_NAME=gudo_cadcoder MODEL=./weights/gudo-CAD-Coder \
PROMPT_TEMPLATE=gudo_train_short MAX_NEW_TOKENS=4096 \
  ./scripts/run_gudo_cadcoder_external_set.sh \
  data/text2cad_random_100_v1_1_intermediate/text2cad_random_100_v1_1_intermediate_prompts.jsonl \
  text2cad_random_100_v1_1_intermediate \
  all
```

For expert prompts, change `--level expert`, the output directory, and the
dataset name.

### Option B: From an Original Text2CAD Manifest

Alternatively, download or prepare the original Text2CAD random-100 v1.1
dataset directory used by the experiments. The directory is expected to contain:

```text
manifest.csv
prompts/
```

`manifest.csv` must include the prompt columns used for generation, such as
`intermediate` and `expert`, together with `prompt_json`.

Example:

```bash
python scripts/build_text2cad_level_jsonl.py \
  --manifest-csv /path/to/Text2CAD_random_100_v1.1/manifest.csv \
  --output-root data/text2cad_random_100_v1_1_intermediate \
  --dataset-name text2cad_random_100_v1_1_intermediate \
  --level intermediate
```

Then run:

```bash
ENV_NAME=gudo_cadcoder MODEL=./weights/gudo-CAD-Coder \
PROMPT_TEMPLATE=gudo_train_short MAX_NEW_TOKENS=4096 \
  ./scripts/run_gudo_cadcoder_external_set.sh \
  data/text2cad_random_100_v1_1_intermediate/text2cad_random_100_v1_1_intermediate_prompts.jsonl \
  text2cad_random_100_v1_1_intermediate \
  all
```

## Postprocessing

The runner removes Markdown fences and extracts executable CadQuery code. It
also adapts the final object to `solid`, because the export script expects:

```python
cq.exporters.export(solid, "output.stl")
```

The raw model output is preserved in `raw_text`.

## Not Included

This repository does not include:

- CAD-Coder model files
- benchmark result archives
- large generated STEP/STL/point-cloud outputs
- proprietary or license-restricted CAD datasets
