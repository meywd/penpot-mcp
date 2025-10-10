"""Test changing fills in text object content structure."""
import os
import json
import uuid
from penpot_mcp.api.penpot_api import PenpotAPI


FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"
OBJECT_ID = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"


def main():
    api = PenpotAPI(debug=True)

    print("=== Step 1: Get current object structure ===")
    file_data = api.get_file(FILE_ID)
    current_revn = file_data.get('revn', 0)
    print(f"Current revision: {current_revn}")

    # Find the object
    pages_index = file_data.get('data', {}).get('pagesIndex', {})
    obj = None
    for page_data in pages_index.values():
        if OBJECT_ID in page_data.get('objects', {}):
            obj = page_data['objects'][OBJECT_ID]
            break

    if not obj:
        print(f"ERROR: Object {OBJECT_ID} not found")
        return

    print(f"\nObject type: {obj.get('type')}")
    print(f"Current content structure:")
    print(json.dumps(obj.get('content', {}), indent=2))

    print("\n=== Step 2: Test modifying content structure with YELLOW ===")

    # Get current content
    content = obj.get('content', {})

    # Modify fills in the content structure (keeping the same structure)
    if content.get('children'):
        for ps in content['children']:
            if ps.get('children'):
                for para in ps['children']:
                    # Set fills at paragraph level
                    para['fills'] = [{
                        'fillColor': '#FFFF00',  # YELLOW
                        'fillOpacity': 1.0
                    }]
                    # Set fills at text node level
                    if para.get('children'):
                        for text_node in para['children']:
                            text_node['fills'] = [{
                                'fillColor': '#FFFF00',  # YELLOW
                                'fillOpacity': 1.0
                            }]

    print("Modified content structure:")
    print(json.dumps(content, indent=2))

    # Create change operation
    session_id = str(uuid.uuid4())

    payload = {
        "~:id": f"~u{FILE_ID}",
        "~:session-id": f"~u{session_id}",
        "~:revn": current_revn,
        "~:changes": [{
            "~:type": "~:mod-obj",
            "~:id": f"~u{OBJECT_ID}",
            "~:operations": [{
                "~:type": "~:set",
                "~:attr": "~:content",
                "~:val": content  # Set the entire content structure
            }]
        }]
    }

    print("\n=== Step 3: Send update request ===")
    url = f"{api.base_url}/rpc/command/update-file"

    try:
        response = api._make_authenticated_request('post', url, json=payload, use_transit=True)
        result = response.json()
        print(f"Response status: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        print("[OK] Content update succeeded")
    except Exception as e:
        print(f"[X] Content update FAILED: {e}")
        return

    print("\n=== Step 4: Verify the change ===")
    file_data = api.get_file(FILE_ID)
    pages_index = file_data.get('data', {}).get('pagesIndex', {})
    for page_data in pages_index.values():
        if OBJECT_ID in page_data.get('objects', {}):
            obj = page_data['objects'][OBJECT_ID]
            content = obj.get('content', {})

            # Check paragraph fills
            if content.get('children'):
                para = content['children'][0]['children'][0]
                para_fills = para.get('fills', [])
                print(f"Paragraph fills: {json.dumps(para_fills, indent=2)}")

                # Check text node fills
                text_node = para['children'][0]
                text_fills = text_node.get('fills', [])
                print(f"Text node fills: {json.dumps(text_fills, indent=2)}")

                if para_fills and para_fills[0].get('fillColor') == '#FFFF00':
                    print("[OK] Text color changed to YELLOW successfully!")
                else:
                    print(f"[X] Color not changed. Current: {para_fills[0].get('fillColor') if para_fills else 'NONE'}")
            break

    print("\n=== CONCLUSION ===")
    print("Text objects require modifying the 'content' structure, not top-level 'fills'")
    print("The fills must be set at both paragraph and text node levels")
    print("Property names use camelCase: fillColor, fillOpacity")


if __name__ == "__main__":
    main()
