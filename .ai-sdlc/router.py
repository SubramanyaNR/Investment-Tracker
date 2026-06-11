import sys
import yaml
from pathlib import Path
from datetime import datetime
import re
from models import get_model

AI_SDLC_DIR = Path(__file__).parent
ARTIFACTS_DIR = AI_SDLC_DIR / "artifacts"
ARTIFACT_TEMPLATES_DIR = ARTIFACTS_DIR / "templates"
PROMPT_TEMPLATES_DIR = AI_SDLC_DIR / "templates"
WORKFLOWS_DIR = AI_SDLC_DIR / "workflows"
CONTEXT_DIR = AI_SDLC_DIR / "context"

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

def get_prompt_template(prompt_name):
    template_path = PROMPT_TEMPLATES_DIR / f"{prompt_name}_prompt.md"
    if not template_path.is_file():
        raise FileNotFoundError(f"Missing prompt template: {template_path}")
    return template_path

def read_text(path):
    with open(path) as f:
        return f.read()

def render_template(template_text, replacements):
    rendered = template_text
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered

def validate_required_files(paths):
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(missing))

def write_prompt(prompt_name, artifact_dir, file_map):
    """
    Validates existence of input files, reads them, and renders a prompt template.
    file_map: dict of {placeholder: Path}
    """
    input_files = list(file_map.values())
    validate_required_files(input_files)

    template_path = get_prompt_template(prompt_name)
    template_text = read_text(template_path)

    replacements = {
        placeholder: read_text(path)
        for placeholder, path in file_map.items()
    }

    rendered = render_template(template_text, replacements)
    output_path = artifact_dir / f"{prompt_name}_prompt.md"
    with open(output_path, "w") as f:
        f.write(rendered)
    print(output_path)

def load_status(workflow_dir):
    status_path = workflow_dir / "status.yaml"
    with open(status_path) as f:
        return yaml.safe_load(f)

def save_status(workflow_dir, status_data):
    status_path = workflow_dir / "status.yaml"
    with open(status_path, "w") as f:
        yaml.dump(status_data, f, sort_keys=False)

def show_status(workflow_dir):
    try:
        status = load_status(workflow_dir)
        print(f"Workflow: {status.get('id', 'unknown')}")
        print(f"Type: {status.get('workflow', 'unknown')}")
        print(f"Current Stage: {status.get('stage', 'unknown')}")
        print(f"Status: {status.get('status', 'unknown')}")
        print(f"Approved: {status.get('approved', False)}")
    except (yaml.YAMLError, AttributeError, KeyError) as exc:
        print(f"Error: Could not read status file in {workflow_dir}")

def approve_workflow(workflow_dir):
    try:
        status = load_status(workflow_dir)
        if status.get("status") == "completed":
            print(f"Workflow '{status['id']}' is already completed.")
            return
            
        status["approved"] = True
        save_status(workflow_dir, status)
        print(f"Approved {status['id']} for current stage: {status['stage']}")
    except (yaml.YAMLError, KeyError) as exc:
        print(f"Error: Corrupted or invalid status file in {workflow_dir}")

def advance_workflow(workflow_dir):
    try:
        status = load_status(workflow_dir)
        workflow_type = status["workflow"]
        current_stage = status["stage"]
        workflow_status = status.get("status", "active")
        is_approved = status.get("approved", False)
        
        if workflow_status == "completed":
            print(f"Workflow '{status['id']}' is already completed and cannot be advanced.")
            return

        if not is_approved:
            print(f"Workflow '{status['id']}' requires human approval before advancing from stage: {current_stage}")
            print(f"Run: python .ai-sdlc/router.py approve {status['id']}")
            return

        stages = WORKFLOWS[workflow_type]["stages"]
        current_idx = stages.index(current_stage)
            
        if current_idx >= len(stages) - 1:
            print(f"Workflow '{status['id']}' is already at the final stage: {current_stage}")
            return

        next_stage = stages[current_idx + 1]
        status["stage"] = next_stage
        status["approved"] = False  # Reset approval for the next stage
        save_status(workflow_dir, status)
        print(f"Advanced {status['id']} to: {next_stage}")
    except (yaml.YAMLError, KeyError, ValueError) as exc:
        print(f"Error: Corrupted or invalid status file in {workflow_dir}")

def complete_workflow(workflow_dir):
    status = load_status(workflow_dir)
    status["status"] = "completed"
    save_status(workflow_dir, status)
    print(f"Marked {status['id']} as completed")

def list_workflows():
    if not ARTIFACTS_DIR.exists():
        print("No workflows found.")
        return

    # Grouping logic
    # type_label -> [ (id, stage) ]
    groups = {
        "feature": "Features",
        "incident": "Incidents",
        "architecture": "Architectures",
        "discuss": "Discussions",
        "secure": "Security",
        "release": "Releases"
    }
    
    found = {k: [] for k in groups}
    others = []

    for d in sorted(ARTIFACTS_DIR.iterdir()):
        if d.is_dir() and (d / "status.yaml").exists():
            status = load_status(d)
            wf_type = status["workflow"]
            entry = f"{status['id']} -> {status['stage']}"
            if status["status"] == "completed":
                entry += " (completed)"
                
            if wf_type in found:
                found[wf_type].append(entry)
            else:
                others.append(f"{entry} [{wf_type}]")

    first = True
    for wf_type, label in groups.items():
        if found[wf_type]:
            if not first: print()
            print(label)
            print()
            for entry in found[wf_type]:
                print(entry)
            first = False

    if others:
        if not first: print()
        print("Other Workflows")
        print()
        for entry in others:
            print(entry)

