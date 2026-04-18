import os
import json
import argparse
from tqdm import tqdm

def read_file(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def prep_apps(raw_root, out_path):
    """
    Convert APPS train split into JSONL of {"prompt": question, "completion": first_solution}.
    """

    train_root = os.path.join(raw_root, "train")
    if not os.path.isdir(train_root):
        raise ValueError(f"train/ directory not found under {raw_root}")

    rows = []

    print("Processing APPS train split...")

    for pid in tqdm(os.listdir(train_root)):
        problem_dir = os.path.join(train_root, pid)
        if not os.path.isdir(problem_dir):
            continue

        # --- Load prompt ---
        qfile = os.path.join(problem_dir, "question.txt")
        question = read_file(qfile)
        if question is None:
            continue

        # --- Load solutions.json ---
        sol_file = os.path.join(problem_dir, "solutions.json")
        if not os.path.exists(sol_file):
            continue

        try:
            with open(sol_file, "r", encoding="utf-8") as f:
                sols = json.load(f)
            if not isinstance(sols, list) or len(sols) == 0:
                continue
            completion = sols[0].strip()
        except Exception:
            continue

        rows.append({
            "prompt": question.strip(),
            "completion": completion,
        })

    print(f"Total train problems collected: {len(rows)}")

    # Save JSONL
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    print(f"Wrote JSONL to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_root", type=str, required=True,
                        help="Path to APPS dataset directory containing train/")
    parser.add_argument("--out", type=str, required=True,
                        help="Output JSONL file")
    args = parser.parse_args()

    prep_apps(args.raw_root, args.out)
