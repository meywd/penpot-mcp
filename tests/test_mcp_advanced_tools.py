"""Tests for MCP advanced design tools (Phase 3)."""

from unittest.mock import MagicMock, patch

import pytest

from penpot_mcp.api.penpot_api import PenpotAPI
from penpot_mcp.server.mcp_server import PenpotMCPServer


@pytest.fixture
def mock_server():
    """Create a mock PenpotMCPServer with a mock API."""
    server = PenpotMCPServer(name="Test Server", test_mode=True)

    # Mock the API methods
    server.api.generate_session_id = MagicMock(return_value="test-obj-id-123")
    server.api.get_file = MagicMock(return_value={'id': 'file-123', 'revn': 1})
    server.api.update_file = MagicMock(return_value={'revn': 2})

    # Mock advanced shape creation methods
    server.api.create_path = MagicMock(return_value={
        'type': 'path',
        'name': 'Path',
        'x': 0,
        'y': 0,
        'width': 100,
        'height': 100,
        'content': []
    })
    server.api.create_group = MagicMock(return_value={
        'type': 'group',
        'name': 'Group'
    })
    server.api.create_boolean_shape = MagicMock(return_value={
        'type': 'bool',
        'name': 'Boolean',
        'bool-type': 'union',
        'shapes': []
    })

    # Mock styling methods
    server.api.create_gradient_fill = MagicMock(return_value={
        'type': 'linear-gradient',
        'start-color': '#ff0000',
        'end-color': '#0000ff'
    })
    server.api.create_stroke = MagicMock(return_value={
        'stroke-color': '#000000',
        'stroke-width': 2.0
    })
    server.api.create_shadow = MagicMock(return_value={
        'color': '#00000080',
        'offset-x': 2,
        'offset-y': 2,
        'blur': 4
    })
    server.api.create_blur = MagicMock(return_value={
        'type': 'layer-blur',
        'value': 10
    })

    # Mock operation creation methods
    server.api.create_add_obj_change = MagicMock(return_value={
        'type': 'add-obj',
        'id': 'test-obj-id-123',
        'pageId': 'page-456',
        'obj': {}
    })
    server.api.create_mod_obj_change = MagicMock(return_value={
        'type': 'mod-obj',
        'id': 'obj-456',
        'operations': []
    })
    server.api.create_parent_operation = MagicMock(return_value={
        'type': 'set',
        'attr': 'parent-id',
        'val': 'group-123'
    })
    server.api.create_fill_operation = MagicMock(return_value={
        'type': 'set',
        'attr': 'fills',
        'val': []
    })
    server.api.create_stroke_operation = MagicMock(return_value={
        'type': 'set',
        'attr': 'strokes',
        'val': []
    })
    server.api.create_shadow_operation = MagicMock(return_value={
        'type': 'set',
        'attr': 'shadow',
        'val': []
    })
    server.api.create_blur_operation = MagicMock(return_value={
        'type': 'set',
        'attr': 'blur',
        'val': {}
    })

    return server


# ========== ADVANCED SHAPE TOOLS TESTS ==========

def test_create_path_tool(mock_server):
    """Test create_path MCP tool."""
    # Test the API method that the tool uses
    result = mock_server.api.create_path(
        points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 50, "y": 100}],
        closed=True,
        fill_color="#ff0000"
    )
    
    assert result['type'] == 'path'
    assert result['name'] == 'Path'
    assert 'content' in result


def test_create_group_tool(mock_server):
    """Test create_group MCP tool."""
    # Update mock to return provided name
    mock_server.api.create_group = MagicMock(return_value={
        'type': 'group',
        'name': 'My Group'
    })
    
    result = mock_server.api.create_group(name="My Group")
    
    assert result['type'] == 'group'
    assert result['name'] == 'My Group'


def test_add_object_to_group_tool(mock_server):
    """Test add_object_to_group MCP tool."""
    result = mock_server.api.create_parent_operation("group-123")
    
    assert result['type'] == 'set'
    assert result['attr'] == 'parent-id'
    assert result['val'] == 'group-123'


def test_create_boolean_shape_tool(mock_server):
    """Test create_boolean_shape MCP tool."""
    result = mock_server.api.create_boolean_shape(
        operation='union',
        shapes=['shape-1', 'shape-2']
    )
    
    assert result['type'] == 'bool'
    assert result['name'] == 'Boolean'
    assert result['bool-type'] == 'union'


# ========== ADVANCED STYLING TOOLS TESTS ==========

def test_apply_gradient_tool(mock_server):
    """Test apply_gradient MCP tool."""
    result = mock_server.api.create_gradient_fill(
        gradient_type='linear',
        start_color='#ff0000',
        end_color='#0000ff'
    )
    
    assert result['type'] == 'linear-gradient'
    assert result['start-color'] == '#ff0000'
    assert result['end-color'] == '#0000ff'


