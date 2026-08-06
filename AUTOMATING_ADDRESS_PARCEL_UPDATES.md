Aaron Portanova<br>
*August 2026*


The sections below describe my processes for maintaining tax parcels and addresses in GIS, a central role of municipal engineering departments.

# Tax Parcel Management

Tax parcels are polygons representing surveyed property boundaries, paired with their assessment records. Massachusetts requires towns to maintain parcel GIS data to a state-defined standard <a href="https://www.mass.gov/info-details/massgis-standard-for-digital-parcels-and-related-data-sets">(MassGIS Digital Parcel Mapping Standard)</a> and to submit it annually.

As properties are split, merged, or reassessed, I keep Braintree's parcel data in sync with the Assessor's office and the Registry of Deeds — monitoring for newly accepted plans, then updating parcel geometry to match.

<!-- screenshot/gif idea: a before/after of a parcel split in ArcGIS Pro -->

## Data Model

I maintain a master parcels geodatabase locally in ArcGIS Pro:

- **Tax Parcels** (feature class)
- **Other Legal** (feature class)
- **Misc** (feature class)
- **Assessor Database Extract** (table)
- **Parcel Type Lookup** (table)
- **Use Code Lookup** (table)

Tax Parcels relates to the Assessor Database Extract in a 1:many relationship — condos and multi-unit properties often carry several assessment records per parcel — so a single click in GIS surfaces every associated record.

Beyond the state standard's required fields, I've added Google Street View, Google Maps, Registry of Deeds, tax map, and related-document links to each parcel. Internally, this also surfaces water, sewer, and sump pump connection records through SharePoint (login-gated, so not visible on the public version).

## Publishing to ArcGIS Online

The master layer is published as a hosted feature service — a joined parcel view plus its related assessment table — that gets overwritten each time I push updates. This service powers both a public and an internal web map, letting users search by address, Parcel ID, or owner name and pull up full assessment details and links via the popup.

<!-- screenshot/gif idea: the public web map, searching an address and showing the popup -->

I also maintain an **Abutter Parcels** layer — one feature per assessment record, rather than one per parcel — so a simple buffer-and-select for abutter notifications correctly pulls every associated record, even for parcels with multiple assessments.

## Automating the Update

Splits, merges, and the assessor ETL are still done manually in GIS, but I've written a Python script that handles the publishing side end-to-end: staging the parcels and assessment table, connecting to ArcGIS Online, and deleting/overwriting the hosted layer and related table — plus regenerating the Abutter Parcels layer each run.

I use a delete-and-reload approach rather than ArcGIS Pro's "Overwrite Web Layer" — it gives me full control over exactly what changes, without disturbing existing symbology or breaking published item URLs. After a batch of parcel edits and a fresh assessor extract, I run the script, log into AGOL, and the published layers are back in sync within a few minutes. All intermediate data is cleaned up automatically, whether or not the run succeeds.

## Generating Tax Maps

Once parcels are updated, I regenerate the affected tax map. Braintree's assessor maps are divided by section, and the first four digits of each Parcel ID correspond to a map number — so I built a custom **Make Tax Map** script tool with a standardized layout: enter a map number, choose 11x17 or 24x36, set rotation and zoom, and it auto-generates the map, ready for final adjustment and export.

<!-- screenshot/gif idea: the tax map tool interface, or a before/after of an auto-generated map -->

# Address Management

I assign and manage address numbers in GIS, and curate and maintain Braintree's Master Address database, associating assessment records with address points as they're created or changed.

## Integration with PermitEyes

I built Braintree's Master Address Database (MAD) from the MassGIS NextGen 9-1-1 MAD format, linking each address point to its assessor record via a unique GIS_ID. This enables address referencing between the ArcGIS Online feature layer and external databases, and enforces official address assignment before permits are issued.


<a href="https://braintreema.maps.arcgis.com/home/item.html?id=8e2abd62703847e1809f2f67e7eb4939#overview">View Braintree's Master Address Database</a>


# **Automating Address and Tax Parcel Updates**

As GIS Coordinator, I maintain Braintree's tax parcel data to the MassGIS standard, keeping it in sync with the Assessor's office and the Registry of Deeds as properties split, merge, or get reassessed. That work includes managing a master geodatabase of parcels, assessment records, and lookup tables, publishing to ArcGIS Online through a custom delete-and-reload Python script, and generating standardized tax maps with a script tool I built for the purpose.

I also assign and manage address numbers in GIS and maintain Braintree's Master Address Database, which was built from the MassGIS NextGen 9-1-1 format and stays linked to assessor records through a unique GIS_ID. It integrates with PermitEyes to enforce official address assignment before a permit can be issued, which keeps addressing authoritative at the exact point where bad addresses would otherwise enter the system.

[← All Projects](README.md)
