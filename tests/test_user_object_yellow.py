"""Test changing the user's specific object to yellow."""
import os
import json
from penpot_mcp.server.mcp_server import PenpotMCPServer


def test_change_to_yellow():
    """Change fab9cafe-e0d9-43c4-9642-295ea9759a5c to yellow."""
    mcp_server = PenpotMCPServer(name="Test", test_mode=False)

    file_id = "689fbaf0-efce-81fe-8006-ed108f8a2104"
    object_id = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"

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

    # Change to YELLOW
    print(f"\nChanging object {object_id} to YELLOW (#FFFF00)...")
    result = call_tool(
        'change_object_color',
        file_id=file_id,
        object_id=object_id,
        fill_color="#FFFF00",  # Yellow
        fill_opacity=1.0
    )

    print(f"\nResult: {json.dumps(result, indent=2)}")

    if result.get('success'):
        print(f"\n[SUCCESS] Revision: {result.get('revn')}")
        print(f"\nRefresh Penpot UI - the 'Make-It-Offline' text should now be YELLOW")
    else:
        print(f"\n[FAILED] {result.get('error')}")


if __name__ == "__main__":
    test_change_to_yellow()
