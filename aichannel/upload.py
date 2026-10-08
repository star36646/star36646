"""Upload to YouTube via the Data API (OAuth). Needs client_secret.json from Google Cloud Console."""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from . import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _creds():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES).run_local_server(port=0)
        open("token.json", "w").write(creds.to_json())
    return creds


def upload(video: str, title: str, description: str, tags: list[str],
           privacy: str = config.DEFAULT_PRIVACY, thumbnail: str | None = None) -> str:
    yt = build("youtube", "v3", credentials=_creds())
    body = {
        "snippet": {"title": title[:100], "description": description, "tags": tags[:15], "categoryId": "28"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": config.CONTAINS_SYNTHETIC_MEDIA},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(video, chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    if thumbnail:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumbnail)).execute()
    return f"https://youtu.be/{vid}"
