"""
work_submission_notifier.py

Polls the Work Locations feature service every 5 minutes (via
GitHub Actions cron) for new records in the related Work_Records table
(sublayer 1). For each new record not yet in emailed_records.txt, sends
a formatted HTML email to all recipients — one email per record — with:

  - Parent layer fields at top (location, type of work, dig safe #, date)
  - All non-null Work_Records fields in a two-column table
  - Photo attached inline if one exists on the record

After sending, appends the record's OBJECTID to emailed_records.txt and
commits it back to the repo so the next run doesn't re-send.

--- SETTINGS ---
EMAIL_RECIPIENTS  : hard-coded list of recipient emails
FEATURE_SERVICE   : base URL for the FeatureServer
TRACKED_FILE      : path to the dedup tracking file (committed to repo)
"""

import os
import io
import smtplib
import requests
import logging
from PIL import Image
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

AGOL_USERNAME = os.environ["AGOL_USERNAME"]
AGOL_PASSWORD = os.environ["AGOL_PASSWORD"]
EMAIL_SENDER  = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

FEATURE_SERVICE   = "https://services9.arcgis.com/YOUR_ORG_ID/arcgis/rest/services/YOUR_LAYER/FeatureServer"
PARENT_URL        = f"{FEATURE_SERVICE}/0/query"
RECORDS_URL       = f"{FEATURE_SERVICE}/1/query"
ATTACHMENTS_URL   = f"{FEATURE_SERVICE}/1"   # /<objectid>/attachments appended at runtime

TRACKED_FILE = "emailed_records.txt"

EASTERN = ZoneInfo("America/New_York") # handles EST/EDT automatically

EMAIL_RECIPIENTS = [
    "email_one@yourdomain.com",
    "email_two@yourdomain.com"
]


# How far back to look on each run — 15 min gives plenty of buffer for
# a 5-min cron that may drift slightly under GitHub Actions load
LOOKBACK_MINUTES = 1440


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DEDUP TRACKING
# ---------------------------------------------------------------------------

def load_tracked() -> set:
    """Return set of already-emailed OBJECTIDs (as strings)."""
    if not os.path.exists(TRACKED_FILE):
        return set()
    with open(TRACKED_FILE, "r") as f:
        return {line.strip() for line in f if line.strip()}


def append_tracked(objectid: int) -> None:
    """Append a single OBJECTID to the tracking file."""
    with open(TRACKED_FILE, "a") as f:
        f.write(f"{objectid}\n")

# ---------------------------------------------------------------------------
# AGOL AUTH
# ---------------------------------------------------------------------------

