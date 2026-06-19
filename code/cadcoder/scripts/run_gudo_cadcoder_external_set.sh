#!/usr/bin/env bash
set -euo pipefail

INPUT_JSONL="${1:-data/external_generation_test_sets/all_test_sets_prompts.jsonl}"
DATASET_NAME="${2:-external_all}"
LIMIT="${3:-1}"
MODEL="${MODEL:-gudo7208/CAD-Coder}"
ENV_NAME="${ENV_NAME:-gudo_cadcoder}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-2048}"
PROMPT_TEMPLATE="${PROMPT_TEMPLATE:-cadquery_solid}"
LOAD_ARGS="${LOAD_ARGS:-}"

if [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
elif [ -f "${HOME}/miniforge3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  source "${HOME}/miniforge3/etc/profile.d/conda.sh"
elif command -v conda >/dev/null 2>&1; then
  # shellcheck source=/dev/null
  source "$(conda info --base)/etc/profile.d/conda.sh"
else
  echo "Conda was not found. Install Miniconda/Miniforge first." >&2
  exit 1
fi

conda activate "${ENV_NAME}"

MODEL_NAME="gudo-CAD-Coder"
RUN_NAME="${DATASET_NAME}"
GEN_LIMIT_ARGS=()
if [ "${LIMIT}" != "all" ]; then
  GEN_LIMIT_ARGS=(--limit "${LIMIT}")
  RUN_NAME="${DATASET_NAME}_first${LIMIT}"
fi

OUT_DIR="./inference/inference_results/${MODEL_NAME}/${RUN_NAME}"
mkdir -p "${OUT_DIR}"

echo "[1/2] Generating CadQuery from ${INPUT_JSONL}"
python scripts/run_gudo_cadcoder_text_generation.py \
  --model "${MODEL}" \
  --input-jsonl "${INPUT_JSONL}" \
  --output-dir "${OUT_DIR}" \
  --max-new-tokens "${MAX_NEW_TOKENS}" \
  --prompt-template "${PROMPT_TEMPLATE}" \
  "${GEN_LIMIT_ARGS[@]}" \
  ${LOAD_ARGS}

echo "[2/2] Executing CadQuery and exporting STEP/STL/point clouds"
python scripts/generate_model_cad.py \
  --dataset_name "${RUN_NAME}" \
  --model_tested "${MODEL_NAME}" \
  --code_language cadquery \
  --pc_reps 1 \
  --parallel

echo "Done. Results in ${OUT_DIR}"
cat "${OUT_DIR}/cad_gen_results.txt"
