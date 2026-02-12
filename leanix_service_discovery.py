import os
import json
import requests
import yaml

LEANIX_API_TOKEN = os.environ["LEANIX_API_TOKEN"]
LEANIX_SUBDOMAIN = os.environ["LEANIX_SUBDOMAIN"]
LEANIX_BASE_URL = f"https://{LEANIX_SUBDOMAIN}.leanix.net/services"
LEANIX_OAUTH2_URL = f"{LEANIX_BASE_URL}/mtm/v1/oauth2/token"
LEANIX_MANIFEST_URL = f"{LEANIX_BASE_URL}/technology-discovery/v1/manifests"
LEANIX_UPLOAD_URL = f"{LEANIX_BASE_URL}/pathfinder/v1/graphql/upload"

MANIFEST_FILE = "leanix.yaml"
DOCUMENT_FILE = "architecture-overview.pdf"


def obtain_access_token():
    response = requests.post(
        LEANIX_OAUTH2_URL,
        auth=("apitoken", LEANIX_API_TOKEN),
        data={"grant_type": "client_credentials"},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def upload_manifest(auth_header):
    with open(MANIFEST_FILE, "rb") as f:
        response = requests.put(
            LEANIX_MANIFEST_URL,
            headers={"Authorization": auth_header},
            files={"file": (MANIFEST_FILE, f, "application/yaml")},
        )
    print(f"Manifest HTTP {response.status_code}: {response.text}")
    response.raise_for_status()
    data = response.json()
    print(f"Manifest response: {json.dumps(data, indent=2)}")

    fact_sheet_id = data.get("data", {}).get("factSheetId")
    if not fact_sheet_id:
        raise Exception(f"No factSheetId in manifest response: {data}")

    print(f"Fact sheet ID: {fact_sheet_id}")
    return fact_sheet_id


def upload_document(auth_header, fact_sheet_id):
    if not os.path.isfile(DOCUMENT_FILE):
        print(f"No document file found at {DOCUMENT_FILE}, skipping upload")
        return

    mutation = f"""
        mutation createDocument {{
            createDocument(
                factSheetId: "{fact_sheet_id}"
                name: "{DOCUMENT_FILE}"
                documentType: "documentation"
                origin: "LX_STORAGE_SERVICE"
            ) {{
                id
                name
                url
                factSheetId
            }}
        }}
    """

    with open(DOCUMENT_FILE, "rb") as f:
        form_data = {
            "graphQLRequest": (None, json.dumps({"query": mutation})),
            "file": (DOCUMENT_FILE, f, "application/pdf"),
        }
        response = requests.post(
            LEANIX_UPLOAD_URL,
            headers={"Authorization": auth_header, "Accept": "application/json"},
            files=form_data,
        )

    response.raise_for_status()
    data = response.json()
    print(f"Document upload response: {json.dumps(data, indent=2)}")

    doc_id = data.get("data", {}).get("createDocument", {}).get("id")
    if not doc_id:
        raise Exception(f"No document ID in response: {data}")

    print(f"Document uploaded successfully (ID: {doc_id})")


def main():
    access_token = obtain_access_token()
    auth_header = f"Bearer {access_token}"

    fact_sheet_id = upload_manifest(auth_header)
    upload_document(auth_header, fact_sheet_id)


if __name__ == "__main__":
    main()
