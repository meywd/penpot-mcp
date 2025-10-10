"""Integration tests for Penpot MCP against local Penpot instance.

These tests create a persistent test document with one file per test class,
allowing visual verification of results in Penpot.

To run these tests:
1. Set environment variables:
   - PENPOT_API_URL=http://localhost:9001/api
   - PENPOT_USERNAME=your_username
   - PENPOT_PASSWORD=your_password
   - CLEANUP_TEST_FILES=true (optional, to delete test project after tests)

2. Run with pytest:
   pytest tests/test_integration_local.py -v -s

The tests create a project "MCP Integration Tests - {timestamp}" with separate
files for each test class. Check Penpot to see the visual results!

Files created:
- 01 - Project & File Management
- 02 - Shape Creation
- 03 - MCP Tools
- 04 - Version Compatibility
"""

import os
import time
from datetime import datetime

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
    """Create a persistent test project for all integration tests."""
    # Create test project
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    project_name = f"MCP Integration Tests - {timestamp}"
    project = api_client.create_project(project_name, test_team)
    project_id = project['id']

    print(f"\n{'='*60}")
    print(f"Created test project: {project_name}")
    print(f"Project ID: {project_id}")
    print(f"{'='*60}\n")

    yield project_id

    # Optional cleanup based on environment variable
    if os.getenv('CLEANUP_TEST_FILES', 'false').lower() == 'true':
        try:
            api_client.delete_project(project_id)
            print(f"\nCleaned up test project: {project_id}")
        except Exception as e:
            print(f"\nWarning: Failed to cleanup project {project_id}: {e}")
    else:
        print(f"\n{'='*60}")
        print(f"Test project preserved for visual inspection:")
        print(f"  Project: {project_name}")
        print(f"  ID: {project_id}")
        print(f"  Set CLEANUP_TEST_FILES=true to auto-delete")
        print(f"{'='*60}\n")


