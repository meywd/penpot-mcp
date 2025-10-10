"""Test changing color on the specific object the user provided."""
import os
import json
from penpot_mcp.api.penpot_api import PenpotAPI
from penpot_mcp.server.mcp_server import PenpotMCPServer


def test_specific_object():
    """Test changing color of fab9cafe-e0d9-43c4-9642-295ea9759a5c to #E0E0E0."""
    api = PenpotAPI(debug=False)
    mcp_server = PenpotMCPServer(name="Test", test_mode=False)

    file_id = "689fbaf0-efce-81fe-8006-ed108f8a2104"
    object_id = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"

    print(f"File ID: {file_id}")
    print(f"Object ID: {object_id}")

    # Get file to check object
    file_data = api.get_file(file_id)
    pages_index = file_data.get('data', {}).get('pagesIndex', {})

    obj = None
    for page_data in pages_index.values():
        if object_id in page_data.get('objects', {}):
            obj = page_data['objects'][object_id]
            break

    if not obj:
        print("ERROR: Object not found!")
        return

    print(f"\n=== OBJECT DETAILS ===")
    print(f"Type: {obj.get('type')}")
    print(f"Name: {obj.get('name')}")
    print(f"Current fills: {obj.get('fills')}")

    if obj.get('type') == 'text':
        content = obj.get('content', {})
        print("\nContent structure:")
        if 'children' in content:
            for ps in content['children']:
                for para in ps.get('children', []):
                    print(f"  Paragraph fills: {para.get('fills', 'NONE')}")
                    for text_node in para.get('children', []):
                        print(f"    Text node: '{text_node.get('text', '')}'")
                        print(f"    Text node fills: {text_node.get('fills', 'NONE')}")

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

    # Try to change color
    print(f"\n=== CHANGING COLOR TO #E0E0E0 ===")
    result = call_tool(
        'change_object_color',
        file_id=file_id,
        object_id=object_id,
        fill_color="#E0E0E0",
        fill_opacity=1.0
    )

    print(f"Result: {json.dumps(result, indent=2)}")

    if result.get('success'):
        print("\n=== VERIFYING CHANGE ===")
        # Clear cache to force fresh fetch
        if hasattr(api, '_cache'):
            api._cache.clear()

        # Get fresh data (bypass cache)
        import requests
        response = requests.post(
            f"{os.getenv('PENPOT_API_URL')}/rpc/command/get-file",
            json={"id": file_id},
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Token {api.auth_token}'
            }
        )
        file_data = response.json()
        pages_index = file_data.get('data', {}).get('pagesIndex', {})

        obj = None
        for page_data in pages_index.values():
            if object_id in page_data.get('objects', {}):
                obj = page_data['objects'][object_id]
                break

        print(f"New fills: {obj.get('fills')}")

        if obj.get('type') == 'text':
            content = obj.get('content', {})
            if 'children' in content:
                for ps in content['children']:
                    for para in ps.get('children', []):
                        print(f"  Paragraph fills: {para.get('fills', 'NONE')}")
                        for text_node in para.get('children', []):
                            print(f"    Text node fills: {text_node.get('fills', 'NONE')}")

        print("\nRefresh Penpot UI to see the change!")


if __name__ == "__main__":
    test_specific_object()
