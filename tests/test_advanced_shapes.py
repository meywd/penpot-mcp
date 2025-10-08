"""Tests for advanced shape creation helper methods."""

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


class TestCreatePath:
    """Tests for create_path method."""

    def test_create_path_basic(self, api_client):
        """Test basic path creation with triangle."""
        points = [
            {'x': 50, 'y': 0},
            {'x': 100, 'y': 100},
            {'x': 0, 'y': 100}
        ]
        path = api_client.create_path(points, fill_color='#ff0000')

        assert path['type'] == 'path'
        assert path['name'] == 'Path'
        assert 'content' in path
        assert len(path['content']) == 4  # M, L, L, Z
        assert path['content'][0]['command'] == 'M'
        assert path['content'][1]['command'] == 'L'
        assert path['content'][2]['command'] == 'L'
        assert path['content'][3]['command'] == 'Z'
        assert 'fills' in path
        assert path['fills'][0]['fillColor'] == '#ff0000'

    def test_create_path_open(self, api_client):
        """Test open path (not closed)."""
        points = [
            {'x': 0, 'y': 0},
            {'x': 100, 'y': 0}
        ]
        path = api_client.create_path(points, closed=False)

        assert len(path['content']) == 2  # M, L (no Z)
        assert path['content'][0]['command'] == 'M'
        assert path['content'][1]['command'] == 'L'

    def test_create_path_with_stroke(self, api_client):
        """Test path with stroke."""
        points = [
            {'x': 0, 'y': 0},
            {'x': 100, 'y': 0},
            {'x': 100, 'y': 100}
        ]
        path = api_client.create_path(
            points,
            stroke_color='#0000ff',
            stroke_width=2.5
        )

        assert 'strokes' in path
        assert len(path['strokes']) == 1
        assert path['strokes'][0]['strokeColor'] == '#0000ff'
        assert path['strokes'][0]['strokeWidth'] == 2.5

    def test_create_path_without_fill(self, api_client):
        """Test path without fill."""
        points = [
            {'x': 0, 'y': 0},
            {'x': 100, 'y': 0}
        ]
        path = api_client.create_path(points)

        assert 'fills' not in path

    def test_create_path_custom_name(self, api_client):
        """Test path with custom name."""
        points = [
            {'x': 0, 'y': 0},
            {'x': 100, 'y': 0}
        ]
        path = api_client.create_path(points, name="My Path")

        assert path['name'] == "My Path"

    def test_create_path_bounding_box(self, api_client):
        """Test path calculates correct bounding box."""
        points = [
            {'x': 10, 'y': 20},
            {'x': 110, 'y': 120},
            {'x': 60, 'y': 70}
        ]
        path = api_client.create_path(points)

        assert path['x'] == 10
        assert path['y'] == 20
        assert path['width'] == 100
        assert path['height'] == 100

    def test_create_path_with_kwargs(self, api_client):
        """Test path with additional properties via kwargs."""
        points = [
            {'x': 0, 'y': 0},
            {'x': 100, 'y': 0}
        ]
        path = api_client.create_path(
            points,
            custom_property="custom_value"
        )

        assert path['custom_property'] == "custom_value"

    def test_create_path_requires_at_least_two_points(self, api_client):
        """Test path creation fails with less than 2 points."""
        with pytest.raises(ValueError, match="at least 2 points"):
            api_client.create_path([{'x': 0, 'y': 0}])

        with pytest.raises(ValueError, match="at least 2 points"):
            api_client.create_path([])


class TestCreateBooleanShape:
    """Tests for create_boolean_shape method."""

    def test_create_boolean_shape_union(self, api_client):
        """Test boolean union shape creation."""
        bool_shape = api_client.create_boolean_shape(
            operation='union',
            shapes=['obj-1', 'obj-2']
        )

        assert bool_shape['type'] == 'bool'
        assert bool_shape['bool-type'] == 'union'
        assert len(bool_shape['shapes']) == 2
        assert bool_shape['shapes'][0] == 'obj-1'
        assert bool_shape['shapes'][1] == 'obj-2'

    def test_create_boolean_shape_difference(self, api_client):
        """Test boolean difference shape creation."""
        bool_shape = api_client.create_boolean_shape(
            operation='difference',
            shapes=['obj-1', 'obj-2', 'obj-3']
        )

        assert bool_shape['bool-type'] == 'difference'
        assert len(bool_shape['shapes']) == 3

    def test_create_boolean_shape_intersection(self, api_client):
        """Test boolean intersection shape creation."""
        bool_shape = api_client.create_boolean_shape(
            operation='intersection',
            shapes=['obj-1', 'obj-2']
        )

        assert bool_shape['bool-type'] == 'intersection'

    def test_create_boolean_shape_exclusion(self, api_client):
        """Test boolean exclusion shape creation."""
        bool_shape = api_client.create_boolean_shape(
            operation='exclusion',
            shapes=['obj-1', 'obj-2']
        )

        assert bool_shape['bool-type'] == 'exclusion'

    def test_create_boolean_shape_custom_name(self, api_client):
        """Test boolean shape with custom name."""
        bool_shape = api_client.create_boolean_shape(
            operation='union',
            shapes=['obj-1', 'obj-2'],
            name="My Boolean"
        )

        assert bool_shape['name'] == "My Boolean"

    def test_create_boolean_shape_with_kwargs(self, api_client):
        """Test boolean shape with additional properties via kwargs."""
        bool_shape = api_client.create_boolean_shape(
            operation='union',
            shapes=['obj-1', 'obj-2'],
            custom_property="custom_value"
        )

        assert bool_shape['custom_property'] == "custom_value"

    def test_create_boolean_shape_invalid_operation(self, api_client):
        """Test boolean shape creation fails with invalid operation."""
        with pytest.raises(ValueError, match="Invalid operation"):
            api_client.create_boolean_shape(
                operation='invalid',
                shapes=['obj-1', 'obj-2']
            )

    def test_create_boolean_shape_requires_at_least_two_shapes(self, api_client):
        """Test boolean shape creation fails with less than 2 shapes."""
        with pytest.raises(ValueError, match="at least 2 shapes"):
            api_client.create_boolean_shape(
                operation='union',
                shapes=['obj-1']
            )

        with pytest.raises(ValueError, match="at least 2 shapes"):
            api_client.create_boolean_shape(
                operation='union',
                shapes=[]
            )


