"""Tests for advanced styling helper methods."""

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


class TestCreateGradientFill:
    """Tests for create_gradient_fill method."""

    def test_create_gradient_fill_linear(self, api_client):
        """Test linear gradient creation."""
        gradient = api_client.create_gradient_fill(
            'linear', '#ff0000', '#0000ff',
            start_x=0, start_y=0, end_x=1, end_y=0
        )

        assert gradient['type'] == 'linear-gradient'
        assert gradient['start-color'] == '#ff0000'
        assert gradient['end-color'] == '#0000ff'
        assert gradient['start-x'] == 0
        assert gradient['start-y'] == 0
        assert gradient['end-x'] == 1
        assert gradient['end-y'] == 0

    def test_create_gradient_fill_radial(self, api_client):
        """Test radial gradient creation."""
        gradient = api_client.create_gradient_fill(
            'radial', '#00ff00', '#ff00ff',
            start_x=0.5, start_y=0.5, end_x=1.0, end_y=1.0
        )

        assert gradient['type'] == 'radial-gradient'
        assert gradient['start-color'] == '#00ff00'
        assert gradient['end-color'] == '#ff00ff'
        assert gradient['start-x'] == 0.5
        assert gradient['start-y'] == 0.5
        assert gradient['end-x'] == 1.0
        assert gradient['end-y'] == 1.0

    def test_create_gradient_fill_default_positions(self, api_client):
        """Test gradient with default positions."""
        gradient = api_client.create_gradient_fill('linear', '#ffffff', '#000000')

        assert gradient['start-x'] == 0.0
        assert gradient['start-y'] == 0.0
        assert gradient['end-x'] == 1.0
        assert gradient['end-y'] == 1.0

    def test_create_gradient_fill_invalid_type(self, api_client):
        """Test gradient with invalid type raises error."""
        with pytest.raises(ValueError, match="Invalid gradient_type"):
            api_client.create_gradient_fill('invalid', '#ff0000', '#0000ff')

    def test_create_gradient_fill_with_kwargs(self, api_client):
        """Test gradient with additional properties."""
        gradient = api_client.create_gradient_fill(
            'linear', '#ff0000', '#0000ff',
            opacity=0.8,
            custom_prop='value'
        )

        assert gradient['opacity'] == 0.8
        assert gradient['custom_prop'] == 'value'


class TestCreateStroke:
    """Tests for create_stroke method."""

    def test_create_stroke_basic(self, api_client):
        """Test basic stroke creation."""
        stroke = api_client.create_stroke('#000000', width=2.0, style='dashed')

        assert stroke['stroke-color'] == '#000000'
        assert stroke['stroke-width'] == 2.0
        assert stroke['stroke-style'] == 'dashed'
        assert stroke['stroke-cap'] == 'round'
        assert stroke['stroke-join'] == 'round'

    def test_create_stroke_with_defaults(self, api_client):
        """Test stroke with default values."""
        stroke = api_client.create_stroke('#ff0000')

        assert stroke['stroke-color'] == '#ff0000'
        assert stroke['stroke-width'] == 1.0
        assert stroke['stroke-style'] == 'solid'
        assert stroke['stroke-cap'] == 'round'
        assert stroke['stroke-join'] == 'round'

    def test_create_stroke_all_styles(self, api_client):
        """Test stroke with different styles."""
        styles = ['solid', 'dashed', 'dotted', 'mixed']
        for style in styles:
            stroke = api_client.create_stroke('#000000', style=style)
            assert stroke['stroke-style'] == style

    def test_create_stroke_all_caps(self, api_client):
        """Test stroke with different cap styles."""
        caps = ['round', 'square', 'butt']
        for cap in caps:
            stroke = api_client.create_stroke('#000000', cap=cap)
            assert stroke['stroke-cap'] == cap

    def test_create_stroke_all_joins(self, api_client):
        """Test stroke with different join styles."""
        joins = ['round', 'bevel', 'miter']
        for join in joins:
            stroke = api_client.create_stroke('#000000', join=join)
            assert stroke['stroke-join'] == join

    def test_create_stroke_invalid_style(self, api_client):
        """Test stroke with invalid style raises error."""
        with pytest.raises(ValueError, match="Invalid style"):
            api_client.create_stroke('#000000', style='invalid')

    def test_create_stroke_invalid_cap(self, api_client):
        """Test stroke with invalid cap raises error."""
        with pytest.raises(ValueError, match="Invalid cap"):
            api_client.create_stroke('#000000', cap='invalid')

    def test_create_stroke_invalid_join(self, api_client):
        """Test stroke with invalid join raises error."""
        with pytest.raises(ValueError, match="Invalid join"):
            api_client.create_stroke('#000000', join='invalid')

    def test_create_stroke_with_kwargs(self, api_client):
        """Test stroke with additional properties."""
        stroke = api_client.create_stroke(
            '#000000',
            width=3.0,
            custom_property='value'
        )

        assert stroke['custom_property'] == 'value'