def get_test_file(api_client, test_project, class_name: str):
    """Helper to create a test file for a test class."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    file_name = f"{class_name} - {timestamp}"
    file = api_client.create_file(file_name, test_project)
    file_id = file['id']

    print(f"\n{'-'*60}")
    print(f"Created test file: {file_name}")
    print(f"File ID: {file_id}")
    print(f"{'-'*60}\n")

    return file_id


def get_test_page(api_client, file_id, test_name: str):
    """Get the first page from a file and display test info."""
    file_data = api_client.get_file(file_id)
    pages = file_data.get('data', {}).get('pages', [])
    if not pages:
        pytest.skip("No pages available in test file")

    # Pages can be a list of page objects or a list of page IDs
    if isinstance(pages[0], dict):
        page_id = pages[0]['id']
    else:
        # pages is a list of IDs
        page_id = pages[0]

    print(f"Test: {test_name}")
    print(f"Page ID: {page_id}")

    return page_id


def create_test_artboard(api_client, file_id, page_id, name: str = "Test Artboard"):
    """Create an artboard on the page for shapes to be added to.

    This is required because shapes added directly to a page go into the Root Frame
    which is tiny (0.01x0.01) and invisible. Proper Penpot workflow is to add shapes
    to artboards/frames.
    """
    artboard_id = api_client.generate_session_id()

    with api_client.editing_session(file_id) as (session_id, revn):
        # Create a desktop-sized artboard
        artboard = api_client.create_frame(
            x=0, y=0,
            width=1920, height=1080,
            name=name
        )

        # Add artboard to the page
        change = api_client.create_add_obj_change(artboard_id, page_id, artboard)
        api_client.update_file(file_id, session_id, revn, [change])

    print(f"Created artboard: {name} (ID: {artboard_id})")
    return artboard_id


# ========== PROJECT & FILE MANAGEMENT TESTS ==========

class TestProjectFileManagement:
    """Test project and file management operations."""

    @pytest.fixture(scope="class")
    def test_file(self, api_client, test_project):
        """Create a dedicated file for this test class."""
        return get_test_file(api_client, test_project, "01 - Project & File Management")

    def test_get_teams(self, api_client):
        """Test retrieving teams."""
        print(f"\n{'-'*60}")
        print("Test: Get Teams")
        print(f"{'-'*60}")

        teams = api_client.get_teams()
        assert isinstance(teams, list)
        assert len(teams) > 0
        assert 'id' in teams[0]
        assert 'name' in teams[0]
        print(f"Found {len(teams)} team(s)")

    def test_create_and_delete_project(self, api_client, test_team):
        """Test creating and deleting a project."""
        print(f"\n{'-'*60}")
        print("Test: Create and Delete Project")
        print(f"{'-'*60}")

        # Create project
        project_name = f"Temp Test Project {int(time.time())}"
        project = api_client.create_project(project_name, test_team)

        assert 'id' in project
        assert project['name'] == project_name
        project_id = project['id']
        print(f"Created project: {project_id}")

        # Delete project
        result = api_client.delete_project(project_id)
        assert result['success'] is True
        print(f"Deleted project: {project_id}")

    def test_create_and_delete_file(self, api_client, test_project):
        """Test creating and deleting a file."""
        print(f"\n{'-'*60}")
        print("Test: Create and Delete File")
        print(f"{'-'*60}")

        # Create file
        file_name = f"Temp Test File {int(time.time())}"
        file = api_client.create_file(file_name, test_project)

        assert 'id' in file
        assert file['name'] == file_name
        file_id = file['id']
        print(f"Created file: {file_id}")

        # Delete file
        result = api_client.delete_file(file_id)
        assert result['success'] is True
        print(f"Deleted file: {file_id}")

    def test_get_file_with_vern(self, api_client, test_file):
        """Test getting file and checking for vern field."""
        print(f"\n{'-'*60}")
        print("Test: Get File with Vern")
        print(f"{'-'*60}")

        file_data = api_client.get_file(test_file)

        assert 'id' in file_data
        assert 'revn' in file_data

        # Check if vern exists (required for self-hosted)
        has_vern = 'vern' in file_data
        print(f"File has vern field: {has_vern}")
        if has_vern:
            print(f"revn={file_data['revn']}, vern={file_data['vern']}")


# ========== SHAPE CREATION TESTS ==========

class TestShapeCreation:
    """Test creating shapes in a file."""

    @pytest.fixture(scope="class")
    def test_file(self, api_client, test_project):
        """Create a dedicated file for this test class."""
        return get_test_file(api_client, test_project, "02 - Shape Creation")

    @pytest.fixture(scope="class")
    def test_artboard(self, api_client, test_file):
        """Create an artboard for all shapes in this test class."""
        file_data = api_client.get_file(test_file)
        pages = file_data.get('data', {}).get('pages', [])
        page_id = pages[0] if isinstance(pages[0], str) else pages[0]['id']
        return create_test_artboard(api_client, test_file, page_id, "Shapes Test Artboard")

    @pytest.fixture
    def test_page(self, api_client, test_file, request):
        """Get the page for this test."""
        test_name = request.node.name.replace("test_", "").replace("_", " ").title()
        return get_test_page(api_client, test_file, test_name)

    def test_add_rectangle(self, api_client, test_file, test_page, test_artboard):
        """Test adding a rectangle to the file."""
        print(f"\n{'-'*60}")
        print("Test: Add Rectangle")
        print(f"{'-'*60}")

        # Generate object ID
        obj_id = api_client.generate_session_id()

        # Create rectangle
        with api_client.editing_session(test_file) as (session_id, revn):
            rect = api_client.create_rectangle(
                x=100, y=100, width=200, height=150,
                name="Test Rectangle",
                fill_color="#FF0000"
            )

            # Add rectangle to the artboard (not the page)
            change = api_client.create_add_obj_change(obj_id, test_page, rect, frame_id=test_artboard)
            result = api_client.update_file(test_file, session_id, revn, [change])

            assert 'revn' in result
            assert result['revn'] == revn + 1
            print(f"Added rectangle to artboard, new revision: {result['revn']}")

    def test_add_circle(self, api_client, test_file, test_page, test_artboard):
        """Test adding a circle to the file."""
        print(f"\n{'-'*60}")
        print("Test: Add Circle")
        print(f"{'-'*60}")

        obj_id = api_client.generate_session_id()

        with api_client.editing_session(test_file) as (session_id, revn):
            circle = api_client.create_circle(
                cx=350, cy=200, radius=50,
                name="Test Circle",
                fill_color="#00FF00"
            )

            # Add circle to the artboard
            change = api_client.create_add_obj_change(obj_id, test_page, circle, frame_id=test_artboard)
            result = api_client.update_file(test_file, session_id, revn, [change])

            assert result['revn'] == revn + 1
            print(f"Added circle to artboard, new revision: {result['revn']}")

    def test_add_text(self, api_client, test_file, test_page, test_artboard):
        """Test adding text to the file."""
        print(f"\n{'-'*60}")
        print("Test: Add Text")
        print(f"{'-'*60}")

        obj_id = api_client.generate_session_id()

        with api_client.editing_session(test_file) as (session_id, revn):
            text = api_client.create_text(
                x=500, y=150,
                content="Integration Test",
                font_size=24
            )

            # Add text to the artboard
            change = api_client.create_add_obj_change(obj_id, test_page, text, frame_id=test_artboard)
            result = api_client.update_file(test_file, session_id, revn, [change])

            assert result['revn'] == revn + 1
            print(f"Added text to artboard, new revision: {result['revn']}")

    def test_add_frame(self, api_client, test_file, test_page, test_artboard):
        """Test adding a frame to the file."""
        print(f"\n{'-'*60}")
        print("Test: Add Frame")
        print(f"{'-'*60}")

        obj_id = api_client.generate_session_id()

        with api_client.editing_session(test_file) as (session_id, revn):
            frame = api_client.create_frame(
                x=750, y=100,
                width=400, height=300,
                name="Test Frame"
            )

            # Add frame to the artboard
            change = api_client.create_add_obj_change(obj_id, test_page, frame, frame_id=test_artboard)
            result = api_client.update_file(test_file, session_id, revn, [change])

            assert result['revn'] == revn + 1
            print(f"Added frame to artboard, new revision: {result['revn']}")


# ========== MCP TOOL TESTS ==========

class TestMCPTools:
    """Test MCP tools against real API."""

    @pytest.fixture(scope="class")
    def test_file(self, api_client, test_project):
        """Create a dedicated file for this test class."""
        return get_test_file(api_client, test_project, "03 - MCP Tools")

    @pytest.fixture(scope="class")
    def test_artboard(self, api_client, test_file):
        """Create an artboard for all MCP tool tests."""
        file_data = api_client.get_file(test_file)
        pages = file_data.get('data', {}).get('pages', [])
        page_id = pages[0] if isinstance(pages[0], str) else pages[0]['id']
        return create_test_artboard(api_client, test_file, page_id, "MCP Tools Test Artboard")

    @pytest.fixture
    def test_page(self, api_client, test_file, request):
        """Get the page for this test."""
        test_name = request.node.name.replace("test_", "").replace("_", " ").title()
        return get_test_page(api_client, test_file, test_name)

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
        print(f"\n{'-'*60}")
        print("Test: List Projects Tool")
        print(f"{'-'*60}")

        result = tool_helper('list_projects')

        assert 'projects' in result
        assert isinstance(result['projects'], list)
        print(f"Found {len(result['projects'])} project(s)")

    def test_add_rectangle_tool(self, tool_helper, test_file, test_page, test_artboard):
        """Test add_rectangle MCP tool."""
        print(f"\n{'-'*60}")
        print("Test: Add Rectangle Tool")
        print(f"{'-'*60}")

        result = tool_helper(
            'add_rectangle',
            file_id=test_file,
            page_id=test_page,
            frame_id=test_artboard,
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
        print(f"Added rectangle via MCP tool to artboard, object ID: {result['objectId']}")

    def test_add_circle_tool(self, tool_helper, test_file, test_page, test_artboard):
        """Test add_circle MCP tool."""
        print(f"\n{'-'*60}")
        print("Test: Add Circle Tool")
        print(f"{'-'*60}")

        result = tool_helper(
            'add_circle',
            file_id=test_file,
            page_id=test_page,
            frame_id=test_artboard,
            cx=200.0,
            cy=200.0,
            radius=40.0,
            name="MCP Tool Circle",
            fill_color="#FFFF00"
        )

        assert result['success'] is True
        assert 'objectId' in result
        print(f"Added circle via MCP tool to artboard, object ID: {result['objectId']}")

    def test_add_text_tool(self, tool_helper, test_file, test_page, test_artboard):
        """Test add_text MCP tool."""
        print(f"\n{'-'*60}")
        print("Test: Add Text Tool")
        print(f"{'-'*60}")

        result = tool_helper(
            'add_text',
            file_id=test_file,
            page_id=test_page,
            frame_id=test_artboard,
            x=300.0,
            y=50.0,
            content="MCP Tool Test",
            font_size=18
        )

        assert result['success'] is True
        assert 'objectId' in result
        print(f"Added text via MCP tool to artboard, object ID: {result['objectId']}")


# ========== VERSION COMPATIBILITY TESTS ==========

class TestVersionCompatibility:
    """Test compatibility with different Penpot versions."""

    @pytest.fixture(scope="class")
    def test_file(self, api_client, test_project):
        """Create a dedicated file for this test class."""
        return get_test_file(api_client, test_project, "04 - Version Compatibility")

    @pytest.fixture(scope="class")
    def test_artboard(self, api_client, test_file):
        """Create an artboard for version compatibility tests."""
        file_data = api_client.get_file(test_file)
        pages = file_data.get('data', {}).get('pages', [])
        page_id = pages[0] if isinstance(pages[0], str) else pages[0]['id']
        return create_test_artboard(api_client, test_file, page_id, "Version Test Artboard")

    @pytest.fixture
    def test_page(self, api_client, test_file, request):
        """Get the page for this test."""
        test_name = request.node.name.replace("test_", "").replace("_", " ").title()
        return get_test_page(api_client, test_file, test_name)

    def test_vern_parameter_handling(self, api_client, test_file, test_page, test_artboard):
        """Test that vern parameter is handled correctly."""
        print(f"\n{'-'*60}")
        print("Test: Vern Parameter Handling")
        print(f"{'-'*60}")

        obj_id = api_client.generate_session_id()

        # Get both revn and vern
        revn, vern = api_client.get_file_version(test_file)
        print(f"File version: revn={revn}, vern={vern}")

        # Create a simple rectangle
        with api_client.editing_session(test_file) as (session_id, file_revn):
            rect = api_client.create_rectangle(
                x=10, y=10, width=50, height=50,
                name="Version Test Rectangle"
            )

            # Add rectangle to the artboard
            change = api_client.create_add_obj_change(obj_id, test_page, rect, frame_id=test_artboard)

            # This should automatically fetch and use vern
            result = api_client.update_file(test_file, session_id, file_revn, [change])

            assert result['revn'] == file_revn + 1
            print(f"Update successful with vern auto-fetch, new revn: {result['revn']}")
