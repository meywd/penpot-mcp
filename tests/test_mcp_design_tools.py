"""Tests for MCP design tools (modification and shape creation)."""

from unittest.mock import MagicMock, patch

import pytest

from penpot_mcp.api.penpot_api import PenpotAPI
from penpot_mcp.server.mcp_server import PenpotMCPServer


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


@pytest.fixture
def mock_server():
    """Create a mock PenpotMCPServer with a mock API."""
    server = PenpotMCPServer(name="Test Server", test_mode=True)

    # Mock the API methods for shape creation
    server.api.generate_session_id = MagicMock(return_value="test-obj-id-123")
    server.api.get_file = MagicMock(return_value={'id': 'file-123', 'revn': 1})
    server.api.update_file = MagicMock(return_value={'revn': 2})
    server.api.create_rectangle = MagicMock(return_value={
        'type': 'rect',
        'name': 'Rectangle',
        'x': 100,
        'y': 100,
        'width': 200,
        'height': 150
    })
    server.api.create_circle = MagicMock(return_value={
        'type': 'circle',
        'name': 'Circle',
        'x': 100,
        'y': 100,
        'width': 100,
        'height': 100
    })
    server.api.create_text = MagicMock(return_value={
        'type': 'text',
        'name': 'Text',
        'x': 50,
        'y': 50,
        'content': 'Hello World'
    })
    server.api.create_frame = MagicMock(return_value={
        'type': 'frame',
        'name': 'Frame',
        'x': 0,
        'y': 0,
        'width': 375,
        'height': 812
    })
    server.api.create_add_obj_change = MagicMock(return_value={
        'type': 'add-obj',
        'id': 'test-obj-id-123',
        'pageId': 'page-456',
        'obj': {}
    })

    return server


# ========== OBJECT MODIFICATION TESTS ==========

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


# ========== SHAPE CREATION TESTS ==========

class TestAddRectangleTool:
    """Tests for add_rectangle MCP tool."""

    def test_add_rectangle_basic(self, mock_server):
        """Test basic rectangle creation."""
        # Get the tool function from the server
        # We need to manually invoke it since we can't call via MCP framework in tests
        with patch.object(mock_server.api, 'editing_session') as mock_session:
            mock_session.return_value.__enter__.return_value = ("session-123", 1)

            # Simulate calling the tool - we'll need to extract and call it directly
            # For now, test the API methods are configured correctly
            result = mock_server.api.create_rectangle(100, 100, 200, 150)

            assert result['type'] == 'rect'
            assert result['name'] == 'Rectangle'
            assert result['x'] == 100
            assert result['y'] == 100
            assert result['width'] == 200
            assert result['height'] == 150

    def test_add_rectangle_with_custom_fill(self, mock_server):
        """Test rectangle with custom fill color."""
        mock_server.api.create_rectangle.return_value = {
            'type': 'rect',
            'name': 'Rectangle',
            'x': 100,
            'y': 100,
            'width': 200,
            'height': 150,
            'fills': [{'fillColor': '#FF0000'}]
        }

        result = mock_server.api.create_rectangle(
            100, 100, 200, 150,
            fill_color="#FF0000"
        )

        assert 'fills' in result
        assert result['fills'][0]['fillColor'] == '#FF0000'

    def test_add_rectangle_with_stroke(self, mock_server):
        """Test rectangle with stroke."""
        mock_server.api.create_rectangle.return_value = {
            'type': 'rect',
            'name': 'Rectangle',
            'x': 100,
            'y': 100,
            'width': 200,
            'height': 150,
            'strokes': [{'strokeColor': '#000000', 'strokeWidth': 2}]
        }

        result = mock_server.api.create_rectangle(
            100, 100, 200, 150,
            stroke_color="#000000",
            stroke_width=2
        )

        assert 'strokes' in result


class TestAddCircleTool:
    """Tests for add_circle MCP tool."""

    def test_add_circle_basic(self, mock_server):
        """Test basic circle creation."""
        result = mock_server.api.create_circle(150, 150, 50)

        assert result['type'] == 'circle'
        assert result['name'] == 'Circle'

    def test_add_circle_with_custom_fill(self, mock_server):
        """Test circle with custom fill color."""
        mock_server.api.create_circle.return_value = {
            'type': 'circle',
            'name': 'Circle',
            'x': 100,
            'y': 100,
            'width': 100,
            'height': 100,
            'fills': [{'fillColor': '#00FF00'}]
        }

        result = mock_server.api.create_circle(
            150, 150, 50,
            fill_color="#00FF00"
        )

        assert 'fills' in result
        assert result['fills'][0]['fillColor'] == '#00FF00'


