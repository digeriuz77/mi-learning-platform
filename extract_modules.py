import json
import re

def extract_modules():
    with open('mi_modules/MI-training-modules.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all JSON blocks
    json_pattern = r'<json>\s*(\{.*?\})\s*</json>'
    matches = re.findall(json_pattern, content, re.DOTALL)
    
    modules = []
    for i, match in enumerate(matches, 1):
        try:
            module_data = json.loads(match)
            modules.append((i, module_data))
        except json.JSONDecodeError as e:
            print(f"Error parsing module {i}: {e}")
    
    return modules

def save_module(module_number, data):
    filename = f'mi_modules/module_{module_number}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved Module {module_number}: {data['dialogue_tree']['title']}")

if __name__ == "__main__":
    modules = extract_modules()
    
    for module_num, module_data in modules:
        save_module(module_num, module_data)
    
    print(f"Successfully extracted {len(modules)} modules")