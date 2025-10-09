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

**Advanced Shape Tools (Phase 3):**
- `create_path`: Create custom vector paths with points
- `create_group`: Create group containers for organizing objects
- `add_object_to_group`: Add existing objects to a group
- `create_boolean_shape`: Boolean operations (union, difference, intersection, exclusion)

**Advanced Styling Tools (Phase 3):**
- `apply_gradient`: Apply linear or radial gradient fills with angle control
- `add_stroke`: Add strokes/borders with style options (solid, dashed, dotted)
- `add_shadow`: Add drop shadow effects with spread
- `apply_blur`: Apply layer or background blur effects

**Advanced Shape/Styling Helpers (API level):**
- `create_gradient_fill`: Create linear or radial gradient fill definitions
- `create_stroke`: Create stroke/border definitions with style, cap, and join options
- `create_shadow`: Create drop shadow effect definitions
- `create_blur`: Create layer or background blur effect definitions
- `create_parent_operation`: Set object parent for grouping
- `create_fill_operation`: Create operation to set fill(s) on an object
- `create_stroke_operation`: Create operation to set stroke(s) on an object
- `create_shadow_operation`: Create operation to set shadow(s) on an object
- `create_blur_operation`: Create operation to set blur effect on an object

**Library & Component System (Phase 5):**
- `link_library`: Link a file to a component library
- `list_library_components`: List all components in a library
- `import_component`: Import a component from a library into the design
- `sync_library`: Synchronize component instances with their library
- `publish_as_library`: Publish a file as a shared component library
- `unpublish_library`: Unpublish a file as a library
- `get_file_libraries`: Get all libraries linked to a file

**Library & Component System Helpers (API level):**
- `get_file_libraries`: Get all libraries linked to a file
- `link_file_to_library`: Link a file to use a library's components
- `unlink_file_from_library`: Remove library link from a file
- `get_library_components`: Get all components in a library
- `instantiate_component`: Create an instance of a library component
- `sync_file_library`: Update component instances to match library
- `publish_library`: Publish/unpublish a file as a library

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

### Phase 3: Advanced Design with MCP Tools

The following examples show how to use the Phase 3 MCP tools for advanced design features. These are high-level tools that handle session management automatically.

#### 1. Creating Custom Paths

```python
# Create a triangle using the create_path MCP tool
create_path(
    file_id="file-123",
    page_id="page-456",
    points=[
        {"x": 50, "y": 0},
        {"x": 100, "y": 100},
        {"x": 0, "y": 100}
    ],
    closed=True,
    fill_color="#ff0000",
    stroke_color="#000000",
    stroke_width=2,
    name="Triangle"
)

# Create a star shape
create_path(
    file_id="file-123",
    page_id="page-456",
    points=[
        {"x": 50, "y": 0},
        {"x": 61, "y": 35},
        {"x": 98, "y": 35},
        {"x": 68, "y": 57},
        {"x": 79, "y": 91},
        {"x": 50, "y": 70},
        {"x": 21, "y": 91},
        {"x": 32, "y": 57},
        {"x": 2, "y": 35},
        {"x": 39, "y": 35}
    ],
    closed=True,
    fill_color="#FFD700",
    name="Star"
)
```

#### 2. Grouping Objects

```python
# Create a group
group_result = create_group(
    file_id="file-123",
    page_id="page-456",
    name="Button Components"
)
group_id = group_result['groupId']

# Add objects to the group
add_object_to_group(
    file_id="file-123",
    object_id="rect-id",
    group_id=group_id
)

add_object_to_group(
    file_id="file-123",
    object_id="text-id",
    group_id=group_id
)
```

#### 3. Boolean Operations

