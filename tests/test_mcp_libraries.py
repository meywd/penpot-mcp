"""Tests for MCP library and component system tools."""

from unittest.mock import MagicMock

import pytest

from penpot_mcp.server.mcp_server import PenpotMCPServer


@pytest.fixture
def mock_server():
    """Create a mock PenpotMCPServer with a mock API."""
    server = PenpotMCPServer(name="Test Server", test_mode=True)

    # Mock the library API methods
    server.api.link_file_to_library = MagicMock(return_value={
        'id': 'file-123',
        'linkedLibraries': ['lib-456']
    })

    server.api.get_library_components = MagicMock(return_value=[
        {'id': 'comp-1', 'name': 'Button'},
        {'id': 'comp-2', 'name': 'Card'},
        {'id': 'comp-3', 'name': 'Modal'}
    ])

    server.api.instantiate_component = MagicMock(return_value={
        'id': 'file-123',
        'revn': 6
    })

    server.api.sync_file_library = MagicMock(return_value={
        'updated-count': 5,
        'file-id': 'file-123',
        'library-id': 'lib-456'
    })

    server.api.publish_library = MagicMock(return_value={
        'id': 'file-123',
        'is-shared': True
    })

    server.api.get_file_libraries = MagicMock(return_value=[
        {'id': 'lib-1', 'name': 'Design System'},
        {'id': 'lib-2', 'name': 'Icon Library'}
    ])

    return server


# ========== API MOCK TESTS ==========
# These tests verify the API mock behavior works correctly

def test_link_file_to_library_api_mock(mock_server):
    """Test link_file_to_library API mock returns expected data."""
    result = mock_server.api.link_file_to_library(
        file_id='file-123',
        library_id='lib-456'
    )

    assert result['id'] == 'file-123'
    assert 'lib-456' in result['linkedLibraries']


def test_get_library_components_api_mock(mock_server):
    """Test get_library_components API mock returns expected data."""
    result = mock_server.api.get_library_components(
        library_id='lib-456'
    )

    assert len(result) == 3
    assert result[0]['name'] == 'Button'
    assert result[2]['name'] == 'Modal'


def test_instantiate_component_api_mock(mock_server):
    """Test instantiate_component API mock returns expected data."""
    result = mock_server.api.instantiate_component(
        file_id='file-123',
        page_id='page-456',
        library_id='lib-789',
        component_id='comp-abc',
        x=100,
        y=200
    )

    assert result['id'] == 'file-123'
    assert result['revn'] == 6


def test_instantiate_component_with_frame_api_mock(mock_server):
    """Test instantiate_component API mock with frame_id parameter."""
    result = mock_server.api.instantiate_component(
        file_id='file-123',
        page_id='page-456',
        library_id='lib-789',
        component_id='comp-abc',
        x=100,
        y=200,
        frame_id='frame-xyz'
    )

    assert result['id'] == 'file-123'
    # Verify frame_id was passed
    mock_server.api.instantiate_component.assert_called_with(
        file_id='file-123',
        page_id='page-456',
        library_id='lib-789',
        component_id='comp-abc',
        x=100,
        y=200,
        frame_id='frame-xyz'
    )


def test_sync_file_library_api_mock(mock_server):
    """Test sync_file_library API mock returns expected data."""
    result = mock_server.api.sync_file_library(
        file_id='file-123',
        library_id='lib-456'
    )

    assert result['updated-count'] == 5
    assert result['file-id'] == 'file-123'
    assert result['library-id'] == 'lib-456'


def test_publish_library_api_mock(mock_server):
    """Test publish_library API mock returns expected data."""
    result = mock_server.api.publish_library(
        file_id='file-123',
        publish=True
    )

    assert result['id'] == 'file-123'
    assert result['is-shared'] is True


def test_unpublish_library_api_mock(mock_server):
    """Test publish_library API mock with publish=False."""
    # Mock the unpublish response
    mock_server.api.publish_library = MagicMock(return_value={
        'id': 'file-123',
        'is-shared': False
    })

    result = mock_server.api.publish_library(
        file_id='file-123',
        publish=False
    )

    assert result['id'] == 'file-123'
    assert result['is-shared'] is False


def test_get_file_libraries_api_mock(mock_server):
    """Test get_file_libraries API mock returns expected data."""
    result = mock_server.api.get_file_libraries(
        file_id='file-123'
    )

    assert len(result) == 2
    assert result[0]['name'] == 'Design System'
    assert result[1]['name'] == 'Icon Library'


