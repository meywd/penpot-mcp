"""Test Penpot API with curl-like requests to verify camelCase vs kebab-case."""
import os
import json
import uuid
import requests

API_URL = "http://localhost:9001/api"
USERNAME = "contact@mahmoudsdarwish.com"
PASSWORD = "jqm!UAW_pfc5cnu9wzh"
FILE_ID = "689fbaf0-efce-81fe-8006-ed108f8a2104"
OBJECT_ID = "fab9cafe-e0d9-43c4-9642-295ea9759a5c"

def main():
    session = requests.Session()

    print("=== Step 1: Authenticate ===")
    login_payload = {
        "~:email": USERNAME,
        "~:password": PASSWORD
    }
    login_resp = session.post(
        f"{API_URL}/rpc/command/login-with-password",
        json=login_payload,
        headers={"Content-Type": "application/transit+json"}
    )
    print(f"Login status: {login_resp.status_code}")
    if login_resp.status_code == 200:
        print(f"Response: {json.dumps(login_resp.json(), indent=2)}")

    print("\n=== Step 2: Get file data to retrieve current revision ===")
    file_resp = session.get(f"{API_URL}/rpc/command/get-file?id={FILE_ID}")
    file_data_raw = file_resp.json()

    # Transit format returns a list, convert to dict
    if isinstance(file_data_raw, list):
        file_data = {}
        for i in range(1, len(file_data_raw), 2):
            key = file_data_raw[i].replace('~:', '')
            file_data[key] = file_data_raw[i + 1]
    else:
        file_data = file_data_raw

    revn = file_data.get('revn', 0)
    print(f"Current revision: {revn}")

    # Get current fills - need to parse nested Transit format
    print(f"File data keys: {list(file_data.keys())}")

    print("\n=== Step 3: Test with KEBAB-CASE (should fail) ===")
    session_id_1 = str(uuid.uuid4())
    print(f"Session ID: {session_id_1}")

    kebab_payload = {
        "~:id": f"~u{FILE_ID}",
        "~:session-id": f"~u{session_id_1}",
        "~:revn": revn,
        "~:changes": [{
            "~:type": "~:mod-obj",
            "~:id": f"~u{OBJECT_ID}",
            "~:operations": [{
                "~:type": "~:set",
                "~:attr": "~:fills",
                "~:val": [{
                    "~:fill-color": "#FF0000",
                    "~:fill-opacity": 1.0
                }]
            }]
        }]
    }

    print("Payload:")
    print(json.dumps(kebab_payload, indent=2))

    kebab_resp = session.post(
        f"{API_URL}/rpc/command/update-file",
        json=kebab_payload,
        headers={"Content-Type": "application/transit+json"}
    )
    print(f"Response status: {kebab_resp.status_code}")
    print(f"Response: {json.dumps(kebab_resp.json(), indent=2)}")

    # Increment revision
    revn += 1

    print("\n=== Step 4: Verify color after kebab-case update ===")
    file_resp = session.get(f"{API_URL}/rpc/command/get-file?id={FILE_ID}")
    file_data = file_resp.json()
    pages_index = file_data.get('data', {}).get('pagesIndex', {})
    for page_data in pages_index.values():
        if OBJECT_ID in page_data.get('objects', {}):
            obj = page_data['objects'][OBJECT_ID]
            fills = obj.get('fills', [])
            print(f"Fills after kebab-case: {json.dumps(fills, indent=2)}")
            if fills:
                print(f"Fill color: {fills[0].get('fillColor', 'NOT SET')}")
            break

    print("\n=== Step 5: Test with CAMELCASE (should work) ===")
    session_id_2 = str(uuid.uuid4())
    print(f"Session ID: {session_id_2}")

    camel_payload = {
        "~:id": f"~u{FILE_ID}",
        "~:session-id": f"~u{session_id_2}",
        "~:revn": revn,
        "~:changes": [{
            "~:type": "~:mod-obj",
            "~:id": f"~u{OBJECT_ID}",
            "~:operations": [{
                "~:type": "~:set",
                "~:attr": "~:fills",
                "~:val": [{
                    "~:fillColor": "#00FF00",
                    "~:fillOpacity": 1.0
                }]
            }]
        }]
    }

    print("Payload:")
    print(json.dumps(camel_payload, indent=2))

    camel_resp = session.post(
        f"{API_URL}/rpc/command/update-file",
        json=camel_payload,
        headers={"Content-Type": "application/transit+json"}
    )
    print(f"Response status: {camel_resp.status_code}")
    print(f"Response: {json.dumps(camel_resp.json(), indent=2)}")

    print("\n=== Step 6: Verify final color after camelCase update ===")
    file_resp = session.get(f"{API_URL}/rpc/command/get-file?id={FILE_ID}")
    file_data = file_resp.json()
    pages_index = file_data.get('data', {}).get('pagesIndex', {})
    for page_data in pages_index.values():
        if OBJECT_ID in page_data.get('objects', {}):
            obj = page_data['objects'][OBJECT_ID]
            fills = obj.get('fills', [])
            print(f"Fills after camelCase: {json.dumps(fills, indent=2)}")
            if fills:
                print(f"Fill color: {fills[0].get('fillColor', 'NOT SET')}")
            break

    print("\n=== SUMMARY ===")
    print("If kebab-case worked, color should be #FF0000 (red)")
    print("If camelCase worked, color should be #00FF00 (green)")
    print("Check the final fills above to see which format was accepted by the API.")

if __name__ == "__main__":
    main()
