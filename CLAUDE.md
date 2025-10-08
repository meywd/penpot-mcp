# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Penpot MCP Server is a Python-based Model Context Protocol (MCP) server that bridges AI language models with Penpot, an open-source design platform. It enables programmatic interaction with design files through a well-structured API.

## Key Commands

### Development Setup

```bash
# Install dependencies (recommended)
uv sync --extra dev

# Run the MCP server
uv run penpot-mcp

# Run tests
uv run pytest
uv run pytest --cov=penpot_mcp tests/  # with coverage

# Lint and fix code
uv run python lint.py              # check issues
uv run python lint.py --autofix    # auto-fix issues
```

### Running the Server

```bash
# Default stdio mode (for Claude Desktop/Cursor)
make mcp-server

# SSE mode (for debugging with inspector)
make mcp-server-sse

# Launch MCP inspector (requires SSE mode)
make mcp-inspector
```

### CLI Tools

```bash
# Generate tree visualization
penpot-tree path/to/penpot_file.json

# Validate Penpot file
penpot-validate path/to/penpot_file.json
```

## Architecture Overview

### Core Components

1. **MCP Server** (`penpot_mcp/server/mcp_server.py`)
   - Built on FastMCP framework
   - Implements resources and tools for Penpot interaction
   - Memory cache with 10-minute TTL
   - Supports stdio (default) and SSE modes

2. **API Client** (`penpot_mcp/api/penpot_api.py`)
   - REST client for Penpot platform
   - Transit+JSON format handling
   - Cookie-based authentication with auto-refresh
   - Lazy authentication pattern

3. **Key Design Patterns**
   - **Authentication**: Cookie-based with automatic re-authentication on 401/403
   - **Caching**: In-memory file cache to reduce API calls
   - **Resource/Tool Duality**: Resources can be exposed as tools via RESOURCES_AS_TOOLS config
   - **Transit Format**: Special handling for UUIDs (`~u` prefix) and keywords (`~:` prefix)
   - **Session and Revision Management**: Every file update requires a session ID and revision number
     - Session ID: Generated UUID for tracking edit sessions
     - Revision number: Integer that increments with each change
     - Use `editing_session()` context manager for convenience

### Available Tools/Functions

**File Management:**
- `list_projects`: Get all Penpot projects
- `get_project_files`: List files in a project
- `get_file`: Retrieve and cache file data
- `create_file`: Create new Penpot design file
- `delete_file`: Delete a Penpot file
- `rename_file`: Rename a Penpot file

**Design Exploration:**
- `search_object`: Search design objects by name (regex)
- `get_object_tree`: Get filtered object tree with screenshot
- `export_object`: Export design objects as images
- `penpot_tree_schema`: Get schema for object tree fields

**Shape Creation (Phase 2):**
- `add_rectangle`: Add a rectangle to the design
- `add_circle`: Add a circle to the design
- `add_text`: Add text to the design
- `add_frame`: Create a new frame (artboard) in the design

**Object Modification Tools (Phase 2):**
- `move_object`: Move an object to new coordinates (x, y)
- `resize_object`: Resize an object (width, height)
- `change_object_color`: Change fill color and opacity
- `rotate_object`: Rotate an object by degrees
- `delete_object`: Delete an object from a page
- `apply_design_changes`: Apply multiple changes atomically

### Environment Configuration

Create a `.env` file with:

```env
PENPOT_API_URL=https://design.penpot.app/api
PENPOT_USERNAME=your_username
PENPOT_PASSWORD=your_password
ENABLE_HTTP_SERVER=true  # for image serving
RESOURCES_AS_TOOLS=false # MCP resource mode
DEBUG=true               # debug logging
```

### Working with the Codebase

