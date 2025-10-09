# Penpot MCP Design API Implementation Plan

## Overview

This plan focuses on implementing design capabilities to enable AI-powered creation and modification of Penpot designs. The core functionality revolves around the `update-file` endpoint which uses a delta/operation-based approach.

## Current State

### ✅ Implemented (Read-Only)
- `login-with-password` - Authentication
- `get-profile` - User profile
- `list_projects` - List all projects
- `get_project_files` - List files in project
- `get_file` - Get file data
- `export_and_download` - Export designs as images

### ❌ Missing (All Write Operations)
- **0 design APIs implemented**
- Cannot create shapes
- Cannot modify objects
- Cannot delete elements
- Cannot create files/projects

## Revised Implementation Plan

### **Phase 1: Foundation - File & Project Management** (Week 1)
*Prerequisites for design operations*

#### 1.1 File Operations (`penpot_mcp/api/penpot_api.py`)
```python
def create_file(name: str, project_id: str, is_shared: bool = False) -> dict
def delete_file(file_id: str) -> dict
def rename_file(file_id: str, name: str) -> dict
```

#### 1.2 Project Operations (`penpot_mcp/api/penpot_api.py`)
```python
def create_project(name: str, team_id: str) -> dict
def get_project(project_id: str) -> dict  # Enhanced version
def delete_project(project_id: str) -> dict
def rename_project(project_id: str, name: str) -> dict
def get_teams() -> list  # Needed to create projects
```

#### 1.3 MCP Tools (`penpot_mcp/server/mcp_server.py`)
```python
@mcp.tool()
def create_file(name: str, project_id: str) -> dict

@mcp.tool()
def create_project(name: str, team_id: str) -> dict
```

**Deliverable**: AI can create new files and projects to work in

---

### **Phase 2: Core Design Operations** (Week 2-3) ⭐ **PRIORITY**
*Enable AI to create and modify designs*

#### 2.1 Update File Infrastructure (`penpot_mcp/api/penpot_api.py`)

**Core Method:**
```python
def update_file(
    file_id: str,
    session_id: str,
    revn: int,
    changes: List[dict]
) -> dict
    """
    Update file with design changes.

    Args:
        file_id: File UUID
        session_id: Session UUID (generate new each update)
        revn: Revision number (increment from current)
        changes: Array of change operations
    """
```

**Change Builders - Shape Creation:**
```python
def create_add_obj_change(
    obj_id: str,
    page_id: str,
    obj_type: str,  # 'rect', 'circle', 'text', 'frame', etc.
    properties: dict,
    frame_id: Optional[str] = None
) -> dict
    """Build an add-obj change operation."""

def create_rectangle(
    x: float, y: float,
    width: float, height: float,
    fill_color: str = "#000000",
    **kwargs
) -> dict
    """Helper to create rectangle object."""

def create_circle(
    cx: float, cy: float,
    radius: float,
    fill_color: str = "#000000",
    **kwargs
) -> dict
    """Helper to create circle object."""

def create_text(
    x: float, y: float,
    content: str,
    font_size: int = 16,
    fill_color: str = "#000000",
    **kwargs
) -> dict
    """Helper to create text object."""

def create_frame(
    x: float, y: float,
    width: float, height: float,
    name: str = "Frame",
    **kwargs
) -> dict
    """Helper to create frame (artboard) object."""
```

**Change Builders - Object Modification:**
```python
def create_mod_obj_change(
    obj_id: str,
    operations: List[dict]
) -> dict
    """Build a mod-obj change operation."""

def create_set_operation(attr: str, value: Any) -> dict
    """Create a 'set' operation for single attribute."""

def create_assign_operation(values: dict) -> dict
    """Create an 'assign' operation for multiple attributes."""
```

**Change Builders - Object Deletion:**
```python
def create_del_obj_change(obj_id: str, page_id: str) -> dict
    """Build a del-obj change operation."""
```

#### 2.2 Session & Revision Management
```python
def get_file_session_info(file_id: str) -> dict
    """Get current session ID and revision number."""

def generate_session_id() -> str
    """Generate new session UUID."""
```

#### 2.3 MCP Design Tools (`penpot_mcp/server/mcp_server.py`)

**Basic Shape Tools:**
```python
@mcp.tool()
def add_rectangle(
    file_id: str,
    page_id: str,
    x: float, y: float,
    width: float, height: float,
    fill_color: str = "#000000",
    frame_id: Optional[str] = None
) -> dict
    """Add a rectangle to the design."""

@mcp.tool()
def add_circle(
    file_id: str,
    page_id: str,
    cx: float, cy: float,
    radius: float,
    fill_color: str = "#000000",
    frame_id: Optional[str] = None
) -> dict
    """Add a circle to the design."""

@mcp.tool()
def add_text(
    file_id: str,
    page_id: str,
    x: float, y: float,
    content: str,
    font_size: int = 16,
    fill_color: str = "#000000",
    frame_id: Optional[str] = None
) -> dict
    """Add text to the design."""

@mcp.tool()
def add_frame(
    file_id: str,
    page_id: str,
    x: float, y: float,
    width: float, height: float,
    name: str = "Frame"
) -> dict
    """Create a new frame (artboard)."""
```

