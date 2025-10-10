"""Test changing text color using the change_object_color MCP tool."""
import os
import pytest
from datetime import datetime
from penpot_mcp.api.penpot_api import PenpotAPI
from penpot_mcp.server.mcp_server import PenpotMCPServer

# Skip if credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv('PENPOT_USERNAME') or not os.getenv('PENPOT_PASSWORD'),
    reason="Test requires PENPOT_USERNAME and PENPOT_PASSWORD environment variables"
)


def test_change_text_color():
    """Create text, then change its color using change_object_color tool."""
    api = PenpotAPI(debug=False)
    mcp_server = PenpotMCPServer(name="Test Server", test_mode=False)

    # Get team
    teams = api.get_teams()
    team_id = teams[0]['id']

    # Create test project
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    project_name = f"Change Text Color Test - {timestamp}"
    project = api.create_project(project_name, team_id)
    project_id = project['id']
    print(f"\nCreated project: {project_name}")

    # Create test file
    file_name = "Color Change Test"
    file = api.create_file(file_name, project_id)
    file_id = file['id']
    print(f"Created file: {file_name}")

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
            name="Color Change Artboard"
        )
        change = api.create_add_obj_change(artboard_id, page_id, artboard)
        result = api.update_file(file_id, session_id, revn, [change])

    # Create initial text with black color
    text_id = api.generate_session_id()
    with api.editing_session(file_id) as (session_id, revn):
        text = api.create_text(
            x=100,
            y=100,
            content="This text will change color!",
            font_size=48,
            fill_color="#000000"  # Black initially
        )
        change = api.create_add_obj_change(text_id, page_id, text, frame_id=artboard_id)
        result = api.update_file(file_id, session_id, revn, [change])

    print(f"Created text with BLACK color (ID: {text_id})")

    # Helper to call MCP tools
    async def call_tool_async(tool_name, **kwargs):
        import json
        result = await mcp_server.mcp.call_tool(tool_name, kwargs)
        if isinstance(result, list) and len(result) > 0:
            return json.loads(result[0].text)
        return result

    def call_tool(tool_name, **kwargs):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(call_tool_async(tool_name, **kwargs))

    # Change text color to RED using MCP tool
    print("\nChanging text color to RED using change_object_color tool...")
    result = call_tool(
        'change_object_color',
        file_id=file_id,
        object_id=text_id,
        fill_color="#FF0000",
        fill_opacity=1.0
    )

    if result.get('success'):
        print(f"SUCCESS! Text color changed to RED")
        print(f"New revision: {result.get('revn')}")
    else:
        print(f"FAILED: {result.get('error')}")
        raise AssertionError(f"Color change failed: {result.get('error')}")

    # Change text color to BLUE
    print("\nChanging text color to BLUE...")
    result = call_tool(
        'change_object_color',
        file_id=file_id,
        object_id=text_id,
        fill_color="#0000FF",
        fill_opacity=1.0
    )

    if result.get('success'):
        print(f"SUCCESS! Text color changed to BLUE")
        print(f"New revision: {result.get('revn')}")
    else:
        print(f"FAILED: {result.get('error')}")
        raise AssertionError(f"Color change failed: {result.get('error')}")

    # Change text color to GREEN
    print("\nChanging text color to GREEN...")
    result = call_tool(
        'change_object_color',
        file_id=file_id,
        object_id=text_id,
        fill_color="#00FF00",
        fill_opacity=1.0
    )

    if result.get('success'):
        print(f"SUCCESS! Text color changed to GREEN")
        print(f"New revision: {result.get('revn')}")
    else:
        print(f"FAILED: {result.get('error')}")
        raise AssertionError(f"Color change failed: {result.get('error')}")

    print(f"\n{'='*60}")
    print(f"ALL COLOR CHANGES SUCCESSFUL!")
    print(f"{'='*60}")
    print(f"\nOpen Penpot and navigate to:")
    print(f"  Project: {project_name}")
    print(f"  File: {file_name}")
    print(f"\nThe text should now be GREEN!")
    print(f"{'='*60}\n")

    # Cleanup option
    if os.getenv('CLEANUP_TEST_FILES', 'false').lower() == 'true':
        api.delete_project(project_id)
        print("Test project cleaned up")
    else:
        print("Test project preserved for inspection")


if __name__ == "__main__":
    test_change_text_color()