class TestCreateShadow:
    """Tests for create_shadow method."""

    def test_create_shadow_basic(self, api_client):
        """Test basic shadow creation."""
        shadow = api_client.create_shadow('#00000080', 2, 2, 4)

        assert shadow['color'] == '#00000080'
        assert shadow['offset-x'] == 2
        assert shadow['offset-y'] == 2
        assert shadow['blur'] == 4
        assert shadow['spread'] == 0.0
        assert shadow['hidden'] is False

    def test_create_shadow_with_spread(self, api_client):
        """Test shadow with spread radius."""
        shadow = api_client.create_shadow('#00000080', 5, 5, 10, spread=3.0)

        assert shadow['spread'] == 3.0

    def test_create_shadow_hidden(self, api_client):
        """Test shadow with hidden flag."""
        shadow = api_client.create_shadow('#00000080', 2, 2, 4, hidden=True)

        assert shadow['hidden'] is True

    def test_create_shadow_negative_offsets(self, api_client):
        """Test shadow with negative offsets."""
        shadow = api_client.create_shadow('#00000080', -5, -5, 4)

        assert shadow['offset-x'] == -5
        assert shadow['offset-y'] == -5

    def test_create_shadow_with_kwargs(self, api_client):
        """Test shadow with additional properties."""
        shadow = api_client.create_shadow(
            '#00000080', 2, 2, 4,
            style='inner',
            custom_prop='value'
        )

        assert shadow['style'] == 'inner'
        assert shadow['custom_prop'] == 'value'


class TestCreateBlur:
    """Tests for create_blur method."""

    def test_create_blur_layer(self, api_client):
        """Test layer blur creation."""
        blur = api_client.create_blur('layer-blur', 10)

        assert blur['type'] == 'layer-blur'
        assert blur['value'] == 10
        assert blur['hidden'] is False

    def test_create_blur_background(self, api_client):
        """Test background blur creation."""
        blur = api_client.create_blur('background-blur', 5)

        assert blur['type'] == 'background-blur'
        assert blur['value'] == 5

    def test_create_blur_hidden(self, api_client):
        """Test blur with hidden flag."""
        blur = api_client.create_blur('layer-blur', 10, hidden=True)

        assert blur['hidden'] is True

    def test_create_blur_invalid_type(self, api_client):
        """Test blur with invalid type raises error."""
        with pytest.raises(ValueError, match="Invalid blur_type"):
            api_client.create_blur('invalid-blur', 10)


class TestCreateFillOperation:
    """Tests for create_fill_operation method."""

    def test_create_fill_operation_single_gradient(self, api_client):
        """Test fill operation with single gradient."""
        gradient = api_client.create_gradient_fill('linear', '#ff0000', '#0000ff')
        op = api_client.create_fill_operation([gradient])

        assert op['type'] == 'set'
        assert op['attr'] == 'fills'
        assert len(op['val']) == 1
        assert op['val'][0]['type'] == 'linear-gradient'

    def test_create_fill_operation_multiple_fills(self, api_client):
        """Test fill operation with multiple fills."""
        gradient1 = api_client.create_gradient_fill('linear', '#ff0000', '#0000ff')
        gradient2 = api_client.create_gradient_fill('radial', '#00ff00', '#ff00ff')
        op = api_client.create_fill_operation([gradient1, gradient2])

        assert len(op['val']) == 2

    def test_create_fill_operation_empty_list(self, api_client):
        """Test fill operation with empty list."""
        op = api_client.create_fill_operation([])

        assert op['val'] == []


class TestCreateStrokeOperation:
    """Tests for create_stroke_operation method."""

    def test_create_stroke_operation_single(self, api_client):
        """Test stroke operation with single stroke."""
        stroke = api_client.create_stroke('#000000', width=2.0)
        op = api_client.create_stroke_operation([stroke])

        assert op['type'] == 'set'
        assert op['attr'] == 'strokes'
        assert len(op['val']) == 1
        assert op['val'][0]['stroke-color'] == '#000000'

    def test_create_stroke_operation_multiple(self, api_client):
        """Test stroke operation with multiple strokes."""
        stroke1 = api_client.create_stroke('#000000', width=2.0)
        stroke2 = api_client.create_stroke('#ff0000', width=1.0)
        op = api_client.create_stroke_operation([stroke1, stroke2])

        assert len(op['val']) == 2


