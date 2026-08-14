Aaron Portanova<br>
*August 2026*

# **Automating Address and Tax Parcel Updates**

***Automating Master Address and Tax Parcel dataset updates - maintaining a Master Address Database, Tax Parcel boundaries, and their associated Assessment records in ArcGIS Online.***

[← All Projects](README.md)

---

## Contents

**Tax Parcels**

| Section | Description |
|---|---|
| [Overview of Tax Parcels](#overview-of-tax-parcels) | What are GIS Tax Parcels and why do they matter? |
| [Maintaining Tax Parcels](#maintaining-tax-parcels) | Maintaining an authoritative Tax Parcel geodatabase in ArcGIS Pro |
| [Tax Parcels Data Model](#tax-parcels-data-model) | Structure of the parcels dataset |
| [The Assessor Extract](#the-assessor-extract) | Getting CAMA data into the geodatabase correctly |
| [Automating Tax Parcel Updates](#automating-tax-parcel-updates) | Automating the publish workflow |
| [Generating Tax Maps](#generating-tax-maps) | Generating printable Tax Map layouts |
| [Tax Parcel Media](#tax-parcel-media) | Screenshots of the parcel maintenance process |

**Addresses**

| Section | Description |
|---|---|
| [Overview of Addresses](#overview-of-addresses) | Why keep addresses in GIS? |
| [Maintaining Addresses](#maintaining-addresses) | Maintaining a Master Address database in ArcGIS Pro |
| [Address Data Model](#address-data-model) | Structure of the address dataset |
| [Spreading Stacked Address Points](#spreading-stacked-address-points) | Making thousands of coincident points legible |
| [Automating Address Updates](#automating-address-updates) | The Generate PermitEyes Points script |
| [Publishing Challenges](#publishing-challenges) | GlobalIDs, error 00374, and View Layers |
| [Integration with PermitEyes](#integration-with-permiteyes) | Matching addresses to assessor records |
| [Address Media](#address-media) | Screenshots of the addressing process |

**Both**

| Section | Description |
|---|---|
| [Lessons Learned](#lessons-learned) | What I'd tell someone else doing this work |

---

## Overview of Tax Parcels

MassGIS - the Commonwealth's Bureau of Geographic Information - requires towns to maintain parcel GIS data to a state-defined standard and to submit it annually: the [MassGIS Digital Parcel Mapping Standard](https://www.mass.gov/info-details/massgis-standard-for-digital-parcels-and-related-data-sets). Per the standard, Tax Parcels are "property (land lot) boundaries and database information from each community's assessor". In many communities, maintenance of the associated GIS parcel datasets falls on the person in charge of GIS, or is otherwise subcontracted.

The assessor maintains property records separately in a standard CAMA (computer-aided mass appraisal) database system. Each parcel may have one or more assessor records, but every assessor record (in theory) is related to only one parcel - in practice the state allows a small percentage of 'mismatches', parcels without an assessor record and vice versa. From the parcel side, this data is exposed through GIS by relating the parcel dataset to an extract of the assessor database in a 1:many structure.

I maintain Braintree's tax parcel data to the MassGIS standard, keeping it in sync with the Assessor's office and the Registry of Deeds as properties split, merge, or get reassessed. That work includes managing a master geodatabase of parcels, assessment records (extracted from the assessor database), and lookup tables, publishing to ArcGIS Online through a custom delete-and-reload Python script, and generating standardized tax maps with a script tool I built for the purpose.

Tax Parcels are an authoritative GIS layer for display and assessment-record linking only. They are NOT survey-grade property boundaries, and are not a substitute for the work of a licensed professional land surveyor.

---

## Maintaining Tax Parcels

As properties are split, merged, or reassessed, the plans are recorded by the town and submitted to the county's Registry of Deeds. Plans are not considered official lot changes until they are recorded at the registry. I keep Braintree's parcel data in sync with the Assessor's office and the Registry of Deeds - monitoring for newly accepted plans, then updating parcel geometry to match. I assign new lot IDs, confirm lot sizes, and notify the Assessor's Office of the updates they need to make from the GIS side of things.

These updates add a key value to the assessor database that is needed to link the GIS dataset to an assessor database extract: the location ID, or `LOC_ID`. Each parcel has a `LOC_ID`, which is a text string of the center point of the parcel preceded by an `F_` (feet) or `M_` (meters), depending on the spatial reference of the parcel dataset. I maintain Braintree's parcels in the Mass State Plane (Feet) coordinate system, so our `LOC_IDs` are in the form `F_1234567_1234567`. The point-in-parcel structure ensures that the IDs are unique. The assessor database is related to the Parcels dataset through `LOC_ID`, which allows for joins and relates in ArcGIS Pro.

The `LOC_ID` is worth dwelling on, because almost everything downstream depends on it. It is a *geometry-derived* key, so it can't collide, and it doesn't require a separate ID-issuing process across two departments. But it also means that moving a parcel boundary enough to shift its centroid invalidates the key. Splits and merges therefore aren't just geometry edits; they're key changes that have to be communicated to the Assessor's office, or the join drops those records on the next publish.

---

## Tax Parcels Data Model

I maintain a master parcels geodatabase locally in ArcGIS Pro:

| Name | Description | Type |
| --- | --- | --- |
| M040TaxPar| Tax Parcels | Feature Class |
| M040OthLeg | Other Legal | Feature Class |
| M040Misc | Miscellaneous | Feature Class |
| M040Assess | Assessor Table Extract | Table |
| M040LUT | Parcel Code Lookup Table | Table | 
| M040UC_LUT | Use Code Lookup Table | Table |
| M040Links | Links Table | Table |
| M040TaxPar_M040Assess_Rel | Parcel / Assess  Table Relationship | Relationship Class

Tax Parcels relates to the Assessor Database Extract in a 1:many relationship through a relationship class - condos and multi-unit properties often carry several assessment records per parcel - so a single click in GIS surfaces every associated record.

Aside from the required fields and geodatabase contents of the parcel standard, MassGIS gives communities leeway to add additional fields and tables to the geodatabase. Beyond the state standard's required fields, I've added Google Street View, Google Maps, Registry of Deeds, and Tax Map links to each parcel. Internally, a Related Documents link surfaces water, sewer, and sump pump connection records through SharePoint (login-gated, so not visible on the public version).

These additional fields are stored in a `Links` table that I keep in the master parcel geodatabase, linked through `LOC_ID`:

- **Google links** are fairly easy to derive with the Field Calculator tool, as they are just a URL with lat/lon pointing to a location. I originally took parcel centroids and joined on the `LOC_ID` field.
- **The Registry of Deeds link** is a URL with an address query. An address field is also stored in the Links table and updated when I run my parcel automation script - `LOC_ID` must be entered or updated manually.
- **Tax Map links** came from publishing the Tax Map layouts to ArcGIS Online and capturing the tax map number (the first 4 digits of the Parcel ID) alongside the published URL, allowing me to join a Tax Map URL to each value in the links table.
- **Related Documents** links point into the SharePoint tie card archive described in [Processing Utility Documents](PROCESSING_UTILITY_DOCS.md).

I've also consolidated our Rights of Way and Easements GIS layers to be stored inside the `Other Legal` feature class, which is intended to store things like easements and takings. The goal is ultimately to scan and store the related easement and taking documents on SharePoint and make them available by clicking on the respective easement in GIS, but this is a long term goal.

New parcel updates happen one or two at a time, so updating links manually is trivial.

A note on lot size: the standard's `LOT_SIZE` field is stored in hundredths of an acre, so the publish script derives a `LOT_ACRES` field by dividing by 100. Where `LOT_SIZE` is null or zero (i.e. very small parcels), it falls back to a planar area calculation from the geometry itself. That fallback is deliberate - a parcel with no assessor-provided lot size still needs a usable acreage for abutter work and general reference - but it's worth knowing that those values are *map* acreage, not assessed acreage, and the two won't always agree.

---

## The Assessor Extract

The assessment records come out of the Assessor's CAMA system (Patriot Properties) as a delimited text extract, and getting that file into the geodatabase *correctly* matters more than it looks like it should.

I originally wrote my own conversion routine for this - reading the extract, applying a field-name header, and writing out a CSV. It worked, but it was solving a problem that had already been solved, and it was solving it without reference to the state schema. The MassGIS parcel standard defines not just which fields the assessment table must have but what type each one is, and my working layer had quietly ignored that. I found out when I ran the MassGIS Parcels QA test against my dataset and it came back with field type errors, so it didn't pass. Fixing it meant reformatting the whole dataset, republishing, and rebuilding it into every map that consumed it - an entirely avoidable headache.

MassGIS provides an **Assess Prep** tool that does exactly what I'd been trying to do by hand. You point it at the extract from the assessor database, tell it which CAMA system the file came from (Patriot, in Braintree's case) and which town, and run it. It produces a `postproc.txt` output along with a schema file mapping field names to their correct field types.

Loading it is a short manual process:

1. Open the Assess Table in ArcGIS Pro and delete all of its contents.
2. Right-click the Assess Table in the geodatabase and choose **Load Data**.
3. Select the `postproc.txt` output from the Assess Prep tool.
4. Choose **use the field map to reconcile field differences**, and run.

The table loads with the correct schema, and the dataset passes QA. The lesson is to check whether a tool already exists before writing your own version.

---

## Automating Tax Parcel Updates

The master layer is published as a hosted feature service - a joined parcel view plus its related assessment table - that gets overwritten each time I push updates. A View Layer was created from the published parcels layer to control popups and symbology, and to create a second degree of removal from the source data, which prevents accidental edits to the parent hosted feature layer. This service powers both a public and an internal web map, letting users search by address, Parcel ID, or owner name and pull up full assessment details and links via the popup.

Splits, merges, and the assessor ETL are still done manually in GIS, but I've written a Python script that handles the publishing side. The script is organized into three files - a `config.py` holding every path, field name, URL, and constant; a `functions.py` holding the reusable GIS and AGOL operations as class methods; and an `update_parcels.py` that reads as a list of steps. Keeping the paths out of the logic means a drive letter change or a new sublayer index is a one-line edit in one file rather than a search-and-replace across the whole workflow.

A single run does the following:

1. **Creates clean intermediate geodatabases** - `Published_Parcels.gdb` and two zip staging geodatabases. These must not already exist when the script starts, which is a deliberate guard against a half-finished previous run contaminating the current one.
2. **Loads the staging geodatabase** by projecting `M040TaxPar` from Mass State Plane to Web Mercator (EPSG:3857) for web display, and copying in the assessor extract and Links table.
3. **Joins the Assessor and Links tables** to the parcel feature class on `LOC_ID`, then drops the field artifacts that a join always produces (`LOC_ID_1`, `MAP_PAR_ID_1`, duplicated address fields, assessor internal fields..).
4. **Builds the Abutter Parcels layer** - see below.
5. **Calculates `LOT_ACRES`** from `LOT_SIZE`, falling back to geometry.
6. **Deletes `ROW` features** from the `POLY_TYPE` field, since rights-of-way aren't taxable parcels and don't belong in the published layer.
7. **Creates the relationship class** between parcels and the assessment table on `LOC_ID`, one-to-many.
8. **Zips the staging geodatabases** to a timestamped archive path, giving me a dated snapshot of every publish as a side-effect.
9. **Connects to ArcGIS Online**, deletes all features from the hosted parcel layer and its related table, then appends the contents of the uploaded zipped file geodatabase. The related assessment table is written in batches of 100 records.
10. **Cleans up** - clears workspace locks, deletes every intermediate geodatabase, and removes the temporary uploaded zip item from AGOL's My Content.

I use a delete-and-reload approach rather than ArcGIS Pro's "Overwrite Web Layer" - it gives me full control over exactly what changes, without disturbing existing symbology or breaking published item URLs. After a batch of parcel edits and a fresh assessor extract, I run the script, log into AGOL, and the published layers are back in sync within a few minutes. All intermediate data is cleaned up automatically, whether or not the run succeeds.

I also maintain an **Abutter Parcels** layer - one feature per assessment record, rather than one per parcel - so a simple buffer-and-select for abutter notifications correctly pulls every associated record, even for parcels with multiple assessments. The script builds it by loading every parcel geometry into a dictionary keyed on `LOC_ID`, then iterating the assessment table and inserting one polygon per assessment record with the parcel's geometry duplicated. For a 40-unit condo building, that produces 40 coincident polygons - which looks absurd on a map, but is correct for a notification query.

---

## Generating Tax Maps

Once parcels are updated, I regenerate the affected tax map. Braintree's assessor maps are divided by section, and the first four digits of each Parcel ID correspond to a map number - so I built a custom **Make Tax Map** script tool with a standardized layout: enter a map number, choose 11x17 or 24x36, set rotation and zoom, and it auto-generates the map, ready for final adjustment and export. Additionally, Tax Map labels are drawn from annotation classes, and not feature labels themselves. Since these are their own datasets, I keep addresses, historic lines, and lot sizes updated there too.

---

## Tax Parcel Media

<div align="center">
    <img src="media/something.jpg" width="100%"><br>
    Before / after of a lot split
</div><br>

<div align="center">
    <img src="media/Generate_Tax_Map.gif" width="100%"><br>
    Example of automatic Tax Map generation
</div><br>

---
---

## Overview of Addresses

I assign and manage address numbers in GIS and maintain Braintree's Master Address Database as a hosted feature layer, originally derived from the MassGIS NextGen 9-1-1 dataset for the State of Massachusetts. The point is to preserve accurate address points for Braintree, and to link those addresses with their respective record in the assessor database through the `CAMA_ID`, and with their respective permits in PermitEyes database through the `GIS_ID`.

That link is what makes the dataset more than a labeling layer. It integrates with PermitEyes to enforce official address assignment before a permit can be issued, which keeps addressing authoritative at the exact point where bad addresses would otherwise enter the system (i.e. whenever someone types one into a permit application manually).

---

## Maintaining Addresses

I assign and manage address numbers in GIS, and curate and maintain Braintree's Master Address database, creating address points and associating assessor records with them as they're created or changed.

Day-to-day maintenance is intentionally manual. `CAMA_ID`, `ACTIVE_STATUS`, and `ADU` are all maintained by hand on the master layer, because each of them represents a judgment call - whether this address point corresponds to that assessor record, whether an address is still in use, whether a unit qualifies as an accessory dwelling unit. Those aren't decisions a script should be making - the automation exists to handle what happens after those decisions.

---

## Address Data Model

One `Addresses` geodatabase with two feature classes:

- `M040_Master_Address_Points` (master)
- `Braintree_Master_Address_Points` (derived, used for publish)

`M040_Master_Address_Points` is my local 'copy' of the NextGen 9-1-1 dataset: all address points associated with a building are stacked on top of each other. Displaying this dataset on a web map would only show labels for the top few points at best. For buildings with hundreds of addresses this is useless, so I created a `Braintree_Master_Address_Points` layer for publishing, where all points that overlap are spread out. Neither of these datasets shows the address points at the 'point of entry' of the building or home that they label, and are strictly for labeling.

On top of the fields that exist in the MassGIS Master Address dataset, I added fields for **ADU** (accessory dwelling unit - yes/no) and **Active Status** (active, inactive, retired). I also created a **GIS_ID** field (type GUID), which is calculated from the GlobalID of the parent layer. This is used by PermitEyes as the unique GIS ID to tie permit records to address points.

The reason I created a `GIS_ID` field is because I required two datasets, one with the stacked points and then one for publish and integration with the permit database. If I simply used a GlobalID on the `Braintree_Master_Address_Points` layer, ArcGIS would recalculate it every time I re-ran my script, breaking the link after the first publish. `GIS_ID` preserves the GlobalID of the parent forever.

This is the single most important design decision in the whole address workflow. An external system holding a foreign key into your GIS is only useful if that key is stable, and system-managed IDs are only stable within a dataset - not across a regenerated one. Copying the parent's GlobalID into a plain GUID field on the derived layer decouples the key from ArcGIS's own housekeeping.

---

## Spreading Stacked Address Points

The spreading routine is the most involved part of the address script, because "make coincident points readable" turns out to have a lot of edge cases in a town with large apartment complexes.

The script first finds clusters - any points within one foot of each other - then handles each cluster independently:

- **Base addresses** (no `UNIT` value) are stacked vertically at 3-foot spacing, sorted by `FULL_NUMBER_STANDARDIZED`, in columns of up to 10. Additional columns expand *left* from the cluster centroid, so the lowest numbers stay on the left.
- **Unit addresses** are offset 6 feet to the right of the centroid and grouped by their `FULL_NUMBER_STANDARDIZED`, so every unit at 8A sits in its own column, separate from the units at 8B. Within a group, units sort naturally by unit value. Columns hold up to 10 units normally, or 25 for very large clusters, so a 300-unit complex doesn't produce a column half a mile tall.
- Every column is vertically centered on the cluster centroid, so the resulting arrangement reads as a block rather than drifting off in one direction.

Address and unit values are text, which means a naive sort gives you 1, 10, 2, 3 - and mixed values like `1A`, `10B`, `B` make it worse. The script uses a natural sort key that splits a leading integer from any trailing letters and sorts on the tuple, with alpha values after numeric ones, and nulls last. It's a small function that does a disproportionate amount of work for how the final map looks.

---

## Automating Address Updates

When a new address is assigned, I create the point on the `M040_Master_Address_Points` feature class and enter the address information. The **Generate PermitEyes Points** script then takes that dataset, enriches it, spreads the points, and overwrites `Braintree_Master_Address_Points`.

The steps in order:

1. **Project** the master address points to Web Mercator.
2. **Create and populate `GIS_ID`** from the GlobalID.
3. **Rename the existing `LOC_ID` and `MAP_PAR_ID`** to `_OLD` so they can be replaced with authoritative values from the parcels layer rather than trusted from the previous run.
4. **Spatially join the parcels layer** using a `WITHIN` match, one-to-one, keeping all address points - so an address that falls outside every parcel still survives the join, just without a `LOC_ID`. The script reports the with/without counts, which is my check that nothing has drifted.
5. **Write `LOC_ID` back to the master layer**, matching on GlobalID and only updating rows where the value actually changed. This is the one place the script edits its own input, and it's intentional: the parcel a point sits in is a spatial fact, not a manual decision, so it should propagate back upstream automatically.
6. **Join the assessor table** on `CAMA_ID`. The assessor extract stores `CAMA_ID` as a double and the address layer stores it as text, so the script builds a text version of the field first - converting through `int()` to strip the decimal that would otherwise make the join fail.
7. **Calculate `FULL_ADDRESS`** from the standardized number and street name, with no unit component.
8. **Delete join artifacts** using an explicit deletion list rather than an explicit keep list, so a new field arriving in the assessor extract is retained by default instead of vanishing.
9. **Spread the overlapping points** as described above.
10. **Reorder fields and set aliases** using a `FieldMappings` object built from an ordered list of name/alias pairs, so the published popup reads in a sensible order with human-readable labels. Any field not in the list is appended at the end rather than dropped.
11. **Write the final output** and print a verification summary - total records, and populated counts for `GIS_ID`, `CAMA_ID`, `LOC_ID`, `MAP_PAR_ID`, owner info, `ACTIVE_STATUS`, and `ADU`.

From there I overwrite the web layer in ArcGIS Online, and the View Layer that PermitEyes consumes updates automatically.

The script cleans up its temporary datasets in a `finally` block, so a failure partway through doesn't leave a pile of `temp_` feature classes behind.

---

## Publishing Challenges

**GlobalIDs disappear partway through a geoprocessing chain.** The `GIS_ID` approach only works if the GlobalID is still there when the script goes to read it, and several common tools - projections, copies, conversions - drop the GlobalID property from their output. Tracking this down meant instrumenting the script with a check after every step, printing `hasGlobalID` and whether the field itself still existed, until the exact step that lost it became obvious. Worth doing preemptively on any workflow that depends on a system-managed field surviving a chain of tools.

**Error 00374 on publish.** Republishing routinely threw "unique numeric IDs not assigned," and the easy fix is to click through and let ArcGIS auto-assign them sequentially. That works fine for a full overwrite of static data, which is why it never appeared to cause problems. It stops being fine as soon as ObjectIDs need to stay stable between publishes - related tables, attachments, selective edits, editor tracking. Adding proper GlobalIDs to the feature class before publishing is the actual answer, and never using OBJECTID to do joins on data that gets routinely refreshed.

Overwriting a hosted feature layer does not disturb the symbology of a View Layer built on top of it, and does not break the view's connection to its source. That's what makes the View Layer pattern viable here (and part of the beauty of View Layers in general) - I can republish the parent as often as I like without touching the styling that every web map depends on. The things that would break it are schema changes that remove fields the symbology references, or deleting and republishing the whole layer rather than overwriting (which obviously creates a new item ID and orphans every reference to it).

---

## Integration with PermitEyes

I built Braintree's Master Address Database (MAD) from the MassGIS NextGen 9-1-1 MAD format, linking each address point to its assessor record via a unique `GIS_ID`. This enables address referencing between the ArcGIS Online feature layer and external databases, and enforces official address assignment before permits are issued.

Linking address points to their respective CAMA ID was a significant effort and it involved multiple address-matching processes, as the Master Address dataset stores address information differently than the assessor database. The initial pass produced a pretty high match rate, but there were still thousands of unmatched addresses, mostly on lots with apartments or condos or multi-unit properties. As is the case in many municipalities, apartment addressing conventions are not standard in Braintree, so one complex might be addressed differently than another.

### Triaging Before Matching

The idea that made this effort manageable was not writing a better matching algorithm - it was categorizing the problem first.

Rather than running one script at 12,000 addresses and manually sorting through whatever failed, I wrote a QC pass that compared, for each parcel, the number of address points against the number of assessor records, and assigned categories:

| Category | Meaning | Strategy |
|---|---|---|
| `OK` | Counts match, one-to-one | Bulk assign by `LOC_ID` - no address parsing needed |
| `MATCH_MULTI` | Counts match, multiple records | Assign by normalized address within the parcel |
| `EXTRA_ADDRESSES` | More address points than assessor records | Needs review - likely retired or duplicate points |
| `NEEDS_ADDRESSES` | More assessor records than address points | Missing address points, had to be created |

That split turned one hard problem into several easier ones. The `OK` parcels needed no address matching at all - if a parcel has exactly one address point and exactly one assessor record, the assignment is unambiguous regardless of how the two systems spell the street. `MATCH_MULTI` needed matching, but only *within* a parcel, which shrinks the candidate pool from 12,000 to a handful and makes near-misses less dangerous.

### Normalizing and Matching

For the parcels that did need address matching, the script builds a lookup from the assessor table using a normalized form of each address, then normalizes each address point the same way and matches on the result. Normalization handles the differences that actually occur between the two systems:

- Street type abbreviation variants (`ST` / `STREET`, `DR` / `DRIVE`, `LN` / `LANE`, and so on)
- Unit designations present on one side and absent on the other (`12B` versus `12`)
- Alphanumeric address numbers with letter suffixes (`76A`, `140B`, `250R`)
- Casing and extra spaces

Every run reports matched and unmatched counts, lists the unmatched addresses, and prints the distinct `LOC_ID` values of the parcels containing unmatched addresses as a ready-to-paste SQL `WHERE` clause, which saved the most time. Selecting the problem parcels in ArcGIS Pro then took one paste rather than a hunt.

Running this complex by complex worked well. Devon Wood matched 398 of 398 on the first pass. The whole `MATCH_MULTI` category came in at 451 of 452, with a single address on Allen Street left over.

### The Remainder

Between the categorical triage and the normalized matching, the process reached about **99.4% automation** - roughly 68 parcels out of 12,000 needed a human. Those were mostly multifamily homes and the more creatively-addressed apartment complexes, and I worked through them by hand.

That last 0.6% could have been automated, in the sense that another few rounds of complex-specific rules would eventually have caught it. But it wouldn't have been worth the effort: writing, testing, and verifying those rules would have taken longer than a few hours of manual assignment, and would have left behind rules nobody would ever run again.

[View Braintree's Master Address Database](https://braintreema.maps.arcgis.com/home/item.html?id=8e2abd62703847e1809f2f67e7eb4939#overview)

---

## Address Media

<div align="center">
    <img src="media/something.jpg" width="100%"><br>
    Master dataset stacked points vs published 'spread' points
</div><br>

<div align="center">
    <img src="media/something.jpg" width="100%"><br>
    Unit addresses grouped and stacked at a multi-unit complex
</div><br>

---

## Lessons Learned

**A geometry-derived key is elegant until the geometry changes.** `LOC_ID` guarantees uniqueness for free since it's inside a unique parcel, which is clever. The cost is that editing a boundary can change it, which can break the join. This kind of workflow requires a deliberate step for communicating those changes to whoever holds the other half of the relationship, in my case the Assessor's office.

**Never let an external system depend on a system-managed ID.** GlobalIDs are stable within a dataset but meaningless across a regenerated one. Copying the parent's GlobalID into a plain GUID field is a one-line change that makes an entire integration possible.

**Categorize before you match.** The biggest success in the address work wasn't a better matching algorithm - it was a QC pass that sorted parcels by whether their address and assessor record counts agreed. Most of them needed no address parsing at all, and the ones that did only had to be matched against a handful of candidates within their own parcel. Sorting the problem first turned one hard problem into several easier ones.

**Know when to stop automating.** The last 68 parcels out of 12,000 could have been automated with enough complex-specific rules. A few hours by hand was cheaper than writing, testing, and verifying rules that would never be used again.

**Separate config from logic early on.** Splitting paths, URLs, field names, and constants into their own file made every subsequent change to these scripts cheaper. It also makes the main script readable as an order of operations rather than a bunch of hardcoded paths.

**Delete-and-reload trades convenience for control.** Overwrite Web Layer is one click, but it can disturb symbology and item URLs. Deleting features and appending gives me exact control over what changes - with the tradeoff that the local master has to be the single source of truth, since anything edited on the online side won't survive the next run. It also allows for extensive customization in one run, since the 'overwrite parcels' script does significantly more than 'overwrite web layer' would do by itself.

**Check for the official tool before building your own.** I wrote a conversion routine for the assessor extract that MassGIS had already solved with Assess Prep, and in the process shipped a dataset that failed the state QA test on field types. Reformatting and republishing everything multiple times cost far more than twenty minutes of reading would have.

**Type mismatches are the most common cause of a failed join, and not very obvious.** A `CAMA_ID` stored as a double joining to one stored as text produces zero matches and no error at all - the join simply succeeds and populates nothing. It's now handled explicitly in the address script, but it cost me time.

**Print your counts.** Every one of these scripts reports how many records got a `LOC_ID`, how many got owner info, how many were spread. Those numbers are how I know a run was clean without opening the output, and how I notice when something has shifted.

**Delete by explicit list, not by exclusion.** The address script names the fields it removes rather than the fields it keeps, so a new field appearing in the assessor extract survives to the output and I find out about it. The reverse would drop it with no mention of what happened.

---

[← All Projects](README.md)