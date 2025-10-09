"""Tests for comment and collaboration API methods."""

from unittest.mock import MagicMock, patch

import pytest

from penpot_mcp.api.penpot_api import PenpotAPI


@pytest.fixture
def api_client():
    """Create a PenpotAPI client for testing."""
    with patch.object(PenpotAPI, 'login_with_password'):
        api = PenpotAPI(debug=False)
        api.access_token = "test-token"
        return api


class TestCreateCommentThread:
    """Tests for create_comment_thread method."""

    def test_create_comment_thread_basic(self, api_client):
        """Test basic comment thread creation."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'thread-123',
            'file-id': 'file-456',
            'page-id': 'page-789',
            'position': {'x': 100, 'y': 200},
            'content': 'This is a test comment'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            thread = api_client.create_comment_thread(
                file_id='file-456',
                page_id='page-789',
                x=100,
                y=200,
                content='This is a test comment'
            )

        assert thread['id'] == 'thread-123'
        assert thread['position']['x'] == 100
        assert thread['position']['y'] == 200
        assert thread['content'] == 'This is a test comment'

    def test_create_comment_thread_with_frame(self, api_client):
        """Test comment thread creation with frame ID."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'thread-456',
            'frame-id': 'frame-123'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            thread = api_client.create_comment_thread(
                file_id='file-456',
                page_id='page-789',
                x=50,
                y=75,
                content='Comment in frame',
                frame_id='frame-123'
            )

        assert thread['id'] == 'thread-456'
        assert thread['frame-id'] == 'frame-123'


class TestAddComment:
    """Tests for add_comment method."""

    def test_add_comment(self, api_client):
        """Test adding a comment to a thread."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'comment-123',
            'thread-id': 'thread-456',
            'content': 'This is a reply',
            'owner-name': 'Test User'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            comment = api_client.add_comment(
                thread_id='thread-456',
                content='This is a reply'
            )

        assert comment['id'] == 'comment-123'
        assert comment['thread-id'] == 'thread-456'
        assert comment['content'] == 'This is a reply'


class TestGetCommentThreads:
    """Tests for get_comment_threads method."""

    def test_get_comment_threads_all(self, api_client):
        """Test retrieving all comment threads for a file."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 'thread-1', 'position': {'x': 100, 'y': 200}},
            {'id': 'thread-2', 'position': {'x': 300, 'y': 400}}
        ]

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            threads = api_client.get_comment_threads(file_id='file-123')

        assert len(threads) == 2
        assert threads[0]['id'] == 'thread-1'
        assert threads[1]['id'] == 'thread-2'

    def test_get_comment_threads_by_page(self, api_client):
        """Test retrieving comment threads for a specific page."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 'thread-1', 'page-id': 'page-123'}
        ]

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            threads = api_client.get_comment_threads(
                file_id='file-123',
                page_id='page-123'
            )

        assert len(threads) == 1
        assert threads[0]['page-id'] == 'page-123'


class TestGetThreadComments:
    """Tests for get_thread_comments method."""

    def test_get_thread_comments(self, api_client):
        """Test retrieving comments from a thread."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 'comment-1', 'content': 'First comment', 'owner-name': 'User 1'},
            {'id': 'comment-2', 'content': 'Second comment', 'owner-name': 'User 2'}
        ]

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            comments = api_client.get_thread_comments(thread_id='thread-123')

        assert len(comments) == 2
        assert comments[0]['content'] == 'First comment'
        assert comments[1]['content'] == 'Second comment'


class TestUpdateCommentThreadStatus:
    """Tests for update_comment_thread_status method."""

    def test_mark_thread_as_resolved(self, api_client):
        """Test marking a thread as resolved."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'thread-123',
            'is-resolved': True
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            thread = api_client.update_comment_thread_status(
                thread_id='thread-123',
                is_resolved=True
            )

        assert thread['id'] == 'thread-123'
        assert thread['is-resolved'] is True

    def test_mark_thread_as_unresolved(self, api_client):
        """Test marking a thread as unresolved."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'thread-123',
            'is-resolved': False
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            thread = api_client.update_comment_thread_status(
                thread_id='thread-123',
                is_resolved=False
            )

        assert thread['is-resolved'] is False


class TestDeleteCommentThread:
    """Tests for delete_comment_thread method."""

    def test_delete_comment_thread(self, api_client):
        """Test deleting a comment thread."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'id': 'thread-123'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.delete_comment_thread(thread_id='thread-123')

        assert result['success'] is True
        assert result['id'] == 'thread-123'

    def test_delete_comment_thread_empty_response(self, api_client):
        """Test deleting a thread when response has no JSON."""
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("No JSON")

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.delete_comment_thread(thread_id='thread-123')

        assert result['success'] is True
        assert result['id'] == 'thread-123'
