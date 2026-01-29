#!/usr/bin/env python3
"""
Generate SQL INSERT statements for learning modules.

Usage:
    python scripts/generate_module_sql.py > scripts/seed_modules.sql

Then copy the contents of seed_modules.sql into Supabase SQL Editor and run it.
"""

import json
import re
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def escape_sql_string(s: str) -> str:
    """Escape single quotes for SQL."""
    if s is None:
        return ''
    return s.replace("'", "''")


def generate_insert(module_number: int, data: dict) -> str:
    """Generate SQL INSERT statement for a module."""
    tree = data.get('dialogue_tree', data)

    title = escape_sql_string(tree.get('title', f'Module {module_number}'))
    slug = slugify(title)
    learning_objective = escape_sql_string(tree.get('learning_objective', ''))
    technique_focus = escape_sql_string(tree.get('technique_focus', ''))
    stage_of_change = escape_sql_string(tree.get('stage_of_change', ''))
    mi_process = escape_sql_string(tree.get('mi_process', ''))
    description = escape_sql_string(tree.get('description', ''))

    # The dialogue content is the nodes array
    dialogue_content = {
        'start_node': tree.get('start_node', 'node_1'),
        'nodes': tree.get('nodes', [])
    }
    dialogue_json = json.dumps(dialogue_content, ensure_ascii=False).replace("'", "''")

    return f"""INSERT INTO public.learning_modules (
    module_number,
    title,
    slug,
    learning_objective,
    technique_focus,
    stage_of_change,
    mi_process,
    description,
    dialogue_content,
    points,
    display_order,
    is_published
) VALUES (
    {module_number},
    '{title}',
    '{slug}',
    '{learning_objective}',
    '{technique_focus}',
    '{stage_of_change}',
    '{mi_process}',
    '{description}',
    '{dialogue_json}'::jsonb,
    500,
    {module_number},
    TRUE
) ON CONFLICT (module_number) DO UPDATE SET
    title = EXCLUDED.title,
    slug = EXCLUDED.slug,
    learning_objective = EXCLUDED.learning_objective,
    technique_focus = EXCLUDED.technique_focus,
    stage_of_change = EXCLUDED.stage_of_change,
    mi_process = EXCLUDED.mi_process,
    description = EXCLUDED.description,
    dialogue_content = EXCLUDED.dialogue_content,
    updated_at = NOW();
"""


def main():
    modules_dir = Path(__file__).parent.parent / 'mi_modules'

    print("-- MI Learning Platform - Module Seed Data")
    print("-- Generated SQL for inserting learning modules")
    print("-- Run this in Supabase SQL Editor after running 001_init_schema.sql")
    print()
    print("-- This uses UPSERT (INSERT ... ON CONFLICT) so it's safe to run multiple times")
    print()

    # Find all module files (module_1.json through module_12.json)
    module_files = []
    for i in range(1, 13):
        path = modules_dir / f'module_{i}.json'
        if path.exists():
            module_files.append((i, path))

    if not module_files:
        print("-- ERROR: No module files found in mi_modules/")
        return

    for module_number, path in module_files:
        print(f"-- Module {module_number}: {path.name}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(generate_insert(module_number, data))
        except Exception as e:
            print(f"-- ERROR loading {path.name}: {e}")
        print()

    print("-- Done! All modules inserted.")
    print(f"-- Total modules: {len(module_files)}")


if __name__ == '__main__':
    main()
