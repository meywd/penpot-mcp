"""Check the format of content returned by API vs what we need to send."""
import json
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"

api = PenpotAPI(debug=False)

# Get file
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

# Find the Yellow Test text we just created
yellow_test_obj = None
yellow_test_id = None
for page_data in pages_index.values():
    for obj_id, obj in page_data.get('objects', {}).items():
        if obj.get('name') == 'Yellow Test':
            yellow_test_obj = obj
            yellow_test_id = obj_id
            break
    if yellow_test_obj:
        break

if yellow_test_obj:
    print("=== Yellow Test object (as returned by API) ===")
    content = yellow_test_obj.get('content', {})
    print(json.dumps(content, indent=2))

    print("\n=== Keys in content structure ===")
    if 'children' in content:
        for ps in content['children']:
            if 'children' in ps:
                for para in ps['children']:
                    print(f"Paragraph keys: {list(para.keys())}")
                    if 'children' in para:
                        for text_node in para['children']:
                            print(f"Text node keys: {list(text_node.keys())}")
else:
    print("Yellow Test object not found")