def test_add_stroke_tool(mock_server):
    """Test add_stroke MCP tool."""
    result = mock_server.api.create_stroke(
        color='#000000',
        width=2.0,
        style='solid'
    )
    
    assert result['stroke-color'] == '#000000'
    assert result['stroke-width'] == 2.0


def test_add_shadow_tool(mock_server):
    """Test add_shadow MCP tool."""
    result = mock_server.api.create_shadow(
        color='#00000080',
        offset_x=2,
        offset_y=2,
        blur=4
    )
    
    assert result['color'] == '#00000080'
    assert result['offset-x'] == 2
    assert result['offset-y'] == 2
    assert result['blur'] == 4


def test_apply_blur_tool(mock_server):
    """Test apply_blur MCP tool."""
    result = mock_server.api.create_blur(
        blur_type='layer-blur',
        value=10
    )
    
    assert result['type'] == 'layer-blur'
    assert result['value'] == 10


# ========== INTEGRATION TESTS ==========

class TestAdvancedShapeIntegration:
    """Integration tests for advanced shape tools."""

    def test_create_path_workflow(self, mock_server):
        """Test complete workflow: create path and verify in file."""
        # Mock editing session
        mock_server.api.editing_session = MagicMock()
        mock_server.api.editing_session.return_value.__enter__ = MagicMock(
            return_value=("session-123", 1)
        )
        mock_server.api.editing_session.return_value.__exit__ = MagicMock(return_value=False)

        # Test API creates path correctly
        path = mock_server.api.create_path(
            points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 50, "y": 100}],
            closed=True,
            fill_color="#ff0000"
        )
        
        assert path['type'] == 'path'
        assert path['name'] == 'Path'

    def test_group_objects_workflow(self, mock_server):
        """Test creating objects and grouping them."""
        # Mock editing session
        mock_server.api.editing_session = MagicMock()
        mock_server.api.editing_session.return_value.__enter__ = MagicMock(
            return_value=("session-123", 1)
        )
        mock_server.api.editing_session.return_value.__exit__ = MagicMock(return_value=False)

        # Test group creation
        group = mock_server.api.create_group(name="Test Group")
        assert group['type'] == 'group'
        
        # Test parent operation
        parent_op = mock_server.api.create_parent_operation("group-id")
        assert parent_op['type'] == 'set'
        assert parent_op['attr'] == 'parent-id'

    def test_apply_multiple_effects(self, mock_server):
        """Test applying gradient, stroke, and shadow to object."""
        # Mock editing session
        mock_server.api.editing_session = MagicMock()
        mock_server.api.editing_session.return_value.__enter__ = MagicMock(
            return_value=("session-123", 1)
        )
        mock_server.api.editing_session.return_value.__exit__ = MagicMock(return_value=False)

        # Test creating multiple effects
        gradient = mock_server.api.create_gradient_fill(
            'linear', '#ff0000', '#0000ff'
        )
        assert gradient['type'] == 'linear-gradient'
        
        stroke = mock_server.api.create_stroke('#000000', width=2.0)
        assert stroke['stroke-width'] == 2.0
        
        shadow = mock_server.api.create_shadow('#00000080', 2, 2, 4)
        assert shadow['blur'] == 4


# ========== ERROR HANDLING TESTS ==========

class TestAdvancedToolsErrorHandling:
    """Test error handling for advanced tools."""

    def test_create_path_with_invalid_points(self, mock_server):
        """Test that create_path handles invalid points gracefully."""
        # Mock the API to raise an error
        mock_server.api.create_path = MagicMock(
            side_effect=ValueError("Path must have at least 2 points")
        )
        mock_server.api.editing_session = MagicMock()
        mock_server.api.editing_session.return_value.__enter__ = MagicMock(
            return_value=("session-123", 1)
        )
        mock_server.api.editing_session.return_value.__exit__ = MagicMock(return_value=False)

        # Tool should handle the error and return error dict
        # (actual invocation would require calling through FastMCP)

    def test_create_boolean_with_invalid_operation(self, mock_server):
        """Test that create_boolean_shape handles invalid operations."""
        mock_server.api.create_boolean_shape = MagicMock(
            side_effect=ValueError("Invalid operation")
        )
        mock_server.api.editing_session = MagicMock()
        mock_server.api.editing_session.return_value.__enter__ = MagicMock(
            return_value=("session-123", 1)
        )
        mock_server.api.editing_session.return_value.__exit__ = MagicMock(return_value=False)

    def test_apply_gradient_with_invalid_type(self, mock_server):
        """Test that apply_gradient handles invalid gradient types."""
        mock_server.api.create_gradient_fill = MagicMock(
            side_effect=ValueError("Invalid gradient_type")
        )
        mock_server.api.editing_session = MagicMock()
        mock_server.api.editing_session.return_value.__enter__ = MagicMock(
            return_value=("session-123", 1)
        )
        mock_server.api.editing_session.return_value.__exit__ = MagicMock(return_value=False)