def show_dashboard():
    if not ARTIFACTS_DIR.exists():
        print("No workflows found.")
        return

    groups = {
        "feature": "Active Features",
        "discuss": "Active Discussions",
        "incident": "Active Incidents",
        "secure": "Active Security Reviews",
        "architecture": "Active Architectures",
        "release": "Active Releases"
    }
    
    active_by_type = {k: [] for k in groups}
    completed_list = []
    stats = {k: 0 for k in groups}
    total_active = 0
    total_completed = 0

    now = datetime.now()

    for d in sorted(ARTIFACTS_DIR.iterdir()):
        if d.is_dir() and (d / "status.yaml").exists():
            status = load_status(d)
            wf_type = status["workflow"]
            
            # Age calculation
            created_at_str = status.get("created_at")
            age_days = 0
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_days = (now - created_at).days
                except ValueError:
                    pass
            
            age_display = f"{age_days} days" if age_days != 1 else "1 day"
            
            entry = {
                "id": status["id"],
                "stage": status["stage"],
                "status": status["status"],
                "age": age_display,
                "approved": status.get("approved", False)
            }

            if status["status"] == "completed":
                completed_list.append(status["id"])
                total_completed += 1
            else:
                if wf_type in active_by_type:
                    active_by_type[wf_type].append(entry)
                total_active += 1
            
            if wf_type in stats:
                stats[wf_type] += 1

    print("=====================================")
    print("AI SDLC Dashboard")
    print("=================")
    print()

    first_active = True
    for wf_type, label in groups.items():
        if active_by_type[wf_type]:
            if not first_active: print("---")
            print(label)
            print()
            for entry in active_by_type[wf_type]:
                approval_tag = "[APPROVED]" if entry["approved"] else "(needs approval)"
                print(f"{entry['id']} {approval_tag}")
                print(f"Stage: {entry['stage']}")
                print(f"Status: {entry['status']}")
                print(f"Age: {entry['age']}")
                print()
            first_active = False

    if completed_list:
        print("---")
        print("Completed Workflows")
        print()
        print(", ".join(completed_list))
        print()

    print("Summary")
    print()
    for wf_type, label in groups.items():
        # Strip "Active " prefix for summary labels
        clean_label = label.replace("Active ", "")
        print(f"{clean_label}: {stats[wf_type]}")
    
    print()
    print(f"Active: {total_active}")
    print(f"Completed: {total_completed}")
    print("=====================================")

def create_artifact(workflow_type):
    workflow = WORKFLOWS.get(workflow_type)
    if not workflow:
        print(f"Unknown workflow type: {workflow_type}")
        return

    templates = get_artifact_templates(workflow_type)
    workflow_dir = ARTIFACTS_DIR / f"{workflow_type}-{get_next_sequence_number(workflow_type)}"
    workflow_dir.mkdir(exist_ok=True)

    # Create status.yaml
    status_data = {
        "workflow": workflow_type,
        "id": workflow_dir.name,
        "stage": workflow["stages"][0],
        "status": "active",
        "approved": False,
        "created_at": datetime.now().isoformat()
    }
    for model_key, model_value in MODELS.items():
        status_data[f"model_{model_key}"] = model_value
        
    save_status(workflow_dir, status_data)

    # Create artifact files from artifact templates, not workflow stages.
    for template in templates:
        with open(template) as src, open(workflow_dir / template.name, "w") as dst:
            dst.write(src.read())

    return workflow_dir

def generate_planning_prompt(workflow_dir):
    write_prompt(
        "planning",
        workflow_dir,
        {
            "{{PRODUCT_CONTEXT}}": CONTEXT_DIR / "product.md",
            "{{ARCHITECTURE_CONTEXT}}": CONTEXT_DIR / "architecture.md",
            "{{GOVERNANCE_CONTEXT}}": CONTEXT_DIR / "governance.md",
            "{{INVESTOR_EXPERIENCE_CONTEXT}}": CONTEXT_DIR / "investor_experience.md",
            "{{REQUEST}}": workflow_dir / "request.md"
        }
    )

def generate_implementation_prompt(workflow_dir):
    write_prompt(
        "implementation",
        workflow_dir,
        {
            "{{PRODUCT_CONTEXT}}": CONTEXT_DIR / "product.md",
            "{{ARCHITECTURE_CONTEXT}}": CONTEXT_DIR / "architecture.md",
            "{{GOVERNANCE_CONTEXT}}": CONTEXT_DIR / "governance.md",
            "{{PLANNING}}": workflow_dir / "planning.md"
        }
    )

