"""Compare the content structure we're sending vs what's stored."""
import json
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"
OBJECT_ID = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"

api = PenpotAPI(debug=False)

# Get current state
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

obj = None
for page_data in pages_index.values():
    if OBJECT_ID in page_data.get('objects', {}):
        obj = page_data['objects'][OBJECT_ID]
        break

if not obj:
    print(f"ERROR: Object {OBJECT_ID} not found")
    exit(1)

print("=== CURRENT STORED CONTENT ===")
stored_content = obj.get('content', {})
print(json.dumps(stored_content, indent=2, sort_keys=True))

# Build what we would send
modified_content = json.loads(json.dumps(stored_content))  # Deep copy

fills_content = [{
    'fillColor': '#FFFF00',
    'fillOpacity': 1.0
}]

if 'children' in modified_content:
    for paragraph_set in modified_content['children']:
        if 'children' in paragraph_set:
            for paragraph in paragraph_set['children']:
                paragraph['fills'] = fills_content
                if 'children' in paragraph:
                    for text_node in paragraph['children']:
                        text_node['fills'] = fills_content

print("\n=== MODIFIED CONTENT WE WOULD SEND ===")
print(json.dumps(modified_content, indent=2, sort_keys=True))

print("\n=== DIFFERENCES ===")

# Check for differences
def compare_dicts(d1, d2, path=""):
    diffs = []
    all_keys = set(d1.keys()) | set(d2.keys())
    for key in all_keys:
        current_path = f"{path}.{key}" if path else key
        if key not in d1:
            diffs.append(f"MISSING in stored: {current_path} = {d2[key]}")
        elif key not in d2:
            diffs.append(f"MISSING in modified: {current_path} = {d1[key]}")
        elif type(d1[key]) != type(d2[key]):
            diffs.append(f"TYPE DIFF at {current_path}: {type(d1[key])} vs {type(d2[key])}")
        elif isinstance(d1[key], dict):
            diffs.extend(compare_dicts(d1[key], d2[key], current_path))
        elif isinstance(d1[key], list):
            if len(d1[key]) != len(d2[key]):
                diffs.append(f"LENGTH DIFF at {current_path}: {len(d1[key])} vs {len(d2[key])}")
            else:
                for i, (item1, item2) in enumerate(zip(d1[key], d2[key])):
                    if isinstance(item1, dict) and isinstance(item2, dict):
                        diffs.extend(compare_dicts(item1, item2, f"{current_path}[{i}]"))
                    elif item1 != item2:
                        diffs.append(f"VALUE DIFF at {current_path}[{i}]: {item1} vs {item2}")
        elif d1[key] != d2[key]:
            diffs.append(f"VALUE DIFF at {current_path}: {d1[key]} vs {d2[key]}")
    return diffs

diffs = compare_dicts(stored_content, modified_content)
if diffs:
    for diff in diffs:
        print(diff)
else:
    print("No structural differences (only fill values changed)")
