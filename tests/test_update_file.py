"""Tests for update_file and change builder methods."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from penpot_mcp.api.penpot_api import PenpotAPI, RevisionConflictError


@pytest.fixture
def api_client():
    """Create a PenpotAPI client for testing."""
    with patch.object(PenpotAPI, 'login_with_password'):
        api = PenpotAPI(debug=True)
        api.access_token = "test-token"
        return api


class TestRevisionConflictError:
    """Tests for RevisionConflictError exception."""

    def test_revision_conflict_error_inheritance(self):
        """Test that RevisionConflictError inherits from PenpotAPIError."""
        from penpot_mcp.api.penpot_api import PenpotAPIError
        error = RevisionConflictError("test")
        assert isinstance(error, PenpotAPIError)

    def test_revision_conflict_error_message(self):
        """Test error message is preserved."""
        error = RevisionConflictError("Revision mismatch")
        assert str(error) == "Revision mismatch"


class TestConvertChangesToTransit:
    """Tests for _convert_changes_to_transit method."""

    def test_convert_simple_change(self, api_client):
        """Test conversion of a simple change operation."""
        changes = [{'type': 'add-obj', 'id': 'obj-123', 'pageId': 'page-456'}]
        transit = api_client._convert_changes_to_transit(changes)
        
        assert len(transit) == 1
        assert transit[0]['~:type'] == '~:add-obj'
        assert transit[0]['~:id'] == '~uobj-123'
        assert transit[0]['~:pageId'] == '~upage-456'

    def test_convert_nested_object(self, api_client):
        """Test conversion with nested object."""
        changes = [{
            'type': 'add-obj',
            'id': 'obj-123',
            'pageId': 'page-456',
            'obj': {
                'type': 'rect',
                'x': 0,
                'y': 0
            }
        }]
        transit = api_client._convert_changes_to_transit(changes)
        
        assert transit[0]['~:obj']['~:type'] == '~:rect'
        assert transit[0]['~:obj']['~:x'] == 0
        assert transit[0]['~:obj']['~:y'] == 0

    def test_convert_with_operations_list(self, api_client):
        """Test conversion with operations list."""
        changes = [{
            'type': 'mod-obj',
            'id': 'obj-123',
            'operations': [
                {'type': 'set', 'attr': 'x', 'val': 100}
            ]
        }]
        transit = api_client._convert_changes_to_transit(changes)
        
        assert transit[0]['~:operations'][0]['~:type'] == '~:set'
        assert transit[0]['~:operations'][0]['~:attr'] == '~:x'
        assert transit[0]['~:operations'][0]['~:val'] == 100

    def test_convert_multiple_changes(self, api_client):
        """Test conversion of multiple changes."""
        changes = [
            {'type': 'add-obj', 'id': 'obj-1', 'pageId': 'page-1'},
            {'type': 'del-obj', 'id': 'obj-2', 'pageId': 'page-1'}
        ]
        transit = api_client._convert_changes_to_transit(changes)
        
        assert len(transit) == 2
        assert transit[0]['~:type'] == '~:add-obj'
        assert transit[1]['~:type'] == '~:del-obj'

    def test_convert_preserves_non_uuid_strings(self, api_client):
        """Test that non-UUID strings are preserved."""
        changes = [{
            'type': 'add-obj',
            'id': 'obj-123',
            'pageId': 'page-456',
            'obj': {
                'name': 'My Object'
            }
        }]
        transit = api_client._convert_changes_to_transit(changes)
        
        # Name should not get ~u prefix
        assert transit[0]['~:obj']['~:name'] == 'My Object'

    def test_convert_with_frame_id(self, api_client):
        """Test conversion with frameId field."""
        changes = [{
            'type': 'add-obj',
            'id': 'obj-123',
            'pageId': 'page-456',
            'frameId': 'frame-789'
        }]
        transit = api_client._convert_changes_to_transit(changes)
        
        assert transit[0]['~:frameId'] == '~uframe-789'

    def test_convert_with_parent_id(self, api_client):
        """Test conversion with parentId field."""
        changes = [{
            'type': 'add-obj',
            'id': 'obj-123',
            'pageId': 'page-456',
            'obj': {
                'parentId': 'parent-789'
            }
        }]
        transit = api_client._convert_changes_to_transit(changes)
        
        assert transit[0]['~:obj']['~:parentId'] == '~uparent-789'

    def test_convert_with_numeric_values(self, api_client):
        """Test conversion preserves numeric values."""
        changes = [{
            'type': 'mod-obj',
            'id': 'obj-123',
            'operations': [
                {'type': 'set', 'attr': 'x', 'val': 100},
                {'type': 'set', 'attr': 'y', 'val': 200.5}
            ]
        }]
        transit = api_client._convert_changes_to_transit(changes)
        
        assert transit[0]['~:operations'][0]['~:val'] == 100
        assert transit[0]['~:operations'][1]['~:val'] == 200.5

    def test_convert_with_boolean_values(self, api_client):
        """Test conversion preserves boolean values."""
        changes = [{
            'type': 'add-obj',
            'id': 'obj-123',
            'pageId': 'page-456',
            'obj': {
                'visible': True,
                'locked': False
            }
        }]
        transit = api_client._convert_changes_to_transit(changes)
        
        assert transit[0]['~:obj']['~:visible'] is True
        assert transit[0]['~:obj']['~:locked'] is False


class TestUpdateFile:
    """Tests for update_file method."""

    def test_update_file_success(self, api_client):
        """Test successful file update."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            changes = [{'type': 'add-obj', 'id': 'obj-1', 'pageId': 'page-1', 'obj': {}}]
            result = api_client.update_file('file-123', 'session-123', 10, changes)
            
            assert result['revn'] == 11
            assert result['id'] == 'file-123'

    def test_update_file_revision_conflict(self, api_client):
        """Test that 409 status raises RevisionConflictError."""
        mock_response = MagicMock()
        mock_response.status_code = 409
        
        http_error = requests.HTTPError()
        http_error.response = mock_response
        
        with patch.object(api_client, '_make_authenticated_request', side_effect=http_error):
            changes = [{'type': 'add-obj', 'id': 'obj-1', 'pageId': 'page-1', 'obj': {}}]

            with pytest.raises(RevisionConflictError) as exc_info:
                api_client.update_file('file-123', 'session-123', 10, changes, vern=0)

            assert "Revision conflict" in str(exc_info.value)
            assert "Expected 10" in str(exc_info.value)

    def test_update_file_calls_transit_conversion(self, api_client):
        """Test that update_file calls _convert_changes_to_transit."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            with patch.object(api_client, '_convert_changes_to_transit', wraps=api_client._convert_changes_to_transit) as mock_convert:
                changes = [{'type': 'add-obj', 'id': 'obj-1', 'pageId': 'page-1', 'obj': {}}]
                api_client.update_file('file-123', 'session-123', 10, changes)
                
                # Verify conversion was called
                mock_convert.assert_called_once_with(changes)

    def test_update_file_sends_correct_payload(self, api_client):
        """Test that update_file sends correct payload structure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            changes = [{'type': 'add-obj', 'id': 'obj-1', 'pageId': 'page-1', 'obj': {}}]
            api_client.update_file('file-123', 'session-456', 10, changes)
            
            # Get the call arguments
            call_args = mock_request.call_args
            payload = call_args[1]['json']
            
            # Verify payload structure
            assert payload['id'] == 'file-123'
            assert payload['session-id'] == 'session-456'
            assert payload['revn'] == 10
            assert 'changes' in payload
            assert len(payload['changes']) == 1

    def test_update_file_uses_transit_format(self, api_client):
        """Test that update_file uses Transit+JSON format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            changes = [{'type': 'add-obj', 'id': 'obj-1', 'pageId': 'page-1', 'obj': {}}]
            api_client.update_file('file-123', 'session-123', 10, changes)
            
            # Verify use_transit=True was passed
            call_args = mock_request.call_args
            assert call_args[1]['use_transit'] is True

    def test_update_file_with_multiple_changes(self, api_client):
        """Test update_file with multiple change operations."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            changes = [
                {'type': 'add-obj', 'id': 'obj-1', 'pageId': 'page-1', 'obj': {}},
                {'type': 'mod-obj', 'id': 'obj-2', 'operations': []},
                {'type': 'del-obj', 'id': 'obj-3', 'pageId': 'page-1'}
            ]
            result = api_client.update_file('file-123', 'session-123', 10, changes)
            
            assert result['revn'] == 11

    def test_update_file_debug_logging(self, api_client, capsys):
        """Test that debug logging works in update_file."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            changes = [{'type': 'add-obj', 'id': 'obj-1', 'pageId': 'page-1', 'obj': {}}]
            api_client.update_file('file-123', 'session-123', 10, changes)
            
            captured = capsys.readouterr()
            assert "Updating file file-123" in captured.out
            assert "Session: session-123, Revision: 10" in captured.out
            assert "Changes: 1 operations" in captured.out
            assert "Update successful. New revision: 11" in captured.out


class TestCreateAddObjChange:
    """Tests for create_add_obj_change method."""

    def test_create_add_obj_change_basic(self, api_client):
        """Test basic add-obj change creation."""
        obj = {'type': 'rect', 'x': 0, 'y': 0}
        change = api_client.create_add_obj_change("obj-1", "page-1", obj)
        
        assert change['type'] == 'add-obj'
        assert change['id'] == 'obj-1'
        assert change['pageId'] == 'page-1'
        assert change['obj'] == obj

    def test_create_add_obj_change_with_frame(self, api_client):
        """Test add-obj change with frame_id."""
        obj = {'type': 'rect', 'x': 0, 'y': 0}
        change = api_client.create_add_obj_change("obj-1", "page-1", obj, frame_id="frame-1")
        
        assert change['type'] == 'add-obj'
        assert change['frameId'] == 'frame-1'

    def test_create_add_obj_change_without_frame(self, api_client):
        """Test that frameId is not included when None."""
        obj = {'type': 'rect'}
        change = api_client.create_add_obj_change("obj-1", "page-1", obj)
        
        assert 'frameId' not in change

    def test_create_add_obj_change_with_complex_obj(self, api_client):
        """Test add-obj change with complex object definition."""
        obj = {
            'type': 'rect',
            'x': 100,
            'y': 200,
            'width': 300,
            'height': 400,
            'fill': '#ff0000',
            'stroke': '#000000'
        }
        change = api_client.create_add_obj_change("obj-1", "page-1", obj)
        
        assert change['obj'] == obj
        assert change['obj']['x'] == 100
        assert change['obj']['fill'] == '#ff0000'


class TestCreateModObjChange:
    """Tests for create_mod_obj_change method."""

    def test_create_mod_obj_change_basic(self, api_client):
        """Test basic mod-obj change creation."""
        operations = [{'type': 'set', 'attr': 'x', 'val': 100}]
        change = api_client.create_mod_obj_change("obj-1", operations)
        
        assert change['type'] == 'mod-obj'
        assert change['id'] == 'obj-1'
        assert change['operations'] == operations

    def test_create_mod_obj_change_multiple_operations(self, api_client):
        """Test mod-obj change with multiple operations."""
        operations = [
            {'type': 'set', 'attr': 'x', 'val': 100},
            {'type': 'set', 'attr': 'y', 'val': 200}
        ]
        change = api_client.create_mod_obj_change("obj-1", operations)
        
        assert len(change['operations']) == 2
        assert change['operations'][0]['attr'] == 'x'
        assert change['operations'][1]['attr'] == 'y'

    def test_create_mod_obj_change_empty_operations(self, api_client):
        """Test mod-obj change with empty operations list."""
        change = api_client.create_mod_obj_change("obj-1", [])
        
        assert change['operations'] == []


class TestCreateSetOperation:
    """Tests for create_set_operation method."""

    def test_create_set_operation_numeric(self, api_client):
        """Test set operation with numeric value."""
        op = api_client.create_set_operation('x', 100)
        
        assert op['type'] == 'set'
        assert op['attr'] == 'x'
        assert op['val'] == 100

    def test_create_set_operation_string(self, api_client):
        """Test set operation with string value."""
        op = api_client.create_set_operation('name', 'My Object')
        
        assert op['attr'] == 'name'
        assert op['val'] == 'My Object'

    def test_create_set_operation_boolean(self, api_client):
        """Test set operation with boolean value."""
        op = api_client.create_set_operation('visible', True)
        
        assert op['attr'] == 'visible'
        assert op['val'] is True

    def test_create_set_operation_dict(self, api_client):
        """Test set operation with dictionary value."""
        op = api_client.create_set_operation('style', {'color': 'red'})
        
        assert op['attr'] == 'style'
        assert op['val'] == {'color': 'red'}


class TestCreateDelObjChange:
    """Tests for create_del_obj_change method."""

    def test_create_del_obj_change_basic(self, api_client):
        """Test basic del-obj change creation."""
        change = api_client.create_del_obj_change("obj-1", "page-1")
        
        assert change['type'] == 'del-obj'
        assert change['id'] == 'obj-1'
        assert change['pageId'] == 'page-1'

    def test_create_del_obj_change_structure(self, api_client):
        """Test del-obj change has correct structure."""
        change = api_client.create_del_obj_change("obj-123", "page-456")
        
        # Should only have these three keys
        assert len(change) == 3
        assert 'type' in change
        assert 'id' in change
        assert 'pageId' in change


class TestChangeBuilderIntegration:
    """Integration tests for change builders with update_file."""

    def test_add_obj_workflow(self, api_client):
        """Test complete workflow: create add-obj change and update file."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            # Create change using builder
            obj = {'type': 'rect', 'x': 0, 'y': 0, 'width': 100, 'height': 100}
            change = api_client.create_add_obj_change("obj-1", "page-1", obj)
            
            # Update file with change
            result = api_client.update_file('file-123', 'session-123', 10, [change])
            
            assert result['revn'] == 11

    def test_mod_obj_workflow(self, api_client):
        """Test complete workflow: create mod-obj change and update file."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            # Create change using builders
            operations = [
                api_client.create_set_operation('x', 100),
                api_client.create_set_operation('y', 200)
            ]
            change = api_client.create_mod_obj_change("obj-1", operations)
            
            # Update file with change
            result = api_client.update_file('file-123', 'session-123', 10, [change])
            
            assert result['revn'] == 11

    def test_del_obj_workflow(self, api_client):
        """Test complete workflow: create del-obj change and update file."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            # Create change using builder
            change = api_client.create_del_obj_change("obj-1", "page-1")
            
            # Update file with change
            result = api_client.update_file('file-123', 'session-123', 10, [change])
            
            assert result['revn'] == 11

    def test_multiple_changes_workflow(self, api_client):
        """Test workflow with multiple different change types."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_response.status_code = 200
        
        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            # Create multiple changes
            changes = [
                api_client.create_add_obj_change("obj-new", "page-1", {'type': 'rect'}),
                api_client.create_mod_obj_change("obj-existing", [
                    api_client.create_set_operation('x', 50)
                ]),
                api_client.create_del_obj_change("obj-old", "page-1")
            ]
            
            # Update file with all changes
            result = api_client.update_file('file-123', 'session-123', 10, changes)
            
            assert result['revn'] == 11

    def test_with_editing_session_context(self, api_client):
        """Test change builders with editing_session context manager."""
        mock_file_response = MagicMock()
        mock_file_response.json.return_value = {'id': 'file-123', 'revn': 10}
        
        mock_update_response = MagicMock()
        mock_update_response.json.return_value = {'id': 'file-123', 'revn': 11}
        mock_update_response.status_code = 200
        
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 10}):
            with patch.object(api_client, '_make_authenticated_request', return_value=mock_update_response):
                # Use editing_session context
                with api_client.editing_session("file-123") as (session_id, revn):
                    # Create changes
                    changes = [
                        api_client.create_add_obj_change("obj-1", "page-1", {'type': 'rect'})
                    ]
                    
                    # Update file
                    result = api_client.update_file("file-123", session_id, revn, changes)
                    
                    assert result['revn'] == 11
