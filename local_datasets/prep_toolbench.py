#!/usr/bin/env python3
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "toolbench", "raw")
INSTR_DIR = os.path.join(RAW_DIR, "test_instruction")
ID_DIR = os.path.join(RAW_DIR, "test_query_ids")

OUT_PATH = os.path.join(SCRIPT_DIR, "toolbench", "toolbench.jsonl")

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def build_completion(api_list):
    """
    Convert ToolBench API metadata into a deterministic text completion.
    """
    if not api_list:
        return "No relevant APIs were provided."

    lines = ["The question involves the following APIs:"]
    for api in api_list:
        tool = api.get("tool_name", "UnknownTool")
        api_name = api.get("api_name", "UnknownAPI")
        desc = api.get("api_description", "")
        lines.append(f"- {tool} / {api_name}: {desc}")

    return "\n".join(lines)


def main():
    out_f = open(OUT_PATH, "w")

    # Collect all matching instruction + id-filter file pairs
    instr_files = sorted(os.listdir(INSTR_DIR))
    id_files = sorted(os.listdir(ID_DIR))

    assert len(instr_files) == len(id_files), \
        "Instruction and ID lists do not match in file count."

    total_written = 0

#     for instr_file, id_file in zip(instr_files, id_files):
    for instr_file in instr_files:
        instr_path = os.path.join(INSTR_DIR, instr_file)
#         id_path = os.path.join(ID_DIR, id_file)

#         print(f"[prep_toolbench] Processing {instr_file} with ID filter {id_file}")
        print(f"[prep_toolbench] Processing {instr_file}")

        instructions = load_json(instr_path)
#         id_filter = load_json(id_path)   # mapping: {"row_id": 0, ...}

        # Convert string keys → int indices
#         keep_indices = {int(k) for k in id_filter.keys()}

        for idx, row in enumerate(instructions):
#             if idx not in keep_indices:
#                 continue

            query = row.get("query", "").strip()
            api_list = row.get("api_list", [])
            completion = build_completion(api_list)

            out_obj = {
                "prompt": query,
                "completion": completion
            }
            out_f.write(json.dumps(out_obj, ensure_ascii=False) + "\n")
            total_written += 1

    out_f.close()
    print(f"[prep_toolbench] Wrote {total_written} entries → {OUT_PATH}")


if __name__ == "__main__":
    main()

