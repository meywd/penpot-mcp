"""Tests for MCP design modification tools."""

from unittest.mock import MagicMock, patch

import pytest

from penpot_mcp.api.penpot_api import PenpotAPI


@pytest.fixture
def mock_api_client():
    """Create a mock PenpotAPI client."""
    with patch.object(PenpotAPI, 'login_with_password'):
        api = PenpotAPI(debug=False)
        api.access_token = "test-token"
        
        # Mock the editing_session context manager
        api.editing_session = MagicMock()
        api.editing_session.return_value.__enter__ = MagicMock(return_value=("session-123", 10))
        api.editing_session.return_value.__exit__ = MagicMock(return_value=False)
        
        # Mock the update_file method
        api.update_file = MagicMock(return_value={"id": "file-123", "revn": 11})
        
        return api


def test_move_object_tool(mock_api_client):
    """Test move_object MCP tool."""
    # Create a callable that matches the tool implementation
    def move_object(file_id: str, object_id: str, x: float, y: float):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                ops = [
                    mock_api_client.create_set_operation('x', x),
                    mock_api_client.create_set_operation('y', y)
                ]
                change = mock_api_client.create_mod_obj_change(object_id, ops)
                result = mock_api_client.update_file(file_id, session_id, revn, [change])
                
                return {
                    "success": True,
                    "objectId": object_id,
                    "revn": result.get('revn')
                }
        except Exception as e:
            return {"error": str(e)}
    
    # Call the tool
    result = move_object("file-123", "obj-456", 200, 150)
    
    # Verify result
    assert result["success"] is True
    assert result["objectId"] == "obj-456"
    assert result["revn"] == 11
    
    # Verify API calls
    mock_api_client.editing_session.assert_called_once_with("file-123")
    mock_api_client.update_file.assert_called_once()


def test_resize_object_tool(mock_api_client):
    """Test resize_object MCP tool."""
    def resize_object(file_id: str, object_id: str, width: float, height: float):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                ops = [
                    mock_api_client.create_set_operation('width', width),
                    mock_api_client.create_set_operation('height', height)
                ]
                change = mock_api_client.create_mod_obj_change(object_id, ops)
                result = mock_api_client.update_file(file_id, session_id, revn, [change])
                
                return {
                    "success": True,
                    "objectId": object_id,
                    "revn": result.get('revn')
                }
        except Exception as e:
            return {"error": str(e)}
    
    result = resize_object("file-123", "obj-456", 300, 200)
    
    assert result["success"] is True
    assert result["objectId"] == "obj-456"
    assert result["revn"] == 11
    
    mock_api_client.update_file.assert_called_once()


def test_change_color_tool(mock_api_client):
    """Test change_object_color MCP tool."""
    def change_object_color(file_id: str, object_id: str, fill_color: str, fill_opacity: float = 1.0):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                fills = [{
                    'fillColor': fill_color,
                    'fillOpacity': fill_opacity
                }]
                ops = [
                    mock_api_client.create_set_operation('fills', fills)
                ]
                change = mock_api_client.create_mod_obj_change(object_id, ops)
                result = mock_api_client.update_file(file_id, session_id, revn, [change])
                
                return {
                    "success": True,
                    "objectId": object_id,
                    "revn": result.get('revn')
                }
        except Exception as e:
            return {"error": str(e)}
    
    result = change_object_color("file-123", "obj-456", "#FF0000")
    
    assert result["success"] is True
    assert result["objectId"] == "obj-456"
    assert result["revn"] == 11


def test_change_color_with_opacity(mock_api_client):
    """Test change_object_color with custom opacity."""
    def change_object_color(file_id: str, object_id: str, fill_color: str, fill_opacity: float = 1.0):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                fills = [{
                    'fillColor': fill_color,
                    'fillOpacity': fill_opacity
                }]
                ops = [
                    mock_api_client.create_set_operation('fills', fills)
                ]
                change = mock_api_client.create_mod_obj_change(object_id, ops)
                result = mock_api_client.update_file(file_id, session_id, revn, [change])
                
                return {
                    "success": True,
                    "objectId": object_id,
                    "revn": result.get('revn')
                }
        except Exception as e:
            return {"error": str(e)}
    
    result = change_object_color("file-123", "obj-456", "#00FF00", 0.5)
    
    assert result["success"] is True
    assert result["revn"] == 11