class TestCreateShadowOperation:
    """Tests for create_shadow_operation method."""

    def test_create_shadow_operation_single(self, api_client):
        """Test shadow operation with single shadow."""
        shadow = api_client.create_shadow('#00000080', 2, 2, 4)
        op = api_client.create_shadow_operation([shadow])

        assert op['type'] == 'set'
        assert op['attr'] == 'shadow'
        assert len(op['val']) == 1
        assert op['val'][0]['color'] == '#00000080'

    def test_create_shadow_operation_multiple(self, api_client):
        """Test shadow operation with multiple shadows."""
        shadow1 = api_client.create_shadow('#00000080', 2, 2, 4)
        shadow2 = api_client.create_shadow('#ff000080', 5, 5, 10)
        op = api_client.create_shadow_operation([shadow1, shadow2])

        assert len(op['val']) == 2


class TestCreateBlurOperation:
    """Tests for create_blur_operation method."""

    def test_create_blur_operation(self, api_client):
        """Test blur operation."""
        blur = api_client.create_blur('layer-blur', 10)
        op = api_client.create_blur_operation(blur)

        assert op['type'] == 'set'
        assert op['attr'] == 'blur'
        assert op['val']['type'] == 'layer-blur'
        assert op['val']['value'] == 10


class TestAdvancedStylingIntegration:
    """Integration tests for advanced styling helpers."""

    def test_apply_gradient_to_shape(self, api_client):
        """Test complete workflow: create shape and apply gradient."""
        # Create rectangle
        rect = api_client.create_rectangle(100, 100, 200, 100)

        # Create gradient
        gradient = api_client.create_gradient_fill('linear', '#ff0000', '#0000ff')

        # Create fill operation
        fill_op = api_client.create_fill_operation([gradient])

        # Create mod-obj change
        change = api_client.create_mod_obj_change('rect-id', [fill_op])

        assert change['type'] == 'mod-obj'
        assert change['id'] == 'rect-id'
        assert len(change['operations']) == 1
        assert change['operations'][0]['attr'] == 'fills'

    def test_apply_multiple_strokes(self, api_client):
        """Test applying multiple strokes to one object."""
        # Create circle
        circle = api_client.create_circle(150, 150, 50)

        # Create multiple strokes
        stroke1 = api_client.create_stroke('#000000', width=5.0, style='solid')
        stroke2 = api_client.create_stroke('#ff0000', width=2.0, style='dashed')

        # Create stroke operation
        stroke_op = api_client.create_stroke_operation([stroke1, stroke2])

        # Create mod-obj change
        change = api_client.create_mod_obj_change('circle-id', [stroke_op])

        assert change['operations'][0]['attr'] == 'strokes'
        assert len(change['operations'][0]['val']) == 2

    def test_apply_shadow_to_text(self, api_client):
        """Test adding shadow effect to text object."""
        # Create text
        text = api_client.create_text(10, 10, "Hello World")

        # Create shadow
        shadow = api_client.create_shadow('#00000080', 2, 2, 4, spread=1.0)

        # Create shadow operation
        shadow_op = api_client.create_shadow_operation([shadow])

        # Create mod-obj change
        change = api_client.create_mod_obj_change('text-id', [shadow_op])

        assert change['operations'][0]['attr'] == 'shadow'
        assert change['operations'][0]['val'][0]['blur'] == 4

    def test_combine_multiple_effects(self, api_client):
        """Test applying gradient, stroke, and shadow together."""
        # Create rectangle
        rect = api_client.create_rectangle(100, 100, 200, 100)

        # Create gradient
        gradient = api_client.create_gradient_fill('radial', '#ff00ff', '#00ffff')
        fill_op = api_client.create_fill_operation([gradient])

        # Create stroke
        stroke = api_client.create_stroke('#000000', width=3.0)
        stroke_op = api_client.create_stroke_operation([stroke])

        # Create shadow
        shadow = api_client.create_shadow('#00000080', 5, 5, 10)
        shadow_op = api_client.create_shadow_operation([shadow])

        # Create blur
        blur = api_client.create_blur('layer-blur', 5)
        blur_op = api_client.create_blur_operation(blur)

        # Create mod-obj change with all effects
        change = api_client.create_mod_obj_change('rect-id', [
            fill_op,
            stroke_op,
            shadow_op,
            blur_op
        ])

        assert len(change['operations']) == 4
        assert change['operations'][0]['attr'] == 'fills'
        assert change['operations'][1]['attr'] == 'strokes'
        assert change['operations'][2]['attr'] == 'shadow'
        assert change['operations'][3]['attr'] == 'blur'

    def test_gradient_with_add_obj_change(self, api_client):
        """Test creating shape with gradient from the start."""
        # Create gradient
        gradient = api_client.create_gradient_fill('linear', '#ff0000', '#ffff00')

        # Create rectangle with gradient
        rect = api_client.create_rectangle(100, 100, 200, 100)
        rect['fills'] = [gradient]

        # Create add-obj change
        change = api_client.create_add_obj_change('rect-id', 'page-id', rect)

        assert change['obj']['fills'][0]['type'] == 'linear-gradient'
        assert change['obj']['fills'][0]['start-color'] == '#ff0000'
        assert change['obj']['fills'][0]['end-color'] == '#ffff00'
