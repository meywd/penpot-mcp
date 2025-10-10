"""Test changing a rectangle's color to verify our change mechanism works."""
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"

api = PenpotAPI(debug=False)

# Get file
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

# Find a rectangle
rect_obj = None
rect_id = None
for page_data in pages_index.values():
    for obj_id, obj in page_data.get('objects', {}).items():
        if obj.get('type') == 'rect':
            rect_obj = obj
            rect_id = obj_id
            break
    if rect_obj:
        break

if not rect_obj:
    print("No rectangle found in file")
    exit(1)

print(f"Found rectangle: {rect_obj.get('name')} (ID: {rect_id})")
print(f"Current fills: {rect_obj.get('fills', [])}")

# Change to YELLOW
with api.editing_session(FILE_ID) as (session_id, revn):
    fills_object = [{
        'fillColor': '#FFFF00',
        'fillOpacity': 1
    }]

    ops = [api.create_set_operation('fills', fills_object)]
    change = api.create_mod_obj_change(rect_id, ops)

    result = api.update_file(FILE_ID, session_id, revn, [change])
    print(f"\n[SUCCESS] Changed rectangle to YELLOW. Revision: {result.get('revn')}")

# Verify
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})
for page_data in pages_index.values():
    if rect_id in page_data.get('objects', {}):
        obj = page_data['objects'][rect_id]
        fills = obj.get('fills', [])
        if fills and fills[0].get('fillColor') == '#FFFF00':
            print("[OK] Rectangle color changed successfully!")
        else:
            print(f"[X] Rectangle color NOT changed. Current: {fills}")
        break