**Modification Tools:**
```python
@mcp.tool()
def move_object(
    file_id: str,
    object_id: str,
    x: float,
    y: float
) -> dict
    """Move an object to new position."""

@mcp.tool()
def resize_object(
    file_id: str,
    object_id: str,
    width: float,
    height: float
) -> dict
    """Resize an object."""

@mcp.tool()
def change_object_color(
    file_id: str,
    object_id: str,
    fill_color: str
) -> dict
    """Change object fill color."""

@mcp.tool()
def rotate_object(
    file_id: str,
    object_id: str,
    rotation: float
) -> dict
    """Rotate an object (degrees)."""
```

**Deletion Tools:**
```python
@mcp.tool()
def delete_object(
    file_id: str,
    page_id: str,
    object_id: str
) -> dict
    """Delete an object from the design."""
```

**Batch Operations:**
```python
@mcp.tool()
def apply_design_changes(
    file_id: str,
    changes: List[dict]
) -> dict
    """Apply multiple design changes in one operation.

    This is the power tool that allows complex multi-step design
    operations to be atomic.
    """
```

**Deliverable**: AI can create shapes, modify them, and delete them

---

### **Phase 3: Advanced Design Features** (Week 4)
*Complex shapes and styling*

#### 3.1 Advanced Shapes (`penpot_mcp/api/penpot_api.py`)
```python
def create_path(points: List[dict], **kwargs) -> dict
    """Create custom vector path."""

def create_group(object_ids: List[str], **kwargs) -> dict
    """Group multiple objects."""

def create_boolean_shape(operation: str, shapes: List[str], **kwargs) -> dict
    """Create boolean shape (union, subtract, intersect, exclude)."""
```

#### 3.2 Advanced Styling
```python
def add_gradient_fill(
    start_color: str,
    end_color: str,
    gradient_type: str = "linear",
    **kwargs
) -> dict
    """Create gradient fill."""

def add_stroke(
    color: str,
    width: float,
    style: str = "solid",
    **kwargs
) -> dict
    """Add stroke/border to object."""

def add_shadow(
    color: str,
    offset_x: float,
    offset_y: float,
    blur: float,
    **kwargs
) -> dict
    """Add drop shadow effect."""
```

#### 3.3 MCP Advanced Tools
```python
@mcp.tool()
def create_component_from_objects(
    file_id: str,
    page_id: str,
    object_ids: List[str],
    name: str
) -> dict
    """Create a reusable component from selected objects."""

@mcp.tool()
def add_interaction(
    file_id: str,
    object_id: str,
    trigger: str,
    action: str,
    destination: str
) -> dict
    """Add interaction/prototype link to object."""
```

**Deliverable**: AI can create complex designs with advanced styling

---

### **Phase 4: Collaboration & Comments** (Week 5)
*Enable feedback and iteration*

#### 4.1 Comments API (`penpot_mcp/api/penpot_api.py`)
```python
def create_comment_thread(file_id: str, page_id: str, position: dict, content: str) -> dict
def create_comment(thread_id: str, content: str) -> dict
def get_comment_threads(file_id: str) -> list
def get_comments(thread_id: str) -> list
```

#### 4.2 MCP Tools
```python
@mcp.tool()
def add_design_comment(file_id: str, page_id: str, x: float, y: float, comment: str) -> dict
```

**Deliverable**: AI can add comments for review

---

### **Phase 5: Library & Components** (Week 6)
*Component system integration*

#### 5.1 Library API
```python
def link_file_to_library(file_id: str, library_id: str) -> dict
def get_file_libraries(file_id: str) -> list
def get_library_usage(file_id: str) -> dict
```

#### 5.2 MCP Tools
```python
@mcp.tool()
def import_component_from_library(file_id: str, library_id: str, component_id: str) -> dict
```

---

## Implementation Details

### Transit+JSON Handling for Design Operations

The `update-file` endpoint requires special Transit+JSON formatting:

