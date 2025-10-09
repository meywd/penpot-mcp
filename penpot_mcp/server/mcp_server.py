"""
Main MCP server implementation for Penpot.

This module defines the MCP server with resources and tools for interacting with
the Penpot design platform.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Dict, List, Optional

from mcp.server.fastmcp import FastMCP, Image

from penpot_mcp.api.penpot_api import CloudFlareError, PenpotAPI, PenpotAPIError
from penpot_mcp.tools.penpot_tree import get_object_subtree_with_fields
from penpot_mcp.utils import config
from penpot_mcp.utils.cache import MemoryCache
from penpot_mcp.utils.http_server import ImageServer


class PenpotMCPServer:
    """Penpot MCP Server implementation."""

    def __init__(self, name="Penpot MCP Server", test_mode=False):
        """
        Initialize the Penpot MCP Server.

        Args:
            name: Server name
            test_mode: If True, certain features like HTTP server will be disabled for testing
        """
        # Initialize the MCP server
        self.mcp = FastMCP(name, instructions="""
I can help you generate code from your Penpot UI designs. My primary aim is to convert Penpot design components into functional code.

The typical workflow for code generation from Penpot designs is:

1. List your projects using 'list_projects' to find the project containing your designs
2. List files within the project using 'get_project_files' to locate the specific design file
3. Search for the target component within the file using 'search_object' to find the component you want to convert
4. Retrieve the Penpot tree schema using 'penpot_tree_schema' to understand which fields are available in the object tree
5. Get a cropped version of the object tree with a screenshot using 'get_object_tree' to see the component structure and visual representation
6. Get the full screenshot of the object using 'get_rendered_component' for detailed visual reference

For complex designs, you may need multiple iterations of 'get_object_tree' and 'get_rendered_component' due to LLM context limits.

Use the resources to access schemas, cached files, and rendered objects (screenshots) as needed.

