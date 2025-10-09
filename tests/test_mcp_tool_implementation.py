"""Tests for actual MCP tool implementations.

These tests verify that the MCP tools correctly wrap API calls,
return proper response structures, and handle errors appropriately.
"""

from unittest.mock import MagicMock, patch

import pytest

from penpot_mcp.server.mcp_server import PenpotMCPServer


@pytest.fixture
def mock_server():
    """Create a PenpotMCPServer with mocked API."""
    server = PenpotMCPServer(name="Test Server", test_mode=True)

    # Mock all API methods we'll be testing
    server.api.create_comment_thread = MagicMock()
    server.api.add_comment = MagicMock()
    server.api.get_comment_threads = MagicMock()
    server.api.update_comment_thread_status = MagicMock()
    server.api.link_file_to_library = MagicMock()
    server.api.get_library_components = MagicMock()
    server.api.instantiate_component = MagicMock()
    server.api.sync_file_library = MagicMock()
    server.api.publish_library = MagicMock()
    server.api.get_file_libraries = MagicMock()

    return server


# Helper function to call a tool through the FastMCP server
async def call_tool_async(server, tool_name, **kwargs):
    """
    Call a tool through the FastMCP server's call_tool method.

    This is an async wrapper since FastMCP's call_tool is async.
    """
    import json
    result = await server.mcp.call_tool(tool_name, kwargs)

    # Result is a list of TextContent objects
    if isinstance(result, list) and len(result) > 0:
        # Extract text from first TextContent and parse as JSON
        return json.loads(result[0].text)

    return result