1. **Adding New Tools**: Decorate functions with `@self.mcp.tool()` in mcp_server.py
2. **API Extensions**: Add methods to PenpotAPI class following existing patterns
3. **Error Handling**: Always check for `"error"` keys in API responses
4. **Testing**: Use `test_mode=True` when creating server instances in tests
5. **Transit Format**: Remember to handle Transit+JSON when working with raw API
6. **Session Management**: Use `editing_session()` context manager for file updates
   - Automatically generates session ID and retrieves current revision
   - Example:
     ```python
     with api.editing_session("file-id") as (session_id, revn):
         # Use session_id and revn for update operations
         api.update_file(file_id, session_id, revn, changes)
     ```

### Common Workflow for Code Generation

1. List projects → Find target project
2. Get project files → Locate design file
3. Search for component → Find specific element
4. Get tree schema → Understand available fields
5. Get object tree → Retrieve structure with screenshot
6. Export if needed → Get rendered component image

### Complete Design Workflow Example

#### 1. Create File and Project
```python
# Create a new project
create_project(team_id="team-123", name="My Design Project")

# Create a new file
file = create_file(name="Mobile UI", project_id="project-123")
file_id = file['id']
page_id = file['data']['pages'][0]['id']
```

#### 2. Add Shapes
```python
# Create a frame (artboard) for mobile screen
frame_result = add_frame(
    file_id=file_id,
    page_id=page_id,
    x=0, y=0,
    width=375, height=812,
    name="iPhone 13",
    background_color="#FFFFFF"
)
frame_id = frame_result['frameId']

# Add a header rectangle inside the frame
header = add_rectangle(
    file_id=file_id,
    page_id=page_id,
    x=0, y=0,
    width=375, height=60,
    name="Header",
    fill_color="#4A90E2",
    frame_id=frame_id
)

# Add title text inside the frame
title = add_text(
    file_id=file_id,
    page_id=page_id,
    x=20, y=20,
    content="My App",
    name="Title",
    font_size=24,
    fill_color="#FFFFFF",
    font_family="Work Sans",
    frame_id=frame_id
)

# Add a circular avatar
avatar = add_circle(
    file_id=file_id,
    page_id=page_id,
    cx=187, cy=150,
    radius=40,
    name="Avatar",
    fill_color="#E0E0E0",
    stroke_color="#CCCCCC",
    stroke_width=2,
    frame_id=frame_id
)
```

#### 3. Modify Shapes
```python
# Move the header
move_object(
    file_id="file-123",
    object_id="header-id",
    x=0,
    y=10
)

# Resize the avatar
resize_object(
    file_id="file-123",
    object_id="avatar-id",
    width=50,
    height=50
)

# Change header color
change_object_color(
    file_id="file-123",
    object_id="header-id",
    fill_color="#00FF00",
    fill_opacity=0.8
)

# Rotate title
rotate_object(
    file_id="file-123",
    object_id="title-id",
    rotation=5
)
```

#### 4. Batch Operations
```python
# Apply multiple changes atomically
changes = [
    {
        "type": "mod-obj",
        "id": "rect-1",
        "operations": [
            {"type": "set", "attr": "x", "val": 100},
            {"type": "set", "attr": "y", "val": 100}
        ]
    },
    {
        "type": "mod-obj",
        "id": "rect-2",
        "operations": [
            {"type": "set", "attr": "x", "val": 200},
            {"type": "set", "attr": "y", "val": 200}
        ]
    }
]

apply_design_changes(file_id="file-123", changes=changes)
```

#### 5. Delete Shapes
```python
# Delete an object
delete_object(
    file_id="file-123",
    page_id="page-456",
    object_id="rect-id"
)
```

#### 6. Export Result
```python
# Export the final design
export_object(
    file_id="file-123",
    page_id="page-456",
    object_id="frame-id",
    export_type="png",
    scale=2
)
```

### Testing Patterns

- Mock fixtures in `tests/conftest.py`
- Test both stdio and SSE modes
- Verify Transit format conversions
- Check cache behavior and expiration

## Memories

- Keep the current transport format for the current API requests