import sys
import yaml
from pathlib import Path
from datetime import datetime
import re

AI_SDLC_DIR = Path(__file__).parent
ARTIFACTS_DIR = AI_SDLC_DIR / "artifacts"
ARTIFACT_TEMPLATES_DIR = ARTIFACTS_DIR / "templates"
WORKFLOWS_DIR = AI_SDLC_DIR / "workflows"

# Load models.yaml
with open(AI_SDLC_DIR / "models.yaml") as f:
    MODELS = yaml.safe_load(f) or {}

# Load workflow definitions
WORKFLOWS = {}
for wf_file in WORKFLOWS_DIR.glob("*.yaml"):
    with open(wf_file) as f:
        workflow_type = wf_file.stem
        workflow = yaml.safe_load(f) or {}
        stages = workflow.get("stages")
        if not isinstance(stages, list) or not stages:
            raise ValueError(f"Workflow {workflow_type} must define a non-empty stages list")
        WORKFLOWS[workflow_type] = {"stages": stages}

def get_next_sequence_number(workflow_type):
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"{re.escape(workflow_type)}-\d{{3}}")
    existing = sorted([
        int(d.name.rsplit("-", 1)[1])
        for d in ARTIFACTS_DIR.iterdir()
        if d.is_dir() and pattern.fullmatch(d.name)
    ])
    return f"{existing[-1] + 1:03d}" if existing else "001"

def get_artifact_templates(workflow_type):
    template_dir = ARTIFACT_TEMPLATES_DIR / workflow_type
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Missing artifact template directory: {template_dir}")

    templates = sorted(path for path in template_dir.iterdir() if path.is_file())
    if not templates:
        raise FileNotFoundError(f"No artifact templates found in: {template_dir}")
    return templates

def create_artifact(workflow_type):
    workflow = WORKFLOWS.get(workflow_type)
    if not workflow:
        print(f"Unknown workflow type: {workflow_type}")
        return

    templates = get_artifact_templates(workflow_type)
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

    # Create artifact files from artifact templates, not workflow stages.
    for template in templates:
        with open(template) as src, open(workflow_dir / template.name, "w") as dst:
            dst.write(src.read())

    print(workflow_dir)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python .ai-sdlc/router.py <workflow_type>")
        sys.exit(1)
    create_artifact(sys.argv[1])
