Aaron Portanova<br>
*August 2026*

# **Managing a Drone Program**

***Building a municipal sUAS program for the Town of Braintree Engineering Department - certification, equipment, processing workflow, and the "SOPs" that make it scalable beyond one pilot.***

[← All Projects](README.md)

---

## Contents

| Section | Description |
|---|---|
| [Overview](#overview) | What the program is and why it exists |
| [Certification and Authorization](#certification-and-authorization) | Part 107, LAANC, and flight authorization |
| [Equipment](#equipment) | Aircraft, sensors, and RTK positioning |
| [Capture Workflow](#capture-workflow) | Mission planning through flight execution |
| [Processing Workflow](#processing-workflow) | DJI Terra to ArcGIS Online |
| [Applications](#applications) | How the outputs actually get used |
| [Standard Operating Procedures](#standard-operating-procedures) | Documentation, checklists, and reporting |
| [Data Management and Retention](#data-management-and-retention) | Storage tiers, archiving, and FOIA obligations |
| [Lessons Learned](#lessons-learned) | What I'd tell someone standing one of these up |

---

## Overview

In 2025-2026 I built out a municipal drone program for the Town of Braintree Engineering Department, from certification through equipment procurement, processing workflow, and written standard practices. The program produces 2D orthomosaics and 3D models used for site development monitoring, pre- and post-paving documentation, and locating buried infrastructure before it disappears under pavement - with results published through ArcGIS Online so the rest of the organization can use them without needing desktop GIS or photogrammetry software.

The distinction I've tried to hold onto throughout is between *flying a drone* and *running a program*. A single pilot with an aircraft can produce a nice orthomosaic. A program produces repeatable deliverables on a documented schedule, survives the pilot leaving, satisfies public records obligations, and has an answer for where the data lives in five years. Most of the work described below is in service of the second thing.

---

## Certification and Authorization

I earned my FAA Part 107 Remote Pilot certification at Norwood Airport after preparing through Bridgewater State University's sUAS program, with the certificate issued in March 2026. Part 107 is the operative rule set for commercial and government sUAS operations, and it governs the practical constraints the program runs under - visual line of sight, altitude ceilings, operations over people, and daylight/civil twilight limits.

Braintree's airspace situation makes authorization a routine part of mission planning rather than an afterthought. Flights in controlled airspace are cleared through **LAANC** (Low Altitude Authorization and Notification Capability), which provides near-immediate authorization for operations within pre-approved altitude ceilings in a given grid. Requesting authorization is built into the pre-flight checklist rather than handled ad hoc, and authorization records are retained alongside the mission documentation.

The Northern section of Braintree is clipped by Class B Airspace around Logan International, and so **LAANC** approval is required to fly there. This is a standard practice: open a B4UFLY app like Aloft Air Control, draw a polygon where you will be flying, provide a max altitude for the mission (300 feet AGL, opposed to 400 feet AGL in uncontrolled airspace), and submit a **LAANC** approval request. The requests are almost instantly approved, and you are granted a several-hour window in which to conduct the flight.

---

## Equipment

The program is built around a **DJI Matrice 4E**, an RTK-enabled mapping platform. The 4E was chosen over the thermal-equipped 4T after evaluating whether thermal use cases - roof moisture inspection, outfall monitoring, building envelope assessment - were likely to materialize often enough to justify the cost difference. They weren't, and a thermal platform can be rented for a specific project if that changes.

**RTK positioning** is the feature that matters most for the program's purpose. With an RTK correction stream, the aircraft's image geotags are accurate to roughly a centimeter rather than the several-meter accuracy of a standard onboard GNSS receiver. In practice this means orthomosaics land in the correct real-world position without a ground control point network, which removes the single most labor-intensive step from a traditional photogrammetry workflow. For municipal work - where the deliverable needs to line up against existing parcel, utility, and roadway data - that positional fidelity is the whole point.

The department also operates two **Emlid Reach RX** RTK GNSS receivers connected to the MaCORS network over NTRIP, used with ArcGIS Field Maps for ground-based feature collection. These are documented separately under [Using a Survey Grade GPS](USING_GPS.md), but the two efforts are complementary: aerial capture for surface conditions and extents, ground survey for precise point features and anything under canopy.

---

## Capture Workflow

Mission planning starts from the extent of interest and works backward to flight parameters. Altitude, overlap, and flight pattern are selected based on the deliverable - a 2D orthomosaic for paving documentation tolerates different settings than a 3D mesh of a structure.

A representative mapping mission runs at roughly **150-200 ft AGL with 80% front and 75% side overlap**, which for a large site (~100 acres) produces several hundred images. Higher overlap improves reconstruction quality (particularly for 3D) at the cost of flight time, battery swaps, image count, and downstream processing hours, so the setting is a deliberate trade rather than a default. A fully charged battery allows for roughly 40 minutes of flight time, so 3 fully charged batteries is sufficient for most missions (i.e. mapping a few hundred acres in 2D, or collecting many close-up photos of a structure for a high-resolution 3D model).  

Pre-flight follows a written checklist covering airspace authorization, weather and wind limits, battery state, storage capacity, RTK fix confirmation, and a brief site survey for obstructions and non-participating people. Post-flight, imagery is offloaded from the aircraft and the mission is logged.

---

## Processing Workflow

Imagery is processed in **DJI Terra**, which handles DJI's RTK metadata and camera lens profiles natively - a meaningful convenience, since it removes the guesswork of manually specifying sensor parameters. Our purchase of the Matrice 4E came with a 1-year subscription to Terra, and so far it's been rock solid.

**For 2D deliverables**, Terra outputs a georeferenced orthomosaic as GeoTIFF, along with a DSM and/or point cloud (if selected during processing). These drop directly into ArcGIS Pro, where I clip to the area of interest and reproject to Web Mercator (Auxillary Sphere) before publishing. Turnaround for a 2D product is fast - typically same-day.

**For 3D deliverables**, Terra produces a textured mesh, and the reconstruction is considerably more time-consuming (depending on image count and scene complexity). I will typically start a 3D reconstruction at the end of the day and leave my computer on overnight. The mesh is published to ArcGIS Online as an **I3S / Scene Layer Package (SLPK)**, which renders in Scene Viewer and ArcGIS Pro Local Scenes without requiring anyone downstream to install photogrammetry software.

A lighter-weight alternative I sometimes use where a full mesh isn't warranted: load the DSM as an elevation surface in a Pro Local Scene and drape the orthomosaic over it. That produces most of the visual value of a 3D product with none of the mesh processing cost.

Once published, outputs are shared through ArcGIS Online with the appropriate groups, which is what actually makes the program useful to the rest of the organization - engineering staff, other departments, and in some cases the public, can view results in a browser rather than requesting a file.

---

## Applications

**Site development monitoring.** Repeat captures of an active development site produce a dated visual record of conditions, useful for tracking progress against approved plans and for documenting what was actually built.

**Pre- and post-paving documentation.** Capturing a street before it's paved records the position of surface features - trench cuts, structure rims, utility markings - that become invisible once new pavement goes down. This has proven to be one of the highest-value applications, because the alternative to having the imagery is excavation or guesswork.

**Locating buried infrastructure.** Trench lines and disturbed pavement are often clearly visible from the air for a period after work is completed. Capturing that window preserves positional evidence of infrastructure that would otherwise rely on as-builts of varying quality.

**General base imagery.** Current, high-resolution, correctly-positioned imagery of town facilities and sites is broadly useful for engineering work in ways that are hard to predict in advance - which is an argument for capturing more than the immediate need.

---

## Standard Operating Procedures

Documenting the program was as deliberate as building it. The SOPs cover:

- **Standardized file structure** - a consistent directory scheme per mission so raw imagery, processing intermediates, and final deliverables are always in predictable locations.
- **Pre-flight checklists** - airspace authorization, weather limits, equipment state, and site assessment, performed and recorded the same way every time.
- **Mission reporting** - what was flown, when, why, at what parameters, and what was produced.
- **LAANC airspace authorization** - when it's required, how it's requested, and how the authorization record is retained.
- **Data retention** - a 7-year retention period driven by public records and FOIA obligations.

The purpose of writing all this down is scalability. A program that lives entirely in one person's head produces good results right up until that person is unavailable, and then produces nothing. Documented procedures mean a future remote pilot can be brought into the program and produce consistent deliverables without reverse-engineering someone else's habits.

---

## Data Management and Retention

Drone programs generate data volume faster than most municipal GIS workflows, and the 7-year FOIA-driven retention requirement means the answer to "can we delete this?" is usually no. That forced an explicit archiving strategy rather than an accumulating pile on a network share.

I triage mission data into three tiers:

| Tier | Contents | Treatment |
|---|---|---|
| **Irreplaceable** | Raw imagery, flight logs | Archived permanently; cannot be regenerated at any cost |
| **Expensive to reproduce** | Orthomosaics, DSMs, SLPKs, point clouds | Archived; regenerable from raw, but at significant processing time |
| **Disposable** | Processing intermediates | Deleted after deliverables are verified |

Cold storage is handled through external SSDs purchased annually, with the broader archiving framework developed alongside the town's IT department. The strategy is deliberately boring - the failure mode for drone data isn't exotic, it's simply running out of room and making bad deletion decisions under pressure.

---

## Lessons Learned

**The certification is the easy part.** Part 107 is a real exam requiring real study, but it's bounded and finite. Building the workflow, documentation, and data strategy around it took substantially longer and mattered more.

**Decide where the data lives before you generate any.** Retention obligations and file sizes are both known in advance. Working out the archiving approach after accumulating a few terabytes is meaningfully harder than working it out first.

**RTK earns its cost in workflow, not just accuracy.** The positional accuracy is the headline, but the practical value is eliminating ground control point placement - which is what actually determines whether a capture is a half-day job or a two-day job.

**Publish, don't distribute.** Handing colleagues a GeoTIFF creates a support obligation and immediately produces version drift. Publishing to ArcGIS Online means one authoritative copy, viewable in a browser, that stays current.

---

## Media
![Orthomosaic of the RMV site](media/RMV_Site.jpg)
Orthomosaic of the RMV site (~250 feet AGL, ~1 inch GSD)

![Orthomosaic of the RMV site (zoomed)](media/RMV_Site_zoomed.jpg)
Zoomed to a section of parking lot

![3D model of the RMV site](media/RMV_Site_3D.jpg)
3D model of the RMV site

<!-- pre / post paving example, in-person photo of drone being used -->
---

[← All Projects](README.md)