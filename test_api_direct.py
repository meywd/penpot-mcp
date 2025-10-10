"""Test fill object format directly using PenpotAPI."""
import os
import json
import uuid
from penpot_mcp.api.penpot_api import PenpotAPI


FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"
OBJECT_ID = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"


def main():
    api = PenpotAPI(debug=True)

    print("=== Step 1: Get current file state ===")
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

    if obj:
        print(f"Current fills: {json.dumps(obj.get('fills', []), indent=2)}")
    else:
        print(f"ERROR: Object {OBJECT_ID} not found")
        return

    print("\n=== Step 2: Test with KEBAB-CASE (expected to not work) ===")
    session_id_1 = str(uuid.uuid4())
    revn_1 = current_revn

    # Manually construct payload with kebab-case
    payload_kebab = {
        "~:id": f"~u{FILE_ID}",
        "~:session-id": f"~u{session_id_1}",
        "~:revn": revn_1,
        "~:changes": [{
            "~:type": "~:mod-obj",
            "~:id": f"~u{OBJECT_ID}",
            "~:operations": [{
                "~:type": "~:set",
                "~:attr": "~:fills",
                "~:val": [{
                    "~:fill-color": "#FF0000",  # RED - kebab-case
                    "~:fill-opacity": 1.0
                }]
            }]
        }]
    }

    print("Payload with kebab-case:")
    print(json.dumps(payload_kebab, indent=2))

    # Send request
    url = f"{api.base_url}/rpc/command/update-file"
    try:
        response_kebab = api._make_authenticated_request('post', url, json=payload_kebab, use_transit=True)
        result_kebab = response_kebab.json()
        print(f"\nResponse: {json.dumps(result_kebab, indent=2)}")
        kebab_success = True
    except Exception as e:
        print(f"\n[X] KEBAB-CASE FAILED with error: {e}")
        print("This is EXPECTED - kebab-case is not valid")
        kebab_success = False
        new_revn_1 = revn_1  # Revision didn't change

    # Check if it was accepted
    if kebab_success:
        if isinstance(result_kebab, list):
            # Transit format - convert
            result_dict = {}
            for i in range(1, len(result_kebab), 2):
                key = str(result_kebab[i]).replace('~:', '')
                result_dict[key] = result_kebab[i + 1]
            new_revn_1 = result_dict.get('revn', revn_1)
        else:
            new_revn_1 = result_kebab.get('revn', revn_1)
        print(f"New revision after kebab-case: {new_revn_1}")
    else:
        print(f"Revision unchanged: {new_revn_1}")

    # Verify the change
    if kebab_success:
        print("\n=== Step 3: Verify color after kebab-case ===")
        file_data = api.get_file(FILE_ID)
        pages_index = file_data.get('data', {}).get('pagesIndex', {})
        for page_data in pages_index.values():
            if OBJECT_ID in page_data.get('objects', {}):
                obj = page_data['objects'][OBJECT_ID]
                fills = obj.get('fills', [])
                print(f"Fills: {json.dumps(fills, indent=2)}")
                if fills and isinstance(fills, list) and len(fills) > 0:
                    fill_color = fills[0].get('fillColor', 'NOT SET')
                    print(f"Fill color: {fill_color}")
                    if fill_color == "#FF0000" or fill_color == "#ff0000":
                        print("[OK] KEBAB-CASE WORKED (unexpected!)")
                    else:
                        print("[X] KEBAB-CASE DID NOT WORK (expected)")
                break
    else:
        print("\n=== Step 3: Skipping verification (kebab-case was rejected by API) ===")

    print("\n=== Step 4: Test with CAMELCASE (expected to work) ===")
    session_id_2 = str(uuid.uuid4())
    revn_2 = new_revn_1

    # Manually construct payload with camelCase
    payload_camel = {
        "~:id": f"~u{FILE_ID}",
        "~:session-id": f"~u{session_id_2}",
        "~:revn": revn_2,
        "~:changes": [{
            "~:type": "~:mod-obj",
            "~:id": f"~u{OBJECT_ID}",
            "~:operations": [{
                "~:type": "~:set",
                "~:attr": "~:fills",
                "~:val": [{
                    "~:fillColor": "#00FF00",  # GREEN - camelCase
                    "~:fillOpacity": 1.0
                }]
            }]
        }]
    }

    print("Payload with camelCase:")
    print(json.dumps(payload_camel, indent=2))

    # Send request
    try:
        response_camel = api._make_authenticated_request('post', url, json=payload_camel, use_transit=True)
        result_camel = response_camel.json()
        print(f"\nResponse: {json.dumps(result_camel, indent=2)}")
        camel_success = True
    except Exception as e:
        print(f"\n[X] CAMELCASE FAILED with error: {e}")
        print("This is UNEXPECTED - camelCase should be valid")
        camel_success = False
        new_revn_2 = revn_2  # Revision didn't change

    # Check if it was accepted
    if camel_success:
        if isinstance(result_camel, list):
            # Transit format - convert
            result_dict = {}
            for i in range(1, len(result_camel), 2):
                key = str(result_camel[i]).replace('~:', '')
                result_dict[key] = result_camel[i + 1]
            new_revn_2 = result_dict.get('revn', revn_2)
        else:
            new_revn_2 = result_camel.get('revn', revn_2)
        print(f"New revision after camelCase: {new_revn_2}")
    else:
        print(f"Revision unchanged: {new_revn_2}")

    # Verify the change
    print("\n=== Step 5: Verify color after camelCase ===")
    file_data = api.get_file(FILE_ID)
    pages_index = file_data.get('data', {}).get('pagesIndex', {})
    for page_data in pages_index.values():
        if OBJECT_ID in page_data.get('objects', {}):
            obj = page_data['objects'][OBJECT_ID]
            fills = obj.get('fills', [])
            print(f"Fills: {json.dumps(fills, indent=2)}")
            if fills and isinstance(fills, list) and len(fills) > 0:
                fill_color = fills[0].get('fillColor', 'NOT SET')
                print(f"Fill color: {fill_color}")
                if fill_color == "#00FF00" or fill_color == "#00ff00":
                    print("[OK] CAMELCASE WORKED (expected)")
                else:
                    print("[X] CAMELCASE DID NOT WORK (unexpected!)")
            break

    print("\n=== SUMMARY ===")
    print(f"Kebab-case test: {'[OK] WORKED' if kebab_success else '[X] FAILED (400 Bad Request)'}")
    print(f"CamelCase test: {'[OK] WORKED' if camel_success else '[X] FAILED'}")
    print("\nConclusion:")
    if not kebab_success and camel_success:
        print("[OK] CONFIRMED: Penpot API requires camelCase (fillColor, fillOpacity)")
        print("[X] REJECTED: kebab-case (fill-color, fill-opacity) is not accepted")
        print("\nThe bug in mcp_server.py lines 594-598 is confirmed:")
        print("  fills_transit uses kebab-case which causes 400 Bad Request")
        print("  Should be changed to camelCase like the content fills")
    else:
        print("Unexpected results - further investigation needed")


if __name__ == "__main__":
    main()