def test_link_library_api_called_correctly(mock_server):
    """Test that link_library calls the API correctly."""
    mock_server.api.link_file_to_library.reset_mock()
    
    mock_server.api.link_file_to_library(
        file_id='test-file',
        library_id='test-lib'
    )

    mock_server.api.link_file_to_library.assert_called_once_with(
        file_id='test-file',
        library_id='test-lib'
    )


def test_list_library_components_api_called_correctly(mock_server):
    """Test that list_library_components calls the API correctly."""
    mock_server.api.get_library_components.reset_mock()
    
    mock_server.api.get_library_components(
        library_id='test-lib'
    )

    mock_server.api.get_library_components.assert_called_once_with(
        library_id='test-lib'
    )


def test_import_component_api_called_correctly(mock_server):
    """Test that import_component calls the API correctly."""
    mock_server.api.instantiate_component.reset_mock()
    
    mock_server.api.instantiate_component(
        file_id='test-file',
        page_id='test-page',
        library_id='test-lib',
        component_id='test-comp',
        x=50.0,
        y=75.0,
        frame_id=None
    )

    mock_server.api.instantiate_component.assert_called_once_with(
        file_id='test-file',
        page_id='test-page',
        library_id='test-lib',
        component_id='test-comp',
        x=50.0,
        y=75.0,
        frame_id=None
    )


def test_sync_library_api_called_correctly(mock_server):
    """Test that sync_library calls the API correctly."""
    mock_server.api.sync_file_library.reset_mock()
    
    mock_server.api.sync_file_library(
        file_id='test-file',
        library_id='test-lib'
    )

    mock_server.api.sync_file_library.assert_called_once_with(
        file_id='test-file',
        library_id='test-lib'
    )


def test_publish_as_library_api_called_correctly(mock_server):
    """Test that publish_as_library calls the API correctly."""
    mock_server.api.publish_library.reset_mock()
    
    mock_server.api.publish_library(
        file_id='test-file',
        publish=True
    )

    mock_server.api.publish_library.assert_called_once_with(
        file_id='test-file',
        publish=True
    )


def test_unpublish_library_api_called_correctly(mock_server):
    """Test that unpublish_library calls the API correctly."""
    mock_server.api.publish_library.reset_mock()
    
    mock_server.api.publish_library(
        file_id='test-file',
        publish=False
    )

    mock_server.api.publish_library.assert_called_once_with(
        file_id='test-file',
        publish=False
    )


def test_get_file_libraries_api_called_correctly(mock_server):
    """Test that get_file_libraries calls the API correctly."""
    mock_server.api.get_file_libraries.reset_mock()
    
    mock_server.api.get_file_libraries(
        file_id='test-file'
    )

    mock_server.api.get_file_libraries.assert_called_once_with(
        file_id='test-file'
    )


# ========== INTEGRATION TESTS ==========

def test_library_workflow_integration(mock_server):
    """Test complete workflow: link, list, import component."""
    # Link library
    link_result = mock_server.api.link_file_to_library('file-123', 'lib-456')
    assert link_result['id'] == 'file-123'

    # List components
    components = mock_server.api.get_library_components('lib-456')
    assert len(components) == 3

    # Import a component
    import_result = mock_server.api.instantiate_component(
        file_id='file-123',
        page_id='page-1',
        library_id='lib-456',
        component_id='comp-1',
        x=100,
        y=200
    )
    assert import_result['id'] == 'file-123'


def test_component_sync_workflow(mock_server):
    """Test workflow: link, import, then sync."""
    # Link library
    mock_server.api.link_file_to_library('file-123', 'lib-456')

    # Import component
    mock_server.api.instantiate_component(
        file_id='file-123',
        page_id='page-1',
        library_id='lib-456',
        component_id='comp-1',
        x=100,
        y=200
    )

    # Sync library
    sync_result = mock_server.api.sync_file_library('file-123', 'lib-456')
    assert sync_result['updated-count'] == 5


def test_publish_and_use_workflow(mock_server):
    """Test workflow: publish file as library, then use in another file."""
    # Publish file as library
    publish_result = mock_server.api.publish_library('lib-file', publish=True)
    assert publish_result['is-shared'] is True

    # Link to another file
    link_result = mock_server.api.link_file_to_library('design-file', 'lib-file')
    assert link_result['id'] == 'file-123'

    # List and use components
    components = mock_server.api.get_library_components('lib-file')
    assert len(components) == 3
