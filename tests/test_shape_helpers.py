"""Tests for shape creation helper methods."""

from unittest.mock import patch

import pytest

from penpot_mcp.api.penpot_api import PenpotAPI


@pytest.fixture
def api_client():
    """Create a PenpotAPI client for testing."""
    with patch.object(PenpotAPI, 'login_with_password'):
        api = PenpotAPI(debug=False)
        api.access_token = "test-token"
        return api


class TestCreateRectangle:
    """Tests for create_rectangle method."""

    def test_create_rectangle_basic(self, api_client):
        """Test basic rectangle creation."""
        rect = api_client.create_rectangle(100, 200, 300, 150)

        assert rect['type'] == 'rect'
        assert rect['name'] == 'Rectangle'
        assert rect['x'] == 100
        assert rect['y'] == 200
        assert rect['width'] == 300
        assert rect['height'] == 150
        assert 'fills' in rect
        assert len(rect['fills']) == 1
        assert rect['fills'][0]['fillColor'] == '#000000'
        assert rect['fills'][0]['fillOpacity'] == 1.0

    def test_create_rectangle_with_custom_fill(self, api_client):
        """Test rectangle with custom fill color."""
        rect = api_client.create_rectangle(
            100, 200, 300, 150,
            fill_color="#FF0000",
            fill_opacity=0.5
        )

        assert rect['fills'][0]['fillColor'] == '#FF0000'
        assert rect['fills'][0]['fillOpacity'] == 0.5

    def test_create_rectangle_with_stroke(self, api_client):
        """Test rectangle with stroke."""
        rect = api_client.create_rectangle(
            100, 200, 300, 150,
            stroke_color="#0000FF",
            stroke_width=2.5
        )

        assert 'strokes' in rect
        assert len(rect['strokes']) == 1
        assert rect['strokes'][0]['strokeColor'] == '#0000FF'
        assert rect['strokes'][0]['strokeWidth'] == 2.5

    def test_create_rectangle_without_stroke(self, api_client):
        """Test rectangle without stroke."""
        rect = api_client.create_rectangle(100, 200, 300, 150)

        assert 'strokes' not in rect

    def test_create_rectangle_with_corner_radius(self, api_client):
        """Test rectangle with corner radius."""
        rect = api_client.create_rectangle(
            100, 200, 300, 150,
            rx=10,
            ry=10
        )

        assert rect['rx'] == 10
        assert rect['ry'] == 10

    def test_create_rectangle_without_corner_radius(self, api_client):
        """Test rectangle without corner radius."""
        rect = api_client.create_rectangle(100, 200, 300, 150)

        assert 'rx' not in rect
        assert 'ry' not in rect

    def test_create_rectangle_with_custom_name(self, api_client):
        """Test rectangle with custom name."""
        rect = api_client.create_rectangle(
            100, 200, 300, 150,
            name="My Custom Rectangle"
        )

        assert rect['name'] == "My Custom Rectangle"

    def test_create_rectangle_with_kwargs(self, api_client):
        """Test rectangle with additional properties via kwargs."""
        rect = api_client.create_rectangle(
            100, 200, 300, 150,
            custom_property="custom_value",
            another_prop=42
        )

        assert rect['custom_property'] == "custom_value"
        assert rect['another_prop'] == 42