```python
# Create two overlapping circles first
circle1 = add_circle(
    file_id="file-123",
    page_id="page-456",
    cx=50, cy=50, radius=40,
    fill_color="#ff0000"
)

circle2 = add_circle(
    file_id="file-123",
    page_id="page-456",
    cx=80, cy=50, radius=40,
    fill_color="#0000ff"
)

# Create union of the circles
create_boolean_shape(
    file_id="file-123",
    page_id="page-456",
    operation="union",
    shape_ids=[circle1['objectId'], circle2['objectId']],
    name="Merged Circles"
)

# Or create a difference (subtract second from first)
create_boolean_shape(
    file_id="file-123",
    page_id="page-456",
    operation="difference",
    shape_ids=[circle1['objectId'], circle2['objectId']],
    name="Donut Shape"
)
```

#### 4. Applying Gradients

```python
# Apply a linear gradient at 45 degrees
apply_gradient(
    file_id="file-123",
    object_id="rect-id",
    gradient_type="linear",
    start_color="#ff0000",
    end_color="#0000ff",
    angle=45
)

# Apply a radial gradient (angle is ignored for radial)
apply_gradient(
    file_id="file-123",
    object_id="circle-id",
    gradient_type="radial",
    start_color="#ffffff",
    end_color="#000000",
    angle=0
)
```

#### 5. Adding Strokes and Shadows

```python
# Add a dashed stroke
add_stroke(
    file_id="file-123",
    object_id="rect-id",
    color="#000000",
    width=3.0,
    style="dashed"
)

# Add a drop shadow
add_shadow(
    file_id="file-123",
    object_id="rect-id",
    color="#00000080",  # 50% transparent black
    offset_x=4,
    offset_y=4,
    blur=8,
    spread=2
)
```

#### 6. Applying Blur Effects

```python
# Apply layer blur
apply_blur(
    file_id="file-123",
    object_id="rect-id",
    blur_amount=10,
    blur_type="layer-blur"
)

# Apply background blur
apply_blur(
    file_id="file-123",
    object_id="rect-id",
    blur_amount=15,
    blur_type="background-blur"
)
```

#### 7. Creating a Complete Design

```python
# Create a modern card design with advanced features
# 1. Create card background with gradient
card = add_rectangle(
    file_id="file-123",
    page_id="page-456",
    x=50, y=50,
    width=300, height=200,
    name="Card Background"
)

apply_gradient(
    file_id="file-123",
    object_id=card['objectId'],
    gradient_type="linear",
    start_color="#667eea",
    end_color="#764ba2",
    angle=135
)

# 2. Add shadow to card
add_shadow(
    file_id="file-123",
    object_id=card['objectId'],
    color="#00000040",
    offset_x=0,
    offset_y=8,
    blur=16,
    spread=0
)

# 3. Create icon using custom path
icon = create_path(
    file_id="file-123",
    page_id="page-456",
    points=[
        {"x": 100, "y": 80},
        {"x": 120, "y": 100},
        {"x": 100, "y": 120},
        {"x": 80, "y": 100}
    ],
    closed=True,
    fill_color="#ffffff",
    name="Icon"
)

# 4. Add text with shadow
text = add_text(
    file_id="file-123",
    page_id="page-456",
    x=150, y=100,
    content="Premium",
    font_size=24,
    fill_color="#ffffff",
    name="Title"
)

add_shadow(
    file_id="file-123",
    object_id=text['objectId'],
    color="#00000060",
    offset_x=0,
    offset_y=2,
    blur=4
)

# 5. Group all elements
group = create_group(
    file_id="file-123",
    page_id="page-456",
    name="Card Component"
)

for obj_id in [card['objectId'], icon['objectId'], text['objectId']]:
    add_object_to_group(
        file_id="file-123",
        object_id=obj_id,
        group_id=group['groupId']
    )
```

### Advanced Shape Creation Workflow (Phase 3 - API Level)

The following examples show the lower-level API methods for advanced control. These require manual session management.

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

### Advanced Styling Workflow (Phase 3)

#### 1. Applying Gradients to Shapes

