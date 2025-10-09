"""Test text colors to verify the fill color fix."""
import os
import pytest
from datetime import datetime
from penpot_mcp.api.penpot_api import PenpotAPI

# Skip if credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv('PENPOT_USERNAME') or not os.getenv('PENPOT_PASSWORD'),
    reason="Test requires PENPOT_USERNAME and PENPOT_PASSWORD environment variables"
)


def test_multiple_text_colors():
    """Create multiple text elements with different colors."""
    api = PenpotAPI(debug=False)

    # Get team
    teams = api.get_teams()
    team_id = teams[0]['id']

    # Create test project
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    project_name = f"Text Colors Test - {timestamp}"
    project = api.create_project(project_name, team_id)
    project_id = project['id']
    print(f"\nCreated project: {project_name}")
    print(f"Project ID: {project_id}")

    # Create test file
    file_name = "Colorful Text Test"
    file = api.create_file(file_name, project_id)
    file_id = file['id']
    print(f"Created file: {file_name}")
    print(f"File ID: {file_id}")

    # Get page ID
    file_data = api.get_file(file_id)
    pages = file_data.get('data', {}).get('pages', [])
    page_id = pages[0] if isinstance(pages[0], str) else pages[0]['id']

    # Create an artboard
    artboard_id = api.generate_session_id()
    with api.editing_session(file_id) as (session_id, revn):
        artboard = api.create_frame(
            x=0, y=0,
            width=1920, height=1080,
            name="Text Colors Artboard"
        )
        change = api.create_add_obj_change(artboard_id, page_id, artboard)
        result = api.update_file(file_id, session_id, revn, [change])
        print(f"Created artboard at revision {result.get('revn')}")

    # Define text samples with different colors
    text_samples = [
        {"text": "Red Text", "color": "#FF0000", "y": 100},
        {"text": "Green Text", "color": "#00FF00", "y": 150},
        {"text": "Blue Text", "color": "#0000FF", "y": 200},
        {"text": "Orange Text", "color": "#FF8800", "y": 250},
        {"text": "Purple Text", "color": "#8800FF", "y": 300},
        {"text": "Cyan Text", "color": "#00FFFF", "y": 350},
        {"text": "Magenta Text", "color": "#FF00FF", "y": 400},
        {"text": "Yellow Text", "color": "#FFFF00", "y": 450},
        {"text": "Pink Text", "color": "#FF69B4", "y": 500},
        {"text": "Teal Text", "color": "#008080", "y": 550},
    ]

    # Create all text elements
    print(f"\nCreating {len(text_samples)} text elements with different colors...")
    for sample in text_samples:
        text_id = api.generate_session_id()

        with api.editing_session(file_id) as (session_id, revn):
            text = api.create_text(
                x=100,
                y=sample["y"],
                content=sample["text"],
                font_size=32,
                fill_color=sample["color"]
            )

            # Add text to artboard
            change = api.create_add_obj_change(text_id, page_id, text, frame_id=artboard_id)
            result = api.update_file(file_id, session_id, revn, [change])

        print(f"  + Created '{sample['text']}' with color {sample['color']}")

    print(f"\n{'='*60}")
    print(f"SUCCESS: Test completed!")
    print(f"{'='*60}")
    print(f"\nOpen Penpot and navigate to:")
    print(f"  Project: {project_name}")
    print(f"  File: {file_name}")
    print(f"\nYou should see 10 colored text elements!")
    print(f"{'='*60}\n")

    # Cleanup option
    if os.getenv('CLEANUP_TEST_FILES', 'false').lower() == 'true':
        api.delete_project(project_id)
        print("Test project cleaned up")
    else:
        print("Test project preserved for inspection")
        print("Set CLEANUP_TEST_FILES=true to auto-delete")


if __name__ == "__main__":
    test_multiple_text_colors()
