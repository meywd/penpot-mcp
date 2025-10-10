"""List all text objects and their colors."""
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"
api = PenpotAPI(debug=False)

file_data = api.get_file(FILE_ID)
pages_index = file_data.get('data', {}).get('pagesIndex', {})

print("Text objects in file:")
for page_id, page_data in pages_index.items():
    for obj_id, obj in page_data.get('objects', {}).items():
        if obj.get('type') == 'text':
            name = obj.get('name', 'Unnamed')
            content = obj.get('content', {})

            # Try to extract color
            color = "N/A"
            if content.get('children'):
                try:
                    para = content['children'][0]['children'][0]
                    fills = para.get('fills', [])
                    if fills:
                        color = fills[0].get('fillColor', 'N/A')
                except:
                    pass

            print(f"  - {name} (ID: {obj_id[:8]}...): {color}")