```python
# Create a rectangle with a linear gradient
api = PenpotAPI()

# Create rectangle
rect = api.create_rectangle(x=100, y=100, width=200, height=100)
rect_id = api.generate_session_id()

# Create linear gradient (left to right)
gradient = api.create_gradient_fill(
    gradient_type='linear',
    start_color='#ff0000',
    end_color='#0000ff',
    start_x=0.0,
    start_y=0.0,
    end_x=1.0,
    end_y=0.0
)

# Apply gradient to rectangle
rect['fills'] = [gradient]

# Add to file
change = api.create_add_obj_change(rect_id, "page-id", rect)

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [change])
```

#### 2. Applying Multiple Strokes

```python
# Add multiple strokes to create outline effects
api = PenpotAPI()

# Create circle
circle = api.create_circle(cx=150, cy=150, radius=50)
circle_id = api.generate_session_id()

# Create outer thick stroke
outer_stroke = api.create_stroke(
    color='#000000',
    width=5.0,
    style='solid',
    cap='round',
    join='round'
)

# Create inner dashed stroke
inner_stroke = api.create_stroke(
    color='#ff0000',
    width=2.0,
    style='dashed',
    cap='round',
    join='round'
)

# Apply both strokes
stroke_op = api.create_stroke_operation([outer_stroke, inner_stroke])

# Create change
change = api.create_mod_obj_change(circle_id, [stroke_op])

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [change])
```

#### 3. Adding Shadow Effects

```python
# Add drop shadow to text
api = PenpotAPI()

# Create text
text = api.create_text(x=50, y=50, content="Hello World", font_size=48)
text_id = api.generate_session_id()

# Create drop shadow with semi-transparent color
shadow = api.create_shadow(
    color='#00000080',  # 50% transparent black
    offset_x=2,
    offset_y=2,
    blur=4,
    spread=1.0
)

# Apply shadow
shadow_op = api.create_shadow_operation([shadow])

# Create change
change = api.create_mod_obj_change(text_id, [shadow_op])

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [change])
```

#### 4. Applying Blur Effects

```python
# Add layer blur to create depth effect
api = PenpotAPI()

rect_id = "existing-rect-id"

# Create layer blur
blur = api.create_blur(
    blur_type='layer-blur',
    value=10
)

# Apply blur
blur_op = api.create_blur_operation(blur)

# Create change
change = api.create_mod_obj_change(rect_id, [blur_op])

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [change])
```

#### 5. Combining Multiple Style Effects

```python
# Apply gradient, stroke, shadow, and blur together
api = PenpotAPI()

# Create rectangle
rect = api.create_rectangle(x=100, y=100, width=200, height=100)
rect_id = api.generate_session_id()

# Add rectangle to file first
add_change = api.create_add_obj_change(rect_id, "page-id", rect)

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [add_change])

# Now apply all styling effects
# Create radial gradient
gradient = api.create_gradient_fill(
    gradient_type='radial',
    start_color='#ff00ff',
    end_color='#00ffff',
    start_x=0.5,
    start_y=0.5,
    end_x=1.0,
    end_y=1.0
)
fill_op = api.create_fill_operation([gradient])

# Create stroke
stroke = api.create_stroke(
    color='#000000',
    width=3.0,
    style='solid'
)
stroke_op = api.create_stroke_operation([stroke])

# Create shadow
shadow = api.create_shadow(
    color='#00000080',
    offset_x=5,
    offset_y=5,
    blur=10
)
shadow_op = api.create_shadow_operation([shadow])

# Create blur
blur = api.create_blur('layer-blur', 5)
blur_op = api.create_blur_operation(blur)

# Apply all effects
style_change = api.create_mod_obj_change(rect_id, [
    fill_op,
    stroke_op,
    shadow_op,
    blur_op
])

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [style_change])
```

#### 6. Creating Shape with Gradient from Start