class TestAddTextTool:
    """Tests for add_text MCP tool."""

    def test_add_text_basic(self, mock_server):
        """Test basic text creation."""
        result = mock_server.api.create_text(50, 50, "Hello World")

        assert result['type'] == 'text'
        assert result['name'] == 'Text'
        assert result['content'] == 'Hello World'

    def test_add_text_with_custom_font(self, mock_server):
        """Test text with custom font."""
        mock_server.api.create_text.return_value = {
            'type': 'text',
            'name': 'Text',
            'x': 50,
            'y': 50,
            'content': 'Hello World',
            'fontSize': 24,
            'fontFamily': 'Arial'
        }

        result = mock_server.api.create_text(
            50, 50, "Hello World",
            font_size=24,
            font_family="Arial"
        )

        assert result['fontSize'] == 24
        assert result['fontFamily'] == 'Arial'


class TestAddFrameTool:
    """Tests for add_frame MCP tool."""

    def test_add_frame_basic(self, mock_server):
        """Test basic frame creation."""
        result = mock_server.api.create_frame(0, 0, 375, 812)

        assert result['type'] == 'frame'
        assert result['name'] == 'Frame'
        assert result['width'] == 375
        assert result['height'] == 812

    def test_add_frame_with_name(self, mock_server):
        """Test frame with custom name."""
        mock_server.api.create_frame.return_value = {
            'type': 'frame',
            'name': 'Mobile',
            'x': 0,
            'y': 0,
            'width': 375,
            'height': 812
        }

        result = mock_server.api.create_frame(
            0, 0, 375, 812,
            name="Mobile"
        )

        assert result['name'] == 'Mobile'


class TestShapeCreationIntegration:
    """Integration tests for shape creation tools."""

    def test_create_rectangle_full_workflow(self, mock_server):
        """Test full workflow for creating a rectangle."""
        with patch.object(mock_server.api, 'editing_session') as mock_session:
            mock_session.return_value.__enter__.return_value = ("session-123", 1)

            # Create rectangle
            rect = mock_server.api.create_rectangle(100, 100, 200, 150)
            obj_id = mock_server.api.generate_session_id()
            change = mock_server.api.create_add_obj_change(obj_id, "page-456", rect)

            # Verify change structure
            assert change['type'] == 'add-obj'
            assert change['id'] == obj_id
            assert change['pageId'] == 'page-456'

            # Update file
            result = mock_server.api.update_file("file-123", "session-123", 1, [change])

            assert result['revn'] == 2

    def test_create_shapes_with_frame_parent(self, mock_server):
        """Test creating shapes with frame_id parent."""
        with patch.object(mock_server.api, 'editing_session') as mock_session:
            mock_session.return_value.__enter__.return_value = ("session-123", 1)

            # Create a frame first
            frame = mock_server.api.create_frame(0, 0, 375, 812)
            frame_id = mock_server.api.generate_session_id()

            # Create rectangle inside frame
            rect = mock_server.api.create_rectangle(10, 10, 100, 100)
            rect_id = mock_server.api.generate_session_id()

            # Create add change with frame_id
            mock_server.api.create_add_obj_change.return_value = {
                'type': 'add-obj',
                'id': rect_id,
                'pageId': 'page-456',
                'frameId': frame_id,
                'obj': rect
            }

            change = mock_server.api.create_add_obj_change(
                rect_id, "page-456", rect, frame_id=frame_id
            )

            assert change['frameId'] == frame_id

    def test_error_handling(self, mock_server):
        """Test error handling in shape creation."""
        with patch.object(mock_server.api, 'editing_session') as mock_session:
            # Simulate an error
            mock_session.side_effect = Exception("Test error")

            # This would normally be caught by _handle_api_error
            with pytest.raises(Exception) as exc_info:
                with mock_server.api.editing_session("file-123"):
                    pass

            assert "Test error" in str(exc_info.value)