```python
# Example update_file implementation
def update_file(self, file_id: str, session_id: str, revn: int, changes: List[dict]) -> dict:
    url = f"{self.base_url}/rpc/command/update-file"

    payload = {
        "~:id": f"~u{file_id}",
        "~:session-id": f"~u{session_id}",
        "~:revn": revn,
        "~:changes": self._convert_changes_to_transit(changes)
    }

    response = self._make_authenticated_request('post', url, json=payload, use_transit=True)
    return response.json()

def _convert_changes_to_transit(self, changes: List[dict]) -> List[dict]:
    """Convert change operations to Transit format."""
    transit_changes = []
    for change in changes:
        transit_change = {}
        for key, value in change.items():
            transit_key = f"~:{key}"
            # Handle UUID fields
            if key in ['id', 'pageId', 'frameId', 'parentId'] and isinstance(value, str):
                transit_value = f"~u{value}"
            # Handle keyword fields
            elif key == 'type':
                transit_value = f"~:{value}"
            else:
                transit_value = value
            transit_change[transit_key] = transit_value
        transit_changes.append(transit_change)
    return transit_changes
```

### Error Handling

```python
class DesignOperationError(PenpotAPIError):
    """Raised when design operation fails."""
    pass

class SessionConflictError(DesignOperationError):
    """Raised when session/revision conflicts occur."""
    pass
```

### Testing Strategy

#### Unit Tests (`tests/test_design_operations.py`)
```python
def test_create_rectangle_change()
def test_modify_object_change()
def test_delete_object_change()
def test_update_file_transit_format()
def test_session_management()
```

#### Integration Tests
```python
def test_create_and_modify_shape()
def test_complex_design_workflow()
def test_batch_operations()
```

#### MCP Tool Tests (`tests/test_mcp_design_tools.py`)
```python
def test_add_rectangle_tool()
def test_move_object_tool()
def test_design_workflow()
```

---

## Documentation Updates

### Update `CLAUDE.md`

Add section:
```markdown
## Design API Capabilities

### Creating Shapes
Use `add_rectangle`, `add_circle`, `add_text`, `add_frame` tools to create basic shapes.

### Modifying Objects
Use `move_object`, `resize_object`, `change_object_color`, `rotate_object` to modify existing shapes.

### Complex Operations
Use `apply_design_changes` for atomic multi-step design operations.

### Workflow Example
1. Create file → `create_file()`
2. Get first page ID from file
3. Add shapes → `add_rectangle()`, `add_text()`
4. Modify → `move_object()`, `change_object_color()`
5. Export → `export_object()`
```

### Add Design Examples (`examples/`)

```python
# examples/create_button_component.py
# Example: AI creates a button component
```

---

## Success Metrics

### Phase 1 (Foundation)
- [ ] Can create new files programmatically
- [ ] Can create new projects programmatically
- [ ] Tests pass for file/project CRUD

### Phase 2 (Core Design) ⭐
- [ ] Can add rectangles, circles, text, frames
- [ ] Can move, resize, recolor objects
- [ ] Can delete objects
- [ ] Can apply batch changes atomically
- [ ] Session and revision management works
- [ ] All design tools have MCP tool wrappers
- [ ] Transit+JSON conversion works correctly

### Phase 3 (Advanced)
- [ ] Can create custom paths
- [ ] Can create groups and boolean shapes
- [ ] Can apply gradients and shadows

### Phase 4 (Collaboration)
- [ ] Can add comments to designs

### Phase 5 (Components)
- [ ] Can link to libraries
- [ ] Can use components

---

## Timeline

- **Week 1**: Phase 1 - Foundation (file/project management)
- **Week 2-3**: Phase 2 - Core Design Operations ⭐ **CRITICAL PATH**
- **Week 4**: Phase 3 - Advanced Design Features
- **Week 5**: Phase 4 - Collaboration
- **Week 6**: Phase 5 - Components

**Total Estimated Time**: 6 weeks

---

## Risk Mitigation

### High Risk Items
1. **update-file complexity** - The change operation format may have undocumented nuances
   - *Mitigation*: Start with simple shapes, test extensively, inspect actual web app traffic

2. **Session/revision conflicts** - Multiple updates might conflict
   - *Mitigation*: Implement proper locking/retry logic

3. **Transit+JSON edge cases** - Format conversion might have issues
   - *Mitigation*: Extensive unit tests, validate against web app requests

### Medium Risk Items
1. **Shape property variations** - Different shapes may have unique required fields
   - *Mitigation*: Create comprehensive shape templates, refer to Penpot source code

2. **Coordinate systems** - Nested frames might have relative coordinates
   - *Mitigation*: Test nested object positioning thoroughly

---

## Next Steps

1. **Review this plan** - Confirm design priorities
2. **Start Phase 1** - Implement file/project creation
3. **Prototype Phase 2** - Build basic `update_file` with rectangle creation
4. **Validate approach** - Test against real Penpot instance
5. **Iterate** - Expand based on learnings
