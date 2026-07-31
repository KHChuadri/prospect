"""One-time: mint a Gmail refresh token for the agent.

Prereqs: a Google Cloud project with the Gmail API enabled and an OAuth
"Desktop app" client. Download its JSON as agent/gmail_client_secret.json.

Run:  python gmail_authorize.py
Then copy the printed values into agent/.env as GMAIL_CLIENT_ID,
GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main() -> None:
    flow = InstalledAppFlow.from_client_secrets_file(
        "gmail_client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)
    print("GMAIL_CLIENT_ID=", creds.client_id)
    print("GMAIL_CLIENT_SECRET=", creds.client_secret)
    print("GMAIL_REFRESH_TOKEN=", creds.refresh_token)


if __name__ == "__main__":
    main()
