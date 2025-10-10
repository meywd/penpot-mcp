"""Quick verification that Downloads text is now RED."""
from penpot_mcp.api.penpot_api import PenpotAPI

# TODO: Update FILE_ID to your local test file
FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"

# Point to local Penpot instance
api = PenpotAPI(base_url="http://localhost:9001/api", debug=False)

# Get file
file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

# Find Downloads text
for page_data in pages_index.values():
    for obj_id, obj in page_data.get('objects', {}).items():
        if obj.get('type') == 'text' and 'Downloads' in str(obj.get('content', {})):
            content = obj.get('content', {})
            if content.get('children'):
                para = content['children'][0]['children'][0]
                fills = para.get('fills', [])
                if fills:
                    color = fills[0].get('fillColor')
                    print(f"Downloads text color: {color}")
                    if color == '#FF0000':
                        print("✅ [SUCCESS] Downloads text is RED!")
                        exit(0)
                    else:
                        print(f"❌ [FAILED] Expected #FF0000, got {color}")
                        exit(1)
            break

print("Downloads text not found")
exit(1)
