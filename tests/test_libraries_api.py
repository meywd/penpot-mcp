"""Tests for library and component system API methods."""

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


class TestGetFileLibraries:
    """Tests for get_file_libraries method."""

    def test_get_file_libraries_basic(self, api_client):
        """Test retrieving linked libraries."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'id': 'lib-123',
                'name': 'Design System',
                'components': []
            },
            {
                'id': 'lib-456',
                'name': 'Icon Library',
                'components': []
            }
        ]

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            libraries = api_client.get_file_libraries(file_id='file-789')

        assert len(libraries) == 2
        assert libraries[0]['id'] == 'lib-123'
        assert libraries[1]['name'] == 'Icon Library'

    def test_get_file_libraries_empty(self, api_client):
        """Test retrieving libraries when none are linked."""
        mock_response = MagicMock()
        mock_response.json.return_value = []

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            libraries = api_client.get_file_libraries(file_id='file-123')

        assert len(libraries) == 0

    def test_get_file_libraries_calls_correct_endpoint(self, api_client):
        """Test that correct API endpoint is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = []

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            api_client.get_file_libraries(file_id='file-123')

            # Verify the call
            call_args = mock_request.call_args
            assert '/rpc/query/file-libraries' in call_args[0][1]
            assert call_args[1]['json']['file-id'] == 'file-123'


class TestLinkFileToLibrary:
    """Tests for link_file_to_library method."""

    def test_link_file_to_library_basic(self, api_client):
        """Test linking file to library."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'file-123',
            'linkedLibraries': ['lib-456']
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.link_file_to_library(
                file_id='file-123',
                library_id='lib-456'
            )

        assert result['id'] == 'file-123'
        assert 'lib-456' in result['linkedLibraries']

    def test_link_file_to_library_calls_correct_endpoint(self, api_client):
        """Test that correct API endpoint is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123'}

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            api_client.link_file_to_library(
                file_id='file-123',
                library_id='lib-456'
            )

            # Verify the call
            call_args = mock_request.call_args
            assert '/rpc/command/link-file-to-library' in call_args[0][1]
            payload = call_args[1]['json']
            assert payload['file-id'] == 'file-123'
            assert payload['library-id'] == 'lib-456'


class TestUnlinkFileFromLibrary:
    """Tests for unlink_file_from_library method."""

    def test_unlink_file_from_library_basic(self, api_client):
        """Test unlinking file from library."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True}

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.unlink_file_from_library(
                file_id='file-123',
                library_id='lib-456'
            )

        assert result['success'] is True

    def test_unlink_file_from_library_handles_no_json_response(self, api_client):
        """Test unlinking handles responses without JSON."""
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("No JSON")

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.unlink_file_from_library(
                file_id='file-123',
                library_id='lib-456'
            )

        assert result['success'] is True

    def test_unlink_file_from_library_calls_correct_endpoint(self, api_client):
        """Test that correct API endpoint is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            api_client.unlink_file_from_library(
                file_id='file-123',
                library_id='lib-456'
            )

            # Verify the call
            call_args = mock_request.call_args
            assert '/rpc/command/unlink-file-from-library' in call_args[0][1]
            payload = call_args[1]['json']
            assert payload['file-id'] == 'file-123'
            assert payload['library-id'] == 'lib-456'


class TestGetLibraryComponents:
    """Tests for get_library_components method."""

    def test_get_library_components_basic(self, api_client):
        """Test retrieving library components."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 'comp-1', 'name': 'Button'},
            {'id': 'comp-2', 'name': 'Card'},
            {'id': 'comp-3', 'name': 'Modal'}
        ]

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            components = api_client.get_library_components(library_id='lib-456')

        assert len(components) == 3
        assert components[0]['name'] == 'Button'
        assert components[2]['id'] == 'comp-3'

    def test_get_library_components_empty(self, api_client):
        """Test retrieving components from empty library."""
        mock_response = MagicMock()
        mock_response.json.return_value = []

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            components = api_client.get_library_components(library_id='lib-456')

        assert len(components) == 0

    def test_get_library_components_calls_correct_endpoint(self, api_client):
        """Test that correct API endpoint is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = []

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            api_client.get_library_components(library_id='lib-456')

            # Verify the call
            call_args = mock_request.call_args
            assert '/rpc/query/library-components' in call_args[0][1]
            assert call_args[1]['json']['library-id'] == 'lib-456'


