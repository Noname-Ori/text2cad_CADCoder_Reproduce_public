import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a CAD-Coder-compatible JSONL from a Text2CAD random subset manifest."
    )
    parser.add_argument("--manifest-csv", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--level",
        choices=["abstract", "description", "beginner", "intermediate", "expert"],
        default="intermediate",
    )
    parser.add_argument("--dataset-name", default=None)
    args = parser.parse_args()

    dataset_name = args.dataset_name or f"text2cad_{args.level}"
    args.output_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_root / f"{dataset_name}_prompts.jsonl"

    with args.manifest_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    with jsonl_path.open("w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            prompt = row.get(args.level, "")
            if not prompt:
                raise ValueError(f"Missing {args.level!r} prompt for row {row.get('index')}")

            sample_id = f"{int(row['index']):03d}_{row['cad_id']}"
            prompt_json_name = Path(row["prompt_json"]).name

            record = {
                "dataset": dataset_name,
                "sample_id": sample_id,
                "source_id": row["cad_id"],
                "uid": row.get("uid", ""),
                "cad_id": row["cad_id"],
                "shard": row.get("shard", ""),
                "prompt_for_generation": prompt,
                "prompt_type": f"text2cad_{args.level}_original",
                "prompt_level": args.level,
                "abstract": row.get("abstract", ""),
                "description": row.get("description", ""),
                "beginner": row.get("beginner", ""),
                "intermediate": row.get("intermediate", ""),
                "expert": row.get("expert", ""),
                "prompt_json": f"original_prompts/{prompt_json_name}",
                "notes": (
                    f"{args.level} prompt copied unchanged from the Text2CAD manifest; "
                    "only wrapper fields were added."
                ),
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "dataset": dataset_name,
        "rows": len(rows),
        "prompt_file": jsonl_path.name,
        "source_prompt_field": args.level,
        "prompt_content_policy": f"prompt_for_generation is copied unchanged from manifest {args.level} field.",
        "recommended_prompt_template": "gudo_train_short",
    }
    (args.output_root / "manifest_for_cadcoder.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {jsonl_path}")


if __name__ == "__main__":
    main()
