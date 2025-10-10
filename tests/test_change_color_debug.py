"""Debug test to verify change_object_color updates text content structure."""
import os
import json
from datetime import datetime
from penpot_mcp.api.penpot_api import PenpotAPI
from penpot_mcp.server.mcp_server import PenpotMCPServer


def test_change_color_updates_content():
    """Verify that change_object_color actually updates the content structure."""
    api = PenpotAPI(debug=False)
    mcp_server = PenpotMCPServer(name="Test Server", test_mode=False)

    # Get team
    teams = api.get_teams()
    team_id = teams[0]['id']

    # Create test project
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    project_name = f"Debug Color Change - {timestamp}"
    project = api.create_project(project_name, team_id)
    project_id = project['id']
    print(f"\nCreated project: {project_name}")

    # Create test file
    file_name = "Debug Test"
    file = api.create_file(file_name, project_id)
    file_id = file['id']
    print(f"Created file: {file_name}")

    # Get page ID
    file_data = api.get_file(file_id)
    pages = file_data.get('data', {}).get('pages', [])
    page_id = pages[0] if isinstance(pages[0], str) else pages[0]['id']

    # Create artboard
    artboard_id = api.generate_session_id()
    with api.editing_session(file_id) as (session_id, revn):
        artboard = api.create_frame(x=0, y=0, width=1920, height=1080, name="Test Artboard")
        change = api.create_add_obj_change(artboard_id, page_id, artboard)
        api.update_file(file_id, session_id, revn, [change])

    # Create initial text with black color
    text_id = api.generate_session_id()
    with api.editing_session(file_id) as (session_id, revn):
        text = api.create_text(
            x=100, y=100,
            content="Test Text",
            font_size=24,
            fill_color="#000000"
        )
        change = api.create_add_obj_change(text_id, page_id, text, frame_id=artboard_id)
        api.update_file(file_id, session_id, revn, [change])

    print(f"\nCreated text with BLACK (ID: {text_id})")

    # Check initial state
    file_data = api.get_file(file_id)
    pages_index = file_data.get('data', {}).get('pagesIndex', {})
    text_obj = None
    for page_data in pages_index.values():
        if text_id in page_data.get('objects', {}):
            text_obj = page_data['objects'][text_id]
            break

    print("\n=== BEFORE change_object_color ===")
    print(f"Object-level fills: {text_obj.get('fills')}")
    content = text_obj.get('content', {})
    if 'children' in content:
        for ps in content['children']:
            for para in ps.get('children', []):
                print(f"Paragraph fills: {para.get('fills', 'NONE')}")
                for text_node in para.get('children', []):
                    print(f"Text node fills: {text_node.get('fills', 'NONE')}")

    # Helper to call MCP tool
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

    # Change color to RED
    print("\n=== Calling change_object_color ===")
    result = call_tool(
        'change_object_color',
        file_id=file_id,
        object_id=text_id,
        fill_color="#FF0000",
        fill_opacity=1.0
    )
    print(f"Result: {result}")

    # Check AFTER state
    file_data = api.get_file(file_id)
    pages_index = file_data.get('data', {}).get('pagesIndex', {})
    text_obj = None
    for page_data in pages_index.values():
        if text_id in page_data.get('objects', {}):
            text_obj = page_data['objects'][text_id]
            break

    print("\n=== AFTER change_object_color ===")
    print(f"Object-level fills: {text_obj.get('fills')}")
    content = text_obj.get('content', {})
    if 'children' in content:
        for ps in content['children']:
            for para in ps.get('children', []):
                print(f"Paragraph fills: {para.get('fills', 'NONE')}")
                for text_node in para.get('children', []):
                    print(f"Text node fills: {text_node.get('fills', 'NONE')}")

    # Verify fills are present
    has_para_fills = False
    has_node_fills = False
    if 'children' in content:
        for ps in content['children']:
            for para in ps.get('children', []):
                if 'fills' in para:
                    has_para_fills = True
                for text_node in para.get('children', []):
                    if 'fills' in text_node:
                        has_node_fills = True

    print("\n=== VERIFICATION ===")
    print(f"Paragraph has fills: {has_para_fills}")
    print(f"Text node has fills: {has_node_fills}")

    if has_para_fills and has_node_fills:
        print("[SUCCESS] change_object_color properly updated content structure!")
    else:
        print("[FAILED] content structure not updated correctly")

    # Cleanup
    if os.getenv('CLEANUP_TEST_FILES', 'false').lower() == 'true':
        api.delete_project(project_id)
        print("\nTest project cleaned up")


if __name__ == "__main__":
    test_change_color_updates_content()
