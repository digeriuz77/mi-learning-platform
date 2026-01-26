from django.core.management.base import BaseCommand
from django.db import transaction
from game.models import DialogueTree, DialogueNode, PractitionerChoice, Scenario
import json
import os

class Command(BaseCommand):
    help = 'Import MI dialogue trees from JSON files'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to JSON file containing dialogue tree')
        parser.add_argument('--module', type=int, help='Module number (1-6)')

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        module_number = options.get('module', 1)
        
        if not os.path.exists(json_file_path):
            self.stdout.write(self.style.ERROR(f'JSON file not found: {json_file_path}'))
            return

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with transaction.atomic():
                self.import_dialogue_tree(data, module_number)
                
            self.stdout.write(
                self.style.SUCCESS(f'Successfully imported Module {module_number}: {data["dialogue_tree"]["title"]}')
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Invalid JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Import failed: {e}'))

    def import_dialogue_tree(self, data, module_number):
        dialogue_tree_data = data['dialogue_tree']
        
        # Create Scenario
        scenario = Scenario.objects.create(
            title=dialogue_tree_data['title'],
            description=dialogue_tree_data['description'],
            module_number=module_number,
            scenario_type='scenario',
            difficulty='intermediate' if module_number > 1 else 'beginner',
            points=500  # Base points for completing modules
        )
        
        # Create DialogueTree
        tree = DialogueTree.objects.create(
            title=dialogue_tree_data['title'],
            learning_objective=dialogue_tree_data['learning_objective'],
            technique_focus=dialogue_tree_data['technique_focus'],
            stage_of_change=dialogue_tree_data['stage_of_change'],
            mi_process=dialogue_tree_data['mi_process'],
            description=dialogue_tree_data['description'],
            start_node=dialogue_tree_data['start_node'],
            module_number=module_number
        )
        
        # Import nodes
        nodes = {}
        for node_data in dialogue_tree_data['nodes']:
            node = DialogueNode.objects.create(
                tree=tree,
                node_id=node_data['id'],
                patient_statement=node_data.get('patient_statement', ''),
                patient_context=node_data.get('patient_context', ''),
                change_talk_present=node_data.get('change_talk_present', False),
                change_talk_type=node_data.get('change_talk_type', ''),
                is_ending=node_data.get('is_ending', False),
                outcome=node_data.get('outcome', ''),
                learning_summary=node_data.get('learning_summary', ''),
                order=int(node_data['id'].split('_')[-1])
            )
            nodes[node_data['id']] = node
        
        # Import practitioner choices
        for node_data in dialogue_tree_data['nodes']:
            if 'practitioner_choices' in node_data:
                node = nodes[node_data['id']]
                for choice_data in node_data['practitioner_choices']:
                    PractitionerChoice.objects.create(
                        node=node,
                        text=choice_data['text'],
                        technique=choice_data['technique'],
                        next_node_id=choice_data['next_node_id'],
                        feedback=choice_data['feedback'],
                        is_correct_technique='effective' in choice_data.get('technique', '').lower(),
                        is_mistake=('ineffective' in choice_data.get('technique', '').lower() or 
                                   'non-MI' in choice_data.get('technique', '').lower())
                    )
        
        self.stdout.write(f'Created {len(nodes)} nodes with practitioner choices')