"""Mirror the Google Drive project folder into data/drive, plus manifest.json.

One-time setup (about 5 minutes):
  1. console.cloud.google.com -> new project -> enable "Google Drive API".
  2. OAuth consent screen (External, add yourself as test user).
  3. Credentials -> OAuth client ID -> Desktop app -> download JSON as credentials.json here.
  4. python drive_sync.py   (a browser opens once for consent, token.json is saved)

Only read access is requested. Older versions of the same document are skipped,
and so are images, video, code exports and backups.
"""
import argparse
import io
import json
import re
from pathlib import Path

import config

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER = "application/vnd.google-apps.folder"
EXPORTS = {  # Google-native files are exported as text
    "application/vnd.google-apps.document": ("text/markdown", ".md"),
    "application/vnd.google-apps.presentation": ("text/plain", ".txt"),
}
KEEP_EXT = {".docx", ".pdf", ".pptx", ".md", ".txt", ".json"}
SKIP_TITLE = re.compile(r"backup|kopyas|copy of|sample (?:cv|resume)|photo|compensation|gehalt", re.I)
MAX_BYTES = 15_000_000
VERSION_NOISE = re.compile(
    r"ayhan[ _]?demir|\bayhan\b|\d{4}[\s_-]\d{2}[\s_-]\d{2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[ _-]?\d{4}"
    r"|\bv\d+\b|final|version|last|locked|review|\(\d+\)", re.I)


def service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if config.GOOGLE_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(config.GOOGLE_TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not config.GOOGLE_CREDENTIALS.exists():
                raise FileNotFoundError(f"Missing {config.GOOGLE_CREDENTIALS.name}. See the setup steps at the top of drive_sync.py.")
            flow = InstalledAppFlow.from_client_secrets_file(str(config.GOOGLE_CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)
        config.GOOGLE_TOKEN.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def walk(svc, folder_id, folder=""):
    """Every file below folder_id, recursively, with its folder name."""
    out, token = [], None
    while True:
        res = svc.files().list(
            q=f"'{folder_id}' in parents and trashed=false", pageSize=200, pageToken=token,
            fields="nextPageToken, files(id,name,mimeType,modifiedTime,size,webViewLink)").execute()
        for f in res["files"]:
            if f["mimeType"] == FOLDER:
                out += walk(svc, f["id"], f["name"])
            else:
                out.append({**f, "folder": folder})
        token = res.get("nextPageToken")
        if not token:
            return out


def stem(name):
    """Title without dates, version tags and the owner's name, so versions group together."""
    base = Path(name).stem if Path(name).suffix.lower() in KEEP_EXT else name
    s = VERSION_NOISE.sub(" ", re.sub(r"[_\-]+", " ", base))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def select(files):
    """Keep indexable files, newest version of each document only."""
    keep = {}
    for f in files:
        ext = EXPORTS.get(f["mimeType"], (None, Path(f["name"]).suffix.lower()))[1]
        if ext not in KEEP_EXT or SKIP_TITLE.search(f["name"]) or int(f.get("size") or 0) > MAX_BYTES:
            continue
        key = stem(f["name"])
        if key not in keep or f["modifiedTime"] > keep[key]["modifiedTime"]:
            keep[key] = {**f, "ext": ext}
    return sorted(keep.values(), key=lambda f: f["name"])


def download(svc, f, dest: Path):
    from googleapiclient.http import MediaIoBaseDownload

    if f["mimeType"] in EXPORTS:
        request = svc.files().export_media(fileId=f["id"], mimeType=EXPORTS[f["mimeType"]][0])
    else:
        request = svc.files().get_media(fileId=f["id"])
    buf, done = io.BytesIO(), False
    downloader = MediaIoBaseDownload(buf, request)
    while not done:
        _, done = downloader.next_chunk()
    dest.write_bytes(buf.getvalue())


def sync(folder_id=config.DRIVE_FOLDER_ID, dry_run=False):
    svc = service()
    chosen = select(walk(svc, folder_id))
    if dry_run:
        return chosen
    config.DRIVE_DIR.mkdir(parents=True, exist_ok=True)
    old = config.DRIVE_DIR / "manifest.json"
    for entry in json.loads(old.read_text()) if old.exists() else []:  # clear the previous mirror
        (config.DRIVE_DIR / entry["path"]).unlink(missing_ok=True)
    manifest = []
    for f in chosen:
        path = re.sub(r"[^A-Za-z0-9]+", "_", Path(f["name"]).stem).strip("_") + f["ext"]
        download(svc, f, config.DRIVE_DIR / path)
        manifest.append({"id": f["id"], "title": f["name"], "mimeType": f["mimeType"],
                         "modifiedTime": f["modifiedTime"], "viewUrl": f.get("webViewLink", ""),
                         "folder": f["folder"], "path": path, "source": "google-drive-api"})
    old.write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder-id", default=config.DRIVE_FOLDER_ID)
    ap.add_argument("--dry-run", action="store_true", help="list what would be mirrored")
    args = ap.parse_args()
    for f in sync(args.folder_id, args.dry_run):
        print(f"{f['modifiedTime'][:10]}  {f.get('folder', ''):<40.40}  {f.get('name') or f['title']}")
    print("Done. Next: python ingest.py")
