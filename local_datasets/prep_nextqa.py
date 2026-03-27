import os
import json
import csv

# SCRIPT_DIR = local_datasets/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

RAW_DIR = os.path.join(SCRIPT_DIR, "nextqa", "raw")
OUT_DIR = os.path.join(SCRIPT_DIR, "nextqa")
os.makedirs(OUT_DIR, exist_ok=True)

OUT_PATH = os.path.join(OUT_DIR, "nextqa.jsonl")

# Map integer index → answer letter
IDX2LETTER = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E"}


def process_csv(csv_path, writer):
    """
    Append processed rows from a CSV into an open JSONL writer.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"[prep_nextqa] Missing file: {csv_path}")

    count = 0

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            video = row["video"].strip()
            question = row["question"].strip()

            # Option strings
            opts = [row[f"a{i}"].strip() for i in range(5)]

            # Convert answer to index if needed
            ans_raw = row["answer"].strip()
            try:
                answer_idx = int(ans_raw)
            except ValueError:
                # Already a letter
                answer_idx = {"A":0,"B":1,"C":2,"D":3,"E":4}[ans_raw.upper()]

            answer_letter = IDX2LETTER[answer_idx]

            # Construct prompt
            prompt = (
                f"Video ID: {video}\n"
                f"Question: {question}\n\n"
                f"Options:\n"
                f"A. {opts[0]}\n"
                f"B. {opts[1]}\n"
                f"C. {opts[2]}\n"
                f"D. {opts[3]}\n"
                f"E. {opts[4]}\n\n"
                f"Answer:"
            )

            completion = answer_letter

            writer.write(json.dumps({"prompt": prompt, "completion": completion},
                                    ensure_ascii=False) + "\n")
            count += 1

    print(f"[prep_nextqa] Processed {count} rows from {os.path.basename(csv_path)}")


def main():
    print("[prep_nextqa] Preparing combined NextQA dataset…")

    train_csv = os.path.join(RAW_DIR, "train.csv")
    val_csv = os.path.join(RAW_DIR, "val.csv")

    total = 0
    with open(OUT_PATH, "w") as writer:
        process_csv(train_csv, writer)
        process_csv(val_csv, writer)

    print(f"[prep_nextqa] Wrote combined dataset → {OUT_PATH}")


if __name__ == "__main__":
    main()

