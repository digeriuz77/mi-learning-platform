#!/usr/bin/env python
"""
Convert modules 7-12 from their custom format to the standard module format.

This script:
1. Parses Modules7 and 8.txt and Modules9 to 12.txt
2. Converts to the standard module_1.json format
3. Saves individual JSON files to mi_modules/
"""
import json
import re
from pathlib import Path


def extract_json_from_file(file_path: str) -> dict:
    """Extract JSON content from a file that may have <json> tags."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if wrapped in <json> tags
    json_match = re.search(r'<json>(.*?)</json>', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)

    return json.loads(content)


def convert_module_to_standard_format(module_data: dict, module_number: int) -> dict:
    """
    Convert a module from the new format to the standard format used by modules 1-6.

    New format has:
    - module_id, title, description, learning_objectives (array)
    - nodes with context, is_end_node, summary

    Standard format has:
    - title, learning_objective (string), technique_focus, stage_of_change, mi_process, description
    - nodes with patient_context, is_ending, learning_summary
    """
    # Map module_id to technique focus and MI process
    module_metadata = {
        7: {
            "technique_focus": "Collaborative Climate & Agenda Setting",
            "stage_of_change": "Precontemplation/Contemplation",
            "mi_process": "Engaging/Focusing"
        },
        8: {
            "technique_focus": "Confidence Scaling",
            "stage_of_change": "Contemplation/Preparation",
            "mi_process": "Focusing"
        },
        9: {
            "technique_focus": "Decisional Balance",
            "stage_of_change": "Contemplation",
            "mi_process": "Focusing"
        },
        10: {
            "technique_focus": "Planning & Implementation Intentions",
            "stage_of_change": "Preparation",
            "mi_process": "Planning"
        },
        11: {
            "technique_focus": "Elicit-Provide-Elicit",
            "stage_of_change": "Contemplation/Preparation",
            "mi_process": "Engaging/Focusing"
        },
        12: {
            "technique_focus": "Anticipatory Coping & Relapse Prevention",
            "stage_of_change": "Action/Maintenance",
            "mi_process": "Planning/Following"
        }
    }

    meta = module_metadata.get(module_number, {
        "technique_focus": "MI Skill Practice",
        "stage_of_change": "Contemplation",
        "mi_process": "Engaging"
    })

    # Convert learning objectives array to single string
    learning_objectives = module_data.get('learning_objectives', [])
    if isinstance(learning_objectives, list):
        learning_objective = "; ".join(learning_objectives)
    else:
        learning_objective = str(learning_objectives)

    # Convert nodes
    converted_nodes = []
    for node in module_data.get('nodes', []):
        converted_node = {
            "id": node["id"],
            "patient_statement": node["patient_statement"],
            "patient_context": node.get("context", ""),
        }

        # Handle end nodes differently
        if node.get("is_end_node"):
            converted_node["is_ending"] = True
            converted_node["outcome"] = node.get("outcome", "")
            converted_node["learning_summary"] = node.get("summary", "")
        else:
            # Convert practitioner choices
            converted_node["practitioner_choices"] = []
            for choice in node.get("practitioner_choices", []):
                converted_choice = {
                    "text": choice["text"],
                    "technique": choice["technique"],
                    "next_node_id": choice["next_node_id"],
                    "feedback": choice["feedback"]
                }
                converted_node["practitioner_choices"].append(converted_choice)

        converted_nodes.append(converted_node)

    # Build standard dialogue_tree format
    dialogue_tree = {
        "title": module_data.get("title", f"Module {module_number}"),
        "learning_objective": learning_objective,
        "technique_focus": meta["technique_focus"],
        "stage_of_change": meta["stage_of_change"],
        "mi_process": meta["mi_process"],
        "description": module_data.get("description", ""),
        "start_node": module_data.get("start_node", ""),
        "nodes": converted_nodes
    }

    return {"dialogue_tree": dialogue_tree}


def main():
    """Convert modules 7-12 and save to mi_modules/"""
    root_dir = Path(__file__).parent.parent
    modules_dir = root_dir / "mi_modules"

    print("Converting modules 7-12...")

    # Process Modules7 and 8.txt
    file_7_8 = root_dir / "Modules7 and 8.txt"
    if file_7_8.exists():
        print(f"\nProcessing: {file_7_8.name}")
        data = extract_json_from_file(str(file_7_8))

        if "modules" in data:
            for module in data["modules"]:
                # Extract module number from module_id
                module_id = module.get("module_id", "")
                match = re.search(r'module_(\d+)', module_id)
                if match:
                    module_num = int(match.group(1))
                    converted = convert_module_to_standard_format(module, module_num)

                    output_file = modules_dir / f"module_{module_num}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(converted, f, indent=2, ensure_ascii=False)

                    print(f"  ✓ Created module_{module_num}.json")
    else:
        print(f"  ❌ File not found: {file_7_8}")

    # Process Modules9 to 12.txt
    file_9_12 = root_dir / "Modules9 to 12.txt"
    if file_9_12.exists():
        print(f"\nProcessing: {file_9_12.name}")
        data = json.loads(file_9_12.read_text(encoding='utf-8'))

        if isinstance(data, dict) and "modules" in data:
            for module in data["modules"]:
                module_id = module.get("module_id", "")
                match = re.search(r'module_(\d+)', module_id)
                if match:
                    module_num = int(match.group(1))
                    converted = convert_module_to_standard_format(module, module_num)

                    output_file = modules_dir / f"module_{module_num}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(converted, f, indent=2, ensure_ascii=False)

                    print(f"  ✓ Created module_{module_num}.json")
        elif isinstance(data, list):
            for module in data:
                module_id = module.get("module_id", "")
                match = re.search(r'module_(\d+)', module_id)
                if match:
                    module_num = int(match.group(1))
                    converted = convert_module_to_standard_format(module, module_num)

                    output_file = modules_dir / f"module_{module_num}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(converted, f, indent=2, ensure_ascii=False)

                    print(f"  ✓ Created module_{module_num}.json")
    else:
        print(f"  ❌ File not found: {file_9_12}")

    print(f"\n✅ Conversion complete! Modules saved to {modules_dir}")


if __name__ == "__main__":
    main()
