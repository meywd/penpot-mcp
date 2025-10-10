"""Check the structure of the manually changed text object."""
import os
import json
from penpot_mcp.api.penpot_api import PenpotAPI


def check_object():
    """Fetch and display the object structure after manual change."""
    api = PenpotAPI(debug=False)

    file_id = "689fbaf0-efce-81fe-8006-ed108f8a2104"
    object_id = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"

    print(f"Fetching file {file_id}...")
    print(f"Looking for object {object_id}...\n")

    # Get file data
    file_data = api.get_file(file_id)
    pages_index = file_data.get('data', {}).get('pagesIndex', {})

    obj = None
    for page_data in pages_index.values():
        if object_id in page_data.get('objects', {}):
            obj = page_data['objects'][object_id]
            break

    if not obj:
        print("ERROR: Object not found!")
        return

    print("=== OBJECT STRUCTURE (after manual change) ===\n")
    print(json.dumps(obj, indent=2))

    print("\n=== CONTENT STRUCTURE DETAIL ===")
    content = obj.get('content', {})
    if 'children' in content:
        for i, ps in enumerate(content['children']):
            print(f"\nParagraph-set {i}:")
            print(f"  Type: {ps.get('type')}")
            for j, para in enumerate(ps.get('children', [])):
                print(f"\n  Paragraph {j}:")
                print(f"    Type: {para.get('type')}")
                print(f"    Fills: {para.get('fills', 'NONE')}")
                for k, text_node in enumerate(para.get('children', [])):
                    print(f"\n    Text node {k}:")
                    print(f"      Text: '{text_node.get('text', '')}'")
                    print(f"      Fills: {text_node.get('fills', 'NONE')}")
                    print(f"      All properties: {json.dumps(text_node, indent=8)}")


if __name__ == "__main__":
    check_object()
