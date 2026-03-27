import os
import json
import argparse
from tqdm import tqdm


def extract_best_task_desc(turk):
    """Pick the description with the highest votes."""
    if not turk or "anns" not in turk:
        return None
    anns = turk["anns"]
    if not anns:
        return None

    # pick the annotation with max total votes
    def score(ann):
        return sum(ann.get("votes", []))

    best = max(anns, key=score)
    return best.get("task_desc", None)


def summarize_scene(scene):
    """Produce a compact, human-readable scene summary."""
    floor_plan = scene.get("floor_plan", "unknown")
    init_action = scene.get("init_action", "")
    dirty = scene.get("dirty_and_empty", None)

    objs = scene.get("object_poses", [])
    obj_names = sorted({obj.get("objectName", "") for obj in objs if obj.get("objectName")})

    # Toggles full structure is too big—summarize by name
    toggles = scene.get("object_toggles", [])
    toggle_names = sorted({t.get("objectName", "") for t in toggles if t.get("objectName")})

    summary = (
        f"- Floor plan: {floor_plan}\n"
        f"- Initial state dirty_and_empty: {dirty}\n"
        f"- Objects ({len(obj_names)}): {', '.join(obj_names)}\n"
        f"- Toggles ({len(toggle_names)}): {', '.join(toggle_names)}\n"
        f"- Init action: {init_action}"
    )
    return summary


def extract_high_actions(plan):
    """Extract high-level discrete actions from plan.high_pddl[]"""
    high = plan.get("high_pddl", [])
    actions = []

    for step in high:
        da = step.get("discrete_action", {})
        action = da.get("action", "")
        args = da.get("args", [])

        if not action:
            continue

        if isinstance(args, list):
            argstr = ", ".join(args)
        else:
            argstr = str(args)

        actions.append(f"{action}({argstr})")

    return actions


def extract_pddl_params(pp):
    """Convert pddl_params into readable text."""
    if not pp:
        return "None"

    out = []
    for k, v in pp.items():
        out.append(f"{k}: {v}")
    return "\n".join(out)


def process_traj(traj_file):
    """Convert a single traj_data.json into {prompt, completion}"""

    with open(traj_file, "r") as f:
        data = json.load(f)

    task_type = data.get("task_type", "").strip()
    pddl_params = extract_pddl_params(data.get("pddl_params", {}))

    # Scene summary
    scene_summary = summarize_scene(data.get("scene", {}))

    # Optional natural language instruction
    task_desc = extract_best_task_desc(data.get("turk_annotations", {}))

    # Expert plan
    actions = extract_high_actions(data.get("plan", {}))
    if not actions:
        return None

    # Build prompt
    prompt_parts = [
        f"AlfWorld task.",
        f"Task type: {task_type}",
        "",
        "PDDL parameters:",
        pddl_params,
        "",
        "Scene summary:",
        scene_summary,
    ]

    if task_desc:
        prompt_parts += [
            "",
            f"Human instruction: {task_desc}"
        ]

    prompt_parts += [
        "",
        "Provide the sequence of high-level actions to solve the task.",
        "Output exactly one action per line. No explanations."
    ]

    prompt = "\n".join(prompt_parts)
    completion = "\n".join(actions)

    return {"prompt": prompt, "completion": completion}


def prep_split(raw_root, split, out_path):
    split_dir = os.path.join(raw_root, split)
    rows = []

    for task_type in tqdm(os.listdir(split_dir), desc=f"{split} task types"):
        task_dir = os.path.join(split_dir, task_type)
        if not os.path.isdir(task_dir):
            continue

        for trial in os.listdir(task_dir):
            traj_dir = os.path.join(task_dir, trial)
            traj_file = os.path.join(traj_dir, "traj_data.json")
            if not os.path.isfile(traj_file):
                continue

            item = process_traj(traj_file)
            if item:
                rows.append(item)

    print(f"[prep_alfworld] {split}: extracted {len(rows)} examples")

    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    print(f"→ wrote {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True,
                        help="Path to local_datasets/alfworld/raw/json_2.1.1")
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # AlfWorld 2.1.1 splits
    splits = [
        ("train", "alfworld_train.jsonl"),
        ("valid_seen", "alfworld_valid_seen.jsonl"),
        ("valid_unseen", "alfworld_valid_unseen.jsonl"),
        ("valid_train", "alfworld_valid_train.jsonl"),
    ]

    for split_dir, out_name in splits:
        raw_split_path = os.path.join(args.raw, split_dir)
        out_file = os.path.join(args.outdir, out_name)
        if os.path.isdir(raw_split_path):
            prep_split(args.raw, split_dir, out_file)
        else:
            print(f"[prep_alfworld] WARNING: split {split_dir} not found, skipping.")

