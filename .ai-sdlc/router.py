import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
import re

AI_SDLC_DIR = Path(__file__).parent
ARTIFACTS_DIR = AI_SDLC_DIR / "artifacts"
WORKFLOWS_DIR = AI_SDLC_DIR / "workflows"

# Load models.yaml
with open(AI_SDLC_DIR / "models.yaml") as f:
    MODELS = yaml.safe_load(f)

# Load workflow definitions
WORKFLOWS = {}
for wf_file in WORKFLOWS_DIR.glob("*.yaml"):
    with open(wf_file) as f:
        workflow_type = wf_file.stem
        WORKFLOWS[workflow_type] = {"stages": yaml.safe_load(f)["stages"]}

def get_next_sequence_number(workflow_type):
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"{workflow_type}-\d{{3}}")
    existing = sorted([
        int(d.name.split("-")[1]) 
        for d in ARTIFACTS_DIR.iterdir()
        if d.is_dir() and pattern.match(d.name)
    ])
    return f"{existing[-1] + 1:03d}" if existing else "001"

def create_artifact(workflow_type):
    workflow = WORKFLOWS.get(workflow_type)
    if not workflow:
        print(f"Unknown workflow type: {workflow_type}")
        return

    workflow_dir = ARTIFACTS_DIR / f"{workflow_type}-{get_next_sequence_number(workflow_type)}"
    workflow_dir.mkdir(exist_ok=True)

    # Create status.yaml
    status_path = workflow_dir / "status.yaml"
    with open(status_path, "w") as f:
        f.write(f"workflow: {workflow_type}\n")
        f.write(f"id: {workflow_dir.name}\n")
        f.write(f"stage: {workflow['stages'][0]}\n")
        f.write(f"status: active\n")
        f.write(f"created_at: {datetime.now().isoformat()}\n")
        for model_key in MODELS:
            model_value = MODELS[model_key]
            f.write(f"model_{model_key}: {model_value}\n")

    # Create template files
    for template in workflow["stages"]:
        with open(workflow_dir / f"{template}.md", "w") as f:
            f.write(f"<!-- Placeholder for {template} -->")