"""Integration tests for Penpot MCP against local Penpot instance.

These tests run against an actual Penpot instance (local or cloud).
They are skipped if credentials are not available.

To run these tests:
1. Set environment variables:
   - PENPOT_API_URL=http://localhost:9001/api
   - PENPOT_USERNAME=your_username
   - PENPOT_PASSWORD=your_password

2. Run with pytest:
   pytest tests/test_integration_local.py -v -s
"""

import os
import time

import pytest

from penpot_mcp.api.penpot_api import PenpotAPI
from penpot_mcp.server.mcp_server import PenpotMCPServer


# Skip all tests if credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv('PENPOT_USERNAME') or not os.getenv('PENPOT_PASSWORD'),
    reason="Integration tests require PENPOT_USERNAME and PENPOT_PASSWORD environment variables"
)


@pytest.fixture(scope="module")
def api_client():
    """Create a real API client for integration testing."""
    api = PenpotAPI(debug=True)
    return api


@pytest.fixture(scope="module")
def mcp_server():
    """Create a real MCP server for integration testing."""
    server = PenpotMCPServer(name="Integration Test Server", test_mode=False)
    return server


@pytest.fixture(scope="module")
def test_team(api_client):
    """Get or create a test team."""
    teams = api_client.get_teams()
    if teams:
        return teams[0]['id']
    pytest.skip("No teams available for testing")


@pytest.fixture(scope="module")
def test_project(api_client, test_team):
    """Create a test project for integration tests."""
    # Create test project
    project_name = f"MCP Integration Test {int(time.time())}"
    project = api_client.create_project(project_name, test_team)
    project_id = project['id']

    yield project_id

    # Cleanup: Delete project after tests
    try:
        api_client.delete_project(project_id)
        print(f"\nCleaned up test project: {project_id}")
    except Exception as e:
        print(f"\nWarning: Failed to cleanup project {project_id}: {e}")


@pytest.fixture(scope="module")
def test_file(api_client, test_project):
    """Create a test file for integration tests."""
    # Create test file
    file_name = f"Test File {int(time.time())}"
    file = api_client.create_file(file_name, test_project)
    file_id = file['id']

    yield file_id

    # Cleanup: Delete file after tests
    try:
        api_client.delete_file(file_id)
        print(f"\nCleaned up test file: {file_id}")
    except Exception as e:
        print(f"\nWarning: Failed to cleanup file {file_id}: {e}")


@pytest.fixture
def test_page(api_client, test_file):
    """Get the first page from the test file."""
    file_data = api_client.get_file(test_file)
    pages = file_data.get('data', {}).get('pages', [])
    if not pages:
        pytest.skip("No pages available in test file")
    return pages[0]


# ========== PROJECT & FILE MANAGEMENT TESTS ==========

class TestProjectFileManagement:
    """Test project and file management operations."""

    def test_get_teams(self, api_client):
        """Test retrieving teams."""
        teams = api_client.get_teams()
        assert isinstance(teams, list)
        assert len(teams) > 0
        assert 'id' in teams[0]
        assert 'name' in teams[0]
        print(f"\nFound {len(teams)} team(s)")

    def test_create_and_delete_project(self, api_client, test_team):
        """Test creating and deleting a project."""
        # Create project
        project_name = f"Temp Test Project {int(time.time())}"
        project = api_client.create_project(project_name, test_team)

        assert 'id' in project
        assert project['name'] == project_name
        project_id = project['id']
        print(f"\nCreated project: {project_id}")

        # Delete project
        result = api_client.delete_project(project_id)
        assert result['success'] is True
        print(f"Deleted project: {project_id}")

    def test_create_and_delete_file(self, api_client, test_project):
        """Test creating and deleting a file."""
        # Create file
        file_name = f"Temp Test File {int(time.time())}"
        file = api_client.create_file(file_name, test_project)

        assert 'id' in file
        assert file['name'] == file_name
        file_id = file['id']
        print(f"\nCreated file: {file_id}")

        # Delete file
        result = api_client.delete_file(file_id)
        assert result['success'] is True
        print(f"Deleted file: {file_id}")

    def test_get_file_with_vern(self, api_client, test_file):
        """Test getting file and checking for vern field."""
        file_data = api_client.get_file(test_file)

        assert 'id' in file_data
        assert 'revn' in file_data

        # Check if vern exists (required for self-hosted)
        has_vern = 'vern' in file_data
        print(f"\nFile has vern field: {has_vern}")
        if has_vern:
            print(f"revn={file_data['revn']}, vern={file_data['vern']}")


# ========== SHAPE CREATION TESTS ==========