class TestCreateParentOperation:
    """Tests for create_parent_operation method."""

    def test_create_parent_operation_basic(self, api_client):
        """Test parent operation creation."""
        op = api_client.create_parent_operation('group-123')

        assert op['type'] == 'set'
        assert op['attr'] == 'parentId'
        assert op['val'] == 'group-123'

    def test_create_parent_operation_different_parent(self, api_client):
        """Test parent operation with different parent ID."""
        op = api_client.create_parent_operation('frame-456')

        assert op['val'] == 'frame-456'


class TestAdvancedShapeIntegration:
    """Integration tests for advanced shape helpers with change builders."""

    def test_create_path_and_add_to_file(self, api_client):
        """Test complete workflow: create path and add to file."""
        # Create path
        points = [
            {'x': 0, 'y': 0},
            {'x': 100, 'y': 0},
            {'x': 50, 'y': 100}
        ]
        path = api_client.create_path(points, fill_color='#00ff00')

        # Create add-obj change
        change = api_client.create_add_obj_change('path-1', 'page-1', path)

        assert change['type'] == 'add-obj'
        assert change['id'] == 'path-1'
        assert change['obj']['type'] == 'path'
        assert len(change['obj']['content']) == 4

    def test_group_multiple_objects(self, api_client):
        """Test creating group and adding objects to it."""
        # Create group
        group = api_client.create_group(name="Button Group")
        group_change = api_client.create_add_obj_change('group-1', 'page-1', group)

        # Create objects to add to group
        rect = api_client.create_rectangle(0, 0, 100, 50)
        text = api_client.create_text(10, 15, "Click Me")

        # Create parent operations to move objects into group
        parent_op = api_client.create_parent_operation('group-1')
        
        # Add objects with parent set
        rect['parentId'] = 'group-1'
        text['parentId'] = 'group-1'
        
        rect_change = api_client.create_add_obj_change('rect-1', 'page-1', rect)
        text_change = api_client.create_add_obj_change('text-1', 'page-1', text)

        assert group_change['obj']['type'] == 'group'
        assert rect_change['obj']['parentId'] == 'group-1'
        assert text_change['obj']['parentId'] == 'group-1'

    def test_boolean_operation_workflow(self, api_client):
        """Test creating shapes and applying boolean operation."""
        # Create two circles
        circle1 = api_client.create_circle(50, 50, 30, fill_color='#ff0000')
        circle2 = api_client.create_circle(70, 50, 30, fill_color='#00ff00')

        # Add circles to page
        circle1_change = api_client.create_add_obj_change('circle-1', 'page-1', circle1)
        circle2_change = api_client.create_add_obj_change('circle-2', 'page-1', circle2)

        # Create boolean shape that references the circles
        bool_shape = api_client.create_boolean_shape(
            operation='union',
            shapes=['circle-1', 'circle-2'],
            name="Union of Circles"
        )
        bool_change = api_client.create_add_obj_change('bool-1', 'page-1', bool_shape)

        assert circle1_change['obj']['type'] == 'circle'
        assert circle2_change['obj']['type'] == 'circle'
        assert bool_change['obj']['type'] == 'bool'
        assert bool_change['obj']['bool-type'] == 'union'
        assert len(bool_change['obj']['shapes']) == 2

    def test_complex_path_workflow(self, api_client):
        """Test creating complex path with multiple operations."""
        # Create a pentagon
        points = [
            {'x': 50, 'y': 0},
            {'x': 100, 'y': 38},
            {'x': 81, 'y': 95},
            {'x': 19, 'y': 95},
            {'x': 0, 'y': 38}
        ]
        path = api_client.create_path(
            points,
            closed=True,
            fill_color='#ff00ff',
            stroke_color='#000000',
            stroke_width=2,
            name="Pentagon"
        )

        # Create change
        change = api_client.create_add_obj_change('pentagon-1', 'page-1', path)

        assert change['obj']['type'] == 'path'
        assert change['obj']['name'] == "Pentagon"
        assert len(change['obj']['content']) == 6  # M + 4xL + Z
        assert change['obj']['fills'][0]['fillColor'] == '#ff00ff'
        assert change['obj']['strokes'][0]['strokeColor'] == '#000000'

    def test_parent_operation_in_mod_obj(self, api_client):
        """Test using parent operation in mod-obj change."""
        # Create parent operation
        parent_op = api_client.create_parent_operation('group-123')
        
        # Create mod-obj change
        change = api_client.create_mod_obj_change('obj-1', [parent_op])

        assert change['type'] == 'mod-obj'
        assert change['id'] == 'obj-1'
        assert len(change['operations']) == 1
        assert change['operations'][0]['attr'] == 'parentId'
        assert change['operations'][0]['val'] == 'group-123'