def generate_qa_prompt(workflow_dir):
    write_prompt(
        "qa",
        workflow_dir,
        {
            "{{PRODUCT_CONTEXT}}": CONTEXT_DIR / "product.md",
            "{{ARCHITECTURE_CONTEXT}}": CONTEXT_DIR / "architecture.md",
            "{{INVESTOR_EXPERIENCE_CONTEXT}}": CONTEXT_DIR / "investor_experience.md",
            "{{PLANNING}}": workflow_dir / "planning.md",
            "{{IMPLEMENTATION}}": workflow_dir / "implementation.md"
        }
    )

def generate_audit_prompt(workflow_dir):
    write_prompt(
        "audit",
        workflow_dir,
        {
            "{{PRODUCT_CONTEXT}}": CONTEXT_DIR / "product.md",
            "{{ARCHITECTURE_CONTEXT}}": CONTEXT_DIR / "architecture.md",
            "{{GOVERNANCE_CONTEXT}}": CONTEXT_DIR / "governance.md",
            "{{SECURITY_CONTEXT}}": CONTEXT_DIR / "security.md",
            "{{INVESTOR_EXPERIENCE_CONTEXT}}": CONTEXT_DIR / "investor_experience.md",
            "{{PLANNING}}": workflow_dir / "planning.md",
            "{{IMPLEMENTATION}}": workflow_dir / "implementation.md",
            "{{QA}}": workflow_dir / "qa.md"
        }
    )

def run_pipeline(command, workflow_dir):
    # Mapping of command to prompt generation function and output file
    pipeline_map = {
        "planning": (generate_planning_prompt, "planning.md"),
        "implementation": (generate_implementation_prompt, "implementation.md"),
        "qa": (generate_qa_prompt, "qa.md"),
        "audit": (generate_audit_prompt, "audit.md")
    }
    
    if command not in pipeline_map:
        print(f"Error: Command '{command}' not supported for run pipeline.")
        sys.exit(1)
        
    prompt_gen_func, output_filename = pipeline_map[command]
    
    # 1. Generate Prompt (uses existing logic and writes *_prompt.md)
    prompt_gen_func(workflow_dir)
        
    prompt_path = workflow_dir / f"{command}_prompt.md"
    prompt_text = read_text(prompt_path)
    
    # 2. Determine model from models.yaml
    model_name = MODELS.get(command)
    if not model_name:
        print(f"Error: No model mapping found for stage '{command}' in models.yaml")
        sys.exit(1)
        
    # 3. Load adapter from registry
    try:
        adapter = get_model(model_name)
    except ValueError as exc:
        print(str(exc))
        sys.exit(1)
        
    # 4. Call adapter.run(prompt)
    print(f"Executing {command} with {model_name}...")
    result = adapter.run(prompt_text)
    
    # 5. Write result to artifact file
    output_path = workflow_dir / output_filename
    with open(output_path, "w") as f:
        f.write(result)
    print(f"Result written to {output_path}")

def resolve_workflow_dir(workflow_id):
    workflow_dir = ARTIFACTS_DIR / workflow_id
    if not workflow_dir.is_dir():
        raise FileNotFoundError(f"Missing workflow directory: {workflow_dir}")
    return workflow_dir

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python .ai-sdlc/router.py <command|workflow_type> [subcommand] [workflow_id]")
        sys.exit(1)
        
    command = sys.argv[1]
    
    # Commands that don't require workflow_id
    if len(sys.argv) == 2:
        if command == "list":
            list_workflows()
        elif command == "dashboard":
            show_dashboard()
        else:
            workflow_dir = create_artifact(command)
            if workflow_dir:
                print(workflow_dir)
        sys.exit(0)

    # Commands that require workflow_id
    if len(sys.argv) == 3:
        workflow_id = sys.argv[2]
        try:
            workflow_dir = resolve_workflow_dir(workflow_id)
            if command == "status":
                show_status(workflow_dir)
            elif command == "approve":
                approve_workflow(workflow_dir)
            elif command == "advance":
                advance_workflow(workflow_dir)
            elif command == "complete":
                complete_workflow(workflow_dir)
            elif command == "planning":
                generate_planning_prompt(workflow_dir)
            elif command == "implementation":
                generate_implementation_prompt(workflow_dir)
            elif command == "qa":
                generate_qa_prompt(workflow_dir)
            elif command == "audit":
                generate_audit_prompt(workflow_dir)
            else:
                print(f"Unknown command: {command}")
                sys.exit(1)
        except FileNotFoundError as exc:
            print(str(exc))
            sys.exit(1)
    elif len(sys.argv) == 4:
        if command == "run":
            subcommand = sys.argv[2]
            workflow_id = sys.argv[3]
            try:
                workflow_dir = resolve_workflow_dir(workflow_id)
                run_pipeline(subcommand, workflow_dir)
            except FileNotFoundError as exc:
                print(str(exc))
                sys.exit(1)
        else:
            print("Usage: python .ai-sdlc/router.py <command|workflow_type> [subcommand] [workflow_id]")
            sys.exit(1)
    else:
        print("Usage: python .ai-sdlc/router.py <command|workflow_type> [subcommand] [workflow_id]")
        sys.exit(1)