class TestCreateCircle:
    """Tests for create_circle method."""

    def test_create_circle_basic(self, api_client):
        """Test basic circle creation."""
        circle = api_client.create_circle(150, 150, 50)

        assert circle['type'] == 'circle'
        assert circle['name'] == 'Circle'
        assert circle['x'] == 100  # cx - radius
        assert circle['y'] == 100  # cy - radius
        assert circle['width'] == 100  # diameter
        assert circle['height'] == 100  # diameter
        assert 'fills' in circle
        assert len(circle['fills']) == 1
        assert circle['fills'][0]['fillColor'] == '#000000'
        assert circle['fills'][0]['fillOpacity'] == 1.0

    def test_create_circle_with_custom_fill(self, api_client):
        """Test circle with custom fill color."""
        circle = api_client.create_circle(
            150, 150, 50,
            fill_color="#00FF00",
            fill_opacity=0.8
        )

        assert circle['fills'][0]['fillColor'] == '#00FF00'
        assert circle['fills'][0]['fillOpacity'] == 0.8

    def test_create_circle_with_stroke(self, api_client):
        """Test circle with stroke."""
        circle = api_client.create_circle(
            150, 150, 50,
            stroke_color="#FF0000",
            stroke_width=3.0
        )

        assert 'strokes' in circle
        assert len(circle['strokes']) == 1
        assert circle['strokes'][0]['strokeColor'] == '#FF0000'
        assert circle['strokes'][0]['strokeWidth'] == 3.0

    def test_create_circle_without_stroke(self, api_client):
        """Test circle without stroke."""
        circle = api_client.create_circle(150, 150, 50)

        assert 'strokes' not in circle

    def test_create_circle_with_custom_name(self, api_client):
        """Test circle with custom name."""
        circle = api_client.create_circle(
            150, 150, 50,
            name="My Circle"
        )

        assert circle['name'] == "My Circle"

    def test_create_circle_with_kwargs(self, api_client):
        """Test circle with additional properties via kwargs."""
        circle = api_client.create_circle(
            150, 150, 50,
            custom_property="custom_value"
        )

        assert circle['custom_property'] == "custom_value"

    def test_create_ellipse_via_kwargs(self, api_client):
        """Test creating an ellipse by overriding width/height via kwargs."""
        circle = api_client.create_circle(
            150, 150, 50,
            width=200,  # Override to make ellipse
            height=100
        )

        assert circle['width'] == 200
        assert circle['height'] == 100


class TestCreateText:
    """Tests for create_text method."""

    def test_create_text_basic(self, api_client):
        """Test basic text creation."""
        text = api_client.create_text(10, 20, "Hello World")

        assert text['type'] == 'text'
        assert text['name'] == 'Text'
        assert text['x'] == 10
        assert text['y'] == 20
        assert text['content'] == 'Hello World'
        assert 'fills' in text
        assert text['fills'][0]['fillColor'] == '#000000'
        assert text['fills'][0]['fillOpacity'] == 1.0
        assert text['fontSize'] == 16
        assert text['fontFamily'] == 'Work Sans'
        assert text['fontWeight'] == 'normal'
        assert text['textAlign'] == 'left'

    def test_create_text_with_custom_font(self, api_client):
        """Test text with custom font properties."""
        text = api_client.create_text(
            10, 20, "Hello World",
            font_size=24,
            font_family="Arial",
            font_weight="bold"
        )

        assert text['fontSize'] == 24
        assert text['fontFamily'] == "Arial"
        assert text['fontWeight'] == "bold"

    def test_create_text_with_custom_color(self, api_client):
        """Test text with custom color."""
        text = api_client.create_text(
            10, 20, "Hello World",
            fill_color="#FF0000"
        )

        assert text['fills'][0]['fillColor'] == '#FF0000'

    def test_create_text_with_alignment(self, api_client):
        """Test text with custom alignment."""
        text = api_client.create_text(
            10, 20, "Hello World",
            text_align="center"
        )

        assert text['textAlign'] == "center"

    def test_create_text_with_custom_name(self, api_client):
        """Test text with custom name."""
        text = api_client.create_text(
            10, 20, "Hello World",
            name="My Text"
        )

        assert text['name'] == "My Text"

    def test_create_text_with_kwargs(self, api_client):
        """Test text with additional properties via kwargs."""
        text = api_client.create_text(
            10, 20, "Hello World",
            custom_property="custom_value"
        )

        assert text['custom_property'] == "custom_value"


