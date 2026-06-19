import argparse
import csv
import json
from pathlib import Path


PROMPT_LEVELS = ("abstract", "description", "beginner", "intermediate", "expert")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a CAD-Coder-compatible JSONL from the packaged Text2CAD random-100 prompts.csv."
    )
    parser.add_argument("--prompts-csv", required=True, type=Path)
    parser.add_argument("--reference-manifest", type=Path, default=None)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--level", choices=PROMPT_LEVELS, default="intermediate")
    parser.add_argument("--dataset-name", default=None)
    args = parser.parse_args()

    dataset_name = args.dataset_name or f"text2cad_random_100_v1_1_{args.level}"
    args.output_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_root / f"{dataset_name}_prompts.jsonl"

    prompt_rows = read_csv_rows(args.prompts_csv)
    reference_rows = {}
    if args.reference_manifest and args.reference_manifest.exists():
        reference_rows = {row["index"]: row for row in read_csv_rows(args.reference_manifest)}

    with jsonl_path.open("w", encoding="utf-8", newline="\n") as out:
        for row in prompt_rows:
            prompt = row.get(args.level, "")
            if not prompt:
                raise ValueError(f"Missing {args.level!r} prompt for row {row.get('index')}")

            index = int(row["index"])
            cad_id = f"{int(row['cad_id']):08d}"
            sample_id = f"{index:03d}_{cad_id}"
            ref = reference_rows.get(str(index), {})

            record = {
                "dataset": dataset_name,
                "sample_id": sample_id,
                "source_id": cad_id,
                "uid": row.get("uid", ""),
                "cad_id": cad_id,
                "shard": row.get("shard", ""),
                "prompt_for_generation": prompt,
                "prompt_type": f"text2cad_{args.level}_original",
                "prompt_level": args.level,
                "abstract": row.get("abstract", ""),
                "description": row.get("description", ""),
                "beginner": row.get("beginner", ""),
                "intermediate": row.get("intermediate", ""),
                "expert": row.get("expert", ""),
                "reference_sequence_json": ref.get("deepcad_cad_json", ""),
                "deepcad_cad_json": ref.get("deepcad_cad_json", ""),
                "deepcad_cad_vec": ref.get("deepcad_cad_vec", ""),
                "prompt_json": ref.get("prompt_json", row.get("prompt_json", "")),
                "notes": (
                    f"{args.level} prompt copied unchanged from packaged prompts.csv; "
                    "reference paths are relative to the package root when available."
                ),
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "dataset": dataset_name,
        "rows": len(prompt_rows),
        "prompt_file": jsonl_path.name,
        "source_prompt_file": str(args.prompts_csv),
        "source_reference_manifest": str(args.reference_manifest) if args.reference_manifest else None,
        "source_prompt_field": args.level,
        "prompt_content_policy": f"prompt_for_generation is copied unchanged from prompts.csv {args.level} field.",
        "recommended_prompt_template": "gudo_train_short",
    }
    (args.output_root / "manifest_for_cadcoder.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {jsonl_path}")


if __name__ == "__main__":
    main()
