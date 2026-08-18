"""
Shared OAuth helper for Sheets + Gmail access. credentials.json is the
downloaded OAuth client secret (Desktop app type); token.json is written
after the first interactive authorization and refreshed automatically
after that. Both are gitignored - never commit either.
"""

import os.path
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]

# Resolved from this file's location, not the process's working directory -
# a scheduled task may be launched from an arbitrary cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TOKEN_PATH = PROJECT_ROOT / "token.json"
DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"


def get_credentials(token_path=DEFAULT_TOKEN_PATH, credentials_path=DEFAULT_CREDENTIALS_PATH):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"{credentials_path} not found - download it from Google Cloud Console "
                    "(OAuth client, Desktop app type) and place it at the project root. See README.md."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds
