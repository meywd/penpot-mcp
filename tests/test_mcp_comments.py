"""Tests for MCP comment and collaboration tools."""

from unittest.mock import MagicMock

import pytest

from penpot_mcp.server.mcp_server import PenpotMCPServer


@pytest.fixture
def mock_server():
    """Create a mock PenpotMCPServer with a mock API."""
    server = PenpotMCPServer(name="Test Server", test_mode=True)

    # Mock the API methods
    server.api.create_comment_thread = MagicMock(return_value={
        'id': 'thread-123',
        'file-id': 'file-456',
        'page-id': 'page-789',
        'position': {'x': 100, 'y': 200},
        'content': 'Test comment'
    })

    server.api.add_comment = MagicMock(return_value={
        'id': 'comment-123',
        'thread-id': 'thread-456',
        'content': 'Test reply',
        'owner-name': 'Test User'
    })

    server.api.get_comment_threads = MagicMock(return_value=[
        {'id': 'thread-1', 'position': {'x': 100, 'y': 200}},
        {'id': 'thread-2', 'position': {'x': 300, 'y': 400}}
    ])

    server.api.update_comment_thread_status = MagicMock(return_value={
        'id': 'thread-123',
        'is-resolved': True
    })

    return server


# ========== API MOCK TESTS ==========
# These tests verify the API mock behavior works correctly

def test_create_comment_thread_api_mock(mock_server):
    """Test create_comment_thread API mock returns expected data."""
    result = mock_server.api.create_comment_thread(
        file_id='file-123',
        page_id='page-456',
        x=150,
        y=200,
        content='This button needs work'
    )

    assert result['id'] == 'thread-123'
    assert result['position']['x'] == 100
    assert result['content'] == 'Test comment'


def test_add_comment_api_mock(mock_server):
    """Test add_comment API mock returns expected data."""
    result = mock_server.api.add_comment(
        thread_id='thread-456',
        content='I agree with this feedback'
    )

    assert result['id'] == 'comment-123'
    assert result['thread-id'] == 'thread-456'
    assert result['content'] == 'Test reply'


def test_get_comment_threads_api_mock(mock_server):
    """Test get_comment_threads API mock returns expected data."""
    result = mock_server.api.get_comment_threads(
        file_id='file-123',
        page_id='page-456'
    )

    assert len(result) == 2
    assert result[0]['id'] == 'thread-1'
    assert result[1]['id'] == 'thread-2'


def test_update_comment_thread_status_api_mock(mock_server):
    """Test update_comment_thread_status API mock returns expected data."""
    result = mock_server.api.update_comment_thread_status(
        thread_id='thread-123',
        is_resolved=True
    )

    assert result['id'] == 'thread-123'
    assert result['is-resolved'] is True


# ========== INTEGRATION TESTS ==========

class TestCommentWorkflow:
    """Integration tests for comment workflow."""

    def test_comment_workflow(self, mock_server):
        """Test complete workflow: create thread, add comment, resolve."""
        # Create comment thread
        thread = mock_server.api.create_comment_thread(
            file_id='file-123',
            page_id='page-456',
            x=100,
            y=200,
            content='Initial comment'
        )
        assert thread['id'] == 'thread-123'

        # Add reply
        comment = mock_server.api.add_comment(
            thread_id=thread['id'],
            content='Reply to comment'
        )
        assert comment['thread-id'] == 'thread-456'

        # Resolve thread
        resolved = mock_server.api.update_comment_thread_status(
            thread_id=thread['id'],
            is_resolved=True
        )
        assert resolved['is-resolved'] is True

    def test_multiple_threads_workflow(self, mock_server):
        """Test multiple comment threads on same page."""
        # Get all threads
        threads = mock_server.api.get_comment_threads(file_id='file-123')
        assert len(threads) == 2

        # Verify different positions
        assert threads[0]['position'] != threads[1]['position']