class TestInstantiateComponent:
    """Tests for instantiate_component method."""

    def test_instantiate_component_basic(self, api_client):
        """Test creating component instance."""
        # Mock file data for editing session
        mock_file_response = MagicMock()
        mock_file_response.json.return_value = {'id': 'file-123', 'revn': 5}

        # Mock update response
        mock_update_response = MagicMock()
        mock_update_response.json.return_value = {
            'id': 'file-123',
            'revn': 6
        }

        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 5}):
            with patch.object(api_client, 'update_file', return_value={'id': 'file-123', 'revn': 6}) as mock_update:
                result = api_client.instantiate_component(
                    file_id='file-123',
                    page_id='page-456',
                    library_id='lib-789',
                    component_id='comp-abc',
                    x=100,
                    y=200
                )

        assert result['id'] == 'file-123'
        assert result['revn'] == 6
        
        # Verify the change structure
        call_args = mock_update.call_args
        changes = call_args[0][3]  # Fourth argument is changes list
        assert len(changes) == 1
        assert changes[0]['type'] == 'add-component-instance'
        assert changes[0]['pageId'] == 'page-456'
        assert changes[0]['libraryId'] == 'lib-789'
        assert changes[0]['componentId'] == 'comp-abc'
        assert changes[0]['x'] == 100
        assert changes[0]['y'] == 200

    def test_instantiate_component_with_frame(self, api_client):
        """Test creating component instance inside a frame."""
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 5}):
            with patch.object(api_client, 'update_file', return_value={'id': 'file-123', 'revn': 6}) as mock_update:
                api_client.instantiate_component(
                    file_id='file-123',
                    page_id='page-456',
                    library_id='lib-789',
                    component_id='comp-abc',
                    x=100,
                    y=200,
                    frame_id='frame-xyz'
                )

        # Verify frame_id is included
        call_args = mock_update.call_args
        changes = call_args[0][3]
        assert changes[0]['frameId'] == 'frame-xyz'

    def test_instantiate_component_generates_unique_id(self, api_client):
        """Test that each instantiation generates a unique ID."""
        with patch.object(api_client, 'get_file', return_value={'id': 'file-123', 'revn': 5}):
            with patch.object(api_client, 'update_file', return_value={'id': 'file-123', 'revn': 6}) as mock_update:
                # Create two instances
                api_client.instantiate_component(
                    file_id='file-123',
                    page_id='page-456',
                    library_id='lib-789',
                    component_id='comp-abc',
                    x=100,
                    y=200
                )
                
                api_client.instantiate_component(
                    file_id='file-123',
                    page_id='page-456',
                    library_id='lib-789',
                    component_id='comp-abc',
                    x=300,
                    y=400
                )

        # Verify two different instance IDs were generated
        calls = mock_update.call_args_list
        id1 = calls[0][0][3][0]['id']
        id2 = calls[1][0][3][0]['id']
        assert id1 != id2


class TestSyncFileLibrary:
    """Tests for sync_file_library method."""

    def test_sync_file_library_basic(self, api_client):
        """Test synchronizing library instances."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'updated-count': 5,
            'file-id': 'file-123',
            'library-id': 'lib-456'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.sync_file_library(
                file_id='file-123',
                library_id='lib-456'
            )

        assert result['updated-count'] == 5
        assert result['file-id'] == 'file-123'

    def test_sync_file_library_calls_correct_endpoint(self, api_client):
        """Test that correct API endpoint is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'updated-count': 0}

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            api_client.sync_file_library(
                file_id='file-123',
                library_id='lib-456'
            )

            # Verify the call
            call_args = mock_request.call_args
            assert '/rpc/command/sync-file' in call_args[0][1]
            payload = call_args[1]['json']
            assert payload['file-id'] == 'file-123'
            assert payload['library-id'] == 'lib-456'


class TestPublishLibrary:
    """Tests for publish_library method."""

    def test_publish_library_basic(self, api_client):
        """Test publishing file as library."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'file-123',
            'is-shared': True
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.publish_library(
                file_id='file-123',
                publish=True
            )

        assert result['id'] == 'file-123'
        assert result['is-shared'] is True

    def test_unpublish_library(self, api_client):
        """Test unpublishing a library."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'file-123',
            'is-shared': False
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.publish_library(
                file_id='file-123',
                publish=False
            )

        assert result['is-shared'] is False

    def test_publish_library_calls_correct_endpoint(self, api_client):
        """Test that correct API endpoint is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123'}

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            api_client.publish_library(
                file_id='file-123',
                publish=True
            )

            # Verify the call
            call_args = mock_request.call_args
            assert '/rpc/command/set-file-shared' in call_args[0][1]
            payload = call_args[1]['json']
            assert payload['id'] == 'file-123'
            assert payload['is-shared'] is True

    def test_publish_library_default_param(self, api_client):
        """Test publish defaults to True."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'file-123'}

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_request:
            api_client.publish_library(file_id='file-123')

            # Verify publish=True is default
            call_args = mock_request.call_args
            payload = call_args[1]['json']
            assert payload['is-shared'] is True


class TestLibraryWorkflowIntegration:
    """Integration tests for library workflow."""

    def test_complete_library_workflow(self, api_client):
        """Test complete workflow: link, get components, instantiate."""
        # Mock link response
        mock_link_response = MagicMock()
        mock_link_response.json.return_value = {'id': 'file-123'}

        # Mock get components response
        mock_components_response = MagicMock()
        mock_components_response.json.return_value = [
            {'id': 'comp-1', 'name': 'Button'}
        ]

        # Mock responses in sequence
        with patch.object(api_client, '_make_authenticated_request') as mock_request:
            mock_request.side_effect = [mock_link_response, mock_components_response]

            # Link library
            link_result = api_client.link_file_to_library('file-123', 'lib-456')
            assert link_result['id'] == 'file-123'

            # Get components
            components = api_client.get_library_components('lib-456')
            assert len(components) == 1
            assert components[0]['name'] == 'Button'

    def test_publish_and_link_workflow(self, api_client):
        """Test publishing a file and linking it to another."""
        mock_publish_response = MagicMock()
        mock_publish_response.json.return_value = {
            'id': 'lib-file',
            'is-shared': True
        }

        mock_link_response = MagicMock()
        mock_link_response.json.return_value = {'id': 'design-file'}

        with patch.object(api_client, '_make_authenticated_request') as mock_request:
            mock_request.side_effect = [mock_publish_response, mock_link_response]

            # Publish as library
            publish_result = api_client.publish_library('lib-file', publish=True)
            assert publish_result['is-shared'] is True

            # Link to another file
            link_result = api_client.link_file_to_library('design-file', 'lib-file')
            assert link_result['id'] == 'design-file'
