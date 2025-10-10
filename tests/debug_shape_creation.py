"""Debug script to check if shapes are actually created."""
import time
import json
from penpot_mcp.api.penpot_api import PenpotAPI

# Create API client with debug=True
api = PenpotAPI(debug=True)

# Get team
teams = api.get_teams()
team_id = teams[0]['id']
print(f"\n{'='*60}")
print(f"Team: {teams[0]['name']}")
print(f"{'='*60}\n")

# Create a test project
project_name = "Debug Shape Test"
project = api.create_project(project_name, team_id)
project_id = project['id']
print(f"Created project: {project_id}\n")

# Create a test file
file_name = "Test File"
file = api.create_file(file_name, project_id)
file_id = file['id']
print(f"Created file: {file_id}\n")

# Get file to get the page ID
file_data = api.get_file(file_id)
pages = file_data.get('data', {}).get('pages', [])
if not pages:
    print("ERROR: No pages in file!")
    exit(1)

page_id = pages[0] if isinstance(pages[0], str) else pages[0]['id']
print(f"Page ID: {page_id}\n")

# Create a rectangle
print(f"{'='*60}")
print("CREATING RECTANGLE")
print(f"{'='*60}\n")

obj_id = api.generate_session_id()
print(f"Object ID: {obj_id}")

with api.editing_session(file_id) as (session_id, revn):
    rect = api.create_rectangle(
        x=100, y=100, width=200, height=150,
        name="Debug Rectangle",
        fill_color="#FF0000"
    )

    change = api.create_add_obj_change(obj_id, page_id, rect)
    result = api.update_file(file_id, session_id, revn, [change])

    print(f"\nUpdate result: {json.dumps(result, indent=2)}")
    print(f"New revision: {result.get('revn')}")

# Wait a moment for indexing
print("\nWaiting 2 seconds for indexing...")
time.sleep(2)

# Fetch the file again
print(f"\n{'='*60}")
print("FETCHING FILE DATA")
print(f"{'='*60}\n")

file_data = api.get_file(file_id)
print(f"File revision: {file_data.get('revn')}")

# Save file data for inspection
with open('file_data_dump.json', 'w') as f:
    json.dump(file_data, f, indent=2, default=str)
print("File data saved to file_data_dump.json")

# Check the data structure
data = file_data.get('data', {})
print(f"\nData keys: {list(data.keys())}")

# Check for the rectangle
objects = data.get('objects', {})
objects_index = data.get('objects-index', {})

print(f"Objects (dict): {len(objects)} items")
print(f"Objects-index (dict): {len(objects_index)} items")

if obj_id in objects:
    print(f"\nSUCCESS! Rectangle found in 'objects' with ID {obj_id}")
    rect_obj = objects[obj_id]
    print(f"   Type: {rect_obj.get('type')}")
    print(f"   Name: {rect_obj.get('name')}")
elif obj_id in objects_index:
    print(f"\nSUCCESS! Rectangle found in 'objects-index' with ID {obj_id}")
else:
    print(f"\nFAILED! Rectangle with ID {obj_id} not found!")
    print("\nChecking all data keys...")
    for key, value in data.items():
        if isinstance(value, dict) and obj_id in value:
            print(f"  Found obj_id in data['{key}']!")
        print(f"  {key}: {type(value).__name__} with {len(value) if hasattr(value, '__len__') else '?'} items")

# Cleanup
print(f"\n{'='*60}")
print("CLEANUP")
print(f"{'='*60}\n")

api.delete_project(project_id)
print("Project deleted")
