#!/usr/bin/env python
"""Prepare prompt/config files for official Text2CAD inference."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


PROMPT_LEVELS = ("abstract", "description", "beginner", "intermediate", "expert")


def as_posix_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def escape_prompt(text: str) -> str:
    return str(text).replace("</prompt>", " ").strip()


def yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\\", "/").replace('"', '\\"')
    return f'"{text}"'


def render_text2cad_config(args: argparse.Namespace, prompt_file: Path, run_dir: Path) -> str:
    cache_dir = Path(args.cache_dir).resolve() if args.cache_dir else None
    checkpoint_path = Path(args.checkpoint_path).resolve() if args.checkpoint_path else ""
    model_name = args.bert_model_name_or_path

    values = {
        "model_name": model_name,
        "cache_dir": as_posix_path(cache_dir) if cache_dir else None,
        "log_dir": as_posix_path(run_dir),
        "checkpoint_path": as_posix_path(checkpoint_path) if checkpoint_path else "",
        "prompt_file": as_posix_path(prompt_file),
    }

    return f"""text_encoder:
  text_embedder:
    model_name: {yaml_scalar(values["model_name"])}
    max_seq_len: 512
    cache_dir: {yaml_scalar(values["cache_dir"])}
  adaptive_layer:
    in_dim: 1024
    out_dim: 1024
    num_heads: 8
    dropout: 0.1
cad_decoder:
  tdim: 1024
  cdim: 256
  num_layers: 8
  num_heads: 8
  dropout: 0.1
  ca_level_start: 2
test:
  batch_size: {args.batch_size}
  num_workers: {args.num_workers}
  prefetch_factor: {args.prefetch_factor}
  log_dir: {yaml_scalar(values["log_dir"])}
  checkpoint_path: {yaml_scalar(values["checkpoint_path"])}
  nucleus_prob: {args.nucleus_prob}
  sampling_type: {yaml_scalar(args.sampling_type)}
  prompt_file: {yaml_scalar(values["prompt_file"])}
debug: false
info: {yaml_scalar(f"Text2CAD random-100 v1.1 {args.prompt_level} prompt inference")}
"""


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root.")
    parser.add_argument("--prompt-level", choices=PROMPT_LEVELS, default="intermediate")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--checkpoint-path", type=Path, default=None)
    parser.add_argument("--bert-model-name-or-path", default="google-bert/bert-large-uncased")
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--prefetch-factor", type=int, default=2)
    parser.add_argument("--nucleus-prob", type=float, default=0)
    parser.add_argument("--sampling-type", choices=("max", "nucleus"), default="max")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    prompts_csv = root / "data" / "prompts" / "prompts.csv"
    ref_manifest_csv = root / "data" / "reference_sequence_gt" / "sequence_gt_reference_manifest.csv"

    if not prompts_csv.exists():
        raise FileNotFoundError(f"Missing prompts CSV: {prompts_csv}")
    if not ref_manifest_csv.exists():
        raise FileNotFoundError(f"Missing reference manifest: {ref_manifest_csv}")

    run_dir = args.output_dir.resolve() if args.output_dir else (root / "runs" / "text2cad" / args.prompt_level).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    prompt_rows = read_csv_dicts(prompts_csv)
    ref_rows = {row["index"]: row for row in read_csv_dicts(ref_manifest_csv)}

    selected_rows = [row for row in prompt_rows if row.get(args.prompt_level)]
    if not selected_rows:
        raise RuntimeError(f"No rows contain prompt level: {args.prompt_level}")

    prompt_file = run_dir / "prompts.txt"
    manifest_file = run_dir / "index_manifest.csv"
    config_file = run_dir / "text2cad_inference.yaml"

    with prompt_file.open("w", encoding="utf-8", newline="\n") as f:
        for row in selected_rows:
            f.write(f"<prompt>{escape_prompt(row[args.prompt_level])}</prompt>\n")

    fieldnames = [
        "run_index",
        "source_index",
        "cad_id",
        "uid",
        "shard",
        "prompt_level",
        "prompt_text",
        "reference_sequence_json",
        "deepcad_cad_json",
        "deepcad_cad_vec",
        "prompt_json",
    ]
    with manifest_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for run_index, row in enumerate(selected_rows):
            ref = ref_rows.get(row["index"], {})
            writer.writerow(
                {
                    "run_index": run_index,
                    "source_index": row.get("index", ""),
                    "cad_id": row.get("cad_id", ""),
                    "uid": row.get("uid", ""),
                    "shard": row.get("shard", ""),
                    "prompt_level": args.prompt_level,
                    "prompt_text": row.get(args.prompt_level, ""),
                    "reference_sequence_json": ref.get("deepcad_cad_json", ""),
                    "deepcad_cad_json": ref.get("deepcad_cad_json", ""),
                    "deepcad_cad_vec": ref.get("deepcad_cad_vec", ""),
                    "prompt_json": ref.get("prompt_json", row.get("prompt_json", "")),
                }
            )

    config_file.write_text(render_text2cad_config(args, prompt_file, run_dir), encoding="utf-8", newline="\n")

    print(f"prompt_level={args.prompt_level}")
    print(f"num_prompts={len(selected_rows)}")
    print(f"prompt_file={prompt_file}")
    print(f"manifest_file={manifest_file}")
    print(f"config_file={config_file}")


if __name__ == "__main__":
    main()
