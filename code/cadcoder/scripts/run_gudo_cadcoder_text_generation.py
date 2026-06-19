import argparse
import json
import re
from pathlib import Path

import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_records(path: Path, limit: int | None) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
                if limit is not None and len(records) >= limit:
                    break
    return records


def extract_cadquery_code(text: str) -> str:
    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1)
    text = text.replace("```", "")

    markers = [
        "import cadquery as cq",
        "import cadquery",
        "from cadquery",
    ]
    lowered = text.lower()
    starts = [lowered.find(marker) for marker in markers if lowered.find(marker) >= 0]
    if starts:
        text = text[min(starts):]

    # Remove common assistant preambles if no import marker was found.
    text = re.sub(r"^.*?(?=(?:import|from|#|result\s*=|solid\s*=))", "", text, flags=re.DOTALL)
    code = text.strip()

    if "cq." in code and not re.search(r"^\s*(?:import\s+cadquery\s+as\s+cq|import\s+cadquery|from\s+cadquery\s+import)", code, flags=re.MULTILINE):
        code = f"import cadquery as cq\n\n{code}"

    if not re.search(r"^\s*solid\s*=", code, flags=re.MULTILINE):
        assignments = re.findall(r"^\s*([A-Za-z_]\w*)\s*=", code, flags=re.MULTILINE)
        candidates = [
            name for name in assignments
            if name not in {"cq"} and not name.startswith("wp_") and not name.startswith("loop")
        ]
        if candidates:
            code = f"{code}\n\nsolid = {candidates[-1]}"

    return code


def build_prompt(description: str, template: str) -> str:
    if template == "gudo_train_short":
        return (
            "Please based on the following description, create a CAD-Query Code to generate a model:\n"
            f"{description}"
        )
    if template == "cadquery_solid":
        return (
            "Generate executable CadQuery Python code for the CAD model described below.\n"
            "Requirements:\n"
            "- Output Python code only, with no Markdown fences and no explanatory text.\n"
            "- Import cadquery as cq.\n"
            "- Assign the final CadQuery object to a variable named solid.\n\n"
            f"CAD description: {description}"
        )
    raise ValueError(f"Unknown prompt template: {template}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gudo7208/CAD-Coder")
    parser.add_argument("--input-jsonl", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--prompt-field", default="prompt_for_generation")
    parser.add_argument("--id-field", default="sample_id")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument(
        "--prompt-template",
        choices=["cadquery_solid", "gudo_train_short"],
        default="cadquery_solid",
        help="Wrapper prompt applied around the raw description.",
    )
    parser.add_argument("--load-4bit", action="store_true")
    parser.add_argument("--load-8bit", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "merge.jsonl"

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)

    model_kwargs = {
        "device_map": "auto",
        "trust_remote_code": True,
    }
    if args.load_4bit:
        model_kwargs["load_in_4bit"] = True
    elif args.load_8bit:
        model_kwargs["load_in_8bit"] = True
    else:
        model_kwargs["torch_dtype"] = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    model.eval()

    records = load_records(args.input_jsonl, args.limit)

    with output_path.open("w", encoding="utf-8", newline="\n") as out:
        for record in tqdm(records, desc="Generating CadQuery"):
            prompt_raw = record[args.prompt_field]
            prompt = build_prompt(prompt_raw, args.prompt_template)
            sample_id = str(record.get(args.id_field) or record.get("source_id") or len(records))
            if record.get("dataset"):
                sample_id = f"{record['dataset']}__{sample_id}"
            messages = [{"role": "user", "content": prompt}]
            chat_text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = tokenizer([chat_text], return_tensors="pt").to(model.device)

            generation_kwargs = {
                "max_new_tokens": args.max_new_tokens,
                "do_sample": args.temperature > 0,
                "temperature": args.temperature if args.temperature > 0 else None,
                "top_p": args.top_p if args.temperature > 0 else None,
                "pad_token_id": tokenizer.eos_token_id,
            }
            generation_kwargs = {k: v for k, v in generation_kwargs.items() if v is not None}

            with torch.inference_mode():
                outputs = model.generate(**inputs, **generation_kwargs)

            raw_text = tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True,
            )
            code = extract_cadquery_code(raw_text)

            out.write(json.dumps({
                "question_id": sample_id,
                "prompt": prompt_raw,
                "model_prompt": prompt,
                "text": code,
                "raw_text": raw_text,
                "answer_id": "gudo7208-CAD-Coder",
                "model_id": args.model,
                "metadata": record,
            }, ensure_ascii=False) + "\n")
            out.flush()

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