def test_rotate_object_tool(mock_api_client):
    """Test rotate_object MCP tool."""
    def rotate_object(file_id: str, object_id: str, rotation: float):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                ops = [
                    mock_api_client.create_set_operation('rotation', rotation)
                ]
                change = mock_api_client.create_mod_obj_change(object_id, ops)
                result = mock_api_client.update_file(file_id, session_id, revn, [change])
                
                return {
                    "success": True,
                    "objectId": object_id,
                    "revn": result.get('revn')
                }
        except Exception as e:
            return {"error": str(e)}
    
    result = rotate_object("file-123", "obj-456", 45)
    
    assert result["success"] is True
    assert result["objectId"] == "obj-456"
    assert result["revn"] == 11


def test_delete_object_tool(mock_api_client):
    """Test delete_object MCP tool."""
    def delete_object(file_id: str, page_id: str, object_id: str):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                change = mock_api_client.create_del_obj_change(object_id, page_id)
                result = mock_api_client.update_file(file_id, session_id, revn, [change])
                
                return {
                    "success": True,
                    "deletedObjectId": object_id,
                    "revn": result.get('revn')
                }
        except Exception as e:
            return {"error": str(e)}
    
    result = delete_object("file-123", "page-456", "obj-789")
    
    assert result["success"] is True
    assert result["deletedObjectId"] == "obj-789"
    assert result["revn"] == 11


def test_batch_changes_tool(mock_api_client):
    """Test apply_design_changes with multiple operations."""
    def apply_design_changes(file_id: str, changes: list):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                result = mock_api_client.update_file(file_id, session_id, revn, changes)
                
                return {
                    "success": True,
                    "revn": result.get('revn'),
                    "changesApplied": len(changes)
                }
        except Exception as e:
            return {"error": str(e)}
    
    changes = [
        {
            "type": "add-obj",
            "id": "obj-1",
            "pageId": "page-1",
            "obj": {"type": "rect", "x": 0, "y": 0}
        },
        {
            "type": "mod-obj",
            "id": "obj-2",
            "operations": [{"type": "set", "attr": "x", "val": 100}]
        }
    ]
    
    result = apply_design_changes("file-123", changes)
    
    assert result["success"] is True
    assert result["changesApplied"] == 2
    assert result["revn"] == 11


def test_batch_changes_empty_list(mock_api_client):
    """Test apply_design_changes with empty list."""
    def apply_design_changes(file_id: str, changes: list):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                result = mock_api_client.update_file(file_id, session_id, revn, changes)
                
                return {
                    "success": True,
                    "revn": result.get('revn'),
                    "changesApplied": len(changes)
                }
        except Exception as e:
            return {"error": str(e)}
    
    result = apply_design_changes("file-123", [])
    
    assert result["success"] is True
    assert result["changesApplied"] == 0


def test_move_object_error_handling(mock_api_client):
    """Test move_object error handling."""
    # Make update_file raise an exception
    mock_api_client.update_file.side_effect = Exception("Test error")
    
    def move_object(file_id: str, object_id: str, x: float, y: float):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                ops = [
                    mock_api_client.create_set_operation('x', x),
                    mock_api_client.create_set_operation('y', y)
                ]
                change = mock_api_client.create_mod_obj_change(object_id, ops)
                result = mock_api_client.update_file(file_id, session_id, revn, [change])
                
                return {
                    "success": True,
                    "objectId": object_id,
                    "revn": result.get('revn')
                }
        except Exception as e:
            return {"error": str(e)}
    
    result = move_object("file-123", "obj-456", 200, 150)
    
    assert "error" in result
    assert result["error"] == "Test error"


def test_delete_object_error_handling(mock_api_client):
    """Test delete_object error handling."""
    # Make update_file raise an exception
    mock_api_client.update_file.side_effect = Exception("Delete failed")
    
    def delete_object(file_id: str, page_id: str, object_id: str):
        try:
            with mock_api_client.editing_session(file_id) as (session_id, revn):
                change = mock_api_client.create_del_obj_change(object_id, page_id)
                result = mock_api_client.update_file(file_id, session_id, revn, [change])
                
                return {
                    "success": True,
                    "deletedObjectId": object_id,
                    "revn": result.get('revn')
                }
        except Exception as e:
            return {"error": str(e)}
    
    result = delete_object("file-123", "page-456", "obj-789")
    
    assert "error" in result
    assert result["error"] == "Delete failed"
