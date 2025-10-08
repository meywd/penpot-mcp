"""Tests for the Penpot API client file CRUD operations."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from penpot_mcp.api.penpot_api import CloudFlareError, PenpotAPI, PenpotAPIError


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.headers = {}
    return mock_resp


@pytest.fixture
def api_client():
    """Create a PenpotAPI client for testing."""
    with patch.object(PenpotAPI, 'login_with_password'):
        api = PenpotAPI(debug=True)
        api.access_token = "test-token"
        return api


class TestGetTeams:
    """Tests for get_teams method."""

    def test_get_teams_success(self, api_client, mock_response):
        """Test getting teams."""
        mock_response.json.return_value = [
            {
                'id': 'team-123',
                'name': 'My Team',
                'isDefault': True,
                'permissions': ['read', 'write']
            },
            {
                'id': 'team-456',
                'name': 'Another Team',
                'isDefault': False,
                'permissions': ['read']
            }
        ]

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            teams = api_client.get_teams()

            assert isinstance(teams, list)
            assert len(teams) == 2
            assert teams[0]['id'] == 'team-123'
            assert teams[0]['name'] == 'My Team'
            assert teams[0]['isDefault'] is True

    def test_get_teams_empty(self, api_client, mock_response):
        """Test getting teams when none exist."""
        mock_response.json.return_value = []

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            teams = api_client.get_teams()

            assert isinstance(teams, list)
            assert len(teams) == 0


class TestCreateProject:
    """Tests for create_project method."""

    def test_create_project_basic(self, api_client, mock_response):
        """Test project creation."""
        mock_response.json.return_value = {
            'id': 'project-123',
            'name': 'Test Project',
            'teamId': 'team-456',
            'created': '2024-01-01T00:00:00Z',
            'modified': '2024-01-01T00:00:00Z'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_req:
            result = api_client.create_project(name="Test Project", team_id="team-456")

            assert result['name'] == "Test Project"
            assert result['teamId'] == "team-456"
            assert 'id' in result
            assert result['id'] == 'project-123'

            # Verify the payload structure
            call_args = mock_req.call_args
            payload = call_args.kwargs['json']
            assert payload['name'] == "Test Project"
            assert payload['team-id'] == "team-456"

    def test_create_project_with_custom_id(self, api_client, mock_response):
        """Test project creation with custom ID."""
        mock_response.json.return_value = {
            'id': 'custom-project-id',
            'name': 'Custom Project',
            'teamId': 'team-789'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_req:
            result = api_client.create_project(
                name="Custom Project",
                team_id="team-789",
                project_id='custom-project-id'
            )

            assert result['id'] == 'custom-project-id'
            assert result['name'] == "Custom Project"

            # Verify the payload includes the custom ID
            call_args = mock_req.call_args
            payload = call_args.kwargs['json']
            assert payload['id'] == 'custom-project-id'

    def test_create_project_handles_auth_error(self, api_client):
        """Test that create_project handles authentication errors properly."""
        with patch.object(api_client, '_make_authenticated_request', side_effect=requests.HTTPError()):
            with pytest.raises(requests.HTTPError):
                api_client.create_project(name="Test", team_id="team-123")


class TestRenameProject:
    """Tests for rename_project method."""

    def test_rename_project_success(self, api_client, mock_response):
        """Test project renaming."""
        mock_response.json.return_value = {
            'id': 'project-123',
            'name': 'New Name',
            'teamId': 'team-456'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_req:
            result = api_client.rename_project(project_id="project-123", name="New Name")

            assert result['name'] == "New Name"
            assert result['id'] == 'project-123'

            # Verify the payload structure
            call_args = mock_req.call_args
            payload = call_args.kwargs['json']
            assert payload['name'] == "New Name"
            assert payload['id'] == "project-123"

    def test_rename_project_with_special_characters(self, api_client, mock_response):
        """Test renaming project with special characters in name."""
        new_name = "My Project (Copy) - 2024 [v1.0]"
        mock_response.json.return_value = {
            'id': 'project-789',
            'name': new_name,
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.rename_project(project_id="project-789", name=new_name)

            assert result['name'] == new_name


class TestDeleteProject:
    """Tests for delete_project method."""

    def test_delete_project_success(self, api_client, mock_response):
        """Test project deletion."""
        mock_response.json.return_value = {'success': True, 'id': 'project-123'}

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_req:
            result = api_client.delete_project(project_id="project-123")

            assert result['success'] is True
            assert result['id'] == 'project-123'

            # Verify the payload structure
            call_args = mock_req.call_args
            payload = call_args.kwargs['json']
            assert payload['id'] == "project-123"

    def test_delete_project_empty_response(self, api_client, mock_response):
        """Test project deletion with empty response (common for DELETE operations)."""
        mock_response.json.side_effect = Exception("No JSON content")

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.delete_project(project_id="project-456")

            assert result['success'] is True
            assert result['id'] == 'project-456'

    def test_delete_project_not_found(self, api_client):
        """Test deletion of non-existent project."""
        http_error = requests.HTTPError()
        http_error.response = MagicMock()
        http_error.response.status_code = 404

        with patch.object(api_client, '_make_authenticated_request', side_effect=http_error):
            with pytest.raises(requests.HTTPError):
                api_client.delete_project(project_id="non-existent-project")


class TestGetProjectDirect:
    """Tests for get_project direct API call method."""

    def test_get_project_direct_success(self, api_client, mock_response):
        """Test getting single project directly."""
        mock_response.json.return_value = {
            'id': 'project-123',
            'name': 'Test Project',
            'teamId': 'team-456',
            'permissions': ['read', 'write']
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_req:
            result = api_client.get_project(project_id="project-123")

            assert result['id'] == "project-123"
            assert result['name'] == "Test Project"
            assert 'permissions' in result

            # Verify the payload structure
            call_args = mock_req.call_args
            payload = call_args.kwargs['json']
            assert payload['id'] == "project-123"

    def test_get_project_not_found(self, api_client):
        """Test getting non-existent project."""
        http_error = requests.HTTPError()
        http_error.response = MagicMock()
        http_error.response.status_code = 404

        with patch.object(api_client, '_make_authenticated_request', side_effect=http_error):
            with pytest.raises(requests.HTTPError):
                api_client.get_project(project_id="non-existent")


class TestProjectCRUDIntegration:
    """Integration tests for project CRUD operations workflow."""

    def test_project_lifecycle(self, api_client):
        """Test complete project lifecycle: create -> rename -> delete."""
        # Create project
        create_response = MagicMock(spec=requests.Response)
        create_response.status_code = 200
        create_response.json.return_value = {
            'id': 'new-project-123',
            'name': 'Initial Name',
            'teamId': 'team-456'
        }

        # Rename project
        rename_response = MagicMock(spec=requests.Response)
        rename_response.status_code = 200
        rename_response.json.return_value = {
            'id': 'new-project-123',
            'name': 'Renamed Project',
            'teamId': 'team-456'
        }

        # Delete project
        delete_response = MagicMock(spec=requests.Response)
        delete_response.status_code = 200
        delete_response.json.return_value = {'success': True, 'id': 'new-project-123'}

        with patch.object(api_client, '_make_authenticated_request') as mock_req:
            mock_req.side_effect = [create_response, rename_response, delete_response]

            # Create
            project = api_client.create_project(name="Initial Name", team_id="team-456")
            assert project['id'] == 'new-project-123'
            assert project['name'] == 'Initial Name'

            # Rename
            renamed = api_client.rename_project(project_id=project['id'], name="Renamed Project")
            assert renamed['name'] == 'Renamed Project'

            # Delete
            deleted = api_client.delete_project(project_id=project['id'])
            assert deleted['success'] is True


class TestProjectErrorHandling:
    """Tests for error handling in project operations."""

    def test_create_project_cloudflare_error(self, api_client):
        """Test CloudFlare error handling in create_project."""
        with patch.object(api_client, '_make_authenticated_request', side_effect=CloudFlareError("CloudFlare block", 403)):
            with pytest.raises(CloudFlareError):
                api_client.create_project(name="Test", team_id="team-123")

    def test_delete_project_permission_denied(self, api_client):
        """Test permission denied error in delete_project."""
        http_error = requests.HTTPError()
        http_error.response = MagicMock()
        http_error.response.status_code = 403

        with patch.object(api_client, '_make_authenticated_request', side_effect=http_error):
            with pytest.raises(requests.HTTPError):
                api_client.delete_project(project_id="project-123")

    def test_rename_project_not_found(self, api_client):
        """Test project not found error in rename_project."""
        http_error = requests.HTTPError()
        http_error.response = MagicMock()
        http_error.response.status_code = 404

        with patch.object(api_client, '_make_authenticated_request', side_effect=http_error):
            with pytest.raises(requests.HTTPError):
                api_client.rename_project(project_id="non-existent", name="New Name")


class TestProjectDebugLogging:
    """Tests for debug logging in project operations."""

    def test_get_teams_debug_logging(self, mock_response, capsys):
        """Test that debug logging works in get_teams."""
        mock_response.json.return_value = [
            {'id': 'team-123', 'name': 'Test Team', 'isDefault': True}
        ]

        with patch.object(PenpotAPI, 'login_with_password'):
            api = PenpotAPI(debug=True)
            api.access_token = "test-token"

            with patch.object(api, '_make_authenticated_request', return_value=mock_response):
                api.get_teams()

                captured = capsys.readouterr()
                assert "Retrieved 1 teams" in captured.out
                assert "Test Team" in captured.out

    def test_create_project_debug_logging(self, mock_response, capsys):
        """Test that debug logging works in create_project."""
        mock_response.json.return_value = {
            'id': 'project-123',
            'name': 'Test Project',
            'teamId': 'team-456'
        }

        with patch.object(PenpotAPI, 'login_with_password'):
            api = PenpotAPI(debug=True)
            api.access_token = "test-token"

            with patch.object(api, '_make_authenticated_request', return_value=mock_response):
                api.create_project(name="Test Project", team_id="team-456")

                captured = capsys.readouterr()
                assert "Project created:" in captured.out
                assert "Test Project" in captured.out

    def test_delete_project_debug_logging(self, mock_response, capsys):
        """Test that debug logging works in delete_project."""
        mock_response.json.return_value = {'success': True, 'id': 'project-123'}

        with patch.object(PenpotAPI, 'login_with_password'):
            api = PenpotAPI(debug=True)
            api.access_token = "test-token"

            with patch.object(api, '_make_authenticated_request', return_value=mock_response):
                api.delete_project(project_id="project-123")

                captured = capsys.readouterr()
                assert "Project deleted:" in captured.out
                assert "project-123" in captured.out


class TestCreateFile:
    """Tests for create_file method."""

    def test_create_file_basic(self, api_client, mock_response):
        """Test basic file creation."""
        mock_response.json.return_value = {
            'id': 'file-123',
            'name': 'Test File',
            'projectId': 'project-456',
            'created': '2024-01-01T00:00:00Z',
            'modified': '2024-01-01T00:00:00Z',
            'isShared': False
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.create_file(name="Test File", project_id="project-456")

            assert result['name'] == "Test File"
            assert result['projectId'] == "project-456"
            assert 'id' in result
            assert result['id'] == 'file-123'

    def test_create_file_with_optional_params(self, api_client, mock_response):
        """Test file creation with optional parameters."""
        mock_response.json.return_value = {
            'id': 'custom-file-id',
            'name': 'Shared File',
            'projectId': 'project-789',
            'isShared': True,
            'features': ['feature1', 'feature2']
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_req:
            result = api_client.create_file(
                name="Shared File",
                project_id="project-789",
                is_shared=True,
                features=['feature1', 'feature2'],
                file_id='custom-file-id'
            )

            assert result['name'] == "Shared File"
            assert result['isShared'] is True
            assert 'features' in result

            # Verify the payload structure
            call_args = mock_req.call_args
            payload = call_args.kwargs['json']
            assert payload['name'] == "Shared File"
            assert payload['project-id'] == "project-789"
            assert payload['is-shared'] is True
            assert payload['id'] == 'custom-file-id'
            assert payload['features'] == ['feature1', 'feature2']

    def test_create_file_handles_auth_error(self, api_client):
        """Test that create_file handles authentication errors properly."""
        with patch.object(api_client, '_make_authenticated_request', side_effect=requests.HTTPError()):
            with pytest.raises(requests.HTTPError):
                api_client.create_file(name="Test", project_id="project-123")


class TestDeleteFile:
    """Tests for delete_file method."""

    def test_delete_file_success(self, api_client, mock_response):
        """Test successful file deletion."""
        mock_response.json.return_value = {'success': True, 'id': 'file-123'}

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.delete_file(file_id="file-123")

            assert result['success'] is True
            assert result['id'] == 'file-123'

    def test_delete_file_empty_response(self, api_client, mock_response):
        """Test file deletion with empty response (common for DELETE operations)."""
        mock_response.json.side_effect = Exception("No JSON content")

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.delete_file(file_id="file-456")

            assert result['success'] is True
            assert result['id'] == 'file-456'

    def test_delete_file_not_found(self, api_client):
        """Test deletion of non-existent file."""
        http_error = requests.HTTPError()
        http_error.response = MagicMock()
        http_error.response.status_code = 404

        with patch.object(api_client, '_make_authenticated_request', side_effect=http_error):
            with pytest.raises(requests.HTTPError):
                api_client.delete_file(file_id="non-existent-file")


class TestRenameFile:
    """Tests for rename_file method."""

    def test_rename_file_success(self, api_client, mock_response):
        """Test successful file renaming."""
        mock_response.json.return_value = {
            'id': 'file-123',
            'name': 'New File Name',
            'projectId': 'project-456'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.rename_file(file_id="file-123", name="New File Name")

            assert result['name'] == "New File Name"
            assert result['id'] == 'file-123'

    def test_rename_file_with_special_characters(self, api_client, mock_response):
        """Test renaming file with special characters in name."""
        new_name = "My File (Copy) - 2024 [v1.0]"
        mock_response.json.return_value = {
            'id': 'file-789',
            'name': new_name,
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_req:
            result = api_client.rename_file(file_id="file-789", name=new_name)

            assert result['name'] == new_name

            # Verify the payload structure
            call_args = mock_req.call_args
            payload = call_args.kwargs['json']
            assert payload['name'] == new_name
            assert payload['id'] == "file-789"


class TestSetFileShared:
    """Tests for set_file_shared method."""

    def test_set_file_shared_true(self, api_client, mock_response):
        """Test setting file to shared."""
        mock_response.json.return_value = {
            'id': 'file-123',
            'isShared': True,
            'name': 'Shared File'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response):
            result = api_client.set_file_shared(file_id="file-123", is_shared=True)

            assert result['isShared'] is True
            assert result['id'] == 'file-123'

    def test_set_file_shared_false(self, api_client, mock_response):
        """Test setting file to not shared."""
        mock_response.json.return_value = {
            'id': 'file-456',
            'isShared': False,
            'name': 'Private File'
        }

        with patch.object(api_client, '_make_authenticated_request', return_value=mock_response) as mock_req:
            result = api_client.set_file_shared(file_id="file-456", is_shared=False)

            assert result['isShared'] is False

            # Verify the payload structure
            call_args = mock_req.call_args
            payload = call_args.kwargs['json']
            assert payload['is-shared'] is False
            assert payload['id'] == "file-456"


class TestCRUDIntegration:
    """Integration tests for CRUD operations workflow."""

    def test_create_rename_delete_workflow(self, api_client, mock_response):
        """Test complete workflow: create -> rename -> delete."""
        # Create file
        create_response = MagicMock(spec=requests.Response)
        create_response.status_code = 200
        create_response.json.return_value = {
            'id': 'new-file-123',
            'name': 'Initial Name',
            'projectId': 'project-456'
        }

        # Rename file
        rename_response = MagicMock(spec=requests.Response)
        rename_response.status_code = 200
        rename_response.json.return_value = {
            'id': 'new-file-123',
            'name': 'Renamed File',
            'projectId': 'project-456'
        }

        # Delete file
        delete_response = MagicMock(spec=requests.Response)
        delete_response.status_code = 200
        delete_response.json.return_value = {'success': True, 'id': 'new-file-123'}

        with patch.object(api_client, '_make_authenticated_request') as mock_req:
            mock_req.side_effect = [create_response, rename_response, delete_response]

            # Create
            file = api_client.create_file(name="Initial Name", project_id="project-456")
            assert file['id'] == 'new-file-123'
            assert file['name'] == 'Initial Name'

            # Rename
            renamed = api_client.rename_file(file_id=file['id'], name="Renamed File")
            assert renamed['name'] == 'Renamed File'

            # Delete
            deleted = api_client.delete_file(file_id=file['id'])
            assert deleted['success'] is True


class TestErrorHandling:
    """Tests for error handling in CRUD operations."""

    def test_create_file_cloudflare_error(self, api_client):
        """Test CloudFlare error handling in create_file."""
        with patch.object(api_client, '_make_authenticated_request', side_effect=CloudFlareError("CloudFlare block", 403)):
            with pytest.raises(CloudFlareError):
                api_client.create_file(name="Test", project_id="project-123")

    def test_delete_file_permission_denied(self, api_client):
        """Test permission denied error in delete_file."""
        http_error = requests.HTTPError()
        http_error.response = MagicMock()
        http_error.response.status_code = 403

        with patch.object(api_client, '_make_authenticated_request', side_effect=http_error):
            with pytest.raises(requests.HTTPError):
                api_client.delete_file(file_id="file-123")

    def test_rename_file_project_not_found(self, api_client):
        """Test project not found error in rename_file."""
        http_error = requests.HTTPError()
        http_error.response = MagicMock()
        http_error.response.status_code = 404

        with patch.object(api_client, '_make_authenticated_request', side_effect=http_error):
            with pytest.raises(requests.HTTPError):
                api_client.rename_file(file_id="non-existent", name="New Name")


class TestDebugLogging:
    """Tests for debug logging in CRUD operations."""

    def test_create_file_debug_logging(self, mock_response, capsys):
        """Test that debug logging works in create_file."""
        mock_response.json.return_value = {
            'id': 'file-123',
            'name': 'Test File',
            'projectId': 'project-456'
        }

        with patch.object(PenpotAPI, 'login_with_password'):
            api = PenpotAPI(debug=True)
            api.access_token = "test-token"

            with patch.object(api, '_make_authenticated_request', return_value=mock_response):
                api.create_file(name="Test File", project_id="project-456")

                captured = capsys.readouterr()
                assert "File created:" in captured.out
                assert "Test File" in captured.out

    def test_delete_file_debug_logging(self, mock_response, capsys):
        """Test that debug logging works in delete_file."""
        mock_response.json.return_value = {'success': True, 'id': 'file-123'}

        with patch.object(PenpotAPI, 'login_with_password'):
            api = PenpotAPI(debug=True)
            api.access_token = "test-token"

            with patch.object(api, '_make_authenticated_request', return_value=mock_response):
                api.delete_file(file_id="file-123")

                captured = capsys.readouterr()
                assert "File deleted:" in captured.out
                assert "file-123" in captured.out

    def test_set_file_shared_debug_logging(self, mock_response, capsys):
        """Test that debug logging works in set_file_shared."""
        mock_response.json.return_value = {
            'id': 'file-123',
            'isShared': True
        }

        with patch.object(PenpotAPI, 'login_with_password'):
            api = PenpotAPI(debug=True)
            api.access_token = "test-token"

            with patch.object(api, '_make_authenticated_request', return_value=mock_response):
                api.set_file_shared(file_id="file-123", is_shared=True)

                captured = capsys.readouterr()
                assert "File set to shared:" in captured.out
                assert "file-123" in captured.out
