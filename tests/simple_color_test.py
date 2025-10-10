"""Simple test to see if color actually changes in Penpot UI."""
import os
from datetime import datetime
from penpot_mcp.api.penpot_api import PenpotAPI
from penpot_mcp.server.mcp_server import PenpotMCPServer
import json


def test_simple_color_change():
    """Create text and change its color, then visually verify in Penpot."""
    api = PenpotAPI(debug=False)
    mcp_server = PenpotMCPServer(name="Test", test_mode=False)

    # Get team
    teams = api.get_teams()
    team_id = teams[0]['id']

    # Create project
    project = api.create_project(f"Color Test {datetime.now().strftime('%H:%M:%S')}", team_id)
    project_id = project['id']
    print(f"Project ID: {project_id}")

    # Create file
    file = api.create_file("Test File", project_id)
    file_id = file['id']
    print(f"File ID: {file_id}")

    # Get page
    file_data = api.get_file(file_id)
    pages = file_data.get('data', {}).get('pages', [])
    page_id = pages[0] if isinstance(pages[0], str) else pages[0]['id']

    # Create artboard
    artboard_id = api.generate_session_id()
    with api.editing_session(file_id) as (session_id, revn):
        artboard = api.create_frame(x=0, y=0, width=1920, height=1080, name="Test")
        change = api.create_add_obj_change(artboard_id, page_id, artboard)
        api.update_file(file_id, session_id, revn, [change])

    # Create text (initially BLACK)
    text_id = api.generate_session_id()
    with api.editing_session(file_id) as (session_id, revn):
        text = api.create_text(x=100, y=100, content="TEST TEXT", font_size=48, fill_color="#000000")
        change = api.create_add_obj_change(text_id, page_id, text, frame_id=artboard_id)
        api.update_file(file_id, session_id, revn, [change])

    print(f"\nText ID: {text_id}")
    print(f"Created BLACK text - CHECK IN PENPOT")
    input("Press Enter when you've verified the text is BLACK...")

    # Call MCP tool helper
    async def call_tool_async(tool_name, **kwargs):
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

    # Change to RED
    print("\nChanging to RED...")
    result = call_tool('change_object_color', file_id=file_id, object_id=text_id, fill_color="#FF0000", fill_opacity=1.0)
    print(f"Result: {result}")

    print("\nREFRESH PENPOT - text should now be RED")
    input("Press Enter when you've verified the text is RED (or still black)...")

    print(f"\nOpen: http://localhost:9001/")
    print(f"Project ID: {project_id}")


if __name__ == "__main__":
    test_simple_color_change()
