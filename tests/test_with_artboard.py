"""Test creating shapes inside an artboard."""
import json
from penpot_mcp.api.penpot_api import PenpotAPI

# Create API client
api = PenpotAPI(debug=True)

# Get team
teams = api.get_teams()
team_id = teams[0]['id']

# Create project
project_name = "Artboard Test"
project = api.create_project(project_name, team_id)
project_id = project['id']
print(f"\nCreated project: {project_id}")

# Create file
file_name = "Test With Artboard"
file = api.create_file(file_name, project_id)
file_id = file['id']
print(f"Created file: {file_id}")

# Get page ID
file_data = api.get_file(file_id)
pages = file_data.get('data', {}).get('pages', [])
page_id = pages[0] if isinstance(pages[0], str) else pages[0]['id']
print(f"Page ID: {page_id}")

print("\n" + "="*60)
print("STEP 1: Create an artboard (frame) on the page")
print("="*60)

# Create an artboard first
artboard_id = api.generate_session_id()
print(f"Artboard ID: {artboard_id}")

with api.editing_session(file_id) as (session_id, revn):
    # Create a proper-sized artboard
    artboard = api.create_frame(
        x=0, y=0,
        width=1920, height=1080,
        name="Desktop Artboard"
    )

    # Add the artboard to the page
    change = api.create_add_obj_change(artboard_id, page_id, artboard)
    result = api.update_file(file_id, session_id, revn, [change])
    print(f"Added artboard, new revision: {result.get('revn')}")

print("\n" + "="*60)
print("STEP 2: Add a rectangle INSIDE the artboard")
print("="*60)

rect_id = api.generate_session_id()
print(f"Rectangle ID: {rect_id}")

with api.editing_session(file_id) as (session_id, revn):
    # Create rectangle
    rect = api.create_rectangle(
        x=100, y=100, width=200, height=150,
        name="Red Rectangle",
        fill_color="#FF0000"
    )

    # Add the rectangle to the ARTBOARD (not the page)
    change = api.create_add_obj_change(rect_id, page_id, rect, frame_id=artboard_id)
    result = api.update_file(file_id, session_id, revn, [change])
    print(f"Added rectangle, new revision: {result.get('revn')}")

# Verify
print("\n" + "="*60)
print("VERIFICATION")
print("="*60)

file_data = api.get_file(file_id)
pages_index = file_data.get('data', {}).get('pagesIndex', {})
page_data = pages_index.get(page_id, {})
objects = page_data.get('objects', {})

print(f"\nObjects in page: {len(objects)}")
for obj_id, obj in objects.items():
    print(f"  - {obj.get('type')}: {obj.get('name')} (ID: {obj_id})")
    print(f"    parent: {obj.get('parentId')}, frame: {obj.get('frameId')}")
    if obj.get('type') == 'frame' and 'shapes' in obj:
        print(f"    children: {obj.get('shapes', [])}")

# Check if our shapes are there
if artboard_id in objects:
    print(f"\n✓ Artboard found!")
    artboard_obj = objects[artboard_id]
    if rect_id in artboard_obj.get('shapes', []):
        print(f"✓ Rectangle is a child of the artboard!")
    else:
        print(f"✗ Rectangle NOT in artboard children")

if rect_id in objects:
    print(f"✓ Rectangle found!")
else:
    print(f"✗ Rectangle NOT found")

# Cleanup
print(f"\n{'='*60}")
print("Cleaning up...")
api.delete_project(project_id)
print("Done!")
