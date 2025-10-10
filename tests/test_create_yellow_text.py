"""Create a NEW text object with yellow color to test if our implementation works."""
import json
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"

# Get page ID
api = PenpotAPI(debug=True)
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})
page_id = list(pages_index.keys())[0]

print(f"Creating new yellow text in file {FILE_ID}, page {page_id}")

# Create a new text object with YELLOW color
obj_id = api.generate_session_id()

with api.editing_session(FILE_ID) as (session_id, revn):
    text = api.create_text(
        x=100, y=50,
        content='TEST YELLOW TEXT',
        name='Yellow Test',
        font_size=24,
        fill_color='#FFFF00',
        font_family='Work Sans'
    )

    print("\n=== Text object (before sending) ===")
    print(json.dumps(text, indent=2))

    change = api.create_add_obj_change(obj_id, page_id, text)

    print("\n=== Change object ===")
    print(json.dumps(change, indent=2))

    result = api.update_file(FILE_ID, session_id, revn, [change])

    print(f"\n[SUCCESS] Created text object: {obj_id}")
    print(f"Revision: {result.get('revn')}")

# Fetch and verify
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

for page_data in pages_index.values():
    if obj_id in page_data.get('objects', {}):
        obj = page_data['objects'][obj_id]
        content = obj.get('content', {})

        # Check the color
        if content.get('children'):
            para = content['children'][0]['children'][0]
            fills = para.get('fills', [])
            if fills:
                color = fills[0].get('fillColor')
                print(f"\nText color in database: {color}")
                if color == '#FFFF00':
                    print("[SUCCESS] New text object is YELLOW!")
                else:
                    print(f"[FAIL] Expected #FFFF00, got {color}")
        break
