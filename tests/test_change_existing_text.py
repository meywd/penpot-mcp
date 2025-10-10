"""Test changing an EXISTING text object's color to yellow."""
import json
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"

api = PenpotAPI(debug=True)

# Get file
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

# Find a text object
text_obj = None
text_id = None
for page_data in pages_index.values():
    for obj_id, obj in page_data.get('objects', {}).items():
        if obj.get('type') == 'text':
            text_obj = obj
            text_id = obj_id
            break
    if text_obj:
        break

if not text_obj:
    print("No text object found in file")
    exit(1)

print(f"Found text: {text_obj.get('name')} (ID: {text_id})")

# Get current color
content = text_obj.get('content', {})
if content.get('children'):
    para = content['children'][0]['children'][0]
    fills = para.get('fills', [])
    if fills:
        current_color = fills[0].get('fillColor')
        print(f"Current color: {current_color}")

# Change to YELLOW using kebab-case
import copy
with api.editing_session(FILE_ID) as (session_id, revn):
    # Deep copy to avoid modifying cache
    content = copy.deepcopy(text_obj.get('content', {}))

    # Update fills with kebab-case keys
    fills_content = [{
        'fill-color': '#FFFF00',
        'fill-opacity': 1
    }]

    # Update at all levels
    if 'children' in content:
        for paragraph_set in content['children']:
            if 'children' in paragraph_set:
                for paragraph in paragraph_set['children']:
                    paragraph['fills'] = fills_content
                    if 'children' in paragraph:
                        for text_node in paragraph['children']:
                            text_node['fills'] = fills_content

    print("\n=== Updated content structure ===")
    print(json.dumps(content, indent=2))

    # Create change
    ops = [api.create_set_operation('content', content)]
    change = api.create_mod_obj_change(text_id, ops)

    result = api.update_file(FILE_ID, session_id, revn, [change])
    print(f"\n[SUCCESS] Changed text to YELLOW. Revision: {result.get('revn')}")

# Verify
print("\nVerifying color change...")
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})
for page_data in pages_index.values():
    if text_id in page_data.get('objects', {}):
        obj = page_data['objects'][text_id]
        content = obj.get('content', {})
        if content.get('children'):
            para = content['children'][0]['children'][0]
            fills = para.get('fills', [])
            if fills:
                color = fills[0].get('fillColor')
                print(f"New color in database: {color}")
                if color == '#FFFF00':
                    print("[SUCCESS] Text color changed to YELLOW!")
                else:
                    print(f"[FAIL] Expected #FFFF00, got {color}")
        break
