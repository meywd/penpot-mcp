#!/bin/bash

API_URL="http://localhost:9001/api"
USERNAME="contact@mahmoudsdarwish.com"
PASSWORD="jqm!UAW_pfc5cnu9wzh"
FILE_ID="689fbaf0-efce-81fe-8006-ed108f8a2104"
OBJECT_ID="fab9cafe-e0d9-43c4-9642-295ea9759a5c"

echo "=== Step 1: Authenticate and get cookies ==="
curl -c cookies.txt -X POST "$API_URL/rpc/command/login-with-password" \
  -H "Content-Type: application/transit+json" \
  -d "{\"~:email\":\"$USERNAME\",\"~:password\":\"$PASSWORD\"}" \
  -s | jq .

echo -e "\n=== Step 2: Get file data to retrieve current revision ==="
FILE_DATA=$(curl -b cookies.txt -s "$API_URL/rpc/command/get-file?id=$FILE_ID")
REVN=$(echo "$FILE_DATA" | jq -r '.revn')
echo "Current revision: $REVN"

echo -e "\n=== Step 3: Generate session ID ==="
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Session ID: $SESSION_ID"

echo -e "\n=== Step 4: Test with KEBAB-CASE (should fail) ==="
curl -b cookies.txt -X POST "$API_URL/rpc/command/update-file" \
  -H "Content-Type: application/transit+json" \
  -d "{
    \"~:id\":\"~u$FILE_ID\",
    \"~:session-id\":\"~u$SESSION_ID\",
    \"~:revn\":$REVN,
    \"~:changes\":[{
      \"~:type\":\"~:mod-obj\",
      \"~:id\":\"~u$OBJECT_ID\",
      \"~:operations\":[{
        \"~:type\":\"~:set\",
        \"~:attr\":\"~:fills\",
        \"~:val\":[{
          \"~:fill-color\":\"#FF0000\",
          \"~:fill-opacity\":1.0
        }]
      }]
    }]
  }" \
  -s | jq .

# Increment revision for next test
REVN=$((REVN + 1))
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

echo -e "\n=== Step 5: Test with CAMELCASE (should work) ==="
curl -b cookies.txt -X POST "$API_URL/rpc/command/update-file" \
  -H "Content-Type: application/transit+json" \
  -d "{
    \"~:id\":\"~u$FILE_ID\",
    \"~:session-id\":\"~u$SESSION_ID\",
    \"~:revn\":$REVN,
    \"~:changes\":[{
      \"~:type\":\"~:mod-obj\",
      \"~:id\":\"~u$OBJECT_ID\",
      \"~:operations\":[{
        \"~:type\":\"~:set\",
        \"~:attr\":\"~:fills\",
        \"~:val\":[{
          \"~:fillColor\":\"#00FF00\",
          \"~:fillOpacity\":1.0
        }]
      }]
    }]
  }" \
  -s | jq .

echo -e "\n=== Step 6: Verify final color ==="
curl -b cookies.txt -s "$API_URL/rpc/command/get-file?id=$FILE_ID" | \
  jq --arg obj_id "$OBJECT_ID" '.data.pagesIndex | to_entries[0].value.objects[$obj_id].fills'