class TestShapeCreation:
    """Test creating shapes in a file."""

    def test_add_rectangle(self, api_client, test_file, test_page):
        """Test adding a rectangle to the file."""
        # Generate object ID
        obj_id = api_client.generate_session_id()

        # Create rectangle
        with api_client.editing_session(test_file) as (session_id, revn):
            rect = api_client.create_rectangle(
                x=100, y=100, width=200, height=150,
                name="Test Rectangle",
                fill_color="#FF0000"
            )

            change = api_client.create_add_obj_change(obj_id, test_page, rect)
            result = api_client.update_file(test_file, session_id, revn, [change])

            assert 'revn' in result
            assert result['revn'] == revn + 1
            print(f"\nAdded rectangle, new revision: {result['revn']}")

    def test_add_circle(self, api_client, test_file, test_page):
        """Test adding a circle to the file."""
        obj_id = api_client.generate_session_id()

        with api_client.editing_session(test_file) as (session_id, revn):
            circle = api_client.create_circle(
                cx=300, cy=300, radius=50,
                name="Test Circle",
                fill_color="#00FF00"
            )

            change = api_client.create_add_obj_change(obj_id, test_page, circle)
            result = api_client.update_file(test_file, session_id, revn, [change])

            assert result['revn'] == revn + 1
            print(f"\nAdded circle, new revision: {result['revn']}")

    def test_add_text(self, api_client, test_file, test_page):
        """Test adding text to the file."""
        obj_id = api_client.generate_session_id()

        with api_client.editing_session(test_file) as (session_id, revn):
            text = api_client.create_text(
                x=100, y=300,
                content="Integration Test",
                font_size=24
            )

            change = api_client.create_add_obj_change(obj_id, test_page, text)
            result = api_client.update_file(test_file, session_id, revn, [change])

            assert result['revn'] == revn + 1
            print(f"\nAdded text, new revision: {result['revn']}")

    def test_add_frame(self, api_client, test_file, test_page):
        """Test adding a frame to the file."""
        obj_id = api_client.generate_session_id()

        with api_client.editing_session(test_file) as (session_id, revn):
            frame = api_client.create_frame(
                x=500, y=100,
                width=400, height=300,
                name="Test Frame"
            )

            change = api_client.create_add_obj_change(obj_id, test_page, frame)
            result = api_client.update_file(test_file, session_id, revn, [change])

            assert result['revn'] == revn + 1
            print(f"\nAdded frame, new revision: {result['revn']}")


# ========== MCP TOOL TESTS ==========

class TestMCPTools:
    """Test MCP tools against real API."""

    @pytest.fixture
    def tool_helper(self, mcp_server):
        """Helper to call MCP tools."""
        async def call_tool_async(tool_name, **kwargs):
            import json
            result = await mcp_server.mcp.call_tool(tool_name, kwargs)
            if isinstance(result, list) and len(result) > 0:
                return json.loads(result[0].text)
            return result

        def call_tool(tool_name, **kwargs):
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(call_tool_async(tool_name, **kwargs))

        return call_tool

    def test_list_projects_tool(self, tool_helper, test_team):
        """Test list_projects MCP tool."""
        result = tool_helper('list_projects')

        assert 'projects' in result
        assert isinstance(result['projects'], list)
        print(f"\nFound {len(result['projects'])} project(s)")

    def test_add_rectangle_tool(self, tool_helper, test_file, test_page):
        """Test add_rectangle MCP tool."""
        result = tool_helper(
            'add_rectangle',
            file_id=test_file,
            page_id=test_page,
            x=50.0,
            y=50.0,
            width=100.0,
            height=100.0,
            name="MCP Tool Rectangle",
            fill_color="#0000FF"
        )

        assert result['success'] is True
        assert 'objectId' in result
        assert 'revn' in result
        print(f"\nAdded rectangle via MCP tool, object ID: {result['objectId']}")

    def test_add_circle_tool(self, tool_helper, test_file, test_page):
        """Test add_circle MCP tool."""
        result = tool_helper(
            'add_circle',
            file_id=test_file,
            page_id=test_page,
            cx=200.0,
            cy=200.0,
            radius=40.0,
            name="MCP Tool Circle",
            fill_color="#FFFF00"
        )

        assert result['success'] is True
        assert 'objectId' in result
        print(f"\nAdded circle via MCP tool, object ID: {result['objectId']}")

    def test_add_text_tool(self, tool_helper, test_file, test_page):
        """Test add_text MCP tool."""
        result = tool_helper(
            'add_text',
            file_id=test_file,
            page_id=test_page,
            x=300.0,
            y=50.0,
            content="MCP Tool Test",
            font_size=18
        )

        assert result['success'] is True
        assert 'objectId' in result
        print(f"\nAdded text via MCP tool, object ID: {result['objectId']}")


# ========== VERSION COMPATIBILITY TESTS ==========

class TestVersionCompatibility:
    """Test compatibility with different Penpot versions."""

    def test_vern_parameter_handling(self, api_client, test_file, test_page):
        """Test that vern parameter is handled correctly."""
        obj_id = api_client.generate_session_id()

        # Get both revn and vern
        revn, vern = api_client.get_file_version(test_file)
        print(f"\nFile version: revn={revn}, vern={vern}")

        # Create a simple rectangle
        with api_client.editing_session(test_file) as (session_id, file_revn):
            rect = api_client.create_rectangle(
                x=10, y=10, width=50, height=50,
                name="Version Test Rectangle"
            )

            change = api_client.create_add_obj_change(obj_id, test_page, rect)

            # This should automatically fetch and use vern
            result = api_client.update_file(test_file, session_id, file_revn, [change])

            assert result['revn'] == file_revn + 1
            print(f"Update successful with vern auto-fetch, new revn: {result['revn']}")
