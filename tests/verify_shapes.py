"""Quick script to verify shapes in the test file."""
import os
from penpot_mcp.api.penpot_api import PenpotAPI

# Use the credentials
api = PenpotAPI(debug=False)

# Get the team
teams = api.get_teams()
team_id = teams[0]['id']
print(f"Team: {teams[0]['name']} (ID: {team_id})")

# List projects
projects = api.list_projects()
print(f"\nFound {len(projects)} projects:")

# Find the most recent integration test project
test_projects = [p for p in projects if p['name'].startswith('MCP Integration Tests')]
if not test_projects:
    print("No integration test projects found!")
    exit(1)

# Sort by modified-at descending to get the latest
test_projects.sort(key=lambda p: p.get('modified-at', ''), reverse=True)
latest_project = test_projects[0]

print(f"\nLatest test project: {latest_project['name']}")
print(f"Project ID: {latest_project['id']}")

# Get files in the project
files = api.get_project_files(latest_project['id'])
print(f"\nFiles in project: {len(files)}")

# Check the "02 - Shape Creation" file
shape_files = [f for f in files if 'Shape Creation' in f['name']]
if not shape_files:
    print("Shape Creation file not found!")
    exit(1)

shape_file = shape_files[0]
print(f"\nChecking file: {shape_file['name']}")
print(f"File ID: {shape_file['id']}")

# Get full file data
file_data = api.get_file(shape_file['id'])
print(f"\nFile revision: {file_data.get('revn')}")

# Check pages
pages_list = file_data.get('data', {}).get('pages', [])
print(f"Pages in file: {len(pages_list)}")

# Get all objects
objects = file_data.get('data', {}).get('objects', {})
print(f"Total objects in file: {len(objects)}")

for page_id in pages_list:
    # Get page object
    if isinstance(page_id, dict):
        page_id = page_id.get('id')

    page_obj = objects.get(page_id, {})
    print(f"\n  Page: {page_obj.get('name', 'Unnamed')}")
    print(f"  Page ID: {page_id}")

    # Find shapes on this page (children of the page frame)
    page_shapes = []
    for obj_id, obj in objects.items():
        parent_id = obj.get('parent-id')
        frame_id = obj.get('frame-id')

        # Skip the page itself
        if obj_id == page_id:
            continue

        # Object belongs to this page if parent or frame is the page
        if parent_id == page_id or frame_id == page_id:
            page_shapes.append(obj)

    print(f"  Shapes on this page: {len(page_shapes)}")

    for obj in page_shapes:
        obj_type = obj.get('type', 'unknown')
        obj_name = obj.get('name', 'Unnamed')
        obj_id = obj.get('id', 'no-id')
        print(f"    - {obj_type}: {obj_name} (ID: {obj_id})")

        # Show position for shapes
        if obj_type in ['rect', 'circle']:
            x = obj.get('x', 0)
            y = obj.get('y', 0)
            width = obj.get('width', 0)
            height = obj.get('height', 0)
            print(f"      Position: ({x}, {y}), Size: {width}x{height}")
