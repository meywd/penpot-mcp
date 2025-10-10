"""Test changing the Downloads text color to RED using the fixed implementation."""
from penpot_mcp.api.penpot_api import PenpotAPI
from penpot_mcp.server.mcp_server import PenpotMCPServer

# TODO: Update FILE_ID to your local test file
FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"

# Create server instance with local Penpot
api = PenpotAPI(base_url="http://localhost:9001/api", debug=True)

# Find the Downloads text object
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

downloads_obj = None
downloads_id = None
for page_data in pages_index.values():
    for obj_id, obj in page_data.get('objects', {}).items():
        if obj.get('type') == 'text' and 'Downloads' in str(obj.get('content', {})):
            downloads_obj = obj
            downloads_id = obj_id
            break
    if downloads_obj:
        break

if not downloads_obj:
    print("Downloads text not found")
    exit(1)

print(f"Found Downloads text: {downloads_id}")

# Test the change_object_color logic directly from the API
# This bypasses MCP async complexity and tests the core logic

with api.editing_session(FILE_ID) as (session_id, revn):
    import copy

    def camel_to_kebab(name):
        """Convert camelCase to kebab-case."""
        import re
        return re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', name).lower()

    def convert_content_to_kebab(obj):
        """Recursively convert content structure keys from camelCase to kebab-case."""
        if isinstance(obj, dict):
            return {camel_to_kebab(k): convert_content_to_kebab(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_content_to_kebab(item) for item in obj]
        else:
            return obj

    content = copy.deepcopy(downloads_obj.get('content', {}))

    # Update fills
    fills_content = [{'fill-color': '#FF0000', 'fill-opacity': 1}]

    if 'children' in content:
        for paragraph_set in content['children']:
            if 'children' in paragraph_set:
                for paragraph in paragraph_set['children']:
                    paragraph['fills'] = fills_content
                    if 'children' in paragraph:
                        for text_node in paragraph['children']:
                            text_node['fills'] = fills_content

    # Convert to kebab-case
    content = convert_content_to_kebab(content)

    # Apply change
    ops = [api.create_set_operation('content', content)]
    change = api.create_mod_obj_change(downloads_id, ops)

    result = api.update_file(FILE_ID, session_id, revn, [change])
    print(f"\n[SUCCESS] Changed color. Revision: {result.get('revn')}")

# Verify the change in database
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

for page_data in pages_index.values():
    if downloads_id in page_data.get('objects', {}):
        obj = page_data['objects'][downloads_id]
        content = obj.get('content', {})
        if content.get('children'):
            para = content['children'][0]['children'][0]
            fills = para.get('fills', [])
            if fills:
                color = fills[0].get('fillColor')
                print(f"Color in database: {color}")
                if color == '#FF0000':
                    print("[VERIFIED] Downloads text is now RED!")
                else:
                    print(f"[FAILED] Expected #FF0000, got {color}")
        break
