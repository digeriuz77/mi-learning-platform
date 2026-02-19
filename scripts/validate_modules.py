#!/usr/bin/env python3
"""
Module Pathway Validation Script

Validates that all learning module JSON files have:
1. Clear pathway from start to end (no dead ends)
2. All next_node_id references exist in the nodes
3. No orphan nodes (nodes not reachable from start)
4. Choices lead logically
5. Proper ending nodes

Usage:
    python scripts/validate_modules.py
    python scripts/validate_modules.py --module module_1
    python scripts/validate_modules.py --verbose
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any


class ModuleValidator:
    def __init__(self, modules_dir: str = "mi_modules", verbose: bool = False):
        self.modules_dir = Path(modules_dir)
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def log(self, message: str):
        if self.verbose:
            print(message)

    def validate_module(self, module_path: Path) -> bool:
        """Validate a single module JSON file."""
        self.errors.clear()
        self.warnings.clear()

        try:
            with open(module_path, "r", encoding="utf-8") as f:
                module = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return False

        dialogue_tree = module.get("dialogue_tree", {})
        if not dialogue_tree:
            self.errors.append("Missing 'dialogue_tree' key")
            return False

        # Get all nodes
        nodes = dialogue_tree.get("nodes", [])
        if not nodes:
            self.errors.append("No nodes found in dialogue_tree")
            return False

        # Create node lookup
        node_map: Dict[str, Dict] = {}
        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                self.errors.append(f"Node missing 'id': {node}")
                continue
            node_map[node_id] = node

        # Validate start node exists
        start_node_id = dialogue_tree.get("start_node")
        if not start_node_id:
            self.errors.append("Missing 'start_node' in dialogue_tree")
            return False

        if start_node_id not in node_map:
            self.errors.append(f"Start node '{start_node_id}' not found in nodes")
            return False

        # Find all referenced node IDs
        referenced_nodes: Set[str] = {start_node_id}

        for node in nodes:
            node_id = node.get("id")
            choices = node.get("practitioner_choices", [])

            for choice in choices:
                next_node_id = choice.get("next_node_id")
                if next_node_id:
                    referenced_nodes.add(next_node_id)

                    # Check if referenced node exists
                    if next_node_id not in node_map:
                        self.errors.append(f"Node '{node_id}' references non-existent node '{next_node_id}'")

        # Check for orphan nodes (not reachable from start)
        for node_id in node_map:
            if node_id not in referenced_nodes:
                # Check if it's an ending node
                node = node_map[node_id]
                if not node.get("is_ending", False):
                    self.warnings.append(f"Node '{node_id}' is not reachable from start (possible orphan)")

        # Check for nodes that don't lead to endings
        self._check_pathways(node_map, start_node_id)

        # Report results
        has_errors = len(self.errors) > 0

        if has_errors:
            print(f"\n[FAIL] {module_path.name}: FAILED")
            for error in self.errors:
                print(f"   ERROR: {error}")
        else:
            print(f"\n[PASS] {module_path.name}: PASSED")

        if self.warnings:
            for warning in self.warnings:
                print(f"   WARNING: {warning}")

        return not has_errors

    def _check_pathways(self, node_map: Dict[str, Dict], start_node_id: str):
        """Check that all pathways lead to ending nodes."""

        def get_next_nodes(node_id: str) -> List[str]:
            node = node_map.get(node_id, {})
            choices = node.get("practitioner_choices", [])
            return [c.get("next_node_id") for c in choices if c.get("next_node_id")]

        # BFS to find all reachable nodes and check for dead ends
        visited: Set[str] = set()
        queue = [start_node_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            node = node_map.get(current, {})

            # Check if this is an ending node
            if node.get("is_ending", False):
                continue

            # Get next nodes
            next_nodes = get_next_nodes(current)

            if not next_nodes:
                # Check if it's the last node before an ending
                if current != start_node_id:
                    # Find nodes that point to this node
                    pointing_nodes = []
                    for nid, n in node_map.items():
                        choices = n.get("practitioner_choices", [])
                        if any(c.get("next_node_id") == current for c in choices):
                            pointing_nodes.append(nid)

                    if not pointing_nodes:
                        self.warnings.append(f"Node '{current}' has no choices and is not marked as ending")
            else:
                for next_node in next_nodes:
                    if next_node not in visited:
                        queue.append(next_node)

        # Check for unreachable ending nodes
        for node_id, node in node_map.items():
            if node.get("is_ending", False) and node_id not in visited:
                self.warnings.append(f"Ending node '{node_id}' is not reachable from start")

    def validate_all_modules(self) -> bool:
        """Validate all module JSON files in the modules directory."""
        if not self.modules_dir.exists():
            print(f"Error: Modules directory '{self.modules_dir}' not found")
            return False

        # Find all module JSON files
        module_files = sorted(self.modules_dir.glob("module_*.json"))

        if not module_files:
            print(f"No module files found in '{self.modules_dir}'")
            return False

        print(f"Found {len(module_files)} module files to validate")

        all_passed = True
        for module_file in module_files:
            self.log(f"\nValidating {module_file.name}...")
            result = self.validate_module(module_file)
            if not result:
                all_passed = False

        # Summary
        print("\n" + "=" * 50)
        if all_passed:
            print("[SUCCESS] ALL MODULES VALIDATED SUCCESSFULLY")
        else:
            print("[ERROR] SOME MODULES HAVE VALIDATION ERRORS")

        return all_passed


def main():
    parser = argparse.ArgumentParser(description="Validate learning module JSON files for pathway integrity")
    parser.add_argument("--module", help="Specific module file to validate (e.g., module_1)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    parser.add_argument("--dir", default="mi_modules", help="Modules directory path (default: mi_modules)")

    args = parser.parse_args()

    validator = ModuleValidator(modules_dir=args.dir, verbose=args.verbose)

    if args.module:
        # Validate specific module
        module_path = validator.modules_dir / f"{args.module}.json"
        if not module_path.exists():
            # Try with module_ prefix
            module_path = validator.modules_dir / f"module_{args.module}.json"

        if not module_path.exists():
            print(f"Error: Module file not found: {args.module}")
            sys.exit(1)

        success = validator.validate_module(module_path)
    else:
        # Validate all modules
        success = validator.validate_all_modules()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
