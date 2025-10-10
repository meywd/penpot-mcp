"""Debug the Transit+JSON conversion for content structures."""
import os
import json
from penpot_mcp.api.penpot_api import PenpotAPI

FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"
OBJECT_ID = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"

def main():
    api = PenpotAPI(debug=True)

    # Get the file and object
    file_data = api.get_file(FILE_ID)
    pages_index = file_data.get('data', {}).get('pagesIndex', {})

    obj = None
    for page_data in pages_index.values():
        if OBJECT_ID in page_data.get('objects', {}):
            obj = page_data['objects'][OBJECT_ID]
            break

    if not obj:
        print(f"ERROR: Object {OBJECT_ID} not found")
        return

    print("=== Original Content Structure ===")
    print(json.dumps(obj.get('content', {}), indent=2))

    # Modify the content to yellow
    content = obj.get('content', {})
    fills_content = [{
        'fillColor': '#FFFF00',
        'fillOpacity': 1.0
    }]

    if 'children' in content:
        for paragraph_set in content['children']:
            if 'children' in paragraph_set:
                for paragraph in paragraph_set['children']:
                    paragraph['fills'] = fills_content
                    if 'children' in paragraph:
                        for text_node in paragraph['children']:
                            text_node['fills'] = fills_content

    print("\n=== Modified Content Structure (before Transit conversion) ===")
    print(json.dumps(content, indent=2))

    # Create the operation
    operation = {
        'type': 'set',
        'attr': 'content',
        'val': content
    }

    print("\n=== Operation (before Transit conversion) ===")
    print(json.dumps(operation, indent=2))

    # Create change
    change = {
        'type': 'mod-obj',
        'id': OBJECT_ID,
        'operations': [operation]
    }

    print("\n=== Change (before Transit conversion) ===")
    print(json.dumps(change, indent=2))

    # Convert to Transit
    transit_changes = api._convert_changes_to_transit([change])

    print("\n=== Transit-converted Changes ===")
    print(json.dumps(transit_changes, indent=2))

    # Check if content structure has Transit prefixes (should NOT have them)
    transit_content = transit_changes[0]['~:operations'][0]['~:val']
    print("\n=== Checking Transit Content Structure ===")
    print(f"Root keys: {list(transit_content.keys())}")

    has_transit_prefix = any(k.startswith('~:') for k in transit_content.keys())
    if has_transit_prefix:
        print("[X] ERROR: Content structure has Transit prefixes (should have plain keys)")
    else:
        print("[OK] Content structure has plain keys (correct)")

    # Check fills
    if 'children' in transit_content:
        ps = transit_content['children'][0]
        para = ps['children'][0]
        fills = para.get('fills', [])
        if fills:
            fill_keys = list(fills[0].keys())
            print(f"\nFill keys: {fill_keys}")
            if any(k.startswith('~:') for k in fill_keys):
                print("[X] ERROR: Fill object has Transit prefixes (should have plain keys)")
            else:
                print("[OK] Fill object has plain keys (correct)")

if __name__ == "__main__":
    main()