def get_token() -> str:
    resp = requests.post(
        "https://www.arcgis.com/sharing/rest/generateToken",
        data={
            "username": AGOL_USERNAME,
            "password": AGOL_PASSWORD,
            "client":   "referer",
            "referer":  "https://www.arcgis.com",
            "f":        "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "token" not in data:
        raise RuntimeError(f"Token generation failed: {data}")
    log.info("AGOL token acquired.")
    return data["token"]

# ---------------------------------------------------------------------------
# FEATURE SERVICE QUERIES
# ---------------------------------------------------------------------------

def get_new_records(token: str) -> list[dict]:
    """
    Query Work_Records table (sublayer 1) for records created in the
    last LOOKBACK_MINUTES. Returns list of attribute dicts.
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    since_str = since.strftime("%Y-%m-%d %H:%M:%S")

    resp = requests.get(
        RECORDS_URL,
        params={
            "where":          f"CreationDate >= TIMESTAMP '{since_str}'",
            "outFields":      "*",
            "orderByFields":  "CreationDate ASC",
            "f":              "json",
            "token":          token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"Feature service error: {data['error']}")

    features = data.get("features", [])
    log.info(f"Found {len(features)} new record(s) in last {LOOKBACK_MINUTES} minutes.")
    return [f["attributes"] for f in features]


def get_parent_record(token: str, parent_globalid: str) -> dict:
    """
    Fetch the parent feature (sublayer 0) by GlobalID.
    Returns attribute dict or empty dict if not found.
    """
    resp = requests.get(
        PARENT_URL,
        params={
            "where":     f"GlobalID = '{parent_globalid}'",
            "outFields": "location_description,type_of_work,dig_safe_number,CreationDate",
            "f":         "json",
            "token":     token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features", [])
    return features[0]["attributes"] if features else {}


def get_attachment(token: str, objectid: int) -> tuple[bytes, str] | None:
    """
    Fetch the first attachment for a Work_Records row.
    Returns (image_bytes, content_type) or None if no attachment.
    """
    url = f"{ATTACHMENTS_URL}/{objectid}/attachments"
    resp = requests.get(url, params={"f": "json", "token": token}, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    attachments = data.get("attachmentInfos", [])
    if not attachments:
        return None

    # Take the first attachment (Field Maps typically stores one photo per record)
    att = attachments[0]
    att_id = att["id"]
    content_type = att.get("contentType", "image/jpeg")

    img_resp = requests.get(
        f"{ATTACHMENTS_URL}/{objectid}/attachments/{att_id}",
        params={"token": token},
        timeout=60,
    )
    img_resp.raise_for_status()
    return img_resp.content, content_type

# ---------------------------------------------------------------------------
# FORMATTING HELPERS
# ---------------------------------------------------------------------------

def fmt_epoch(ms) -> str:
    """Convert AGOL epoch milliseconds to readable Eastern Time string."""
    if ms is None:
        return ""
    try:
        dt_utc = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
        dt_eastern = dt_utc.astimezone(EASTERN)
        return dt_eastern.strftime("%m/%d/%Y %I:%M %p")
    except Exception:
        return str(ms)


def calc_duration(start_ms, end_ms) -> str:
    """Return human-readable duration between two epoch-ms values."""
    if start_ms is None or end_ms is None:
        return ""
    try:
        delta = timedelta(milliseconds=int(end_ms) - int(start_ms))
        total_min = int(delta.total_seconds() / 60)
        if total_min < 0:
            return ""
        hours, minutes = divmod(total_min, 60)
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        else:
            return f"{minutes}m"
    except Exception:
        return ""


def is_blank(value) -> bool:
    """Return True if a field value should be considered empty."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def resize_image(image_bytes: bytes, max_width: int = 600) -> bytes:
    """Resize image to max_width while preserving aspect ratio."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=75)
        return output.getvalue()
    except Exception as e:
        log.warning(f"Could not resize image: {e}")
        return image_bytes


# ---------------------------------------------------------------------------
# EMAIL BODY BUILDER
# ---------------------------------------------------------------------------

def build_email_body(record: dict, parent: dict, has_photo: bool) -> str:
    """
    Build the HTML email body. Mirrors the Word report template layout:
      - Header block: location, type of work, dig safe #, submitted date
      - Two-column table: label | value, skipping blank fields
      - Optional inline photo placeholder (cid:photo0)
    """

    def header_row(label: str, value: str) -> str:
        if not value:
            return ""
        return f"""
        <tr>
          <td style="padding:3px 10px 3px 0;font-weight:bold;color:#2c5f8a;
                     white-space:nowrap;vertical-align:top;">{label}</td>
          <td style="padding:3px 0;vertical-align:top;">{value}</td>
        </tr>"""

    def field_row(label: str, value: str) -> str:
        if not value:
            return ""
        # Preserve line breaks for multiline fields
        safe_value = value.replace("\n", "<br>") if isinstance(value, str) else value
        return f"""
        <tr style="border-top:1px solid #e0e0e0;">
          <td style="padding:6px 16px 6px 0;font-weight:bold;color:#2c5f8a;
                     white-space:nowrap;vertical-align:top;width:200px;">{label}</td>
          <td style="padding:6px 0;vertical-align:top;">{safe_value}</td>
        </tr>"""

    # --- Header fields from parent layer ---
    location    = parent.get("location_description") or ""
    work_type   = parent.get("type_of_work") or ""
    dig_safe    = parent.get("dig_safe_number") or ""
    created_ms  = parent.get("CreationDate")
    created_str = fmt_epoch(created_ms) if created_ms else fmt_epoch(record.get("CreationDate"))

    header_rows = "".join(filter(None, [
        header_row("Location",      location),
        header_row("Type of Work",  work_type),
        header_row("Dig Safe #",    dig_safe),
        header_row("Submitted",     created_str),
    ]))

    # --- Work_Records fields ---
    # Work start / duration calculated from start+end
    work_start_ms  = record.get("work_start")
    work_end_ms    = record.get("work_end")
    work_start_str = fmt_epoch(work_start_ms)
    duration_str   = calc_duration(work_start_ms, work_end_ms)

    detail_rows = "".join(filter(None, [
        field_row("Work Start",               work_start_str),
        field_row("Duration of Work",         duration_str),
        field_row("Completed By",             record.get("completed_by") or ""),
        field_row("Name(s) of Workers",       record.get("names_of_workers") or ""),
        field_row("Name of Contractor",       record.get("name_of_contractor") or ""),
        field_row("Contractor Overseen By",   record.get("contractor_overseen_by") or ""),
        field_row("Type of Water Inspection", record.get("type_of_water_inspection") or ""),
        field_row("Type of Water Work",       record.get("type_of_water_work") or ""),
        field_row("Type of Sewer Inspection", record.get("type_of_sewer_inspection") or ""),
        field_row("Type of Sewer Work",       record.get("type_of_sewer_work") or ""),
        field_row("Type of Meter Work",       record.get("type_of_meter_work") or ""),
        field_row("Equipment Used",           record.get("equipment_used") or ""),
        field_row("Materials Used",           record.get("materials_used") or ""),
        field_row("Comments",                 record.get("comments") or ""),
    ]))

    photo_block = ""
    if has_photo:
        photo_block = """
        <br>
        <p style="font-weight:bold;color:#2c5f8a;margin-bottom:4px;">Photo</p>
        <img src="cid:photo0" style="max-width:600px;border:1px solid #ccc;" />
        """

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:700px;">

      <h2 style="color:#2c5f8a;margin-bottom:4px;">Work Summary Report</h2>

      <table border="0" cellpadding="0" cellspacing="0"
             style="margin-bottom:18px;border-collapse:collapse;">
        {header_rows}
      </table>

      <table border="0" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;border-top:2px solid #2c5f8a;width:100%;">
        {detail_rows}
      </table>

      {photo_block}

      <br>
      <p style="margin-top:24px;">
        <a href="HTTPS://LINK_TO_MAP_SHOWING_WORK_LOCATIONS"
           style="background-color:#2c5f8a;color:#ffffff;padding:10px 20px;
                  text-decoration:none;border-radius:4px;font-weight:bold;">
          View in Online Map
        </a>
      </p>
      
      <br>
      <p style="color:#aaa;font-size:11px;margin-top:12px;">
        Automated notification &mdash; DPW Work Locations
        &mdash; Record OBJECTID: {record.get("OBJECTID")}
      </p>

    </body>
    </html>
    """

# ---------------------------------------------------------------------------
# EMAIL SENDING
# ---------------------------------------------------------------------------

def send_email(
    subject: str,
    html_body: str,
    photo_bytes: bytes | None = None,
    photo_content_type: str = "image/jpeg",
) -> None:
    """
    Send a single formatted email. If photo_bytes is provided, attaches
    the image inline so it renders inside the HTML body via cid:photo0.
    """
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = f"TOB Engineering <{EMAIL_SENDER}>"
    msg["To"]      = ", ".join(EMAIL_RECIPIENTS)

    # Attach HTML body
    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)
    msg_alt.attach(MIMEText(html_body, "html"))

    # Attach inline photo if present
    if photo_bytes:
        img = MIMEImage(photo_bytes, _subtype=photo_content_type.split("/")[-1])
        img.add_header("Content-ID", "<photo0>")
        img.add_header("Content-Disposition", "inline", filename="photo.jpg")
        msg.attach(img)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENTS, msg.as_string())

    log.info(f"Email sent: {subject}")

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== Work Submission Notifier started ===")

    tracked = load_tracked()
    log.info(f"Tracking file has {len(tracked)} previously emailed record(s).")

    try:
        token   = get_token()
        records = get_new_records(token)

        if not records:
            log.info("No new records found. Exiting.")
            return

        emails_sent = 0

        for record in records:
            objectid = record.get("OBJECTID")

            if str(objectid) in tracked:
                log.info(f"OBJECTID {objectid} already emailed, skipping.")
                continue

            # Fetch parent for location/type/dig safe
            parent_globalid = record.get("ParentGlobalID")
            parent = get_parent_record(token, parent_globalid) if parent_globalid else {}

            # Try to fetch photo attachment
            photo_bytes = None
            photo_ct    = "image/jpeg"
            try:
                result = get_attachment(token, objectid)
                if result:
                    photo_bytes, photo_ct = result
                    photo_bytes = resize_image(photo_bytes)
                    log.info(f"OBJECTID {objectid}: photo attachment found.")
                else:
                    log.info(f"OBJECTID {objectid}: no photo attachment.")
            except Exception as e:
                log.warning(f"OBJECTID {objectid}: could not fetch attachment — {e}")

            location  = parent.get("location_description") or "Unknown Location"
            work_type = parent.get("type_of_work") or "Work Record"
            subject   = f"Work Record Submitted — {location} ({work_type})"

            html_body = build_email_body(record, parent, has_photo=photo_bytes is not None)
            send_email(subject, html_body, photo_bytes=photo_bytes, photo_content_type="image/jpeg")

            append_tracked(objectid)
            tracked.add(str(objectid))
            emails_sent += 1

        log.info(f"Done. {emails_sent} email(s) sent this run.")

    except Exception as e:
        log.exception(f"Unhandled error: {e}")


if __name__ == "__main__":
    main()