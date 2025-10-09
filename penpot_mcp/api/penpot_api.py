import argparse
import json
import os
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import requests
from dotenv import load_dotenv


class CloudFlareError(Exception):
    """Exception raised when CloudFlare protection blocks the request."""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        
    def __str__(self):
        return f"CloudFlare Protection Error: {super().__str__()}"


class PenpotAPIError(Exception):
    """General exception for Penpot API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None, is_cloudflare: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.is_cloudflare = is_cloudflare


class RevisionConflictError(PenpotAPIError):
    """Raised when revision number conflicts."""
    pass


class PenpotAPI:
    def __init__(
            self,
            base_url: str = None,
            debug: bool = False,
            email: Optional[str] = None,
            password: Optional[str] = None):
        # Load environment variables if not already loaded
        load_dotenv()

        # Use base_url from parameters if provided, otherwise from environment,
        # fallback to default URL
        self.base_url = base_url or os.getenv("PENPOT_API_URL", "https://design.penpot.app/api")
        self.session = requests.Session()
        self.access_token = None
        self.debug = debug
        self.email = email or os.getenv("PENPOT_USERNAME")
        self.password = password or os.getenv("PENPOT_PASSWORD")
        self.profile_id = None

        # Set default headers - we'll use different headers at request time
        # based on the required content type (JSON vs Transit+JSON)
        self.session.headers.update({
            "Accept": "application/json, application/transit+json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def _is_cloudflare_error(self, response: requests.Response) -> bool:
        """Check if the response indicates a CloudFlare error."""
        # Check for CloudFlare-specific indicators
        cloudflare_indicators = [
            'cloudflare',
            'cf-ray',
            'attention required',
            'checking your browser',
            'challenge',
            'ddos protection',
            'security check',
            'cf-browser-verification',
            'cf-challenge-running',
            'please wait while we are checking your browser',
            'enable cookies and reload the page',
            'this process is automatic'
        ]
        
        # Check response headers for CloudFlare
        server_header = response.headers.get('server', '').lower()
        cf_ray = response.headers.get('cf-ray')
        
        if 'cloudflare' in server_header or cf_ray:
            return True
            
        # Check response content for CloudFlare indicators
        try:
            response_text = response.text.lower()
            for indicator in cloudflare_indicators:
                if indicator in response_text:
                    return True
        except:
            # If we can't read the response text, don't assume it's CloudFlare
            pass
            
        # Check for specific status codes that might indicate CloudFlare blocks
        if response.status_code in [403, 429, 503]:
            # Additional check for CloudFlare-specific error pages
            try:
                response_text = response.text.lower()
                if any(['cloudflare' in response_text, 'cf-ray' in response_text, 'attention required' in response_text]):
                    return True
            except:
                pass
                
        return False

    def _create_cloudflare_error_message(self, response: requests.Response) -> str:
        """Create a user-friendly CloudFlare error message."""
        base_message = (
            "CloudFlare protection has blocked this request. This is common on penpot.app. "
            "To resolve this issue:\\n\\n"
            "1. Open your web browser and navigate to https://design.penpot.app\\n"
            "2. Log in to your Penpot account\\n"
            "3. Complete any CloudFlare human verification challenges if prompted\\n"
            "4. Once verified, try your request again\\n\\n"
            "The verification typically lasts for a period of time, after which you may need to repeat the process."
        )
        
        if response.status_code:
            return f"{base_message}\\n\\nHTTP Status: {response.status_code}"
        
        return base_message

    def set_access_token(self, token: str):
        """Set the auth token for authentication."""
        self.access_token = token
        # For cookie-based auth, set the auth-token cookie
        self.session.cookies.set("auth-token", token)
        # Also set Authorization header for APIs that use it
        self.session.headers.update({
            "Authorization": f"Token {token}"
        })

    def login_with_password(
            self,
            email: Optional[str] = None,
            password: Optional[str] = None) -> str:
        """
        Login with email and password to get an auth token.

        This method uses the same cookie-based auth approach as the export methods.

        Args:
            email: Email for Penpot account (if None, will use stored email or PENPOT_USERNAME env var)
            password: Password for Penpot account (if None, will use stored password or PENPOT_PASSWORD env var)

        Returns:
            Auth token for API calls
        """
        # Use the export authentication which also extracts profile ID
        token = self.login_for_export(email, password)
        self.set_access_token(token)
        # Profile ID is now extracted during login_for_export, no need to call get_profile
        if self.debug and self.profile_id:
            print(f"\nProfile ID available: {self.profile_id}")
        return token

    def get_profile(self) -> Dict[str, Any]:
        """
        Get profile information for the current authenticated user.

        Returns:
            Dictionary containing profile information, including the profile ID
        """
        url = f"{self.base_url}/rpc/command/get-profile"

        payload = {}  # No parameters needed

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)

        # Parse and normalize the response
        data = response.json()
        normalized_data = self._normalize_transit_response(data)

        if self.debug:
            print("\nProfile data retrieved:")
            print(json.dumps(normalized_data, indent=2)[:200] + "...")

        # Store profile ID for later use
        if 'id' in normalized_data:
            self.profile_id = normalized_data['id']
            if self.debug:
                print(f"\nStored profile ID: {self.profile_id}")

        return normalized_data

    def login_for_export(self, email: Optional[str] = None, password: Optional[str] = None) -> str:
        """
        Login with email and password to get an auth token for export operations.

        This is required for export operations which use a different authentication
        mechanism than the standard API access token.

        Args:
            email: Email for Penpot account (if None, will use stored email or PENPOT_USERNAME env var)
            password: Password for Penpot account (if None, will use stored password or PENPOT_PASSWORD env var)

        Returns:
            Auth token extracted from cookies
        """
        # Use parameters if provided, else use instance variables, else check environment variables
        email = email or self.email or os.getenv("PENPOT_USERNAME")
        password = password or self.password or os.getenv("PENPOT_PASSWORD")

        if not email or not password:
            raise ValueError(
                "Email and password are required for export authentication. "
                "Please provide them as parameters or set PENPOT_USERNAME and "
                "PENPOT_PASSWORD environment variables."
            )

        url = f"{self.base_url}/rpc/command/login-with-password"

        # Use Transit+JSON format
        payload = {
            "~:email": email,
            "~:password": password
        }

        if self.debug:
            print("\nLogin request payload (Transit+JSON format):")
            print(json.dumps(payload, indent=2).replace(password, "********"))

        # Create a new session just for this request
        login_session = requests.Session()

        # Set headers
        headers = {
            "Content-Type": "application/transit+json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = login_session.post(url, json=payload, headers=headers)
        if self.debug and response.status_code != 200:
            print(f"\nError response: {response.status_code}")
            print(f"Response text: {response.text}")
        response.raise_for_status()

        # Extract profile ID from response
        try:
            # The response is in Transit+JSON array format
            data = response.json()
            if isinstance(data, list):
                # Convert Transit array to dict
                transit_dict = {}
                i = 1  # Skip the "^ " marker
                while i < len(data) - 1:
                    key = data[i]
                    value = data[i + 1]
                    transit_dict[key] = value
                    i += 2
                
                # Extract profile ID
                if "~:id" in transit_dict:
                    profile_id = transit_dict["~:id"]
                    # Remove the ~u prefix for UUID
                    if isinstance(profile_id, str) and profile_id.startswith("~u"):
                        profile_id = profile_id[2:]
                    self.profile_id = profile_id
                    if self.debug:
                        print(f"\nExtracted profile ID from login response: {profile_id}")
        except Exception as e:
            if self.debug:
                print(f"\nCouldn't extract profile ID from response: {e}")

        # Also try to extract profile ID from auth-data cookie
        if not self.profile_id:
            for cookie in login_session.cookies:
                if cookie.name == "auth-data":
                    # Cookie value is like: "profile-id=7ae66c33-6ede-81e2-8006-6a1b4dce3d2b"
                    if "profile-id=" in cookie.value:
                        profile_id = cookie.value.split("profile-id=")[1].split(";")[0].strip('"')
                        self.profile_id = profile_id
                        if self.debug:
                            print(f"\nExtracted profile ID from auth-data cookie: {profile_id}")
                    break

        # Extract auth token from cookies
        if 'Set-Cookie' in response.headers:
            if self.debug:
                print("\nSet-Cookie header found")

            for cookie in login_session.cookies:
                if cookie.name == "auth-token":
                    if self.debug:
                        print(f"\nAuth token extracted from cookies: {cookie.value[:10]}...")
                    return cookie.value

            raise ValueError("Auth token not found in response cookies")
        else:
            # Try to extract from response JSON if available
            try:
                data = response.json()
                if 'auth-token' in data:
                    return data['auth-token']
            except Exception:
                pass

            # If we reached here, we couldn't find the token
            raise ValueError("Auth token not found in response cookies or JSON body")

    def _make_authenticated_request(self, method: str, url: str, retry_auth: bool = True, **kwargs) -> requests.Response:
        """
        Make an authenticated request, handling re-auth if needed.

        This internal method handles lazy authentication when a request
        fails due to authentication issues, using the same cookie-based
        approach as the export methods.

        Args:
            method: HTTP method (post, get, etc.)
            url: URL to make the request to
            **kwargs: Additional arguments to pass to requests

        Returns:
            The response object
        """
        # If we don't have a token yet but have credentials, login first
        if not self.access_token and self.email and self.password:
            if self.debug:
                print("\nNo access token set, logging in with credentials...")
            self.login_with_password()

        # Set up headers
        headers = kwargs.get('headers', {})
        if 'headers' in kwargs:
            del kwargs['headers']

        # Use Transit+JSON format for API calls (required by Penpot)
        use_transit = kwargs.pop('use_transit', True)

        if use_transit:
            headers['Content-Type'] = 'application/transit+json'
            headers['Accept'] = 'application/transit+json'

            # Convert payload to Transit+JSON format if present
            if 'json' in kwargs and kwargs['json']:
                payload = kwargs['json']

                # Only transform if not already in Transit format
                if not any(isinstance(k, str) and k.startswith('~:') for k in payload.keys()):
                    transit_payload = {}

                    # Add cmd if not present
                    if 'cmd' not in payload and '~:cmd' not in payload:
                        # Extract command from URL
                        cmd = url.split('/')[-1]
                        transit_payload['~:cmd'] = f"~:{cmd}"

                    # Convert standard JSON to Transit+JSON format
                    for key, value in payload.items():
                        # Skip command if already added
                        if key == 'cmd':
                            continue

                        transit_key = f"~:{key}" if not key.startswith('~:') else key

                        # Handle special UUID conversion for IDs
                        if isinstance(value, str) and ('-' in value) and len(value) > 30:
                            transit_value = f"~u{value}"
                        else:
                            transit_value = value

                        transit_payload[transit_key] = transit_value

                    if self.debug:
                        print("\nConverted payload to Transit+JSON format:")
                        print(f"Original: {payload}")
                        print(f"Transit: {transit_payload}")

                    kwargs['json'] = transit_payload
        else:
            headers['Content-Type'] = 'application/json'
            headers['Accept'] = 'application/json'

        # Ensure the Authorization header is set if we have a token
        if self.access_token:
            headers['Authorization'] = f"Token {self.access_token}"

        # Combine with session headers
        combined_headers = {**self.session.headers, **headers}

        # Make the request
        try:
            response = getattr(self.session, method)(url, headers=combined_headers, **kwargs)

            if self.debug:
                print(f"\nRequest to: {url}")
                print(f"Method: {method}")
                print(f"Headers: {combined_headers}")
                if 'json' in kwargs:
                    print(f"Payload: {json.dumps(kwargs['json'], indent=2)}")
                print(f"Response status: {response.status_code}")

            response.raise_for_status()
            return response

        except requests.HTTPError as e:
            # Check for CloudFlare errors first
            if self._is_cloudflare_error(e.response):
                cloudflare_message = self._create_cloudflare_error_message(e.response)
                raise CloudFlareError(cloudflare_message, e.response.status_code, e.response.text)
            
            # Handle authentication errors
            if e.response.status_code in (401, 403) and self.email and self.password and retry_auth:
                # Special case: don't retry auth for get-profile to avoid infinite loops
                if url.endswith('/get-profile'):
                    raise
                    
                if self.debug:
                    print("\nAuthentication failed. Trying to re-login...")

                # Re-login and update token
                self.login_with_password()

                # Update headers with new token
                headers['Authorization'] = f"Token {self.access_token}"
                combined_headers = {**self.session.headers, **headers}

                # Retry the request with the new token (but don't retry auth again)
                response = getattr(self.session, method)(url, headers=combined_headers, **kwargs)
                response.raise_for_status()
                return response
            else:
                # Re-raise other errors
                raise
        except requests.RequestException as e:
            # Handle other request exceptions (connection errors, timeouts, etc.)
            # Check if we have a response to analyze
            if hasattr(e, 'response') and e.response is not None:
                if self._is_cloudflare_error(e.response):
                    cloudflare_message = self._create_cloudflare_error_message(e.response)
                    raise CloudFlareError(cloudflare_message, e.response.status_code, e.response.text)
            # Re-raise if not a CloudFlare error
            raise

    def _normalize_transit_response(self, data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
        """
        Normalize a Transit+JSON response to a more usable format.

        This recursively processes the response data, handling special Transit types
        like UUIDs, keywords, and nested structures.

        Args:
            data: The data to normalize, can be a dict, list, or other value

        Returns:
            Normalized data
        """
        if isinstance(data, dict):
            # Normalize dictionary
            result = {}
            for key, value in data.items():
                # Convert transit keywords in keys (~:key -> key)
                norm_key = key.replace(
                    '~:', '') if isinstance(
                    key, str) and key.startswith('~:') else key
                # Recursively normalize values
                result[norm_key] = self._normalize_transit_response(value)
            return result
        elif isinstance(data, list):
            # Normalize list items
            return [self._normalize_transit_response(item) for item in data]
        elif isinstance(data, str) and data.startswith('~u'):
            # Convert Transit UUIDs (~u123-456 -> 123-456)
            return data[2:]
        else:
            # Return other types as-is
            return data

    def get_teams(self) -> List[Dict[str, Any]]:
        """
        Get all teams for the authenticated user.
        
        Returns:
            List of team dictionaries containing:
            - id: Team UUID
            - name: Team name
            - isDefault: Whether this is the default team
            - permissions: User permissions in the team
            
        Example:
            >>> api = PenpotAPI()
            >>> teams = api.get_teams()
            >>> print(teams[0]['name'])
        """
        url = f"{self.base_url}/rpc/command/get-teams"
        
        payload = {}  # No parameters required
        
        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        
        # Parse JSON
        data = response.json()
        
        if self.debug:
            print(f"\nRetrieved {len(data)} teams")
            if data:
                print(f"First team: {data[0].get('name')} (ID: {data[0].get('id')})")
        
        return data

    def list_projects(self) -> Dict[str, Any]:
        """
        List all available projects for the authenticated user.

        Returns:
            Dictionary containing project information
        """
        url = f"{self.base_url}/rpc/command/get-all-projects"

        payload = {}  # No parameters required

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)

        if self.debug:
            content_type = response.headers.get('Content-Type', '')
            print(f"\nResponse content type: {content_type}")
            print(f"Response preview: {response.text[:100]}...")

        # Parse JSON
        data = response.json()

        if self.debug:
            print("\nData preview:")
            print(json.dumps(data, indent=2)[:200] + "...")

        return data

    def create_project(
        self,
        name: str,
        team_id: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new project within a team.
        
        Args:
            name: Project name
            team_id: UUID of the team to create project in
            project_id: Optional custom project UUID
        
        Returns:
            Dictionary containing created project information:
            - id: Project UUID
            - name: Project name
            - teamId: Team UUID
            - created: Creation timestamp
            - modified: Last modified timestamp
            
        Example:
            >>> api = PenpotAPI()
            >>> teams = api.get_teams()
            >>> project = api.create_project("My Project", team_id=teams[0]['id'])
            >>> print(project['id'])
        """
        url = f"{self.base_url}/rpc/command/create-project"
        
        payload = {
            "name": name,
            "team-id": team_id
        }
        
        if project_id:
            payload["id"] = project_id
        
        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()
        
        if self.debug:
            print(f"\nProject created: {data.get('name')} (ID: {data.get('id')})")
        
        return data

    def rename_project(self, project_id: str, name: str) -> Dict[str, Any]:
        """
        Rename an existing project.
        
        Args:
            project_id: UUID of the project to rename
            name: New project name
        
        Returns:
            Updated project information
            
        Example:
            >>> api = PenpotAPI()
            >>> result = api.rename_project(project_id="abc-123", name="Better Name")
            >>> print(result['name'])
        """
        url = f"{self.base_url}/rpc/command/rename-project"
        
        payload = {
            "id": project_id,
            "name": name
        }
        
        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()
        
        if self.debug:
            print(f"\nProject renamed: {data.get('name')} (ID: {data.get('id')})")
        
        return data

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """
        Delete a project.
        
        WARNING: This will delete all files in the project!
        
        Args:
            project_id: UUID of the project to delete
        
        Returns:
            Success confirmation
            
        Example:
            >>> api = PenpotAPI()
            >>> result = api.delete_project(project_id="abc-123")
        """
        url = f"{self.base_url}/rpc/command/delete-project"
        
        payload = {
            "id": project_id
        }
        
        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        
        # Try to parse JSON response, but handle empty responses
        try:
            data = response.json()
        except Exception:
            # If no JSON response, return success with the project_id
            data = {"success": True, "id": project_id}
        
        if self.debug:
            print(f"\nProject deleted: {project_id}")
        
        return data

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific project.
        
        Args:
            project_id: UUID of the project
        
        Returns:
            Project details including permissions, team info, etc.
            
        Example:
            >>> api = PenpotAPI()
            >>> project = api.get_project(project_id="abc-123")
            >>> print(project['name'])
        """
        url = f"{self.base_url}/rpc/command/get-project"
        
        payload = {
            "id": project_id
        }
        
        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()
        
        if self.debug:
            print(f"\nRetrieved project: {data.get('name')} (ID: {data.get('id')})")
        
        return data

    def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all files for a specific project.

        Args:
            project_id: The ID of the project

        Returns:
            List of file information dictionaries
        """
        url = f"{self.base_url}/rpc/command/get-project-files"

        payload = {
            "project-id": project_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)

        # Parse JSON
        files = response.json()
        return files

    def get_file(self, file_id: str, save_data: bool = False,
                 save_raw_response: bool = False) -> Dict[str, Any]:
        """
        Get details for a specific file.

        Args:
            file_id: The ID of the file to retrieve
            features: List of features to include in the response
            project_id: Optional project ID if known
            save_data: Whether to save the data to a file
            save_raw_response: Whether to save the raw response

        Returns:
            Dictionary containing file information
        """
        url = f"{self.base_url}/rpc/command/get-file"

        payload = {
            "id": file_id,
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)

        # Save raw response if requested
        if save_raw_response:
            raw_filename = f"{file_id}_raw_response.json"
            with open(raw_filename, 'w') as f:
                f.write(response.text)
            if self.debug:
                print(f"\nSaved raw response to {raw_filename}")

        # Parse JSON
        data = response.json()

        # Save normalized data if requested
        if save_data:
            filename = f"{file_id}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            if self.debug:
                print(f"\nSaved file data to {filename}")

        return data

    def generate_session_id(self) -> str:
        """
        Generate a new session UUID for file editing.
        
        Returns:
            UUID string without ~u prefix
            
        Example:
            session_id = api.generate_session_id()
            # Returns: "123e4567-e89b-12d3-a456-426614174000"
        """
        return str(uuid.uuid4())

    def get_file_revision(self, file_id: str) -> int:
        """
        Get the current revision number for a file.

        This extracts the revn field from the file data.

        Args:
            file_id: UUID of the file

        Returns:
            Current revision number (integer)

        Example:
            revn = api.get_file_revision("file-123")
            # Use this revn when calling update_file
        """
        file_data = self.get_file(file_id)

        # Revision number is in the root of file data
        revn = file_data.get('revn', 0)

        if self.debug:
            print(f"Current revision for file {file_id}: {revn}")

        return revn

    def get_file_version(self, file_id: str) -> Tuple[int, int]:
        """
        Get the current revision and version numbers for a file.

        This extracts both revn and vern fields from the file data.
        Some Penpot instances (especially self-hosted) require both.

        Args:
            file_id: UUID of the file

        Returns:
            Tuple of (revn, vern) - revision and version numbers

        Example:
            revn, vern = api.get_file_version("file-123")
        """
        file_data = self.get_file(file_id)

        # Get both revision and version numbers
        revn = file_data.get('revn', 0)
        vern = file_data.get('vern', 0)

        if self.debug:
            print(f"Current revision for file {file_id}: revn={revn}, vern={vern}")

        return revn, vern

    @contextmanager
    def editing_session(self, file_id: str) -> Generator[Tuple[str, int], None, None]:
        """
        Context manager for file editing sessions.
        
        Automatically manages session ID and revision numbers.
        
        Args:
            file_id: UUID of the file to edit
            
        Yields:
            Tuple of (session_id, current_revn)
            
        Example:
            with api.editing_session("file-123") as (session_id, revn):
                changes = [...]
                api.update_file(file_id, session_id, revn, changes)
        """
        session_id = self.generate_session_id()
        revn = self.get_file_revision(file_id)
        
        if self.debug:
            print(f"Starting editing session {session_id} at revision {revn}")
            
        try:
            yield (session_id, revn)
        finally:
            if self.debug:
                print(f"Ending editing session {session_id}")

    def _convert_changes_to_transit(self, changes: List[dict]) -> List[dict]:
        """
        Convert a list of change operations to Transit+JSON format.
        
        This method recursively processes change operations, adding:
        - ~u prefix to UUID fields (id, pageId, frameId, parentId)
        - ~: prefix to keyword fields (type, attr names)
        
        Args:
            changes: List of change operations
            
        Returns:
            List of changes in Transit+JSON format
        """
        def should_convert_to_keyword(key: str, value: str) -> bool:
            """Determine if a string value should be converted to a Transit keyword.

            Text content structure types (root, paragraph-set, paragraph) must remain
            as strings, not keywords, for Penpot API compatibility.
            """
            keyword_fields = {'type', 'attr'}
            text_content_types = {'root', 'paragraph-set', 'paragraph'}
            return key in keyword_fields and value not in text_content_types

        def convert_value(key: str, value: Any) -> Any:
            """Convert a single value based on its key and type."""
            # UUID fields that need ~u prefix
            uuid_fields = {'id', 'pageId', 'frameId', 'parentId', 'obj-id'}

            if isinstance(value, dict):
                # Recursively convert nested dictionaries
                return convert_dict(value)
            elif isinstance(value, list):
                # Recursively convert list items
                return [convert_value(key, item) for item in value]
            elif isinstance(value, str):
                # Handle string values based on the key
                if key in uuid_fields:
                    # Add ~u prefix to UUIDs (even short test IDs)
                    return f"~u{value}"
                elif should_convert_to_keyword(key, value):
                    # Add ~: prefix to keyword values (except text content types)
                    return f"~:{value}"
                else:
                    # Return other strings as-is (like names, descriptions, text content types)
                    return value
            else:
                # Return non-string types as-is (numbers, booleans, None)
                return value
        
        def convert_dict(obj: dict) -> dict:
            """Convert a dictionary to Transit+JSON format."""
            transit_obj = {}
            for key, value in obj.items():
                # Convert key to Transit keyword format
                transit_key = f"~:{key}" if not key.startswith('~:') else key
                # Convert value
                transit_value = convert_value(key, value)
                transit_obj[transit_key] = transit_value
            return transit_obj
        
        # Convert each change operation
        return [convert_dict(change) for change in changes]

    def update_file(
        self,
        file_id: str,
        session_id: str,
        revn: int,
        changes: List[dict],
        vern: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update a Penpot file with design changes.

        This is the core method for ALL design operations. Changes are
        applied atomically as a batch.

        Args:
            file_id: UUID of the file to update
            session_id: UUID for this editing session
            revn: Current revision number (will increment to revn+1)
            changes: List of change operations (add-obj, mod-obj, del-obj, etc.)
            vern: Optional version number (required by some Penpot instances).
                  If not provided, will be fetched automatically.

        Returns:
            Updated file information with new revision number

        Raises:
            RevisionConflictError: If revn does not match server state
            PenpotAPIError: For other API errors

        Example:
            >>> api = PenpotAPI()
            >>> with api.editing_session("file-123") as (session_id, revn):
            >>>     changes = [api.create_add_obj_change("obj-1", "page-1", {"type": "rect"})]
            >>>     result = api.update_file("file-123", session_id, revn, changes)
        """
        url = f"{self.base_url}/rpc/command/update-file"

        # If vern not provided, fetch it
        if vern is None:
            _, vern = self.get_file_version(file_id)
            if self.debug:
                print(f"Fetched vern={vern} for file {file_id}")

        # Convert changes to Transit+JSON format
        transit_changes = self._convert_changes_to_transit(changes)

        payload = {
            "id": file_id,
            "session-id": session_id,
            "revn": revn,
            "vern": vern,
            "changes": transit_changes
        }

        if self.debug:
            print(f"\nUpdating file {file_id}")
            print(f"Session: {session_id}, Revision: {revn}, Version: {vern}")
            print(f"Changes: {len(changes)} operations")

        try:
            response = self._make_authenticated_request(
                'post', url, json=payload, use_transit=True
            )
            data = response.json()

            if self.debug:
                # Handle both list and dict responses
                if isinstance(data, list):
                    print(f"Update successful. Response contains {len(data)} items")
                    # Return a success dict with the new revision
                    return {'revn': revn + 1, 'changes': data}
                else:
                    print(f"Update successful. New revision: {data.get('revn', revn + 1)}")

            # If data is a list (Transit format), wrap it in a dict
            if isinstance(data, list):
                return {'revn': revn + 1, 'changes': data}

            return data

        except requests.HTTPError as e:
            # Log error response for debugging
            if self.debug and hasattr(e, 'response') and e.response is not None:
                print(f"\n!!! UPDATE FILE ERROR !!!")
                print(f"Status: {e.response.status_code}")
                print(f"Response body: {e.response.text[:2000]}")

            # Check for revision conflict
            if e.response.status_code == 409:
                raise RevisionConflictError(
                    f"Revision conflict. Expected {revn} but server has different version."
                )
            raise

    def create_add_obj_change(
        self, obj_id: str, page_id: str, obj: dict,
        frame_id: Optional[str] = None
    ) -> dict:
        """
        Create an add-obj change operation.

        Args:
            obj_id: UUID for the new object
            page_id: UUID of the page to add object to
            obj: Object definition (type, properties, etc.)
            frame_id: Optional UUID of parent frame

        Returns:
            Change operation dictionary

        Example:
            >>> api = PenpotAPI()
            >>> obj = {'type': 'rect', 'x': 0, 'y': 0, 'width': 100, 'height': 100}
            >>> change = api.create_add_obj_change("obj-1", "page-1", obj)
        """
        # Add required fields to the object
        obj_with_required_fields = obj.copy()
        obj_with_required_fields['id'] = obj_id

        # If frame_id is not provided, use page_id for both parent and frame
        # This assumes top-level objects on a page
        if frame_id is None:
            obj_with_required_fields['parent-id'] = page_id
            obj_with_required_fields['frame-id'] = page_id
        else:
            obj_with_required_fields['parent-id'] = frame_id
            obj_with_required_fields['frame-id'] = frame_id

        change = {
            'type': 'add-obj',
            'id': obj_id,
            'page-id': page_id,
            'frame-id': frame_id if frame_id is not None else page_id,
            'obj': obj_with_required_fields
        }
        return change

    def create_mod_obj_change(self, obj_id: str, operations: List[dict]) -> dict:
        """
        Create a mod-obj change operation.
        
        Args:
            obj_id: UUID of the object to modify
            operations: List of operations to apply (set, unset, etc.)
            
        Returns:
            Change operation dictionary
            
        Example:
            >>> api = PenpotAPI()
            >>> ops = [api.create_set_operation('x', 100)]
            >>> change = api.create_mod_obj_change("obj-1", ops)
        """
        return {
            'type': 'mod-obj',
            'id': obj_id,
            'operations': operations
        }

    def create_set_operation(self, attr: str, val: Any) -> dict:
        """
        Create a set operation for single attribute.
        
        Args:
            attr: Attribute name to set
            val: Value to set
            
        Returns:
            Set operation dictionary
            
        Example:
            >>> api = PenpotAPI()
            >>> op = api.create_set_operation('x', 100)
        """
        return {'type': 'set', 'attr': attr, 'val': val}

    def create_del_obj_change(self, obj_id: str, page_id: str) -> dict:
        """
        Create a del-obj change operation.
        
        Args:
            obj_id: UUID of the object to delete
            page_id: UUID of the page containing the object
            
        Returns:
            Change operation dictionary
            
        Example:
            >>> api = PenpotAPI()
            >>> change = api.create_del_obj_change("obj-1", "page-1")
        """
        return {
            'type': 'del-obj',
            'id': obj_id,
            'page-id': page_id
        }

    def _add_geometric_properties(self, obj: dict, x: float, y: float, width: float, height: float) -> dict:
        """
        Add required geometric properties to a shape object.

        Args:
            obj: Shape object dictionary
            x: X coordinate
            y: Y coordinate
            width: Width
            height: Height

        Returns:
            Shape object with geometric properties added
        """
        # Add selection rectangle (bounding box)
        obj['selrect'] = {
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'x1': x,
            'y1': y,
            'x2': x + width,
            'y2': y + height
        }

        # Add corner points (top-left, top-right, bottom-right, bottom-left)
        obj['points'] = [
            {'x': x, 'y': y},
            {'x': x + width, 'y': y},
            {'x': x + width, 'y': y + height},
            {'x': x, 'y': y + height}
        ]

        # Add identity transformation matrix [a, b, c, d, e, f]
        # This represents no transformation
        obj['transform'] = {
            'a': 1.0,
            'b': 0.0,
            'c': 0.0,
            'd': 1.0,
            'e': 0.0,
            'f': 0.0
        }

        # Add inverse transformation (also identity)
        obj['transform-inverse'] = {
            'a': 1.0,
            'b': 0.0,
            'c': 0.0,
            'd': 1.0,
            'e': 0.0,
            'f': 0.0
        }

        return obj

    def create_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        name: str = "Rectangle",
        fill_color: str = "#000000",
        fill_opacity: float = 1.0,
        stroke_color: Optional[str] = None,
        stroke_width: Optional[float] = None,
        rx: float = 0,
        ry: float = 0,
        **kwargs
    ) -> dict:
        """
        Create a rectangle shape object.

        Args:
            x: X coordinate
            y: Y coordinate
            width: Width
            height: Height
            name: Shape name
            fill_color: Fill color (hex format #RRGGBB)
            fill_opacity: Fill opacity (0.0 to 1.0)
            stroke_color: Optional stroke/border color
            stroke_width: Optional stroke width
            rx: Corner radius X
            ry: Corner radius Y
            **kwargs: Additional shape properties

        Returns:
            Rectangle object dictionary ready for add-obj change

        Example:
            >>> api = PenpotAPI()
            >>> rect = api.create_rectangle(100, 200, 300, 150, fill_color="#FF0000")
            >>> rect_id = api.generate_session_id()
            >>> change = api.create_add_obj_change(rect_id, "page-id", rect)
        """
        rect = {
            'type': 'rect',
            'name': name,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'fills': [{
                'fill-color': fill_color,
                'fill-opacity': fill_opacity
            }]
        }

        if rx > 0 or ry > 0:
            rect['rx'] = rx
            rect['ry'] = ry

        if stroke_color and stroke_width:
            rect['strokes'] = [{
                'stroke-color': stroke_color,
                'stroke-width': stroke_width
            }]

        # Merge any additional kwargs
        rect.update(kwargs)

        # Add required geometric properties
        rect = self._add_geometric_properties(rect, x, y, width, height)

        return rect

    def create_circle(
        self,
        cx: float,
        cy: float,
        radius: float,
        name: str = "Circle",
        fill_color: str = "#000000",
        fill_opacity: float = 1.0,
        stroke_color: Optional[str] = None,
        stroke_width: Optional[float] = None,
        **kwargs
    ) -> dict:
        """
        Create a circle/ellipse shape object.

        Args:
            cx: Center X coordinate
            cy: Center Y coordinate
            radius: Radius (for circle) or use width/height for ellipse
            name: Shape name
            fill_color: Fill color
            fill_opacity: Fill opacity
            stroke_color: Optional stroke color
            stroke_width: Optional stroke width
            **kwargs: Additional properties (e.g., width, height for ellipse)

        Returns:
            Circle object dictionary

        Example:
            >>> api = PenpotAPI()
            >>> circle = api.create_circle(150, 150, 50, fill_color="#00FF00")
            >>> circle_id = api.generate_session_id()
            >>> change = api.create_add_obj_change(circle_id, "page-id", circle)
        """
        # Circle is positioned by top-left corner in Penpot
        circle = {
            'type': 'circle',
            'name': name,
            'x': cx - radius,
            'y': cy - radius,
            'width': radius * 2,
            'height': radius * 2,
            'fills': [{
                'fill-color': fill_color,
                'fill-opacity': fill_opacity
            }]
        }

        if stroke_color and stroke_width:
            circle['strokes'] = [{
                'stroke-color': stroke_color,
                'stroke-width': stroke_width
            }]

        circle.update(kwargs)

        # Add required geometric properties
        x = cx - radius
        y = cy - radius
        width = radius * 2
        height = radius * 2
        circle = self._add_geometric_properties(circle, x, y, width, height)

        return circle

    def create_text(
        self,
        x: float,
        y: float,
        content: str,
        name: str = "Text",
        font_size: int = 16,
        font_family: str = "Work Sans",
        fill_color: str = "#000000",
        font_weight: str = "normal",
        text_align: str = "left",
        **kwargs
    ) -> dict:
        """
        Create a text shape object.

        Args:
            x: X coordinate
            y: Y coordinate
            content: Text content
            name: Shape name
            font_size: Font size in pixels
            font_family: Font family name
            fill_color: Text color
            font_weight: Font weight (normal, bold, etc.)
            text_align: Text alignment (left, center, right)
            **kwargs: Additional properties

        Returns:
            Text object dictionary

        Example:
            >>> api = PenpotAPI()
            >>> text = api.create_text(10, 20, "Hello World", font_size=24)
            >>> text_id = api.generate_session_id()
            >>> change = api.create_add_obj_change(text_id, "page-id", text)
        """
        # Create proper text content structure
        # IMPORTANT: Text color must be set in the content structure, not just at object level
        # Penpot UI reads text color from content.children[].children[].children[].fills
        fills_array = [{
            'fill-color': fill_color,
            'fill-opacity': 1.0
        }]

        text_content = {
            'type': 'root',
            'children': [{
                'type': 'paragraph-set',
                'children': [{
                    'type': 'paragraph',
                    'fills': fills_array,  # Add fills at paragraph level
                    'children': [{
                        'text': content,
                        'font-family': font_family,
                        'font-size': str(font_size),
                        'font-weight': font_weight,
                        'fills': fills_array  # Add fills at text level
                    }]
                }]
            }]
        }

        # NOTE: Property names use kebab-case (fill-color, font-size) as required by Penpot API
        # This is intentional and differs from Python's snake_case or JavaScript's camelCase
        text = {
            'type': 'text',
            'name': name,
            'x': x,
            'y': y,
            'content': text_content,
            'fills': fills_array  # Also set at object level for completeness
        }

        text.update(kwargs)

        # Estimate text dimensions if not provided
        # Simple heuristic: width = char_count * font_size * 0.6, height = font_size * 1.5
        if 'width' not in text:
            text['width'] = max(len(content) * font_size * 0.6, 10)
        if 'height' not in text:
            text['height'] = font_size * 1.5

        # Add required geometric properties
        text = self._add_geometric_properties(text, text['x'], text['y'], text['width'], text['height'])

        return text

    def create_frame(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        name: str = "Frame",
        background_color: Optional[str] = None,
        **kwargs
    ) -> dict:
        """
        Create a frame (artboard) object.

        Frames are containers for other objects, similar to artboards.

        Args:
            x: X coordinate
            y: Y coordinate
            width: Width
            height: Height
            name: Frame name
            background_color: Optional background color
            **kwargs: Additional properties

        Returns:
            Frame object dictionary

        Example:
            >>> api = PenpotAPI()
            >>> frame = api.create_frame(0, 0, 375, 812, name="iPhone", background_color="#FFFFFF")
            >>> frame_id = api.generate_session_id()
            >>> change = api.create_add_obj_change(frame_id, "page-id", frame)
        """
        frame = {
            'type': 'frame',
            'name': name,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'shapes': []  # Frames need a shapes list (initially empty)
        }

        if background_color:
            frame['fills'] = [{
                'fill-color': background_color,
                'fill-opacity': 1.0
            }]

        frame.update(kwargs)

        # Add required geometric properties
        frame = self._add_geometric_properties(frame, x, y, width, height)

        return frame

    def create_group(
        self,
        name: str = "Group",
        **kwargs
    ) -> dict:
        """
        Create a group container object.

        Groups are containers that organize multiple objects.

        Args:
            name: Group name
            **kwargs: Additional properties

        Returns:
            Group object dictionary

        Example:
            >>> api = PenpotAPI()
            >>> group = api.create_group(name="My Group")
            >>> group_id = api.generate_session_id()
            >>> change = api.create_add_obj_change(group_id, "page-id", group)
        """
        group = {
            'type': 'group',
            'name': name
        }

        group.update(kwargs)

        return group

    def create_path(
        self,
        points: List[dict],
        closed: bool = True,
        fill_color: Optional[str] = None,
        stroke_color: Optional[str] = None,
        stroke_width: float = 1.0,
        name: str = "Path",
        **kwargs
    ) -> dict:
        """
        Create a custom vector path object.

        Args:
            points: List of point dictionaries with x, y coordinates
                    Example: [{'x': 0, 'y': 0}, {'x': 100, 'y': 0}, {'x': 100, 'y': 100}]
            closed: Whether the path should be closed (default: True)
            fill_color: Fill color (hex format, optional)
            stroke_color: Stroke color (hex format, optional)
            stroke_width: Stroke width in pixels
            name: Path name
            **kwargs: Additional object properties

        Returns:
            Path object dictionary ready for add-obj change

        Example:
            >>> api = PenpotAPI()
            >>> # Create triangle
            >>> path = api.create_path([
            ...     {'x': 50, 'y': 0},
            ...     {'x': 100, 'y': 100},
            ...     {'x': 0, 'y': 100}
            ... ], fill_color='#ff0000')
        """
        if not points or len(points) < 2:
            raise ValueError("Path must have at least 2 points")

        # Convert points to SVG path commands
        # Start with move to first point
        path_commands = [{'command': 'M', 'params': {'x': points[0]['x'], 'y': points[0]['y']}}]
        
        # Add line to commands for remaining points
        for point in points[1:]:
            path_commands.append({'command': 'L', 'params': {'x': point['x'], 'y': point['y']}})
        
        # Close path if requested
        if closed:
            path_commands.append({'command': 'Z', 'params': {}})

        # Calculate bounding box
        xs = [p['x'] for p in points]
        ys = [p['y'] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max_x - min_x
        height = max_y - min_y

        path = {
            'type': 'path',
            'name': name,
            'x': min_x,
            'y': min_y,
            'width': width if width > 0 else 1,
            'height': height if height > 0 else 1,
            'content': path_commands
        }

        # Add fills if specified
        if fill_color:
            path['fills'] = [{
                'fill-color': fill_color,
                'fill-opacity': 1.0
            }]

        # Add strokes if specified
        if stroke_color and stroke_width:
            path['strokes'] = [{
                'stroke-color': stroke_color,
                'stroke-width': stroke_width
            }]

        path.update(kwargs)

        return path

    def create_boolean_shape(
        self,
        operation: str,
        shapes: List[str],
        name: str = "Boolean",
        **kwargs
    ) -> dict:
        """
        Create a boolean shape from multiple shapes.

        Args:
            operation: Boolean operation type
                      - 'union': Combine shapes
                      - 'difference': Subtract shapes
                      - 'intersection': Keep only overlapping areas
                      - 'exclusion': Keep non-overlapping areas
            shapes: List of object IDs to apply boolean operation to
            name: Boolean shape name
            **kwargs: Additional object properties

        Returns:
            Boolean object dictionary ready for add-obj change

        Example:
            >>> api = PenpotAPI()
            >>> # Create boolean shape from two circles
            >>> bool_shape = api.create_boolean_shape(
            ...     operation='union',
            ...     shapes=['circle-1', 'circle-2']
            ... )
        """
        valid_operations = ['union', 'difference', 'intersection', 'exclusion']
        if operation not in valid_operations:
            raise ValueError(f"Invalid operation '{operation}'. Must be one of: {', '.join(valid_operations)}")

        if not shapes or len(shapes) < 2:
            raise ValueError("Boolean shape requires at least 2 shapes")

        bool_shape = {
            'type': 'bool',
            'name': name,
            'bool-type': operation,
            'shapes': shapes
        }

        bool_shape.update(kwargs)

        return bool_shape

    def create_parent_operation(
        self,
        parent_id: str
    ) -> dict:
        """
        Create operation to set object's parent (for grouping).

        Args:
            parent_id: UUID of the parent frame/group

        Returns:
            Set operation for parentId

        Example:
            >>> api = PenpotAPI()
            >>> # Move object into group
            >>> op = api.create_parent_operation("group-123")
            >>> change = api.create_mod_obj_change("obj-1", [op])
        """
        return self.create_set_operation('parentId', parent_id)

    def create_gradient_fill(
        self,
        gradient_type: str,
        start_color: str,
        end_color: str,
        start_x: float = 0.0,
        start_y: float = 0.0,
        end_x: float = 1.0,
        end_y: float = 1.0,
        **kwargs
    ) -> dict:
        """
        Create a gradient fill definition.

        Args:
            gradient_type: Type of gradient ('linear' or 'radial')
            start_color: Start color in hex format (e.g., '#ff0000')
            end_color: End color in hex format
            start_x: Start X position (0.0-1.0, relative to shape)
            start_y: Start Y position (0.0-1.0, relative to shape)
            end_x: End X position (0.0-1.0, relative to shape)
            end_y: End Y position (0.0-1.0, relative to shape)
            **kwargs: Additional gradient properties

        Returns:
            Gradient fill dictionary

        Example:
            >>> api = PenpotAPI()
            >>> # Linear gradient from red to blue
            >>> gradient = api.create_gradient_fill(
            ...     'linear',
            ...     '#ff0000',
            ...     '#0000ff',
            ...     start_x=0, start_y=0,
            ...     end_x=1, end_y=0
            ... )
        """
        valid_types = ['linear', 'radial']
        if gradient_type not in valid_types:
            raise ValueError(f"Invalid gradient_type '{gradient_type}'. Must be one of: {', '.join(valid_types)}")

        gradient = {
            'type': f'{gradient_type}-gradient',
            'start-color': start_color,
            'end-color': end_color,
            'start-x': start_x,
            'start-y': start_y,
            'end-x': end_x,
            'end-y': end_y
        }

        gradient.update(kwargs)

        return gradient

    def create_stroke(
        self,
        color: str,
        width: float = 1.0,
        style: str = 'solid',
        cap: str = 'round',
        join: str = 'round',
        **kwargs
    ) -> dict:
        """
        Create a stroke (border) definition.

        Args:
            color: Stroke color in hex format
            width: Stroke width in pixels (default: 1.0)
            style: Stroke style ('solid', 'dashed', 'dotted', 'mixed')
            cap: Line cap style ('round', 'square', 'butt')
            join: Line join style ('round', 'bevel', 'miter')
            **kwargs: Additional stroke properties

        Returns:
            Stroke dictionary

        Example:
            >>> api = PenpotAPI()
            >>> stroke = api.create_stroke('#000000', width=2.0, style='dashed')
        """
        valid_styles = ['solid', 'dashed', 'dotted', 'mixed']
        if style not in valid_styles:
            raise ValueError(f"Invalid style '{style}'. Must be one of: {', '.join(valid_styles)}")

        valid_caps = ['round', 'square', 'butt']
        if cap not in valid_caps:
            raise ValueError(f"Invalid cap '{cap}'. Must be one of: {', '.join(valid_caps)}")

        valid_joins = ['round', 'bevel', 'miter']
        if join not in valid_joins:
            raise ValueError(f"Invalid join '{join}'. Must be one of: {', '.join(valid_joins)}")

        stroke = {
            'stroke-color': color,
            'stroke-width': width,
            'stroke-style': style,
            'stroke-cap': cap,
            'stroke-join': join
        }

        stroke.update(kwargs)

        return stroke

    def create_shadow(
        self,
        color: str,
        offset_x: float,
        offset_y: float,
        blur: float,
        spread: float = 0.0,
        hidden: bool = False,
        **kwargs
    ) -> dict:
        """
        Create a drop shadow effect.

        Args:
            color: Shadow color in hex format with alpha (e.g., '#00000080')
            offset_x: Horizontal offset in pixels
            offset_y: Vertical offset in pixels
            blur: Blur radius in pixels
            spread: Spread radius in pixels (default: 0.0)
            hidden: Whether shadow is hidden (default: False)
            **kwargs: Additional shadow properties

        Returns:
            Shadow dictionary

        Example:
            >>> api = PenpotAPI()
            >>> shadow = api.create_shadow('#00000080', 2, 2, 4)
        """
        shadow = {
            'color': color,
            'offset-x': offset_x,
            'offset-y': offset_y,
            'blur': blur,
            'spread': spread,
            'hidden': hidden
        }

        shadow.update(kwargs)

        return shadow

    def create_blur(
        self,
        blur_type: str,
        value: float,
        hidden: bool = False
    ) -> dict:
        """
        Create a blur effect.

        Args:
            blur_type: Type of blur ('layer-blur' or 'background-blur')
            value: Blur amount in pixels
            hidden: Whether blur is hidden (default: False)

        Returns:
            Blur effect dictionary

        Example:
            >>> api = PenpotAPI()
            >>> blur = api.create_blur('layer-blur', 10)
        """
        valid_types = ['layer-blur', 'background-blur']
        if blur_type not in valid_types:
            raise ValueError(f"Invalid blur_type '{blur_type}'. Must be one of: {', '.join(valid_types)}")

        blur = {
            'type': blur_type,
            'value': value,
            'hidden': hidden
        }

        return blur

    def create_fill_operation(self, fills: List[dict]) -> dict:
        """
        Create operation to set fill(s) on object.

        Args:
            fills: List of fill dictionaries (solid colors or gradients)

        Returns:
            Set operation for fills attribute

        Example:
            >>> api = PenpotAPI()
            >>> gradient = api.create_gradient_fill('linear', '#ff0000', '#0000ff')
            >>> op = api.create_fill_operation([gradient])
        """
        return self.create_set_operation('fills', fills)

    def create_stroke_operation(self, strokes: List[dict]) -> dict:
        """
        Create operation to set stroke(s) on object.

        Args:
            strokes: List of stroke dictionaries

        Returns:
            Set operation for strokes attribute

        Example:
            >>> api = PenpotAPI()
            >>> stroke = api.create_stroke('#000000', width=2.0)
            >>> op = api.create_stroke_operation([stroke])
        """
        return self.create_set_operation('strokes', strokes)

    def create_shadow_operation(self, shadows: List[dict]) -> dict:
        """
        Create operation to set shadow(s) on object.

        Args:
            shadows: List of shadow dictionaries

        Returns:
            Set operation for shadow attribute

        Example:
            >>> api = PenpotAPI()
            >>> shadow = api.create_shadow('#00000080', 2, 2, 4)
            >>> op = api.create_shadow_operation([shadow])
        """
        return self.create_set_operation('shadow', shadows)

    def create_blur_operation(self, blur: dict) -> dict:
        """
        Create operation to set blur effect on object.

        Args:
            blur: Blur effect dictionary

        Returns:
            Set operation for blur attribute

        Example:
            >>> api = PenpotAPI()
            >>> blur = api.create_blur('layer-blur', 10)
            >>> op = api.create_blur_operation(blur)
        """
        return self.create_set_operation('blur', blur)

    # ========== COMMENT & COLLABORATION METHODS ==========

    def create_comment_thread(
        self,
        file_id: str,
        page_id: str,
        x: float,
        y: float,
        content: str,
        frame_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new comment thread at a specific position.

        Args:
            file_id: UUID of the file
            page_id: UUID of the page
            x: X position of comment marker
            y: Y position of comment marker
            content: Initial comment text
            frame_id: Optional frame ID if comment is within a frame

        Returns:
            Created comment thread information including thread_id

        Example:
            >>> api = PenpotAPI()
            >>> thread = api.create_comment_thread(
            ...     file_id="file-123",
            ...     page_id="page-1",
            ...     x=100, y=100,
            ...     content="This button should be larger"
            ... )
            >>> print(thread['id'])
        """
        url = f"{self.base_url}/rpc/command/create-comment-thread"

        payload = {
            "file-id": file_id,
            "page-id": page_id,
            "position": {
                "x": x,
                "y": y
            },
            "content": content
        }

        if frame_id:
            payload["frame-id"] = frame_id

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nComment thread created: {data.get('id')}")

        return data

    def add_comment(
        self,
        thread_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Add a comment to an existing thread.

        Args:
            thread_id: UUID of the comment thread
            content: Comment text

        Returns:
            Created comment information

        Example:
            >>> api = PenpotAPI()
            >>> comment = api.add_comment(
            ...     thread_id="thread-123",
            ...     content="I agree, let's increase it by 20%"
            ... )
        """
        url = f"{self.base_url}/rpc/command/add-comment"

        payload = {
            "thread-id": thread_id,
            "content": content
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nComment added to thread {thread_id}")

        return data

    def get_comment_threads(
        self,
        file_id: str,
        page_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all comment threads for a file or page.

        Args:
            file_id: UUID of the file
            page_id: Optional UUID of specific page (if None, returns all threads)

        Returns:
            List of comment thread dictionaries

        Example:
            >>> api = PenpotAPI()
            >>> threads = api.get_comment_threads(file_id="file-123")
            >>> for thread in threads:
            ...     print(f"Thread at ({thread['position']['x']}, {thread['position']['y']})")
        """
        url = f"{self.base_url}/rpc/query/comment-threads"

        payload = {
            "file-id": file_id
        }

        if page_id:
            payload["page-id"] = page_id

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nRetrieved {len(data)} comment threads")

        return data

    def get_thread_comments(
        self,
        thread_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all comments in a thread.

        Args:
            thread_id: UUID of the comment thread

        Returns:
            List of comment dictionaries in chronological order

        Example:
            >>> api = PenpotAPI()
            >>> comments = api.get_thread_comments(thread_id="thread-123")
            >>> for comment in comments:
            ...     print(f"{comment['owner-name']}: {comment['content']}")
        """
        url = f"{self.base_url}/rpc/query/comments"

        payload = {
            "thread-id": thread_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nRetrieved {len(data)} comments from thread")

        return data

    def update_comment_thread_status(
        self,
        thread_id: str,
        is_resolved: bool
    ) -> Dict[str, Any]:
        """
        Update the resolved status of a comment thread.

        Args:
            thread_id: UUID of the comment thread
            is_resolved: Whether the thread should be marked as resolved

        Returns:
            Updated thread information

        Example:
            >>> api = PenpotAPI()
            >>> api.update_comment_thread_status("thread-123", is_resolved=True)
        """
        url = f"{self.base_url}/rpc/command/update-comment-thread"

        payload = {
            "id": thread_id,
            "is-resolved": is_resolved
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            status = "resolved" if is_resolved else "unresolved"
            print(f"\nThread {thread_id} marked as {status}")

        return data

    def delete_comment_thread(
        self,
        thread_id: str
    ) -> Dict[str, Any]:
        """
        Delete a comment thread and all its comments.

        Args:
            thread_id: UUID of the comment thread

        Returns:
            Success confirmation

        Example:
            >>> api = PenpotAPI()
            >>> api.delete_comment_thread("thread-123")
        """
        url = f"{self.base_url}/rpc/command/delete-comment-thread"

        payload = {
            "id": thread_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)

        try:
            data = response.json()
        except Exception:
            data = {"success": True, "id": thread_id}

        if self.debug:
            print(f"\nComment thread deleted: {thread_id}")

        return data

    def create_file(
        self,
        name: str,
        project_id: str,
        is_shared: bool = False,
        features: Optional[List[str]] = None,
        file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Penpot file.

        Args:
            name: File name
            project_id: UUID of the project to create file in
            is_shared: Whether the file is shared
            features: Optional list of feature flags
            file_id: Optional custom file UUID (auto-generated if not provided)

        Returns:
            Dictionary containing created file information including:
            - id: File UUID
            - name: File name
            - projectId: Project UUID
            - created: Creation timestamp
            - modified: Last modified timestamp

        Example:
            >>> api = PenpotAPI()
            >>> result = api.create_file(name="My Design", project_id="abc-123")
            >>> print(result['id'])
        """
        url = f"{self.base_url}/rpc/command/create-file"

        payload = {
            "name": name,
            "project-id": project_id,
            "is-shared": is_shared
        }

        if file_id:
            payload["id"] = file_id
        if features:
            payload["features"] = features

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nFile created: {data.get('name')} (ID: {data.get('id')})")

        return data

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Delete a Penpot file.

        Args:
            file_id: UUID of the file to delete

        Returns:
            Success confirmation. If API returns empty response,
            returns {"success": True, "id": file_id}

        Example:
            >>> api = PenpotAPI()
            >>> result = api.delete_file(file_id="abc-123")
        """
        url = f"{self.base_url}/rpc/command/delete-file"

        payload = {
            "id": file_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        
        # Some DELETE operations might return empty responses or just status codes
        try:
            data = response.json()
        except Exception:
            # If no JSON response, return success based on status code
            data = {"success": True, "id": file_id}

        if self.debug:
            print(f"\nFile deleted: {file_id}")

        return data

    def rename_file(self, file_id: str, name: str) -> Dict[str, Any]:
        """
        Rename a Penpot file.

        Args:
            file_id: UUID of the file to rename
            name: New file name

        Returns:
            Updated file information

        Example:
            >>> api = PenpotAPI()
            >>> result = api.rename_file(file_id="abc-123", name="New Name")
            >>> print(result['name'])
        """
        url = f"{self.base_url}/rpc/command/rename-file"

        payload = {
            "id": file_id,
            "name": name
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nFile renamed to: {name} (ID: {file_id})")

        return data

    def set_file_shared(self, file_id: str, is_shared: bool) -> Dict[str, Any]:
        """
        Set file sharing status.

        Args:
            file_id: UUID of the file
            is_shared: Whether the file should be shared

        Returns:
            Updated file information

        Example:
            >>> api = PenpotAPI()
            >>> result = api.set_file_shared(file_id="abc-123", is_shared=True)
            >>> print(result['isShared'])
        """
        url = f"{self.base_url}/rpc/command/set-file-shared"

        payload = {
            "id": file_id,
            "is-shared": is_shared
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            shared_status = "shared" if is_shared else "not shared"
            print(f"\nFile set to {shared_status}: {file_id}")

        return data

    def get_file_libraries(
        self,
        file_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all libraries linked to a file.

        Args:
            file_id: UUID of the file

        Returns:
            List of linked library dictionaries

        Example:
            >>> api = PenpotAPI()
            >>> libraries = api.get_file_libraries(file_id="file-123")
            >>> for lib in libraries:
            ...     print(f"{lib['name']}: {len(lib['components'])} components")
        """
        url = f"{self.base_url}/rpc/query/file-libraries"

        payload = {
            "file-id": file_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nRetrieved {len(data)} linked libraries")

        return data

    def link_file_to_library(
        self,
        file_id: str,
        library_id: str
    ) -> Dict[str, Any]:
        """
        Link a file to a library to use its components.

        Args:
            file_id: UUID of the file
            library_id: UUID of the library file to link

        Returns:
            Updated file information

        Example:
            >>> api = PenpotAPI()
            >>> api.link_file_to_library(
            ...     file_id="file-123",
            ...     library_id="library-456"
            ... )
        """
        url = f"{self.base_url}/rpc/command/link-file-to-library"

        payload = {
            "file-id": file_id,
            "library-id": library_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nLinked file {file_id} to library {library_id}")

        return data

    def unlink_file_from_library(
        self,
        file_id: str,
        library_id: str
    ) -> Dict[str, Any]:
        """
        Unlink a file from a library.

        Args:
            file_id: UUID of the file
            library_id: UUID of the library file to unlink

        Returns:
            Success confirmation

        Example:
            >>> api = PenpotAPI()
            >>> api.unlink_file_from_library("file-123", "library-456")
        """
        url = f"{self.base_url}/rpc/command/unlink-file-from-library"

        payload = {
            "file-id": file_id,
            "library-id": library_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)

        try:
            data = response.json()
        except Exception:
            data = {"success": True}

        if self.debug:
            print(f"\nUnlinked file {file_id} from library {library_id}")

        return data

    def get_library_components(
        self,
        library_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all components available in a library.

        Args:
            library_id: UUID of the library file

        Returns:
            List of component dictionaries with metadata

        Example:
            >>> api = PenpotAPI()
            >>> components = api.get_library_components(library_id="library-456")
            >>> for comp in components:
            ...     print(f"{comp['name']} (ID: {comp['id']})")
        """
        url = f"{self.base_url}/rpc/query/library-components"

        payload = {
            "library-id": library_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nRetrieved {len(data)} components from library")

        return data

    def instantiate_component(
        self,
        file_id: str,
        page_id: str,
        library_id: str,
        component_id: str,
        x: float,
        y: float,
        frame_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an instance of a library component in the design.

        Args:
            file_id: UUID of the target file
            page_id: UUID of the target page
            library_id: UUID of the library file
            component_id: UUID of the component to instantiate
            x: X position for the instance
            y: Y position for the instance
            frame_id: Optional parent frame ID

        Returns:
            Updated file information with new component instance

        Example:
            >>> api = PenpotAPI()
            >>> with api.editing_session("file-123") as (session_id, revn):
            ...     result = api.instantiate_component(
            ...         file_id="file-123",
            ...         page_id="page-1",
            ...         library_id="library-456",
            ...         component_id="button-component",
            ...         x=100, y=100
            ...     )
        """
        # This uses the update_file mechanism with a special
        # instantiate-component change operation
        with self.editing_session(file_id) as (session_id, revn):
            instance_id = str(uuid.uuid4())

            change = {
                'type': 'add-component-instance',
                'id': instance_id,
                'pageId': page_id,
                'libraryId': library_id,
                'componentId': component_id,
                'x': x,
                'y': y
            }

            if frame_id:
                change['frameId'] = frame_id

            result = self.update_file(file_id, session_id, revn, [change])

            if self.debug:
                print(f"\nInstantiated component {component_id} as {instance_id}")

            return result

    def sync_file_library(
        self,
        file_id: str,
        library_id: str
    ) -> Dict[str, Any]:
        """
        Synchronize component instances with their library source.

        Updates all instances of components from the specified library
        to match the current library version.

        Args:
            file_id: UUID of the file
            library_id: UUID of the library to sync

        Returns:
            Sync result information

        Example:
            >>> api = PenpotAPI()
            >>> result = api.sync_file_library("file-123", "library-456")
            >>> print(f"Updated {result['updated-count']} instances")
        """
        url = f"{self.base_url}/rpc/command/sync-file"

        payload = {
            "file-id": file_id,
            "library-id": library_id
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            print(f"\nSynchronized library {library_id} in file {file_id}")

        return data

    def publish_library(
        self,
        file_id: str,
        publish: bool = True
    ) -> Dict[str, Any]:
        """
        Publish or unpublish a file as a shared library.

        Args:
            file_id: UUID of the file
            publish: Whether to publish (True) or unpublish (False)

        Returns:
            Updated file information

        Example:
            >>> api = PenpotAPI()
            >>> # Publish file as library
            >>> api.publish_library(file_id="file-123", publish=True)
        """
        url = f"{self.base_url}/rpc/command/set-file-shared"

        payload = {
            "id": file_id,
            "is-shared": publish
        }

        response = self._make_authenticated_request('post', url, json=payload, use_transit=False)
        data = response.json()

        if self.debug:
            action = "published" if publish else "unpublished"
            print(f"\nFile {file_id} {action} as library")

        return data

    def create_export(self, file_id: str, page_id: str, object_id: str,
                      export_type: str = "png", scale: int = 1,
                      email: Optional[str] = None, password: Optional[str] = None,
                      profile_id: Optional[str] = None):
        """
        Create an export job for a Penpot object.

        Args:
            file_id: The file ID
            page_id: The page ID
            object_id: The object ID to export
            export_type: Type of export (png, svg, pdf)
            scale: Scale factor for the export
            name: Name for the export
            suffix: Suffix to add to the export name
            email: Email for authentication (if different from instance)
            password: Password for authentication (if different from instance)
            profile_id: Optional profile ID (if not provided, will be fetched automatically)

        Returns:
            Export resource ID
        """
        # This uses the cookie auth approach, which requires login
        token = self.login_for_export(email, password)

        # If profile_id is not provided, get it from instance variable
        if not profile_id:
            profile_id = self.profile_id

        if not profile_id:
            raise ValueError("Profile ID not available. It should be automatically extracted during login.")

        # Build the URL for export creation
        url = f"{self.base_url}/export"

        # Set up the data for the export
        payload = {
            "~:wait": True,
            "~:exports": [
                {"~:type": f"~:{export_type}",
                 "~:suffix": "",
                 "~:scale": scale,
                 "~:page-id": f"~u{page_id}",
                 "~:file-id": f"~u{file_id}",
                 "~:name": "",
                 "~:object-id": f"~u{object_id}"}
            ],
            "~:profile-id": f"~u{profile_id}",
            "~:cmd": "~:export-shapes"
        }

        if self.debug:
            print("\nCreating export with parameters:")
            print(json.dumps(payload, indent=2))

        # Create a session with the auth token
        export_session = requests.Session()
        export_session.cookies.set("auth-token", token)

        headers = {
            "Content-Type": "application/transit+json",
            "Accept": "application/transit+json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Make the request
        response = export_session.post(url, json=payload, headers=headers)

        if self.debug and response.status_code != 200:
            print(f"\nError response: {response.status_code}")
            print(f"Response text: {response.text}")

        response.raise_for_status()

        # Parse the response
        data = response.json()

        if self.debug:
            print("\nExport created successfully")
            print(f"Response: {json.dumps(data, indent=2)}")

        # Extract and return the resource ID
        resource_id = data.get("~:id")
        if not resource_id:
            raise ValueError("Resource ID not found in response")

        return resource_id

    def get_export_resource(self,
                            resource_id: str,
                            save_to_file: Optional[str] = None,
                            email: Optional[str] = None,
                            password: Optional[str] = None) -> Union[bytes,
                                                                     str]:
        """
        Download an export resource by ID.

        Args:
            resource_id: The resource ID from create_export
            save_to_file: Path to save the file (if None, returns the content)
            email: Email for authentication (if different from instance)
            password: Password for authentication (if different from instance)

        Returns:
            Either the file content as bytes, or the path to the saved file
        """
        # This uses the cookie auth approach, which requires login
        token = self.login_for_export(email, password)

        # Build the URL for the resource
        url = f"{self.base_url}/export"

        payload = {
            "~:wait": False,
            "~:cmd": "~:get-resource",
            "~:id": resource_id
        }
        headers = {
            "Content-Type": "application/transit+json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if self.debug:
            print(f"\nFetching export resource: {url}")

        # Create a session with the auth token
        export_session = requests.Session()
        export_session.cookies.set("auth-token", token)

        # Make the request
        response = export_session.post(url, json=payload, headers=headers)

        if self.debug and response.status_code != 200:
            print(f"\nError response: {response.status_code}")
            print(f"Response headers: {response.headers}")

        response.raise_for_status()

        # Get the content type
        content_type = response.headers.get('Content-Type', '')

        if self.debug:
            print(f"\nResource fetched successfully")
            print(f"Content-Type: {content_type}")
            print(f"Content length: {len(response.content)} bytes")

        # Determine filename if saving to file
        if save_to_file:
            if os.path.isdir(save_to_file):
                # If save_to_file is a directory, we need to figure out the filename
                filename = None

                # Try to get filename from Content-Disposition header
                content_disp = response.headers.get('Content-Disposition', '')
                if 'filename=' in content_disp:
                    filename = content_disp.split('filename=')[1].strip('"\'')

                # If we couldn't get a filename, use the resource_id with an extension
                if not filename:
                    ext = content_type.split('/')[-1].split(';')[0]
                    if ext in ('jpeg', 'png', 'pdf', 'svg+xml'):
                        if ext == 'svg+xml':
                            ext = 'svg'
                        filename = f"{resource_id}.{ext}"
                    else:
                        filename = f"{resource_id}"

                save_path = os.path.join(save_to_file, filename)
            else:
                # Use the provided path directly
                save_path = save_to_file

            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

            # Save the content to file
            with open(save_path, 'wb') as f:
                f.write(response.content)

            if self.debug:
                print(f"\nSaved resource to {save_path}")

            return save_path
        else:
            # Return the content
            return response.content

    def export_and_download(self, file_id: str, page_id: str, object_id: str,
                            save_to_file: Optional[str] = None, export_type: str = "png",
                            scale: int = 1, name: str = "Board", suffix: str = "",
                            email: Optional[str] = None, password: Optional[str] = None,
                            profile_id: Optional[str] = None) -> Union[bytes, str]:
        """
        Create and download an export in one step.

        This is a convenience method that combines create_export and get_export_resource.

        Args:
            file_id: The file ID
            page_id: The page ID
            object_id: The object ID to export
            save_to_file: Path to save the file (if None, returns the content)
            export_type: Type of export (png, svg, pdf)
            scale: Scale factor for the export
            name: Name for the export
            suffix: Suffix to add to the export name
            email: Email for authentication (if different from instance)
            password: Password for authentication (if different from instance)
            profile_id: Optional profile ID (if not provided, will be fetched automatically)

        Returns:
            Either the file content as bytes, or the path to the saved file
        """
        # Create the export
        resource_id = self.create_export(
            file_id=file_id,
            page_id=page_id,
            object_id=object_id,
            export_type=export_type,
            scale=scale,
            email=email,
            password=password,
            profile_id=profile_id
        )

        # Download the resource
        return self.get_export_resource(
            resource_id=resource_id,
            save_to_file=save_to_file,
            email=email,
            password=password
        )

    def extract_components(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract components from file data.

        This processes a file's data to extract and normalize component information.

        Args:
            file_data: The file data from get_file

        Returns:
            Dictionary containing components information
        """
        components = {}
        components_index = file_data.get('data', {}).get('componentsIndex', {})

        for component_id, component_data in components_index.items():
            # Extract basic component info
            component = {
                'id': component_id,
                'name': component_data.get('name', 'Unnamed'),
                'path': component_data.get('path', []),
                'shape': component_data.get('shape', ''),
                'fileId': component_data.get('fileId', file_data.get('id')),
                'created': component_data.get('created'),
                'modified': component_data.get('modified')
            }

            # Add the component to our collection
            components[component_id] = component

        return {'components': components}

    def analyze_file_structure(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze file structure and return summary information.

        Args:
            file_data: The file data from get_file

        Returns:
            Dictionary containing analysis information
        """
        data = file_data.get('data', {})

        # Count pages
        pages = data.get('pagesIndex', {})
        page_count = len(pages)

        # Count objects by type
        object_types = {}
        total_objects = 0

        for page_id, page_data in pages.items():
            objects = page_data.get('objects', {})
            total_objects += len(objects)

            for obj_id, obj_data in objects.items():
                obj_type = obj_data.get('type', 'unknown')
                object_types[obj_type] = object_types.get(obj_type, 0) + 1

        # Count components
        components = data.get('componentsIndex', {})
        component_count = len(components)

        # Count colors, typographies, etc.
        colors = data.get('colorsIndex', {})
        color_count = len(colors)

        typographies = data.get('typographiesIndex', {})
        typography_count = len(typographies)

        return {
            'pageCount': page_count,
            'objectCount': total_objects,
            'objectTypes': object_types,
            'componentCount': component_count,
            'colorCount': color_count,
            'typographyCount': typography_count,
            'fileName': file_data.get('name', 'Unknown'),
            'fileId': file_data.get('id')
        }


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Penpot API Tool')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # List projects command
    list_parser = subparsers.add_parser('list-projects', help='List all projects')

    # Get project command
    project_parser = subparsers.add_parser('get-project', help='Get project details')
    project_parser.add_argument('--id', required=True, help='Project ID')

    # List files command
    files_parser = subparsers.add_parser('list-files', help='List files in a project')
    files_parser.add_argument('--project-id', required=True, help='Project ID')

    # Get file command
    file_parser = subparsers.add_parser('get-file', help='Get file details')
    file_parser.add_argument('--file-id', required=True, help='File ID')
    file_parser.add_argument('--save', action='store_true', help='Save file data to JSON')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export an object')
    export_parser.add_argument(
        '--profile-id',
        required=False,
        help='Profile ID (optional, will be fetched automatically if not provided)')
    export_parser.add_argument('--file-id', required=True, help='File ID')
    export_parser.add_argument('--page-id', required=True, help='Page ID')
    export_parser.add_argument('--object-id', required=True, help='Object ID')
    export_parser.add_argument(
        '--type',
        default='png',
        choices=[
            'png',
            'svg',
            'pdf'],
        help='Export type')
    export_parser.add_argument('--scale', type=int, default=1, help='Scale factor')
    export_parser.add_argument('--output', required=True, help='Output file path')

    # Parse arguments
    args = parser.parse_args()

    # Create API client
    api = PenpotAPI(debug=args.debug)

    # Handle different commands
    if args.command == 'list-projects':
        projects = api.list_projects()
        print(f"Found {len(projects)} projects:")
        for project in projects:
            print(f"- {project.get('name')} - {project.get('teamName')} (ID: {project.get('id')})")

    elif args.command == 'get-project':
        try:
            project = api.get_project(args.id)
            print(f"Project: {project.get('name')}")
            print(json.dumps(project, indent=2))
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 404:
                print(f"Project not found: {args.id}")
            else:
                print(f"Error retrieving project: {e}")

    elif args.command == 'list-files':
        files = api.get_project_files(args.project_id)
        print(f"Found {len(files)} files:")
        for file in files:
            print(f"- {file.get('name')} (ID: {file.get('id')})")

    elif args.command == 'get-file':
        file_data = api.get_file(args.file_id, save_data=args.save)
        print(f"File: {file_data.get('name')}")
        if args.save:
            print(f"Data saved to {args.file_id}.json")
        else:
            print("File metadata:")
            print(json.dumps({k: v for k, v in file_data.items() if k != 'data'}, indent=2))

    elif args.command == 'export':
        output_path = api.export_and_download(
            file_id=args.file_id,
            page_id=args.page_id,
            object_id=args.object_id,
            export_type=args.type,
            scale=args.scale,
            save_to_file=args.output,
            profile_id=args.profile_id
        )
        print(f"Exported to: {output_path}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