def call_tool(server, tool_name, **kwargs):
    """
    Synchronous wrapper to call a tool.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(call_tool_async(server, tool_name, **kwargs))


# ========== COMMENT TOOL TESTS ==========

class TestCommentTools:
    """Test comment and collaboration MCP tools."""

    def test_add_design_comment_success(self, mock_server):
        """Test add_design_comment tool returns correct structure on success."""
        # Setup mock
        mock_server.api.create_comment_thread.return_value = {
            'id': 'thread-123',
            'file-id': 'file-456',
            'position': {'x': 100, 'y': 200},
            'content': 'Test comment'
        }

        # Invoke the tool
        result = call_tool(
            mock_server,
            'add_design_comment',
            file_id='file-456',
            page_id='page-789',
            x=100.0,
            y=200.0,
            comment='Test comment'
        )

        # Verify structure
        assert result['success'] is True
        assert result['thread_id'] == 'thread-123'
        assert 'thread' in result
        assert result['thread']['id'] == 'thread-123'

        # Verify API was called correctly
        mock_server.api.create_comment_thread.assert_called_once_with(
            'file-456', 'page-789', 100.0, 200.0, 'Test comment', None
        )

    def test_add_design_comment_with_frame(self, mock_server):
        """Test add_design_comment tool with optional frame_id."""
        mock_server.api.create_comment_thread.return_value = {
            'id': 'thread-123',
            'frame-id': 'frame-xyz'
        }

        result = call_tool(
            mock_server,
            'add_design_comment',
            file_id='file-456',
            page_id='page-789',
            x=100.0,
            y=200.0,
            comment='Test',
            frame_id='frame-xyz'
        )

        assert result['success'] is True
        mock_server.api.create_comment_thread.assert_called_once_with(
            'file-456', 'page-789', 100.0, 200.0, 'Test', 'frame-xyz'
        )

    def test_add_design_comment_error_handling(self, mock_server):
        """Test add_design_comment tool handles API errors."""
        mock_server.api.create_comment_thread.side_effect = Exception("API Error")

        result = call_tool(
            mock_server,
            'add_design_comment',
            file_id='file-456',
            page_id='page-789',
            x=100.0,
            y=200.0,
            comment='Test'
        )

        assert 'error' in result
        assert result['error'] == 'API Error'

    def test_reply_to_comment_success(self, mock_server):
        """Test reply_to_comment tool returns correct structure."""
        mock_server.api.add_comment.return_value = {
            'id': 'comment-123',
            'thread-id': 'thread-456',
            'content': 'Test reply'
        }

        result = call_tool(
            mock_server,
            'reply_to_comment',
            thread_id='thread-456',
            reply='Test reply'
        )

        assert result['success'] is True
        assert result['comment_id'] == 'comment-123'
        assert 'comment' in result

    def test_get_file_comments_success(self, mock_server):
        """Test get_file_comments tool returns correct structure."""
        mock_server.api.get_comment_threads.return_value = [
            {'id': 'thread-1'},
            {'id': 'thread-2'}
        ]

        result = call_tool(
            mock_server,
            'get_file_comments',
            file_id='file-123'
        )

        assert result['success'] is True
        assert result['count'] == 2
        assert len(result['threads']) == 2

    def test_get_file_comments_with_page_id(self, mock_server):
        """Test get_file_comments tool with optional page_id."""
        mock_server.api.get_comment_threads.return_value = [{'id': 'thread-1'}]

        result = call_tool(
            mock_server,
            'get_file_comments',
            file_id='file-123',
            page_id='page-456'
        )

        assert result['success'] is True
        mock_server.api.get_comment_threads.assert_called_once_with('file-123', 'page-456')

    def test_resolve_comment_thread_success(self, mock_server):
        """Test resolve_comment_thread tool returns correct structure."""
        mock_server.api.update_comment_thread_status.return_value = {
            'id': 'thread-123',
            'is-resolved': True
        }

        result = call_tool(
            mock_server,
            'resolve_comment_thread',
            thread_id='thread-123'
        )

        assert result['success'] is True
        assert 'thread' in result
        assert result['thread']['is-resolved'] is True

        # Verify API called with is_resolved=True
        mock_server.api.update_comment_thread_status.assert_called_once_with(
            'thread-123', is_resolved=True
        )


# ========== LIBRARY TOOL TESTS ==========

class TestLibraryTools:
    """Test library and component system MCP tools."""

    def test_link_library_success(self, mock_server):
        """Test link_library tool returns correct structure."""
        mock_server.api.link_file_to_library.return_value = {
            'id': 'file-123',
            'linkedLibraries': ['lib-456']
        }

        result = call_tool(
            mock_server,
            'link_library',
            file_id='file-123',
            library_id='lib-456'
        )

        assert result['success'] is True
        assert 'result' in result
        assert result['result']['id'] == 'file-123'

    def test_list_library_components_success(self, mock_server):
        """Test list_library_components tool returns correct structure."""
        mock_server.api.get_library_components.return_value = [
            {'id': 'comp-1', 'name': 'Button'},
            {'id': 'comp-2', 'name': 'Card'}
        ]

        result = call_tool(
            mock_server,
            'list_library_components',
            library_id='lib-456'
        )

        assert result['success'] is True
        assert result['count'] == 2
        assert len(result['components']) == 2
        assert result['components'][0]['name'] == 'Button'

    def test_import_component_success(self, mock_server):
        """Test import_component tool returns correct structure."""
        mock_server.api.instantiate_component.return_value = {
            'id': 'file-123',
            'revn': 6
        }

        result = call_tool(
            mock_server,
            'import_component',
            file_id='file-123',
            page_id='page-456',
            library_id='lib-789',
            component_id='comp-abc',
            x=100.0,
            y=200.0
        )

        assert result['success'] is True
        assert 'file' in result
        assert result['file']['revn'] == 6

    def test_import_component_with_frame(self, mock_server):
        """Test import_component tool with optional frame_id."""
        mock_server.api.instantiate_component.return_value = {'id': 'file-123'}

        result = call_tool(
            mock_server,
            'import_component',
            file_id='file-123',
            page_id='page-456',
            library_id='lib-789',
            component_id='comp-abc',
            x=100.0,
            y=200.0,
            frame_id='frame-xyz'
        )

        assert result['success'] is True
        mock_server.api.instantiate_component.assert_called_once_with(
            'file-123', 'page-456', 'lib-789', 'comp-abc', 100.0, 200.0, 'frame-xyz'
        )

    def test_sync_library_success(self, mock_server):
        """Test sync_library tool returns correct structure."""
        mock_server.api.sync_file_library.return_value = {
            'updated-count': 5,
            'file-id': 'file-123'
        }

        result = call_tool(
            mock_server,
            'sync_library',
            file_id='file-123',
            library_id='lib-456'
        )

        assert result['success'] is True
        assert 'result' in result
        assert result['result']['updated-count'] == 5

    def test_publish_as_library_success(self, mock_server):
        """Test publish_as_library tool returns correct structure."""
        mock_server.api.publish_library.return_value = {
            'id': 'file-123',
            'is-shared': True
        }

        result = call_tool(
            mock_server,
            'publish_as_library',
            file_id='file-123'
        )

        assert result['success'] is True
        assert 'file' in result
        assert result['file']['is-shared'] is True

        # Verify API called with publish=True
        mock_server.api.publish_library.assert_called_once_with('file-123', publish=True)

    def test_unpublish_library_success(self, mock_server):
        """Test unpublish_library tool returns correct structure."""
        mock_server.api.publish_library.return_value = {
            'id': 'file-123',
            'is-shared': False
        }

        result = call_tool(
            mock_server,
            'unpublish_library',
            file_id='file-123'
        )

        assert result['success'] is True
        assert 'file' in result
        assert result['file']['is-shared'] is False

        # Verify API called with publish=False
        mock_server.api.publish_library.assert_called_once_with('file-123', publish=False)

    def test_get_file_libraries_success(self, mock_server):
        """Test get_file_libraries tool returns correct structure."""
        mock_server.api.get_file_libraries.return_value = [
            {'id': 'lib-1', 'name': 'Design System'},
            {'id': 'lib-2', 'name': 'Icons'}
        ]

        result = call_tool(
            mock_server,
            'get_file_libraries',
            file_id='file-123'
        )

        assert result['success'] is True
        assert result['count'] == 2
        assert len(result['libraries']) == 2
        assert result['libraries'][0]['name'] == 'Design System'

    def test_library_tool_error_handling(self, mock_server):
        """Test library tools handle API errors correctly."""
        mock_server.api.link_file_to_library.side_effect = Exception("Network error")

        result = call_tool(
            mock_server,
            'link_library',
            file_id='file-123',
            library_id='lib-456'
        )

        assert 'error' in result
        assert result['error'] == 'Network error'
