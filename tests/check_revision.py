"""Check what revision the file is actually at."""
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"

api = PenpotAPI(debug=False)

print(f"Fetching file {FILE_ID}...")
file_data = api.get_file(FILE_ID)

print(f"\nFile revision (revn): {file_data.get('revn')}")
print(f"File version (vern): {file_data.get('vern', 'not present')}")
print(f"File name: {file_data.get('name')}")