```python
# Create shape with gradient in one step
api = PenpotAPI()

# Create gradient
gradient = api.create_gradient_fill(
    gradient_type='linear',
    start_color='#ff0000',
    end_color='#ffff00',
    start_x=0.0,
    start_y=0.0,
    end_x=1.0,
    end_y=1.0  # Diagonal gradient
)

# Create circle with gradient
circle = api.create_circle(cx=150, cy=150, radius=50)
circle['fills'] = [gradient]  # Replace default fill with gradient

# Add to file
circle_id = api.generate_session_id()
change = api.create_add_obj_change(circle_id, "page-id", circle)

with api.editing_session("file-id") as (session_id, revn):
    api.update_file("file-id", session_id, revn, [change])
```

### Comments & Collaboration Workflow

The Penpot MCP server supports adding comments to designs for collaboration and review.

#### Creating Comment Threads

```python
# Add a comment to a design
result = add_design_comment(
    file_id="file-123",
    page_id="page-456",
    x=150,  # X position on the canvas
    y=200,  # Y position on the canvas
    comment="This button needs to be larger"
)

thread_id = result['thread_id']
```

#### Replying to Comments

```python
# Add a reply to an existing thread
reply = reply_to_comment(
    thread_id=thread_id,
    reply="Agreed! I'll increase the size by 20%"
)
```

#### Retrieving Comments

```python
# Get all comment threads for a file
all_comments = get_file_comments(file_id="file-123")

# Get comments for a specific page
page_comments = get_file_comments(
    file_id="file-123",
    page_id="page-456"
)

print(f"Found {page_comments['count']} comment threads")
for thread in page_comments['threads']:
    print(f"Comment at ({thread['position']['x']}, {thread['position']['y']})")
```

#### Resolving Comments

```python
# Mark a comment thread as resolved
result = resolve_comment_thread(thread_id=thread_id)
```

#### AI-Assisted Design Review Example

```python
# 1. Get the design file
file_data = get_file(file_id="design-123")

# 2. Analyze the design and add review comments
comments = [
    {
        'x': 100, 'y': 150,
        'comment': 'Consider using higher contrast for accessibility'
    },
    {
        'x': 300, 'y': 200,
        'comment': 'This heading should use the brand font (Roboto Bold)'
    },
    {
        'x': 450, 'y': 300,
        'comment': 'Button padding seems inconsistent with design system'
    }
]

# 3. Add all comments to the design
for c in comments:
    add_design_comment(
        file_id="design-123",
        page_id="page-1",
        x=c['x'],
        y=c['y'],
        comment=c['comment']
    )

# 4. Review and resolve comments as fixes are made
all_threads = get_file_comments(file_id="design-123")
for thread in all_threads['threads']:
    # After verifying the fix, resolve the thread
    resolve_comment_thread(thread_id=thread['id'])
```

### Library & Component System Workflow

The Penpot MCP server supports working with component libraries and design systems, enabling reusable components across projects.

#### Publishing a File as a Library

```python
# 1. Create a design file with components you want to share
file = create_file(name="Design System", project_id="project-123")
file_id = file['id']
page_id = file['data']['pages'][0]['id']

# 2. Create reusable components (buttons, cards, etc.)
button = add_rectangle(
    file_id=file_id,
    page_id=page_id,
    x=50, y=50,
    width=120, height=40,
    name="Primary Button",
    fill_color="#4A90E2"
)

card = add_rectangle(
    file_id=file_id,
    page_id=page_id,
    x=200, y=50,
    width=300, height=200,
    name="Card Component",
    fill_color="#FFFFFF",
    stroke_color="#E0E0E0",
    stroke_width=1
)

# 3. Publish the file as a shared library
publish_result = publish_as_library(file_id=file_id)
print(f"Library published: {publish_result['file']['name']}")
```

#### Linking a Library and Using Components