Let me know which Penpot design you'd like to convert to code, and I'll guide you through the process!
""")

        # Initialize the Penpot API
        self.api = PenpotAPI(
            base_url=config.PENPOT_API_URL,
            debug=config.DEBUG
        )

        # Initialize memory cache
        self.file_cache = MemoryCache(ttl_seconds=600)  # 10 minutes

        # Storage for rendered component images
        self.rendered_components: Dict[str, Image] = {}
        
        # Initialize HTTP server for images if enabled and not in test mode
        self.image_server = None
        self.image_server_url = None
        
        # Detect if running in a test environment
        is_test_env = test_mode or 'pytest' in sys.modules
        
        if config.ENABLE_HTTP_SERVER and not is_test_env:
            try:
                self.image_server = ImageServer(
                    host=config.HTTP_SERVER_HOST,
                    port=config.HTTP_SERVER_PORT
                )
                # Start the server and get the URL with actual port assigned
                self.image_server_url = self.image_server.start()
                print(f"Image server started at {self.image_server_url}")
            except Exception as e:
                print(f"Warning: Failed to start image server: {str(e)}")

        # Register resources and tools
        if config.RESOURCES_AS_TOOLS:
            self._register_resources(resources_only=True)
            self._register_tools(include_resource_tools=True)
        else:
            self._register_resources(resources_only=False)
            self._register_tools(include_resource_tools=False)
    
    def _handle_api_error(self, e: Exception) -> dict:
        """Handle API errors and return user-friendly error messages."""
        if isinstance(e, CloudFlareError):
            return {
                "error": "CloudFlare Protection",
                "message": str(e),
                "error_type": "cloudflare_protection",
                "instructions": [
                    "Open your web browser and navigate to https://design.penpot.app",
                    "Log in to your Penpot account",
                    "Complete any CloudFlare human verification challenges if prompted",
                    "Once verified, try your request again"
                ]
            }
        elif isinstance(e, PenpotAPIError):
            return {
                "error": "Penpot API Error",
                "message": str(e),
                "error_type": "api_error",
                "status_code": getattr(e, 'status_code', None)
            }
        # Handle HTTPError with response body
        elif hasattr(e, 'response') and e.response is not None:
            error_dict = {
                "error": str(e),
                "status_code": e.response.status_code,
            }
            # Try to extract error details from response body (limited to 2000 chars)
            try:
                error_body = e.response.text
                if error_body:
                    # Limit response body to 2000 characters to avoid token limits
                    max_body_length = 2000
                    if len(error_body) > max_body_length:
                        error_dict["response_body"] = error_body[:max_body_length] + "... (truncated)"
                        error_dict["response_body_length"] = len(error_body)
                    else:
                        error_dict["response_body"] = error_body

                    # Try to parse as JSON for better formatting
                    try:
                        import json
                        error_json = json.loads(error_body)
                        # Only include JSON if it's reasonably sized
                        if len(str(error_json)) < 5000:
                            error_dict["response_json"] = error_json
                    except:
                        pass
            except:
                pass
            return error_dict
        else:
            return {"error": str(e)}

    def _register_resources(self, resources_only=False):
        """Register all MCP resources. If resources_only is True, only register server://info as a resource."""
        @self.mcp.resource("server://info")
        def server_info() -> dict:
            """Provide information about the server."""
            info = {
                "status": "online",
                "name": "Penpot MCP Server",
                "description": "Model Context Provider for Penpot",
                "api_url": config.PENPOT_API_URL
            }
            
            if self.image_server and self.image_server.is_running:
                info["image_server"] = self.image_server_url
                
            return info
        if resources_only:
            return
        @self.mcp.resource("penpot://schema", mime_type="application/schema+json")
        def penpot_schema() -> dict:
            """Provide the Penpot API schema as JSON."""
            schema_path = os.path.join(config.RESOURCES_PATH, 'penpot-schema.json')
            try:
                with open(schema_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                return {"error": f"Failed to load schema: {str(e)}"}
        @self.mcp.resource("penpot://tree-schema", mime_type="application/schema+json")
        def penpot_tree_schema() -> dict:
            """Provide the Penpot object tree schema as JSON."""
            schema_path = os.path.join(config.RESOURCES_PATH, 'penpot-tree-schema.json')
            try:
                with open(schema_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                return {"error": f"Failed to load tree schema: {str(e)}"}
        @self.mcp.resource("rendered-component://{component_id}", mime_type="image/png")
        def get_rendered_component(component_id: str) -> Image:
            """Return a rendered component image by its ID."""
            if component_id in self.rendered_components:
                return self.rendered_components[component_id]
            raise Exception(f"Component with ID {component_id} not found")
        @self.mcp.resource("penpot://cached-files")
        def get_cached_files() -> dict:
            """List all files currently stored in the cache."""
            return self.file_cache.get_all_cached_files()

    def _register_tools(self, include_resource_tools=False):
        """Register all MCP tools. If include_resource_tools is True, also register resource logic as tools."""
        @self.mcp.tool()
        def list_projects() -> dict:
            """Retrieve a list of all available Penpot projects."""
            try:
                projects = self.api.list_projects()
                return {"projects": projects}
            except Exception as e:
                return self._handle_api_error(e)
        @self.mcp.tool()
        def get_project_files(project_id: str) -> dict:
            """Get all files contained within a specific Penpot project.
            
            Args:
                project_id: The ID of the Penpot project
            """
            try:
                files = self.api.get_project_files(project_id)
                return {"files": files}
            except Exception as e:
                return self._handle_api_error(e)
        def get_cached_file(file_id: str) -> dict:
            """Internal helper to retrieve a file, using cache if available.
            
            Args:
                file_id: The ID of the Penpot file
            """
            cached_data = self.file_cache.get(file_id)
            if cached_data is not None:
                return cached_data
            try:
                file_data = self.api.get_file(file_id=file_id)
                self.file_cache.set(file_id, file_data)
                return file_data
            except Exception as e:
                return self._handle_api_error(e)
        @self.mcp.tool()
        def get_file(file_id: str) -> dict:
            """Retrieve a Penpot file by its ID and cache it. Don't use this tool for code generation, use 'get_object_tree' instead.
            
            Args:
                file_id: The ID of the Penpot file
            """
            try:
                file_data = self.api.get_file(file_id=file_id)
                self.file_cache.set(file_id, file_data)
                return file_data
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def create_file(
            name: str,
            project_id: str,
            is_shared: bool = False
        ) -> dict:
            """
            Create a new Penpot design file.
            
            Args:
                name: Name for the new file
                project_id: ID of the project to create the file in
                is_shared: Whether the file should be shared (default: False)
            
            Returns:
                Created file information including file ID
            
            Example:
                create_file(name="Login Screen", project_id="abc-123")
            """
            try:
                result = self.api.create_file(name, project_id, is_shared)
                # Cache the newly created file
                self.file_cache.set(result['id'], result)
                return result
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def delete_file(file_id: str) -> dict:
            """
            Delete a Penpot file.
            
            Args:
                file_id: ID of the file to delete
            
            Returns:
                Deletion confirmation
            
            Example:
                delete_file(file_id="abc-123")
            """
            try:
                result = self.api.delete_file(file_id)
                # Remove from cache if present
                if file_id in self.file_cache._cache:
                    del self.file_cache._cache[file_id]
                return result
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def rename_file(file_id: str, name: str) -> dict:
            """
            Rename a Penpot file.
            
            Args:
                file_id: ID of the file to rename
                name: New name for the file
            
            Returns:
                Updated file information
            
            Example:
                rename_file(file_id="abc-123", name="Updated Design")
            """
            try:
                result = self.api.rename_file(file_id, name)
                # Update cache if present
                if file_id in self.file_cache._cache:
                    self.file_cache._cache[file_id]['data']['name'] = name
                return result
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def list_teams() -> dict:
            """
            List all teams the user has access to.
            
            Returns:
                Dictionary containing list of teams
            
            Example:
                list_teams()
            """
            try:
                teams = self.api.get_teams()
                return {"teams": teams}
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def create_project(name: str, team_id: str) -> dict:
            """
            Create a new project within a team.
            
            Args:
                name: Name for the new project
                team_id: ID of the team to create the project in
            
            Returns:
                Created project information including project ID
            
            Example:
                create_project(name="Mobile App", team_id="team-123")
            """
            try:
                result = self.api.create_project(name, team_id)
                return result
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def rename_project(project_id: str, name: str) -> dict:
            """
            Rename a project.
            
            Args:
                project_id: ID of the project to rename
                name: New name for the project
            
            Returns:
                Updated project information
            
            Example:
                rename_project(project_id="proj-123", name="Redesign 2024")
            """
            try:
                result = self.api.rename_project(project_id, name)
                return result
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def delete_project(project_id: str) -> dict:
            """
            Delete a project and all its files.
            
            WARNING: This is a permanent deletion operation!
            
            Args:
                project_id: ID of the project to delete
            
            Returns:
                Deletion confirmation
            
            Example:
                delete_project(project_id="proj-123")
            """
            try:
                result = self.api.delete_project(project_id)
                return result
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def export_object(
                file_id: str,
                page_id: str,
                object_id: str,
                export_type: str = "png",
                scale: int = 1) -> Image:
            """Export a Penpot design object as an image.
            
            Args:
                file_id: The ID of the Penpot file
                page_id: The ID of the page containing the object
                object_id: The ID of the object to export
                export_type: Image format (png, svg, etc.)
                scale: Scale factor for the exported image
            """
            temp_filename = None
            try:
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_filename = os.path.join(temp_dir, f"{object_id}.{export_type}")
                output_path = self.api.export_and_download(
                    file_id=file_id,
                    page_id=page_id,
                    object_id=object_id,
                    export_type=export_type,
                    scale=scale,
                    save_to_file=temp_filename
                )
                with open(output_path, "rb") as f:
                    file_content = f.read()
                    
                image = Image(data=file_content, format=export_type)
                
                # If HTTP server is enabled, add the image to the server
                if self.image_server and self.image_server.is_running:
                    image_id = hashlib.md5(f"{file_id}:{page_id}:{object_id}".encode()).hexdigest()
                    # Use the current image_server_url to ensure the correct port
                    image_url = self.image_server.add_image(image_id, file_content, export_type)
                    # Add HTTP URL to the image metadata
                    image.http_url = image_url
                    
                return image
            except Exception as e:
                if isinstance(e, CloudFlareError):
                    raise Exception(f"CloudFlare Protection: {str(e)}")
                else:
                    raise Exception(f"Export failed: {str(e)}")
            finally:
                if temp_filename and os.path.exists(temp_filename):
                    try:
                        os.remove(temp_filename)
                    except Exception as e:
                        print(f"Warning: Failed to delete temporary file {temp_filename}: {str(e)}")
        
        @self.mcp.tool()
        def move_object(
            file_id: str,
            object_id: str,
            x: float,
            y: float
        ) -> dict:
            """
            Move an object to a new position.

            Args:
                file_id: ID of the file
                object_id: ID of the object to move
                x: New X coordinate
                y: New Y coordinate

            Returns:
                Success result with new revision

            Example:
                move_object(file_id="file-123", object_id="obj-456", x=200, y=150)
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    # Create modification operations
                    ops = [
                        self.api.create_set_operation('x', x),
                        self.api.create_set_operation('y', y)
                    ]

                    # Create modify change
                    change = self.api.create_mod_obj_change(object_id, ops)

                    # Apply change
                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def resize_object(
            file_id: str,
            object_id: str,
            width: float,
            height: float
        ) -> dict:
            """
            Resize an object.

            Args:
                file_id: ID of the file
                object_id: ID of the object to resize
                width: New width
                height: New height

            Returns:
                Success result

            Example:
                resize_object(file_id="file-123", object_id="obj-456", width=300, height=200)
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    ops = [
                        self.api.create_set_operation('width', width),
                        self.api.create_set_operation('height', height)
                    ]

                    change = self.api.create_mod_obj_change(object_id, ops)
                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def change_object_color(
            file_id: str,
            object_id: str,
            fill_color: str,
            fill_opacity: float = 1.0
        ) -> dict:
            """
            Change the fill color of an object.

            Args:
                file_id: ID of the file
                object_id: ID of the object
                fill_color: New fill color (hex format, e.g., #FF0000)
                fill_opacity: Fill opacity (0.0 to 1.0)

            Returns:
                Success result

            Example:
                change_object_color(file_id="file-123", object_id="obj-456", fill_color="#FF0000")
            """
            try:
                # First, get the file to check object type
                file_data = self.api.get_file(file_id)
                pages_index = file_data.get('data', {}).get('pagesIndex', {})

                # Find the object in the pages
                obj = None
                for page_id, page_data in pages_index.items():
                    objects = page_data.get('objects', {})
                    if object_id in objects:
                        obj = objects[object_id]
                        break

                if not obj:
                    return {
                        "success": False,
                        "error": f"Object {object_id} not found in file"
                    }

                obj_type = obj.get('type')

                with self.api.editing_session(file_id) as (session_id, revn):
                    # Use kebab-case as required by Penpot API
                    fills = [{
                        'fill-color': fill_color,
                        'fill-opacity': fill_opacity
                    }]

                    ops = []

                    # For text objects, update the content structure
                    if obj_type == 'text':
                        # Get existing content structure
                        content = obj.get('content', {})

                        # Update fills in content structure at all levels
                        if 'children' in content:
                            for paragraph_set in content['children']:
                                if 'children' in paragraph_set:
                                    for paragraph in paragraph_set['children']:
                                        # Set fills at paragraph level
                                        paragraph['fills'] = fills
                                        if 'children' in paragraph:
                                            for text_node in paragraph['children']:
                                                # Set fills at text node level
                                                text_node['fills'] = fills

                        # Update both content and fills
                        ops.append(self.api.create_set_operation('content', content))
                        ops.append(self.api.create_set_operation('fills', fills))
                    else:
                        # For non-text objects, just update fills
                        ops.append(self.api.create_set_operation('fills', fills))

                    change = self.api.create_mod_obj_change(object_id, ops)
                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def rotate_object(
            file_id: str,
            object_id: str,
            rotation: float
        ) -> dict:
            """
            Rotate an object.

            Args:
                file_id: ID of the file
                object_id: ID of the object
                rotation: Rotation angle in degrees (0-360)

            Returns:
                Success result

            Example:
                rotate_object(file_id="file-123", object_id="obj-456", rotation=45)
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    ops = [
                        self.api.create_set_operation('rotation', rotation)
                    ]

                    change = self.api.create_mod_obj_change(object_id, ops)
                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def delete_object(
            file_id: str,
            page_id: str,
            object_id: str
        ) -> dict:
            """
            Delete an object from the design.

            Args:
                file_id: ID of the file
                page_id: ID of the page containing the object
                object_id: ID of the object to delete

            Returns:
                Success result

            Example:
                delete_object(file_id="file-123", page_id="page-456", object_id="obj-789")
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    # Create delete change
                    change = self.api.create_del_obj_change(object_id, page_id)

                    # Apply change
                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "deletedObjectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def apply_design_changes(
            file_id: str,
            changes: List[dict]
        ) -> dict:
            """
            Apply multiple design changes atomically.

            This is a power tool for complex multi-step operations.

            Args:
                file_id: ID of the file
                changes: List of change operations (from change builders)

            Returns:
                Success result

            Example:
                changes = [
                    {"type": "add-obj", "id": "obj-1", "pageId": "page-1", "obj": {...}},
                    {"type": "mod-obj", "id": "obj-2", "operations": [...]},
                    {"type": "del-obj", "id": "obj-3", "pageId": "page-1"}
                ]
                apply_design_changes(file_id="file-123", changes=changes)
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    result = self.api.update_file(file_id, session_id, revn, changes)

                    return {
                        "success": True,
                        "revn": result.get('revn'),
                        "changesApplied": len(changes)
                    }
            except Exception as e:
                return self._handle_api_error(e)
        
        @self.mcp.tool()
        def get_object_tree(
            file_id: str, 
            object_id: str, 
            fields: List[str],
            depth: int = -1,
            format: str = "json"
        ) -> dict:
            """Get the object tree structure for a Penpot object ("tree" field) with rendered screenshot image of the object ("image.mcp_uri" field).
            Args:
                file_id: The ID of the Penpot file
                object_id: The ID of the object to retrieve
                fields: Specific fields to include in the tree (call "penpot_tree_schema" resource/tool for available fields)
                depth: How deep to traverse the object tree (-1 for full depth)
                format: Output format ('json' or 'yaml')
            """
            try:
                file_data = get_cached_file(file_id)
                if "error" in file_data:
                    return file_data
                result = get_object_subtree_with_fields(
                    file_data, 
                    object_id, 
                    include_fields=fields,
                    depth=depth
                )
                if "error" in result:
                    return result
                simplified_tree = result["tree"]
                page_id = result["page_id"]
                final_result = {"tree": simplified_tree}
                
                try:
                    image = export_object(
                        file_id=file_id,
                        page_id=page_id,
                        object_id=object_id
                    )
                    image_id = hashlib.md5(f"{file_id}:{object_id}".encode()).hexdigest()
                    self.rendered_components[image_id] = image
                    
                    # Image URI preferences:
                    # 1. HTTP server URL if available
                    # 2. Fallback to MCP resource URI
                    image_uri = f"render_component://{image_id}"
                    if hasattr(image, 'http_url'):
                        final_result["image"] = {
                            "uri": image.http_url,
                            "mcp_uri": image_uri,
                            "format": image.format if hasattr(image, 'format') else "png"
                        }
                    else:
                        final_result["image"] = {
                            "uri": image_uri,
                            "format": image.format if hasattr(image, 'format') else "png"
                        }
                except Exception as e:
                    final_result["image_error"] = str(e)
                if format.lower() == "yaml":
                    try:
                        import yaml
                        yaml_result = yaml.dump(final_result, default_flow_style=False, sort_keys=False)
                        return {"yaml_result": yaml_result}
                    except ImportError:
                        return {"format_error": "YAML format requested but PyYAML package is not installed"}
                    except Exception as e:
                        return {"format_error": f"Error formatting as YAML: {str(e)}"}
                return final_result
            except Exception as e:
                return self._handle_api_error(e)
        @self.mcp.tool()
        def search_object(file_id: str, query: str) -> dict:
            """Search for objects within a Penpot file by name.
            
            Args:
                file_id: The ID of the Penpot file to search in
                query: Search string (supports regex patterns)
            """
            try:
                file_data = get_cached_file(file_id)
                if "error" in file_data:
                    return file_data
                pattern = re.compile(query, re.IGNORECASE)
                matches = []
                data = file_data.get('data', {})
                for page_id, page_data in data.get('pagesIndex', {}).items():
                    page_name = page_data.get('name', 'Unnamed')
                    for obj_id, obj_data in page_data.get('objects', {}).items():
                        obj_name = obj_data.get('name', '')
                        if pattern.search(obj_name):
                            matches.append({
                                'id': obj_id,
                                'name': obj_name,
                                'page_id': page_id,
                                'page_name': page_name,
                                'object_type': obj_data.get('type', 'unknown')
                            })
                return {'objects': matches}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def add_rectangle(
            file_id: str,
            page_id: str,
            x: float,
            y: float,
            width: float,
            height: float,
            name: str = "Rectangle",
            fill_color: str = "#000000",
            stroke_color: Optional[str] = None,
            stroke_width: Optional[float] = None,
            frame_id: Optional[str] = None
        ) -> dict:
            """
            Add a rectangle to the design.

            Args:
                file_id: ID of the file to add to
                page_id: ID of the page to add to
                x: X coordinate
                y: Y coordinate
                width: Rectangle width
                height: Rectangle height
                name: Name for the rectangle
                fill_color: Fill color (hex format, e.g., #FF0000)
                stroke_color: Optional border color
                stroke_width: Optional border width
                frame_id: Optional parent frame ID

            Returns:
                Result with created object ID

            Example:
                add_rectangle(
                    file_id="file-123",
                    page_id="page-456",
                    x=100, y=100,
                    width=200, height=150,
                    fill_color="#FF0000"
                )
            """
            try:
                # Generate ID for new object
                obj_id = self.api.generate_session_id()

                # Get session and revision
                with self.api.editing_session(file_id) as (session_id, revn):
                    # Create rectangle object
                    rect = self.api.create_rectangle(
                        x, y, width, height,
                        name=name,
                        fill_color=fill_color,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width
                    )

                    # Create add change
                    change = self.api.create_add_obj_change(
                        obj_id, page_id, rect, frame_id=frame_id
                    )

                    # Apply change
                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": obj_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def add_circle(
            file_id: str,
            page_id: str,
            cx: float,
            cy: float,
            radius: float,
            name: str = "Circle",
            fill_color: str = "#000000",
            stroke_color: Optional[str] = None,
            stroke_width: Optional[float] = None,
            frame_id: Optional[str] = None
        ) -> dict:
            """
            Add a circle to the design.

            Args:
                file_id: ID of the file
                page_id: ID of the page
                cx: Center X coordinate
                cy: Center Y coordinate
                radius: Circle radius
                name: Name for the circle
                fill_color: Fill color
                stroke_color: Optional border color
                stroke_width: Optional border width
                frame_id: Optional parent frame ID

            Returns:
                Result with created object ID
            """
            try:
                obj_id = self.api.generate_session_id()

                with self.api.editing_session(file_id) as (session_id, revn):
                    circle = self.api.create_circle(
                        cx, cy, radius,
                        name=name,
                        fill_color=fill_color,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width
                    )

                    change = self.api.create_add_obj_change(
                        obj_id, page_id, circle, frame_id=frame_id
                    )

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": obj_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def add_text(
            file_id: str,
            page_id: str,
            x: float,
            y: float,
            content: str,
            name: str = "Text",
            font_size: int = 16,
            fill_color: str = "#000000",
            font_family: str = "Work Sans",
            frame_id: Optional[str] = None
        ) -> dict:
            """
            Add text to the design.

            Args:
                file_id: ID of the file
                page_id: ID of the page
                x: X coordinate
                y: Y coordinate
                content: Text content
                name: Name for the text object
                font_size: Font size in pixels
                fill_color: Text color
                font_family: Font family name
                frame_id: Optional parent frame ID

            Returns:
                Result with created object ID
            """
            try:
                obj_id = self.api.generate_session_id()

                with self.api.editing_session(file_id) as (session_id, revn):
                    text = self.api.create_text(
                        x, y, content,
                        name=name,
                        font_size=font_size,
                        fill_color=fill_color,
                        font_family=font_family
                    )

                    change = self.api.create_add_obj_change(
                        obj_id, page_id, text, frame_id=frame_id
                    )

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": obj_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def add_frame(
            file_id: str,
            page_id: str,
            x: float,
            y: float,
            width: float,
            height: float,
            name: str = "Frame",
            background_color: Optional[str] = None
        ) -> dict:
            """
            Create a new frame (artboard) in the design.

            Frames act as containers for other objects.

            Args:
                file_id: ID of the file
                page_id: ID of the page
                x: X coordinate
                y: Y coordinate
                width: Frame width
                height: Frame height
                name: Name for the frame
                background_color: Optional background color

            Returns:
                Result with created frame ID
            """
            try:
                obj_id = self.api.generate_session_id()

                with self.api.editing_session(file_id) as (session_id, revn):
                    frame = self.api.create_frame(
                        x, y, width, height,
                        name=name,
                        background_color=background_color
                    )

                    change = self.api.create_add_obj_change(
                        obj_id, page_id, frame
                    )

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "frameId": obj_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        # ========== ADVANCED SHAPE TOOLS ==========

        @self.mcp.tool()
        def create_path(
            file_id: str,
            page_id: str,
            points: List[dict],
            closed: bool = True,
            fill_color: Optional[str] = None,
            stroke_color: Optional[str] = None,
            stroke_width: float = 1.0,
            name: str = "Path",
            frame_id: Optional[str] = None
        ) -> dict:
            """
            Create a custom vector path.

            Args:
                file_id: ID of the Penpot file
                page_id: ID of the page to add path to
                points: List of point dictionaries with x, y coordinates
                        Example: [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 50, "y": 100}]
                closed: Whether the path should be closed (default: True)
                fill_color: Fill color in hex format (optional)
                stroke_color: Stroke color in hex format (optional)
                stroke_width: Stroke width in pixels (default: 1.0)
                name: Path name (default: "Path")
                frame_id: Optional parent frame ID

            Returns:
                Updated file information with new path object

            Example:
                create_path(
                    file_id="abc-123",
                    page_id="page-1",
                    points=[{"x": 50, "y": 0}, {"x": 100, "y": 100}, {"x": 0, "y": 100}],
                    fill_color="#ff0000"
                )
            """
            try:
                obj_id = self.api.generate_session_id()

                with self.api.editing_session(file_id) as (session_id, revn):
                    path_obj = self.api.create_path(
                        points=points,
                        closed=closed,
                        fill_color=fill_color,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width,
                        name=name
                    )

                    change = self.api.create_add_obj_change(
                        obj_id, page_id, path_obj, frame_id=frame_id
                    )

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": obj_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def create_group(
            file_id: str,
            page_id: str,
            name: str = "Group",
            frame_id: Optional[str] = None
        ) -> dict:
            """
            Create a group for organizing multiple objects.

            Args:
                file_id: ID of the Penpot file
                page_id: ID of the page to add group to
                name: Group name (default: "Group")
                frame_id: Optional parent frame ID

            Returns:
                Updated file information with new group ID

            Example:
                create_group(
                    file_id="abc-123",
                    page_id="page-1",
                    name="Button Components"
                )
            """
            try:
                obj_id = self.api.generate_session_id()

                with self.api.editing_session(file_id) as (session_id, revn):
                    group_obj = self.api.create_group(name=name)

                    change = self.api.create_add_obj_change(
                        obj_id, page_id, group_obj, frame_id=frame_id
                    )

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "groupId": obj_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def add_object_to_group(
            file_id: str,
            object_id: str,
            group_id: str
        ) -> dict:
            """
            Add an existing object to a group.

            Args:
                file_id: ID of the Penpot file
                object_id: ID of the object to add to group
                group_id: ID of the group

            Returns:
                Updated file information

            Example:
                add_object_to_group(
                    file_id="abc-123",
                    object_id="rect-1",
                    group_id="group-1"
                )
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    parent_op = self.api.create_parent_operation(group_id)
                    change = self.api.create_mod_obj_change(object_id, [parent_op])

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "groupId": group_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def create_boolean_shape(
            file_id: str,
            page_id: str,
            operation: str,
            shape_ids: List[str],
            name: str = "Boolean",
            frame_id: Optional[str] = None
        ) -> dict:
            """
            Create a boolean shape from multiple shapes.

            Args:
                file_id: ID of the Penpot file
                page_id: ID of the page
                operation: Boolean operation ('union', 'difference', 'intersection', 'exclusion')
                shape_ids: List of shape IDs to combine
                name: Boolean shape name (default: "Boolean")
                frame_id: Optional parent frame ID

            Returns:
                Updated file information with new boolean shape

            Example:
                create_boolean_shape(
                    file_id="abc-123",
                    page_id="page-1",
                    operation="union",
                    shape_ids=["circle-1", "circle-2"]
                )
            """
            try:
                obj_id = self.api.generate_session_id()

                with self.api.editing_session(file_id) as (session_id, revn):
                    bool_obj = self.api.create_boolean_shape(
                        operation=operation,
                        shapes=shape_ids,
                        name=name
                    )

                    change = self.api.create_add_obj_change(
                        obj_id, page_id, bool_obj, frame_id=frame_id
                    )

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": obj_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        # ========== ADVANCED STYLING TOOLS ==========

        @self.mcp.tool()
        def apply_gradient(
            file_id: str,
            object_id: str,
            gradient_type: str,
            start_color: str,
            end_color: str,
            angle: float = 0.0
        ) -> dict:
            """
            Apply a gradient fill to an object.

            Args:
                file_id: ID of the Penpot file
                object_id: ID of the object to apply gradient to
                gradient_type: Type of gradient ('linear' or 'radial')
                start_color: Start color in hex format
                end_color: End color in hex format
                angle: Gradient angle in degrees (0-360, for linear gradients)

            Returns:
                Updated file information

            Example:
                apply_gradient(
                    file_id="abc-123",
                    object_id="rect-1",
                    gradient_type="linear",
                    start_color="#ff0000",
                    end_color="#0000ff",
                    angle=45
                )
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    # Convert angle to start/end coordinates
                    import math
                    rad = math.radians(angle)
                    # For linear gradients, angle determines direction
                    # 0° = left to right, 90° = top to bottom
                    start_x = 0.5 - 0.5 * math.cos(rad)
                    start_y = 0.5 - 0.5 * math.sin(rad)
                    end_x = 0.5 + 0.5 * math.cos(rad)
                    end_y = 0.5 + 0.5 * math.sin(rad)

                    gradient = self.api.create_gradient_fill(
                        gradient_type=gradient_type,
                        start_color=start_color,
                        end_color=end_color,
                        start_x=start_x,
                        start_y=start_y,
                        end_x=end_x,
                        end_y=end_y
                    )

                    fill_op = self.api.create_fill_operation([gradient])
                    change = self.api.create_mod_obj_change(object_id, [fill_op])

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def add_stroke(
            file_id: str,
            object_id: str,
            color: str,
            width: float = 1.0,
            style: str = "solid"
        ) -> dict:
            """
            Add a stroke (border) to an object.

            Args:
                file_id: ID of the Penpot file
                object_id: ID of the object
                color: Stroke color in hex format
                width: Stroke width in pixels (default: 1.0)
                style: Stroke style ('solid', 'dashed', 'dotted', 'mixed')

            Returns:
                Updated file information

            Example:
                add_stroke(
                    file_id="abc-123",
                    object_id="rect-1",
                    color="#000000",
                    width=2.0,
                    style="solid"
                )
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    stroke = self.api.create_stroke(
                        color=color,
                        width=width,
                        style=style
                    )

                    stroke_op = self.api.create_stroke_operation([stroke])
                    change = self.api.create_mod_obj_change(object_id, [stroke_op])

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def add_shadow(
            file_id: str,
            object_id: str,
            color: str,
            offset_x: float,
            offset_y: float,
            blur: float,
            spread: float = 0.0
        ) -> dict:
            """
            Add a drop shadow to an object.

            Args:
                file_id: ID of the Penpot file
                object_id: ID of the object
                color: Shadow color in hex format with alpha (e.g., "#00000080")
                offset_x: Horizontal offset in pixels
                offset_y: Vertical offset in pixels
                blur: Blur radius in pixels
                spread: Spread radius in pixels (default: 0.0)

            Returns:
                Updated file information

            Example:
                add_shadow(
                    file_id="abc-123",
                    object_id="rect-1",
                    color="#00000080",
                    offset_x=2,
                    offset_y=2,
                    blur=4
                )
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    shadow = self.api.create_shadow(
                        color=color,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        blur=blur,
                        spread=spread
                    )

                    shadow_op = self.api.create_shadow_operation([shadow])
                    change = self.api.create_mod_obj_change(object_id, [shadow_op])

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def apply_blur(
            file_id: str,
            object_id: str,
            blur_amount: float,
            blur_type: str = "layer-blur"
        ) -> dict:
            """
            Apply a blur effect to an object.

            Args:
                file_id: ID of the Penpot file
                object_id: ID of the object
                blur_amount: Blur amount in pixels
                blur_type: Type of blur ('layer-blur' or 'background-blur')

            Returns:
                Updated file information

            Example:
                apply_blur(file_id="abc-123", object_id="rect-1", blur_amount=10)
            """
            try:
                with self.api.editing_session(file_id) as (session_id, revn):
                    blur = self.api.create_blur(
                        blur_type=blur_type,
                        value=blur_amount
                    )

                    blur_op = self.api.create_blur_operation(blur)
                    change = self.api.create_mod_obj_change(object_id, [blur_op])

                    result = self.api.update_file(file_id, session_id, revn, [change])

                    return {
                        "success": True,
                        "objectId": object_id,
                        "revn": result.get('revn')
                    }
            except Exception as e:
                return self._handle_api_error(e)

        # ========== COMMENT & COLLABORATION TOOLS ==========

        @self.mcp.tool()
        def add_design_comment(
            file_id: str,
            page_id: str,
            x: float,
            y: float,
            comment: str,
            frame_id: Optional[str] = None
        ) -> dict:
            """
            Add a comment to a design at a specific location.

            Args:
                file_id: ID of the Penpot file
                page_id: ID of the page
                x: X position for comment marker
                y: Y position for comment marker
                comment: Comment text
                frame_id: Optional frame ID if commenting within a frame

            Returns:
                Created comment thread information

            Example:
                add_design_comment(
                    file_id="abc-123",
                    page_id="page-1",
                    x=150, y=200,
                    comment="This heading should use our brand font"
                )
            """
            try:
                thread = self.api.create_comment_thread(
                    file_id, page_id, x, y, comment, frame_id
                )
                return {"success": True, "thread_id": thread.get('id'), "thread": thread}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def reply_to_comment(
            thread_id: str,
            reply: str
        ) -> dict:
            """
            Reply to an existing comment thread.

            Args:
                thread_id: ID of the comment thread
                reply: Reply text

            Returns:
                Created comment information

            Example:
                reply_to_comment(
                    thread_id="thread-123",
                    reply="Done! Updated the font to Roboto Bold"
                )
            """
            try:
                comment = self.api.add_comment(thread_id, reply)
                return {"success": True, "comment_id": comment.get('id'), "comment": comment}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def get_file_comments(
            file_id: str,
            page_id: Optional[str] = None
        ) -> dict:
            """
            Get all comment threads for a file or specific page.

            Args:
                file_id: ID of the Penpot file
                page_id: Optional ID of specific page

            Returns:
                List of comment threads with their positions and content

            Example:
                get_file_comments(file_id="abc-123", page_id="page-1")
            """
            try:
                threads = self.api.get_comment_threads(file_id, page_id)
                return {"success": True, "count": len(threads), "threads": threads}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def resolve_comment_thread(
            thread_id: str
        ) -> dict:
            """
            Mark a comment thread as resolved.

            Args:
                thread_id: ID of the comment thread

            Returns:
                Updated thread information

            Example:
                resolve_comment_thread(thread_id="thread-123")
            """
            try:
                thread = self.api.update_comment_thread_status(thread_id, is_resolved=True)
                return {"success": True, "thread": thread}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def link_library(
            file_id: str,
            library_id: str
        ) -> dict:
            """
            Link a file to a component library.

            Args:
                file_id: ID of the file
                library_id: ID of the library file to link

            Returns:
                Success confirmation

            Example:
                link_library(file_id="abc-123", library_id="lib-456")
            """
            try:
                result = self.api.link_file_to_library(file_id, library_id)
                return {"success": True, "result": result}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def list_library_components(
            library_id: str
        ) -> dict:
            """
            List all components available in a library.

            Args:
                library_id: ID of the library file

            Returns:
                List of components with their names and IDs

            Example:
                list_library_components(library_id="lib-456")
            """
            try:
                components = self.api.get_library_components(library_id)
                return {
                    "success": True,
                    "count": len(components),
                    "components": components
                }
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def import_component(
            file_id: str,
            page_id: str,
            library_id: str,
            component_id: str,
            x: float,
            y: float,
            frame_id: Optional[str] = None
        ) -> dict:
            """
            Import a component from a library into the design.

            Args:
                file_id: ID of the target file
                page_id: ID of the target page
                library_id: ID of the library file
                component_id: ID of the component to import
                x: X position for the component instance
                y: Y position for the component instance
                frame_id: Optional parent frame ID

            Returns:
                Created component instance information

            Example:
                import_component(
                    file_id="abc-123",
                    page_id="page-1",
                    library_id="lib-456",
                    component_id="button-primary",
                    x=100, y=100
                )
            """
            try:
                result = self.api.instantiate_component(
                    file_id, page_id, library_id, component_id, x, y, frame_id
                )
                return {"success": True, "file": result}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def sync_library(
            file_id: str,
            library_id: str
        ) -> dict:
            """
            Synchronize component instances with their library.

            Updates all instances of components from the library to match
            the current library version.

            Args:
                file_id: ID of the file
                library_id: ID of the library to sync

            Returns:
                Sync result with count of updated instances

            Example:
                sync_library(file_id="abc-123", library_id="lib-456")
            """
            try:
                result = self.api.sync_file_library(file_id, library_id)
                return {"success": True, "result": result}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def publish_as_library(
            file_id: str
        ) -> dict:
            """
            Publish a file as a shared component library.

            Args:
                file_id: ID of the file to publish

            Returns:
                Updated file information

            Example:
                publish_as_library(file_id="abc-123")
            """
            try:
                result = self.api.publish_library(file_id, publish=True)
                return {"success": True, "file": result}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def unpublish_library(
            file_id: str
        ) -> dict:
            """
            Unpublish a file as a library.

            Removes the library status from a file, making its components
            no longer available for use in other files.

            Args:
                file_id: ID of the file to unpublish

            Returns:
                Updated file information

            Example:
                unpublish_library(file_id="abc-123")
            """
            try:
                result = self.api.publish_library(file_id, publish=False)
                return {"success": True, "file": result}
            except Exception as e:
                return self._handle_api_error(e)

        @self.mcp.tool()
        def get_file_libraries(
            file_id: str
        ) -> dict:
            """
            Get all libraries linked to a file.

            Returns a list of all component libraries that are currently
            linked to the specified file, allowing you to discover which
            libraries' components are available for use.

            Args:
                file_id: ID of the file

            Returns:
                List of linked libraries with their information

            Example:
                get_file_libraries(file_id="abc-123")
            """
            try:
                libraries = self.api.get_file_libraries(file_id)
                return {
                    "success": True,
                    "count": len(libraries),
                    "libraries": libraries
                }
            except Exception as e:
                return self._handle_api_error(e)

        if include_resource_tools:
            @self.mcp.tool()
            def penpot_schema() -> dict:
                """Provide the Penpot API schema as JSON."""
                schema_path = os.path.join(config.RESOURCES_PATH, 'penpot-schema.json')
                try:
                    with open(schema_path, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    return {"error": f"Failed to load schema: {str(e)}"}
            @self.mcp.tool()
            def penpot_tree_schema() -> dict:
                """Provide the Penpot object tree schema as JSON."""
                schema_path = os.path.join(config.RESOURCES_PATH, 'penpot-tree-schema.json')
                try:
                    with open(schema_path, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    return {"error": f"Failed to load tree schema: {str(e)}"}
            @self.mcp.tool()
            def get_rendered_component(component_id: str) -> Image:
                """Return a rendered component image by its ID."""
                if component_id in self.rendered_components:
                    return self.rendered_components[component_id]
                raise Exception(f"Component with ID {component_id} not found")
            @self.mcp.tool()
            def get_cached_files() -> dict:
                """List all files currently stored in the cache."""
                return self.file_cache.get_all_cached_files()

    def run(self, port=None, debug=None, mode=None):
        """
        Run the MCP server.

        Args:
            port: Port to run on (overrides config) - only used in 'sse' mode
            debug: Debug mode (overrides config)
            mode: MCP mode ('stdio' or 'sse', overrides config)
        """
        # Use provided values or fall back to config
        debug = debug if debug is not None else config.DEBUG
        
        # Get mode from parameter, environment variable, or default to stdio
        mode = mode or os.environ.get('MODE', 'stdio')
        
        # Validate mode
        if mode not in ['stdio', 'sse']:
            print(f"Invalid mode: {mode}. Using stdio mode.")
            mode = 'stdio'

        if mode == 'sse':
            print(f"Starting Penpot MCP Server on port {port} (debug={debug}, mode={mode})")
        else:
            print(f"Starting Penpot MCP Server (debug={debug}, mode={mode})")
            
        # Start HTTP server if enabled and not already running
        if config.ENABLE_HTTP_SERVER and self.image_server and not self.image_server.is_running:
            try:
                self.image_server_url = self.image_server.start()
            except Exception as e:
                print(f"Warning: Failed to start image server: {str(e)}")
            
        self.mcp.run(mode)


def create_server():
    """Create and configure a new server instance."""
    # Detect if running in a test environment
    is_test_env = 'pytest' in sys.modules
    return PenpotMCPServer(test_mode=is_test_env)


# Create a global server instance with a standard name for the MCP tool
server = create_server()


def main():
    """Entry point for the console script."""
    parser = argparse.ArgumentParser(description='Run the Penpot MCP Server')
    parser.add_argument('--port', type=int, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--mode', choices=['stdio', 'sse'], default=os.environ.get('MODE', 'stdio'),
                       help='MCP mode (stdio or sse)')
    
    args = parser.parse_args()
    server.run(port=args.port, debug=args.debug, mode=args.mode)


if __name__ == "__main__":
    main()
