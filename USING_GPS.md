Aaron Portanova<br>
*August 2026*

# **Using a Survey-Grade GPS**

***Putting centimeter-accurate positioning in the hands of field crews - so the dot on the map is where the asset actually is, whether or not you can see it from the street.***

[← All Projects](README.md)

---

## Contents

| Section | Description |
|---|---|
| [Overview](#overview) | The problem and the shape of the solution |
| [Why Phone GPS Isn't Enough](#why-phone-gps-isnt-enough) | What a few meters of error actually costs |
| [Equipment and Corrections](#equipment-and-corrections) | The receiver, the network, and the datum |
| [Field Workflow](#field-workflow) | What staff actually do with it |
| [Utility Data Improvement](#utility-data-improvement) | The day-to-day use case |
| [Beyond Utilities](#beyond-utilities) | Cemeteries, memorials, and public-facing apps |
| [What This Does and Doesn't Solve](#what-this-does-and-doesnt-solve) | Honest scope |
| [Lessons Learned](#lessons-learned) | What I'd tell someone buying one |

---

## Overview

In 2025, the Engineering Department purchased an `Emlid Reach RX` RTK-enabled GNSS receiver to support GIS data collection workflows. It connects to the MaCORS RTK network over NTRIP for centimeter-level positional accuracy, and pairs with ArcGIS Field Maps as an external receiver in place of the significantly less capable GPS built into a mobile device.

The purchase was deliberately structured as a trial. We started with one unit to see how easy it was for field staff to use and how much value we'd actually get out of it in a normal work week. It was successful enough that we bought a second. The Water & Sewer department uses the original day-to-day; the Stormwater department uses the other to update our drainage system data, slowly improving the accuracy of our utility datasets over time.

The underlying goal is the same one behind most of our field work: shift data collection to the people who are already standing next to the asset. A crew member at a hydrant knows where the hydrant is better than any desk-based digitizing process ever will - the only thing missing was a way to record that location with precision.

---

## Why Phone GPS Isn't Enough

A phone or tablet's internal GNSS receiver is generally accurate to somewhere between three and ten meters in real-world conditions, and considerably worse under tree canopy, next to buildings, or anywhere multipath is a factor. For navigation that's fine. For asset management it isn't.

Legacy utility data compounds the problem. Much of our infrastructure was originally digitized from paper plans, scanned mylars, or heads-up tracing against imagery of varying quality or available as-builts. The result is a dataset that is *topologically* correct - the main runs down the right street, the hydrant is on the right side of the road - but positionally off, sometimes by several meters.

The cost of that inaccuracy is paid in the field, now that field staff genuinely rely on our maps to locate infrastructure. A few meters of error is the difference between finding a curb stop and probing a lawn for twenty minutes, between locating a manhole cover under six inches of snow and giving up, and between confident Dig Safe markouts or approximate ones.

---

## Equipment and Corrections

| Component | Role |
|---|---|
| **Emlid Reach RX** | Multi-band GNSS receiver, pole-mounted, connects to a phone or tablet over Bluetooth |
| **MaCORS** | The Commonwealth's Continuously Operating Reference Station network, providing the correction stream |
| **NTRIP** | The protocol carrying corrections from the network to the receiver over the device's cellular connection |
| **ArcGIS Field Maps** | The collection client, configured to use the RX as an external receiver |

The Reach RX was chosen over a traditional base-and-rover setup specifically because there is no base station to set up, level, or log. A network RTK solution means a crew member turns the receiver on, waits for a fixed solution, and starts working. That matters enormously when the user is a water foreman with a full day of actual work ahead of them rather than a surveyor whose whole job is the equipment.

**A note on datums:** MaCORS delivers positions in NAD83 (2011), with orthometric heights via the current geoid model. Older Massachusetts data - including a fair amount of what we inherited - was collected against earlier NAD83 realizations, which can differ from (2011) by a meaningful fraction of a meter. When the entire point of the exercise is centimeter accuracy, a systematic offset between new and legacy data is not a rounding error. Confirming which realization a given dataset was collected in is worth doing before assuming a discrepancy is a field mistake.

---

## Field Workflow

The workflow was designed to add as few steps as possible to what staff already do in Field Maps.

1. Power on the receiver and confirm a fixed RTK solution.
2. Open the relevant Field Maps map - the same maps staff already use for utility editing.
3. Select an existing feature and update its geometry, or add a new one.
4. Field Maps records the position from the external receiver rather than the device, along with the accuracy metadata for that fix.

Because the receiver is configured at the device level, the crew member's actual interaction with the map is unchanged. There's no separate survey app, no export step, no file to hand off. The edit lands in the hosted feature layer immediately, which means the improved geometry is available to everyone else the moment it's collected.

The most common single operation is repositioning rather than creating. Staff move existing hydrants, manholes, gate valves, and catch basins from their inherited digitized positions to their real ones. This is probably the highest-value thing the units do.

---

## Utility Data Improvement

The two departments use the receivers differently, which turned out to be a useful natural experiment.

**Water & Sewer** uses theirs opportunistically and continuously. Crews are already out at hydrants, valves, and services for other reasons; capturing an accurate position while they're standing there costs a minute. Over a season, that accumulates into a materially better dataset without a single dedicated field day being scheduled or funded.

**Stormwater** uses theirs more systematically, with our office staff working through drainage structures as part of ongoing MS4-driven inventory and inspection work. Because our stormwater compliance work already requires visiting basins on a schedule, accurate positioning rides along with an activity that has to happen anyway. Our Stormwater field staff uses Field Maps to track catch basin cleanings, but does not use the GPS.

Neither approach required a survey campaign, a consultant, or a line item beyond the hardware itself. The improvement is incremental and permanent - every structure that gets corrected stays corrected until it's moved again.

---

## Beyond Utilities

The receivers turned out to have a second life in projects that had nothing to do with underground infrastructure.

**Cemeteries (Summer 2025).** Our intern used the Reach RX to map headstones in town-managed cemeteries, recording each marker's position along with the individuals interred, dates, veteran status, marker type, condition, inscription notes, and headstone images. Headstone mapping is a use case where precision genuinely matters: markers sit close together, and a dataset that can't reliably distinguish adjacent stones isn't much use to someone trying to find a specific grave.

**Memorials and banners (Summer 2026).** A later intern used the second unit to map memorial signs and `Hometown Hero` banners around town - the latter being pole-mounted banners honoring local veterans, with up to two honorees per pole and attributes covering rank, branch, and conflict.

Both datasets became public-facing Experience Builder apps:

- [Cemetery Viewer](https://experience.arcgis.com/experience/eec4b0274672428896da302f0d01b9ef)
- [Memorial Viewer](https://experience.arcgis.com/experience/4e38840f42ff43d1b9b71f3ae465b8c7)

The popups in both apps are driven by Arcade expressions rather than default field lists, because the raw schemas carry a lot of structure a resident doesn't need to see - parallel name fields for multiple honorees, empty attributes on partially documented records, and system fields. The expressions assemble a readable block, skip anything blank, and keep a half-populated record from rendering as a wall of empty labels.

These projects also made a useful internal argument: equipment bought for utility work paid for itself again in public engagement, at no extra cost.

---

## What This Does and Doesn't Solve

**What it solves:** new and corrected features land at centimeter-level accuracy, collected by the people closest to the asset, using software they already know. Buried, snow-covered, or overgrown assets become findable. The datasets improve continuously rather than in expensive discrete campaigns.

**What it doesn't solve:** this is not a substitute for a licensed survey. RTK positions are excellent asset locations; they are not boundary determinations, and nothing collected this way carries a professional surveyor's stamp. The receivers also depend on both cellular coverage for the NTRIP stream and reasonable sky view for a fix - dense canopy, deep cuts, and downtown building faces still degrade the solution, and a float solution recorded as though it were fixed is worse than no data at all because it looks authoritative.

The hardware does not retroactively fix the existing dataset. Only features someone physically visits get corrected. The improvement is real but it's linear - this is an ongoing process and it takes a long time.

---

## Lessons Learned

**Ease of use.** The reason a second unit got purchased is that the first one didn't require a specialist. Network RTK with no base station to set up meant the barrier to a crew member using it was roughly "turn it on."

**Buy one, then buy the second.** Starting with a single unit and letting it prove itself made the second purchase an easy conversation instead of a speculative one. In a municipal budget context, a demonstrated use case is worth more than a good proposal.

**Correcting old data beats collecting new data.** The instinct is to go map something that isn't in GIS yet. The higher return was moving features that were already there to where they *actually* are.

**Know your realization, not just your datum.** "NAD83" isn't a single thing. When you're working at centimeter precision, the difference between realizations stops being academic.

**Watch the fix status, not just the app.** Field Maps will happily record a float or autonomous position. Accuracy metadata is only useful if someone is actually looking at it, and that's a training point rather than a settings point.

**Precision hardware finds unplanned uses.** Nothing in the purchase justification mentioned headstones or veterans' banners. Two of the most visible public products of this program came out of summer intern work with equipment bought for buried pipes.

---

## Media


---

[← All Projects](README.md)