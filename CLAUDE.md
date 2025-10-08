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

**Advanced Shape Helpers (Phase 3):**
- `create_path`: Create custom vector paths with points
- `create_boolean_shape`: Boolean operations (union, difference, intersection, exclusion)
- `create_parent_operation`: Set object parent for grouping
- `create_group`: Create group containers (already implemented in Phase 2)

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

### Advanced Shape Creation Workflow (Phase 3)

#### 1. Creating Custom Vector Paths

```python
# Create a triangle path
api = PenpotAPI()
triangle_points = [
    {'x': 50, 'y': 0},
    {'x': 100, 'y': 100},
    {'x': 0, 'y': 100}
]
triangle = api.create_path(
    points=triangle_points,
    closed=True,
    fill_color='#ff0000',
    stroke_color='#000000',
    stroke_width=2,
    name="Triangle"
)

# Add to file
triangle_id = api.generate_session_id()
change = api.create_add_obj_change(triangle_id, "page-id", triangle)

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [change])
```

#### 2. Creating Grouped Objects

```python
# Create a button group with rectangle and text
api = PenpotAPI()

# Create group container
group = api.create_group(name="Button Group", x=100, y=100)
group_id = api.generate_session_id()

# Create rectangle for button background
button_bg = api.create_rectangle(
    x=0, y=0,
    width=120, height=40,
    fill_color='#4A90E2',
    rx=5, ry=5
)
button_bg['parentId'] = group_id  # Set parent to group
bg_id = api.generate_session_id()

# Create text for button label
button_text = api.create_text(
    x=30, y=12,
    content="Click Me",
    fill_color='#FFFFFF',
    font_size=16
)
button_text['parentId'] = group_id  # Set parent to group
text_id = api.generate_session_id()

# Add all objects
changes = [
    api.create_add_obj_change(group_id, "page-id", group),
    api.create_add_obj_change(bg_id, "page-id", button_bg),
    api.create_add_obj_change(text_id, "page-id", button_text)
]

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, changes)
```

#### 3. Boolean Operations with Shapes

```python
# Create a union of two circles (Venn diagram overlap)
api = PenpotAPI()

# Create first circle
circle1 = api.create_circle(cx=50, cy=50, radius=40, fill_color='#ff0000')
circle1_id = api.generate_session_id()

# Create second circle
circle2 = api.create_circle(cx=80, cy=50, radius=40, fill_color='#00ff00')
circle2_id = api.generate_session_id()

# Create boolean union shape
bool_shape = api.create_boolean_shape(
    operation='union',
    shapes=[circle1_id, circle2_id],
    name="Union of Circles"
)
bool_id = api.generate_session_id()

# Add shapes and boolean operation
changes = [
    api.create_add_obj_change(circle1_id, "page-id", circle1),
    api.create_add_obj_change(circle2_id, "page-id", circle2),
    api.create_add_obj_change(bool_id, "page-id", bool_shape)
]

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, changes)
```

#### 4. Moving Objects into Groups (Parent Operations)

```python
# Move existing objects into a group
api = PenpotAPI()

# Create parent operations
parent_op = api.create_parent_operation("group-123")

# Apply to multiple objects
changes = [
    api.create_mod_obj_change("obj-1", [parent_op]),
    api.create_mod_obj_change("obj-2", [parent_op]),
    api.create_mod_obj_change("obj-3", [parent_op])
]

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, changes)
```

#### 5. Complex Path Example (Pentagon)

```python
# Create a regular pentagon
api = PenpotAPI()
import math

# Calculate pentagon points
n_sides = 5
radius = 50
center_x, center_y = 100, 100
points = []

for i in range(n_sides):
    angle = (2 * math.pi * i / n_sides) - (math.pi / 2)  # Start from top
    x = center_x + radius * math.cos(angle)
    y = center_y + radius * math.sin(angle)
    points.append({'x': x, 'y': y})

pentagon = api.create_path(
    points=points,
    closed=True,
    fill_color='#ff00ff',
    stroke_color='#000000',
    stroke_width=2,
    name="Pentagon"
)

pentagon_id = api.generate_session_id()
change = api.create_add_obj_change(pentagon_id, "page-id", pentagon)

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [change])
```

#### 6. Advanced Boolean Operations

```python
# Create complex shapes using different boolean operations
api = PenpotAPI()

# Operation types:
# - 'union': Combine shapes
# - 'difference': Subtract second shape from first
# - 'intersection': Keep only overlapping areas
# - 'exclusion': Keep non-overlapping areas

# Example: Create a donut shape (circle with hole)
outer_circle = api.create_circle(cx=100, cy=100, radius=50, fill_color='#4A90E2')
inner_circle = api.create_circle(cx=100, cy=100, radius=30, fill_color='#4A90E2')
outer_id = api.generate_session_id()
inner_id = api.generate_session_id()

# Subtract inner from outer
donut = api.create_boolean_shape(
    operation='difference',
    shapes=[outer_id, inner_id],
    name="Donut"
)
donut_id = api.generate_session_id()

changes = [
    api.create_add_obj_change(outer_id, "page-id", outer_circle),
    api.create_add_obj_change(inner_id, "page-id", inner_circle),
    api.create_add_obj_change(donut_id, "page-id", donut)
]

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, changes)
```

### Testing Patterns

- Mock fixtures in `tests/conftest.py`
- Test both stdio and SSE modes
- Verify Transit format conversions
- Check cache behavior and expiration

## Memories

- Keep the current transport format for the current API requests