class TestCreateFrame:
    """Tests for create_frame method."""

    def test_create_frame_basic(self, api_client):
        """Test basic frame creation."""
        frame = api_client.create_frame(0, 0, 375, 812)

        assert frame['type'] == 'frame'
        assert frame['name'] == 'Frame'
        assert frame['x'] == 0
        assert frame['y'] == 0
        assert frame['width'] == 375
        assert frame['height'] == 812
        assert 'fills' not in frame  # No background by default

    def test_create_frame_with_background(self, api_client):
        """Test frame with background color."""
        frame = api_client.create_frame(
            0, 0, 375, 812,
            background_color="#FFFFFF"
        )

        assert 'fills' in frame
        assert len(frame['fills']) == 1
        assert frame['fills'][0]['fillColor'] == '#FFFFFF'
        assert frame['fills'][0]['fillOpacity'] == 1.0

    def test_create_frame_with_custom_name(self, api_client):
        """Test frame with custom name."""
        frame = api_client.create_frame(
            0, 0, 375, 812,
            name="iPhone"
        )

        assert frame['name'] == "iPhone"

    def test_create_frame_with_kwargs(self, api_client):
        """Test frame with additional properties via kwargs."""
        frame = api_client.create_frame(
            0, 0, 375, 812,
            custom_property="custom_value"
        )

        assert frame['custom_property'] == "custom_value"


class TestCreateGroup:
    """Tests for create_group method."""

    def test_create_group_basic(self, api_client):
        """Test basic group creation."""
        group = api_client.create_group()

        assert group['type'] == 'group'
        assert group['name'] == 'Group'

    def test_create_group_with_custom_name(self, api_client):
        """Test group with custom name."""
        group = api_client.create_group(name="My Group")

        assert group['name'] == "My Group"

    def test_create_group_with_kwargs(self, api_client):
        """Test group with additional properties via kwargs."""
        group = api_client.create_group(
            name="My Group",
            custom_property="custom_value"
        )

        assert group['custom_property'] == "custom_value"


class TestShapeHelperIntegration:
    """Integration tests for shape helpers with change builders."""

    def test_rectangle_with_add_obj_change(self, api_client):
        """Test creating a rectangle and using it with add-obj change."""
        rect = api_client.create_rectangle(100, 200, 300, 150, fill_color="#FF0000")
        change = api_client.create_add_obj_change("rect-id", "page-id", rect)

        assert change['type'] == 'add-obj'
        assert change['id'] == 'rect-id'
        assert change['pageId'] == 'page-id'
        assert change['obj']['type'] == 'rect'
        assert change['obj']['fills'][0]['fillColor'] == '#FF0000'

    def test_circle_with_add_obj_change(self, api_client):
        """Test creating a circle and using it with add-obj change."""
        circle = api_client.create_circle(150, 150, 50, fill_color="#00FF00")
        change = api_client.create_add_obj_change("circle-id", "page-id", circle)

        assert change['type'] == 'add-obj'
        assert change['id'] == 'circle-id'
        assert change['obj']['type'] == 'circle'
        assert change['obj']['width'] == 100

    def test_text_with_add_obj_change(self, api_client):
        """Test creating text and using it with add-obj change."""
        text = api_client.create_text(10, 20, "Hello World", font_size=24)
        change = api_client.create_add_obj_change("text-id", "page-id", text)

        assert change['type'] == 'add-obj'
        assert change['obj']['type'] == 'text'
        assert change['obj']['content'] == 'Hello World'
        assert change['obj']['fontSize'] == 24

    def test_frame_with_add_obj_change(self, api_client):
        """Test creating a frame and using it with add-obj change."""
        frame = api_client.create_frame(0, 0, 375, 812, name="iPhone", background_color="#FFFFFF")
        change = api_client.create_add_obj_change("frame-id", "page-id", frame)

        assert change['type'] == 'add-obj'
        assert change['obj']['type'] == 'frame'
        assert change['obj']['name'] == 'iPhone'
        assert change['obj']['width'] == 375

    def test_multiple_shapes_workflow(self, api_client):
        """Test creating multiple shapes in a single workflow."""
        # Create multiple shapes
        rect = api_client.create_rectangle(100, 100, 200, 150, fill_color="#FF0000")
        circle = api_client.create_circle(300, 200, 50, fill_color="#00FF00")
        text = api_client.create_text(100, 300, "Label", font_size=18)

        # Create changes for all shapes
        changes = [
            api_client.create_add_obj_change("rect-1", "page-1", rect),
            api_client.create_add_obj_change("circle-1", "page-1", circle),
            api_client.create_add_obj_change("text-1", "page-1", text)
        ]

        assert len(changes) == 3
        assert changes[0]['obj']['type'] == 'rect'
        assert changes[1]['obj']['type'] == 'circle'
        assert changes[2]['obj']['type'] == 'text'
