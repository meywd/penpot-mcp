"""
Comprehensive validation of object update tools against local Penpot instance.

This test creates a file, adds objects, and validates all update operations:
- move_object
- resize_object
- change_object_color
- rotate_object
- delete_object

IMPORTANT: Make sure your local Penpot instance is running at http://localhost:9001
           and the file is NOT open in your browser during testing.
"""
import asyncio
import os

# IMPORTANT: Set environment variables BEFORE importing anything else
# This ensures the config module reads the correct values
os.environ['PENPOT_API_URL'] = 'http://localhost:9001/api'

# Configure local instance credentials
LOCAL_EMAIL = os.environ.get('PENPOT_LOCAL_EMAIL', 'admin@example.com')
LOCAL_PASSWORD = os.environ.get('PENPOT_LOCAL_PASSWORD', '123123')

# Set credentials in environment so MCP server picks them up
os.environ['PENPOT_USERNAME'] = LOCAL_EMAIL
os.environ['PENPOT_PASSWORD'] = LOCAL_PASSWORD

# Now import the modules - they will read the environment variables we just set
from penpot_mcp.server.mcp_server import PenpotMCPServer
from penpot_mcp.api.penpot_api import PenpotAPI


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def validate_object_updates():
    """Validate all object update tools against local instance."""

    print_section("PENPOT OBJECT UPDATE TOOLS VALIDATION")

    # Connect to local instance with credentials
    api = PenpotAPI(
        base_url="http://localhost:9001/api",
        email=LOCAL_EMAIL,
        password=LOCAL_PASSWORD,
        debug=True
    )
    server = PenpotMCPServer(test_mode=True)

    print("\n[OK] Connected to local Penpot instance")

    # Get or create test project
    print_section("1. Setup Test Environment")

    projects = api.list_projects()
    test_project = None
    for p in projects:
        if p['name'] == 'MCP Test Project':
            test_project = p
            print(f"[OK] Found existing test project: {p['id']}")
            break

    if not test_project:
        print("Creating new test project...")
        # Get team ID from first project
        team_id = projects[0]['teamId'] if projects else None
        if not team_id:
            print("[FAIL] No team found. Cannot create project.")
            return False
        test_project = api.create_project(team_id=team_id, name="MCP Test Project")
        print(f"[OK] Created test project: {test_project['id']}")

    project_id = test_project['id']

    # Create test file
    print("\nCreating test file...")
    file_response = api.create_file(name="Object Update Validation", project_id=project_id)

    # The response might be just the ID string or the full file data
    if isinstance(file_response, str):
        file_id = file_response
        # Get the file to extract page ID
        file_data = api.get_file(file_id)
    else:
        # Full file data returned
        file_id = file_response['id']
        file_data = file_response

    print(f"[OK] Created test file: {file_id}")
    # Pages is a list of page IDs, not full page objects
    page_id = file_data['data']['pages'][0]
    print(f"  Page ID: {page_id}")

    # Create test objects
    print_section("2. Create Test Objects")

    # Create rectangle
    print("\nCreating rectangle...")
    rect_result = await server.mcp.call_tool(
        "add_rectangle",
        {
            "file_id": file_id,
            "page_id": page_id,
            "x": 100,
            "y": 100,
            "width": 200,
            "height": 100,
            "name": "Test Rectangle",
            "fill_color": "#FF0000"
        }
    )
    # Extract object ID from JSON result
    import json
    if hasattr(rect_result, 'content'):
        rect_text = rect_result.content[0].text
    else:
        rect_text = rect_result[0].text if isinstance(rect_result, list) else str(rect_result)

    result_data = json.loads(rect_text)
    rect_id = result_data['objectId']
    print(f"[OK] Created rectangle: {rect_id}")

    # Create circle
    print("\nCreating circle...")
    circle_result = await server.mcp.call_tool(
        "add_circle",
        {
            "file_id": file_id,
            "page_id": page_id,
            "cx": 500,
            "cy": 150,
            "radius": 50,
            "name": "Test Circle",
            "fill_color": "#00FF00"
        }
    )
    if hasattr(circle_result, 'content'):
        circle_text = circle_result.content[0].text
    else:
        circle_text = circle_result[0].text
    circle_data = json.loads(circle_text)
    circle_id = circle_data['objectId']
    print(f"[OK] Created circle: {circle_id}")

    # Create text
    print("\nCreating text...")
    text_result = await server.mcp.call_tool(
        "add_text",
        {
            "file_id": file_id,
            "page_id": page_id,
            "x": 100,
            "y": 300,
            "content": "Test Text",
            "name": "Test Text",
            "font_size": 24,
            "fill_color": "#0000FF"
        }
    )
    if hasattr(text_result, 'content'):
        text_text = text_result.content[0].text
    else:
        text_text = text_result[0].text
    text_data = json.loads(text_text)
    text_id = text_data['objectId']
    print(f"[OK] Created text: {text_id}")

    # Validation tests
    all_passed = True

    # Test 1: move_object
    print_section("3. Test move_object")
    try:
        print(f"\nMoving rectangle to (150, 150)...")
        move_result = await server.mcp.call_tool(
            "move_object",
            {
                "file_id": file_id,
                "object_id": rect_id,
                "x": 150,
                "y": 150
            }
        )

        # Verify
        file_data = api.get_file(file_id)
        pages_index = file_data['data']['pagesIndex']
        for page_data in pages_index.values():
            if rect_id in page_data['objects']:
                obj = page_data['objects'][rect_id]
                if obj['x'] == 150 and obj['y'] == 150:
                    print("[PASS] PASSED: Object moved successfully")
                else:
                    print(f"[FAIL] FAILED: Expected x=150, y=150, got x={obj['x']}, y={obj['y']}")
                    all_passed = False
                break
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        all_passed = False

    # Test 2: resize_object
    print_section("4. Test resize_object")
    try:
        print(f"\nResizing rectangle to 250x150...")
        resize_result = await server.mcp.call_tool(
            "resize_object",
            {
                "file_id": file_id,
                "object_id": rect_id,
                "width": 250,
                "height": 150
            }
        )

        # Verify
        file_data = api.get_file(file_id)
        pages_index = file_data['data']['pagesIndex']
        for page_data in pages_index.values():
            if rect_id in page_data['objects']:
                obj = page_data['objects'][rect_id]
                if obj['width'] == 250 and obj['height'] == 150:
                    print("[PASS] PASSED: Object resized successfully")
                else:
                    print(f"[FAIL] FAILED: Expected 250x150, got {obj['width']}x{obj['height']}")
                    all_passed = False
                break
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        all_passed = False

    # Test 3: change_object_color (rectangle)
    print_section("5. Test change_object_color (Rectangle)")
    try:
        print(f"\nChanging rectangle color to #FFFF00 (yellow)...")
        color_result = await server.mcp.call_tool(
            "change_object_color",
            {
                "file_id": file_id,
                "object_id": rect_id,
                "fill_color": "#FFFF00",
                "fill_opacity": 0.8
            }
        )

        # Verify
        file_data = api.get_file(file_id)
        pages_index = file_data['data']['pagesIndex']
        for page_data in pages_index.values():
            if rect_id in page_data['objects']:
                obj = page_data['objects'][rect_id]
                fills = obj.get('fills', [])
                if fills and fills[0].get('fillColor') == '#FFFF00':
                    opacity = fills[0].get('fillOpacity', 1)
                    if opacity == 0.8:
                        print("[PASS] PASSED: Rectangle color and opacity changed successfully")
                    else:
                        print(f"[FAIL] FAILED: Opacity expected 0.8, got {opacity}")
                        all_passed = False
                else:
                    print(f"[FAIL] FAILED: Color not changed. Fills: {fills}")
                    all_passed = False
                break
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        all_passed = False

    # Test 4: change_object_color (text)
    print_section("6. Test change_object_color (Text)")
    try:
        print(f"\nChanging text color to #FF00FF (magenta)...")
        color_result = await server.mcp.call_tool(
            "change_object_color",
            {
                "file_id": file_id,
                "object_id": text_id,
                "fill_color": "#FF00FF",
                "fill_opacity": 1
            }
        )

        # Verify - text colors are in content structure
        file_data = api.get_file(file_id)
        pages_index = file_data['data']['pagesIndex']
        for page_data in pages_index.values():
            if text_id in page_data['objects']:
                obj = page_data['objects'][text_id]
                content = obj.get('content', {})
                # Check content structure for fills
                if content.get('children'):
                    para = content['children'][0]['children'][0]
                    fills = para.get('fills', [])
                    if fills and fills[0].get('fillColor') == '#FF00FF':
                        print("[PASS] PASSED: Text color changed successfully")
                    else:
                        print(f"[FAIL] FAILED: Text color not changed. Fills: {fills}")
                        all_passed = False
                else:
                    print(f"[FAIL] FAILED: No content structure found")
                    all_passed = False
                break
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        all_passed = False

    # Test 5: rotate_object
    print_section("7. Test rotate_object")
    try:
        print(f"\nRotating rectangle by 45 degrees...")
        rotate_result = await server.mcp.call_tool(
            "rotate_object",
            {
                "file_id": file_id,
                "object_id": rect_id,
                "rotation": 45
            }
        )

        # Verify
        file_data = api.get_file(file_id)
        pages_index = file_data['data']['pagesIndex']
        for page_data in pages_index.values():
            if rect_id in page_data['objects']:
                obj = page_data['objects'][rect_id]
                rotation = obj.get('rotation', 0)
                # Check if close to 45 degrees (convert radians to degrees)
                import math
                rotation_deg = math.degrees(rotation) if rotation > 1 else rotation
                if abs(rotation_deg - 45) < 0.1:
                    print(f"[PASS] PASSED: Object rotated to {rotation_deg}°")
                else:
                    print(f"[FAIL] FAILED: Expected 45°, got {rotation_deg}°")
                    all_passed = False
                break
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        all_passed = False

    # Test 6: delete_object
    print_section("8. Test delete_object")
    try:
        print(f"\nDeleting circle object...")
        delete_result = await server.mcp.call_tool(
            "delete_object",
            {
                "file_id": file_id,
                "page_id": page_id,
                "object_id": circle_id
            }
        )

        # Verify
        file_data = api.get_file(file_id)
        pages_index = file_data['data']['pagesIndex']
        found = False
        for page_data in pages_index.values():
            if circle_id in page_data['objects']:
                found = True
                break

        if not found:
            print("[PASS] PASSED: Object deleted successfully")
        else:
            print("[FAIL] FAILED: Object still exists after deletion")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        all_passed = False

    # Final summary
    print_section("VALIDATION SUMMARY")
    print(f"\nTest file ID: {file_id}")
    print(f"Test file URL: http://localhost:9001/#/workspace/{file_id}/{page_id}")
    print(f"\nRemaining objects:")
    print(f"  - Rectangle: {rect_id} (moved, resized, recolored, rotated)")
    print(f"  - Text: {text_id} (recolored)")
    print(f"  - Circle: {circle_id} (deleted)")

    if all_passed:
        print("\n" + "***" * 30)
        print("[PASS] ALL TESTS PASSED!")
        print("***" * 30)
    else:
        print("\n" + "!!! " * 30)
        print("[FAIL] SOME TESTS FAILED")
        print("!!! " * 30)

    print(f"\n[NOTE] IMPORTANT: Open the file in browser to visually verify changes")
    print(f"   Make sure to CLOSE the browser before running this test again!")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(validate_object_updates())
    exit(0 if success else 1)
