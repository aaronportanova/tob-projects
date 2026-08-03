Aaron Portanova<br>
*August 2026*

# **Analyzing Impervious Surfaces**

The Stormwater department bills a utility fee on residential and non-residential properties, and while residential parcels pay a fixed fee, non-residential parcels are billed on how much impervious surface exists on them. As properties are developed or boundaries change, that number changes too, so it has to be routinely recalculated and compared against historical data to keep our billing database accurate. I produced an automated, parcel-level comparison of impervious surface change using ArcPy geoprocessing workflows and custom scripts, calculating the impervious area that actually exists on each non-residential parcel and comparing it to the value being billed and to prior years.

Most of the time those numbers align closely, but the analysis surfaces parcels that appear to be over- or under-billed. Often that's an artifact of an imperfect impervious surface dataset, but in some cases it's a genuine billing discrepancy worth investigating. The analysis runs in ArcGIS Pro and exports cleanly to an Excel table that the Stormwater department can use to check parcels against the billing system and update it accordingly.

[← All Projects](README.md)
