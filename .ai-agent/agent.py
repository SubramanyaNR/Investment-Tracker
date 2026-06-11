import sys
from pathlib import Path

# Add .ai-sdlc to path for reusing router logic
AI_SDLC_DIR = Path(__file__).parent.parent / ".ai-sdlc"
sys.path.append(str(AI_SDLC_DIR))

from router import (
    create_artifact, run_pipeline, read_text, 
    resolve_workflow_dir, show_status, approve_workflow, 
    advance_workflow, load_status
)

def handle_feature(description):
    if not description:
        print("Error: /feature requires a description.")
        return

    print(f"Starting feature workflow for: {description}")

    # 1. Create workflow
    workflow_dir = create_artifact("feature")
    if not workflow_dir:
        print("Error: Failed to create feature workflow.")
        return

    # 2. Populate request.md
    request_path = workflow_dir / "request.md"
    with open(request_path, "w") as f:
        f.write(description)
    
    # 3. Run planning
    print(f"Running planning for {workflow_dir.name}...")
    run_pipeline("planning", workflow_dir)

    # 4. Read planning.md and return summary
    planning_path = workflow_dir / "planning.md"
    if planning_path.exists():
        summary = read_text(planning_path)
        print("\n=== Planning Summary ===\n")
        print(summary)
        print("\n========================\n")
    else:
        print("Error: planning.md was not generated.")

def handle_status(workflow_id):
    if not workflow_id:
        print("Error: /status requires a workflow ID.")
        return
    try:
        workflow_dir = resolve_workflow_dir(workflow_id)
        show_status(workflow_dir)
    except FileNotFoundError as exc:
        print(str(exc))

def handle_approve(workflow_id):
    if not workflow_id:
        print("Error: /approve requires a workflow ID.")
        return
        
    try:
        workflow_dir = resolve_workflow_dir(workflow_id)
        
        # 1. Approve current stage
        status = load_status(workflow_dir)
        old_stage = status.get("stage")
        approve_workflow(workflow_dir)
        
        # 2. Advance workflow
        advance_workflow(workflow_dir)
        
        # Check if advanced
        new_status = load_status(workflow_dir)
        new_stage = new_status.get("stage")
        
        if new_stage == old_stage:
            # Workflow didn't advance (e.g. final stage or other block)
            return
            
        # 3. Execute next stage automatically (if supported)
        supported_stages = ["planning", "implementation", "qa", "audit"]
        if new_stage in supported_stages:
            print(f"Running {new_stage} for {workflow_dir.name}...")
            try:
                run_pipeline(new_stage, workflow_dir)
                
                # 4. Return summary of generated artifact
                artifact_path = workflow_dir / f"{new_stage}.md"
                if artifact_path.exists():
                    summary = read_text(artifact_path)
                    print(f"\n=== {new_stage.capitalize()} Summary ===\n")
                    print(summary)
                    print("\n========================\n")
                else:
                    print(f"Error: {new_stage}.md was not generated.")
            except SystemExit:
                print(f"Failed to execute pipeline for {new_stage}.")
        else:
            print(f"Advanced to manual or unsupported stage: {new_stage}. No automated pipeline executed.")
            
    except FileNotFoundError as exc:
        print(str(exc))

def main():
    if len(sys.argv) < 2:
        print("Usage: python .ai-agent/agent.py \"<command>\"")
        sys.exit(1)

    user_input = sys.argv[1].strip()
    
    parts = user_input.split(" ", 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    if command == "/feature":
        handle_feature(args)
    elif command == "/status":
        handle_status(args)
    elif command == "/approve":
        handle_approve(args)
    else:
        print(f"Unknown command or not a command: {user_input}")
        sys.exit(1)

if __name__ == "__main__":
    main()