```python
# 1. Check what libraries are already linked (optional)
linked_libs = get_file_libraries(file_id="design-file-123")
print(f"Currently linked to {linked_libs['count']} libraries")

# 2. Link the library to your design file
link_result = link_library(
    file_id="design-file-123",
    library_id="library-file-456"
)
print("Library linked successfully")

# 3. List available components from the library
components_result = list_library_components(library_id="library-file-456")
print(f"Found {components_result['count']} components:")
for component in components_result['components']:
    print(f"  - {component['name']} (ID: {component['id']})")

# 4. Import components into your design
button_instance = import_component(
    file_id="design-file-123",
    page_id="page-1",
    library_id="library-file-456",
    component_id="button-component-id",
    x=100,
    y=100
)

card_instance = import_component(
    file_id="design-file-123",
    page_id="page-1",
    library_id="library-file-456",
    component_id="card-component-id",
    x=300,
    y=100
)

print("Components imported successfully")
```

#### Unpublishing a Library

```python
# Remove library status from a file
unpublish_result = unpublish_library(file_id="library-file-456")
print(f"Library unpublished: {unpublish_result['file']['name']}")
```

#### Synchronizing Component Instances

```python
# When the library is updated, sync all instances in the design
sync_result = sync_library(
    file_id="design-file-123",
    library_id="library-file-456"
)

print(f"Updated {sync_result['result']['updated-count']} component instances")
```

#### Complete Design System Workflow (API Level)

```python
from penpot_mcp.api.penpot_api import PenpotAPI

api = PenpotAPI()

# 1. Create and publish a design system library
library_file = api.create_file(
    name="Design System v2",
    project_id="project-123",
    is_shared=True  # Mark as library immediately
)
library_id = library_file['id']
page_id = library_file['data']['pages'][0]['id']

# 2. Add components to the library
with api.editing_session(library_id) as (session_id, revn):
    # Create a button component
    button = api.create_rectangle(
        x=50, y=50, width=120, height=40,
        fill_color='#4A90E2',
        name='Button Primary'
    )
    button_id = api.generate_session_id()
    
    changes = [
        api.create_add_obj_change(button_id, page_id, button)
    ]
    api.update_file(library_id, session_id, revn, changes)

# 3. Link library to a design file
design_file_id = "existing-design-file"
api.link_file_to_library(design_file_id, library_id)

# 4. Get available components
components = api.get_library_components(library_id)
for comp in components:
    print(f"Component: {comp['name']}")

# 5. Instantiate a component from the library
component_to_use = components[0]
result = api.instantiate_component(
    file_id=design_file_id,
    page_id="page-1",
    library_id=library_id,
    component_id=component_to_use['id'],
    x=200,
    y=200
)

# 6. Later, sync all instances when library is updated
sync_result = api.sync_file_library(design_file_id, library_id)
print(f"Synced {sync_result.get('updated-count', 0)} instances")
```

#### Design System Best Practices

1. **Library Organization**: Create separate library files for different component categories (UI controls, icons, layouts)
2. **Naming Convention**: Use clear, descriptive names for components (e.g., "Button Primary", "Card Default")
3. **Regular Syncing**: After updating a library, sync all dependent files to propagate changes
4. **Version Control**: Consider using file naming or descriptions to track library versions
5. **Component Variants**: Create multiple versions of components for different states (hover, active, disabled)
6. **Documentation**: Add comments to complex components to help users understand usage

#### AI-Assisted Library Management Example

```python
# AI analyzes a design and recommends using library components
design_file = get_file(file_id="new-design")

# Get linked libraries
libraries = api.get_file_libraries(design_file_id)

# For each library, check for relevant components
for library in libraries:
    components = api.get_library_components(library['id'])
    
    # AI suggests: "I found a 'Primary Button' component in your design system"
    # "Would you like to replace this custom button with the library component?"
    
    # Import the standardized component
    import_component(
        file_id=design_file_id,
        page_id="page-1",
        library_id=library['id'],
        component_id="button-primary-id",
        x=100, y=200
    )
```

### Testing Patterns

- Mock fixtures in `tests/conftest.py`
- Test both stdio and SSE modes
- Verify Transit format conversions
- Check cache behavior and expiration

## Memories

- Keep the current transport format for the current API requests