# Stormwater Analysis Tools

*Town of Braintree Engineering Department*

---

## Contents

| Section | |
|---|---|
| [To Start the Program](#to-start-the-program) | How to launch |
| [Before You Start](#before-you-start) | Requirements and sign-in |
| [What It Does](#what-it-does) | The two analysis tools |
| [If Something Goes Wrong](#if-something-goes-wrong) | Known errors and troubleshooting |
| [Notes](#notes) | Folder structure and configuration |

---

## To Start the Program

Open the `stormwater_analysis` folder and double-click:

```
launch.vbs
```

---

## Before You Start

**ArcGIS Pro must be installed, and you must be signed in to it.** The tool pulls live data from ArcGIS Online through your Pro sign-in. If you have recently signed out, open Pro, sign back in, then start this tool.

You also need access to the Stormwater Inlets layer. If you get a connection error and you are definitely signed in, contact GIS about layer permissions.

---

## What It Does

### Catch Basin Cleaning Analysis

Cleanings, basins cleaned, and sediment volume removed, broken out by town fiscal year and MS4 permit year.

### Sump Depth Analysis

Sump depths across the inlet inventory, filtered by threshold or grouped into ranges.

> **Read the methodology before quoting any volume number in a report.**
>
> - Full usage notes are in the program under **Help → About**.
> - How the volume figures are calculated is under **Help → Methodology**.

---

## If Something Goes Wrong

**"Entry Point Not Found" error mentioning `BGLImageCoders.dll`**

This is a known ArcGIS Pro conflict and is harmless. Click OK and the program continues.

**The program does not open at all, or closes immediately**

Run `launch_debug.bat` instead. It does the same thing but leaves a black console window open showing the error.

---

## Notes

- Keep the whole `stormwater_analysis` folder together. Copying only the launcher will not work; it needs the script, the icon, and the about file alongside it.
- `item_ids.json` holds the ArcGIS Online item ID for the inlets layer. It does not normally need to be edited.