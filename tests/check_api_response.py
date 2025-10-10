"""Check what the update-file API actually returns."""
import json
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"
OBJECT_ID = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"

api = PenpotAPI(debug=True)

# Get current file
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

obj = None
for page_data in pages_index.values():
    if OBJECT_ID in page_data.get('objects', {}):
        obj = page_data['objects'][OBJECT_ID]
        break

# Modify content to YELLOW
content = obj.get('content', {})
fills_content = [{
    'fillColor': '#FFFF00',
    'fillOpacity': 1  # Integer, not float
}]

if 'children' in content:
    for paragraph_set in content['children']:
        if 'children' in paragraph_set:
            for paragraph in paragraph_set['children']:
                paragraph['fills'] = fills_content
                if 'children' in paragraph:
                    for text_node in paragraph['children']:
                        text_node['fills'] = fills_content

# Update
with api.editing_session(FILE_ID) as (session_id, revn):
    ops = [api.create_set_operation('content', content)]
    change = api.create_mod_obj_change(OBJECT_ID, ops)

    print("\n=== Sending update request ===")
    result = api.update_file(FILE_ID, session_id, revn, [change])

    print("\n=== Full API Response ===")
    print(json.dumps(result, indent=2))
    print(f"\nResult type: {type(result)}")
    print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
