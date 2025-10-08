"""Tests for session and revision management."""

from unittest.mock import patch

import pytest

from penpot_mcp.api.penpot_api import PenpotAPI


@pytest.fixture
def api_client():
    """Create a PenpotAPI client for testing."""
    with patch.object(PenpotAPI, 'login_with_password'):
        api = PenpotAPI(debug=True)
        api.access_token = "test-token"
        return api


class TestGenerateSessionId:
    """Tests for generate_session_id method."""

    def test_generate_session_id(self, api_client):
        """Test session ID generation."""
        session_id = api_client.generate_session_id()
        
        # Should be valid UUID format
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID format
        assert session_id.count('-') == 4
        
    def test_generate_session_id_unique(self, api_client):
        """Test that generated session IDs are unique."""
        session_id1 = api_client.generate_session_id()
        session_id2 = api_client.generate_session_id()
        
        assert session_id1 != session_id2


class TestGetFileRevision:
    """Tests for get_file_revision method."""

    def test_get_file_revision(self, api_client):
        """Test getting file revision number."""
        # Mock get_file to return data with revn
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 42}):
            revn = api_client.get_file_revision("file-123")
            
            assert revn == 42

    def test_get_file_revision_default(self, api_client):
        """Test revision defaults to 0 if not present."""
        # Mock get_file to return data without revn
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123'}):
            revn = api_client.get_file_revision("file-123")
            
            assert revn == 0

    def test_get_file_revision_zero(self, api_client):
        """Test that revision number 0 is handled correctly."""
        # Mock get_file to return data with revn=0
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 0}):
            revn = api_client.get_file_revision("file-123")
            
            assert revn == 0

    def test_get_file_revision_large_number(self, api_client):
        """Test with large revision numbers."""
        # Mock get_file to return data with large revn
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 9999}):
            revn = api_client.get_file_revision("file-123")
            
            assert revn == 9999

    def test_get_file_revision_debug_logging(self, api_client, capsys):
        """Test that debug logging works in get_file_revision."""
        # Mock get_file to return data with revn
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 10}):
            api_client.get_file_revision("file-123")
            
            captured = capsys.readouterr()
            assert "Current revision for file file-123: 10" in captured.out


class TestEditingSessionContext:
    """Tests for editing_session context manager."""

    def test_editing_session_context(self, api_client):
        """Test editing session context manager."""
        # Mock get_file
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 10}):
            with api_client.editing_session("file-123") as (session_id, revn):
                assert isinstance(session_id, str)
                assert len(session_id) == 36
                assert revn == 10

    def test_editing_session_yields_correct_data(self, api_client):
        """Test that context manager provides usable data."""
        with patch.object(api_client, 'get_file', return_value={'id': 'test-file', 'revn': 5}):
            file_id = "test-file"
            
            with api_client.editing_session(file_id) as (session_id, revn):
                # Should be able to use these in update_file call
                assert session_id is not None
                assert revn == 5
                
                # Simulate what update_file would do
                next_revn = revn + 1
                assert next_revn == 6

    def test_editing_session_cleanup(self, api_client):
        """Test that context manager cleanup works."""
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 3}):
            try:
                with api_client.editing_session("file-123") as (session_id, revn):
                    assert session_id is not None
                    assert revn == 3
            except Exception:
                pytest.fail("Context manager cleanup failed")

    def test_editing_session_with_exception(self, api_client):
        """Test that context manager handles exceptions properly."""
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 7}):
            with pytest.raises(ValueError):
                with api_client.editing_session("file-123") as (session_id, revn):
                    # Simulate an error during editing
                    raise ValueError("Simulated error")

    def test_editing_session_debug_logging(self, api_client, capsys):
        """Test that debug logging works in editing_session."""
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 15}):
            with api_client.editing_session("file-123") as (session_id, revn):
                pass
            
            captured = capsys.readouterr()
            assert "Starting editing session" in captured.out
            assert "at revision 15" in captured.out
            assert "Ending editing session" in captured.out

    def test_editing_session_unique_ids(self, api_client):
        """Test that each context manager generates unique session IDs."""
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 1}):
            with api_client.editing_session("file-123") as (session_id1, _):
                with api_client.editing_session("file-123") as (session_id2, _):
                    assert session_id1 != session_id2


class TestSessionManagementIntegration:
    """Integration tests for session and revision management."""

    def test_session_workflow(self, api_client):
        """Test typical session workflow."""
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 5}):
            # Generate a session ID
            session_id = api_client.generate_session_id()
            assert session_id is not None
            
            # Get revision number
            revn = api_client.get_file_revision("file-123")
            assert revn == 5
            
            # Verify they can be used together
            assert isinstance(session_id, str)
            assert isinstance(revn, int)

    def test_context_manager_workflow(self, api_client):
        """Test workflow using context manager."""
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 10}):
            with api_client.editing_session("file-123") as (session_id, revn):
                # Verify we have valid session data
                assert len(session_id) == 36
                assert revn == 10
                
                # Could be used for update_file in the future
                # api.update_file(file_id, session_id, revn, changes)
