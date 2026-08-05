# Work Submission Notifier

*Automated email notifications for ArcGIS Online field work submissions*

Polls a Work Locations feature service on a schedule, finds newly submitted records in the related Work Records table, and emails a formatted HTML summary (including any photo attachment) to a list of recipients. Runs entirely on GitHub Actions; no server required.

---

## Contents

| Section | |
|---|---|
| [How It Works](#how-it-works) | Architecture overview |
| [Repository Structure](#repository-structure) | Where each file goes |
| [Setup](#setup) | Step-by-step deployment |
| [Configuration](#configuration) | What to edit in the script |
| [The Workflow File](#the-workflow-file) | Full YAML with notes |
| [Data Model Assumptions](#data-model-assumptions) | Required layer structure |
| [Troubleshooting](#troubleshooting) | Common failures |

---

## How It Works

1. A GitHub Actions cron job runs the script on a fixed interval.
2. The script authenticates to ArcGIS Online with a username/password stored as a GitHub secret and generates a short-lived token.
3. It queries the related table for records created within `LOOKBACK_MINUTES`.
4. For each record not already listed in `emailed_records.txt`, it pulls the parent feature for context, fetches the first photo attachment if one exists, builds an HTML email, and sends it via SMTP.
5. The record's OBJECTID is appended to `emailed_records.txt`, which the workflow commits back to the repository so the next run skips it.

The lookback window and the tracking file do different jobs. The window keeps the query small and prevents the first run from emailing your entire history. The tracking file prevents duplicates when a record falls inside the window on two consecutive runs.

---

## Repository Structure

This tool must live at the **root of its own repository**. The script writes `emailed_records.txt` relative to the working directory, and GitHub Actions only reads workflow files from `.github/workflows/` at the repository root.

```
workorders/                        <- repository root
├── work_submission_notifier.py
├── requirements.txt
├── emailed_records.txt            <- created automatically on first run
├── README.md
└── .github/
    └── workflows/
        └── notify_submission.yml
```

> **Note:** If you are reading this inside a larger projects repository, the `.github/` folder here is a template only. GitHub does not execute workflow files from subdirectories - copy this entire folder to the root of a new repository to deploy it.

`requirements.txt`:

```
requests
Pillow
```

---

## Setup

### 1. Create a private repository

Make it **private**. The workflow logs record locations and field values, and the commit history of `emailed_records.txt` will show your submission volume.

Copy the folder contents to the repository root, preserving the `.github/workflows/` path.

### 2. Prepare the sending email account

If sending through Gmail, the account needs 2-Step Verification enabled, and you must generate an **App Password** - your normal account password will be rejected by SMTP. Generate one under Google Account → Security → App passwords, and use that 16-character string as `EMAIL_PASSWORD`.

### 3. Add repository secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add four secrets. Note this is the *Actions* tab, not Codespaces or Dependabot.

| Secret | Value |
|---|---|
| `AGOL_USERNAME` | ArcGIS Online account with read access to the feature service |
| `AGOL_PASSWORD` | That account's password |
| `EMAIL_SENDER` | Full sending email address |
| `EMAIL_PASSWORD` | App password for the sending account |

You do **not** create a `GITHUB_TOKEN` secret. Actions provides one automatically; the `permissions: contents: write` block in the workflow grants it the access needed to commit the tracking file.

### 4. Configure the script

See [Configuration](#configuration) below. At minimum, set `FEATURE_SERVICE` and `EMAIL_RECIPIENTS`.

### 5. Test before scheduling

The workflow includes `workflow_dispatch`, so you can trigger it manually from the **Actions** tab → select the workflow → **Run workflow**. Do this once with a single recipient to confirm the whole chain works before letting the cron loose on a full recipient list.

---

## Configuration

Everything configurable sits at the top of `work_submission_notifier.py`.

| Setting | Notes |
|---|---|
| `FEATURE_SERVICE` | Base FeatureServer URL. The script appends `/0/query` for the parent layer and `/1/query` for the related table. |
| `EMAIL_RECIPIENTS` | List of quoted address strings. Every recipient receives every email. |
| `LOOKBACK_MINUTES` | How far back each run queries. Must comfortably exceed your cron interval. |
| `TRACKED_FILE` | Dedup tracking file. Leave as-is unless you also update the workflow's `git add`. |
| `EASTERN` | Display timezone for dates in the email body. |

### Choosing a lookback window

The window should be several times your cron interval, not equal to it. GitHub Actions scheduled jobs are frequently delayed under load - a run scheduled for every 15 minutes may in practice fire hourly. A generous window costs nothing, because the tracking file handles the resulting overlap. A tight window silently drops records whenever a run is delayed.

A full day (`1440`) is a reasonable default. The tradeoff is that the query returns more rows each run, and every one is checked against the tracking file.

### First-run behavior

On a fresh deployment the tracking file is empty, so anything inside the lookback window gets emailed. With a 1440-minute window that means up to a full day of existing records will go out on the first run. If that isn't wanted, either drop `LOOKBACK_MINUTES` temporarily for the first run, or pre-populate `emailed_records.txt` with the OBJECTIDs you want suppressed.

---

## The Workflow File

`.github/workflows/notify_submission.yml`:

```yaml
name: Work Submission Notifier

on:
  schedule:
    # Every 15 minutes. GitHub throttles more aggressive schedules.
    - cron: '*/15 * * * *'
  workflow_dispatch:   # enables the manual "Run workflow" button

jobs:
  notify:
    runs-on: ubuntu-latest

    permissions:
      contents: write   # required to commit emailed_records.txt back

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run notifier
        env:
          AGOL_USERNAME:  ${{ secrets.AGOL_USERNAME }}
          AGOL_PASSWORD:  ${{ secrets.AGOL_PASSWORD }}
          EMAIL_SENDER:   ${{ secrets.EMAIL_SENDER }}
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
        run: python work_submission_notifier.py

      - name: Commit updated tracking file
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add emailed_records.txt
          git diff --cached --quiet || git commit -m "chore: update emailed_records.txt [skip ci]"
          git push
```

Notes on the pieces that matter:

- **Python 3.11 or later is required.** The script uses `zoneinfo` and `X | None` union syntax in annotations.
- **`[skip ci]`** in the commit message prevents the tracking-file commit from triggering another workflow run.
- **`git diff --cached --quiet ||`** makes the commit conditional, so runs that send no emails don't fail on "nothing to commit."
- **Cron frequency.** `*/5` is routinely throttled by GitHub and runs collapse together. `*/15` is more reliably honored. Neither is guaranteed - treat the schedule as a floor, not a promise, and size `LOOKBACK_MINUTES` accordingly.

---

## Data Model Assumptions

The script expects a specific structure. Adapt the field names in `build_email_body()` if yours differ.

**Sublayer 0 - parent feature layer**, queried by GlobalID:

`location_description`, `type_of_work`, `dig_safe_number`, `CreationDate`

**Sublayer 1 - related table**, one-to-many against the parent, with attachments enabled:

`ParentGlobalID`, `CreationDate`, `OBJECTID`, `work_start`, `work_end`, `completed_by`, `names_of_workers`, `name_of_contractor`, `contractor_overseen_by`, `type_of_water_inspection`, `type_of_water_work`, `type_of_sewer_inspection`, `type_of_sewer_work`, `type_of_meter_work`, `equipment_used`, `materials_used`, `comments`

Blank fields are omitted from the email rather than rendered empty, so a partially filled form still produces a clean report. Only the first attachment on a record is embedded; additional photos are ignored.

---

## Troubleshooting

**Workflow runs but no emails arrive**

Check the run log. "No new records found" means the query returned nothing - either genuinely no submissions, or `LOOKBACK_MINUTES` is shorter than the gap since the last one. "already emailed, skipping" means the tracking file is doing its job.

**`Token generation failed`**

The AGOL credentials are wrong, or the account uses SSO. Accounts federated through an identity provider cannot generate tokens via `generateToken` - this requires a built-in ArcGIS Online account.

**SMTP authentication error**

Almost always a normal password used where an App Password is required, or 2-Step Verification not enabled on the sending account.

**Emails send but the tracking file never updates**

The commit step is failing. Confirm `permissions: contents: write` is present, and that branch protection rules aren't blocking pushes from `github-actions[bot]`.

**Duplicate emails**

The tracking file isn't persisting between runs. Check whether the commit step succeeded in the previous run's log - if the push failed, the next run starts from a stale file and re-sends anything still inside the lookback window.

**Runs are far less frequent than the cron specifies**

Expected behavior from GitHub's scheduler, not a bug in the workflow. Increase `LOOKBACK_MINUTES` rather than fighting it.