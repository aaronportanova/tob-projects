Aaron Portanova<br>
*August 2026*

# **Creating a Map Grid and Street Name Index**

***A reusable grid feature class and alphabetized street index for standard town map layouts - built once, shared across every map that uses the same extent and needs a street list.***

[← All Projects](README.md)

---

## Contents

| Section | Description |
|---|---|
| [Overview](#overview) | What the layout needs and why the grid has to be data |
| [Enforcing a Shared Extent](#enforcing-a-shared-extent) | Making every map line up with the same grid |
| [Drawing the Rectangle](#drawing-the-rectangle) | Getting a clean starting polygon out of a layout |
| [Building the Street List](#building-the-street-list) | Dissolving, splitting, and de-duplicating road names |
| [The Sidebar Text Element](#the-sidebar-text-element) | Arcade driving the alphabetized index |
| [Reusing the List: Trash Day Map](#reusing-the-list-trash-day-map) | The same street list, grouped a different way |
| [Lessons Learned](#lessons-learned) | What I'd tell someone else doing this |
| [Media](#media) | Screenshots of the layout and grid |

---

## Overview

Many of the maps I produce share the same standard layout: a map area with the usual elements (title, legend, scale bar, north arrow, description) and a sidebar street list keyed to a grid on the map (A1, B1, A2, B2, and so on), broken up alphabetically so someone can find a street name and go straight to the right cell.

The part that makes this more than a cartography exercise is that the grid can't be a graphic. Each cell has to exist as a feature so that cell values can be spatially joined to the streets - which is the only way the sidebar list can know that Washington Street belongs in D4. Once the grid is a feature class, the index becomes a data problem rather than something anyone has to keep up to date by hand.

---

## Enforcing a Shared Extent

A grid feature class is only reusable if every map that displays it is showing the same area. I enforce this by adding the town boundary polygon to each map (toggled off if necessary) and using ArcGIS Pro's 'fit extent' - Alt + click the layer. Every layout built that way lands on the same extent, so the grid cells fall in the same place and the street index stays valid across maps.

---

## Drawing the Rectangle

I drew the initial rectangle from inside an activated map layout so it sized closely to the actual map window element, then used a Python script to divide it into a reasonable grid and enrich it with the correct cell values.

Getting that first rectangle right took some fiddling. I had to zoom the layout extent to 100% or more to get in close to the corners, activate the map, and create the polygon by clicking near each corner. That result wasn't a perfect square, so it needed refining: I created a second polygon using the rectangle draw option in the normal map view, clicked two adjacent corners on the square-ish polygon I'd made in the layout, then dragged to the other side to produce a genuine rectangle.

This could probably have been scripted to correct the geometry of the initial polygon, but doing it manually worked just as well and got it very close to a true rectangle fitting inside the 'fit extent' of the town boundary. While somewhat finicky, the approach works reliably, and it only has to be done once.

---

## Building the Street List

The street list needed its own cleanup, since our master MassDOT roads dataset often carries multiple features per road - different segments, non-continuous roads. Left alone, that produces an index where a single street appears half a dozen times in half a dozen cells.

The workflow:

1. **Dissolve** a copy of the roads layer on road name, creating a single feature per unique name.
2. **Split** that result by the grid, so each road is broken at cell boundaries.
3. **De-duplicate again**, keeping only the longest segment per name - so each road is labeled in the cell it overlaps most, rather than in every cell it touches.
4. **Spatially join** the result back to the grid, producing a list of unique street names each tied to a single grid cell value.

The "longest segment wins" rule is the decision that makes the index usable. A street crossing four cells is genuinely in all four, but an index that says so is worse than one that points at the cell where most of the street actually is.

The resulting feature class carries the fields the sidebar needs:

| Field | Purpose |
|---|---|
| `STREETNAME` | The road name, stored uppercase |
| `Label` | The grid cell the street was assigned to (e.g. `D4`) |
| `Header` | The letter heading, populated only on the first street of each alphabetical group |
| `Shape_Length` | Length of the retained segment |
| `TRASHDAY` | Collection day for that street - see below |

---

## The Sidebar Text Element

The list itself is drawn by a Text (distinctValues list) layout element, driven by an Arcade expression. `Header` is only populated on the first entry of each letter group, so the expression checks for it and prepends the letter heading when it's there - which is what produces the alphabetical breaks down the sidebar without any manual formatting.

```
if (!IsEmpty($feature.Header)) {
    return $feature.Header + "\n" + Proper($feature.STREETNAME) + " - " + $feature.Label + "\n"
} else {
    return Proper($feature.STREETNAME) + " - " + $feature.Label + "\n"
}
```

`Proper()` handles the casing at draw time, so the underlying data stays uppercase and consistent with the source roads dataset while the sidebar reads as normal text.

---

## Reusing the List: Trash Day Map

The curated street list turned out to be worth more than the one map it was built for. It also drives the Trash Day map on the town website, which answers a question residents ask constantly: what day does my street get picked up?

That map uses the same feature class and the same grid cell references, but organizes the sidebar differently. Instead of alphabetical letter sections, the list is broken into collection day sections - Monday, Tuesday, Wednesday, Thursday, Friday - with streets alphabetized within each day. A resident finds their day, finds their street, and gets the grid cell to locate it on the map.

The payoff of having done the dissolve-split-dedupe work once is that adding a second product meant adding a field and changing how the sidebar groups, not rebuilding the street list from the roads data again.

---

## Lessons Learned

**If a map element needs to know about the data, it has to be data.** A drawn grid looks identical to a grid feature class right up until you need to know which cell a street falls in. Building it as features cost more up front and made the entire index automatic.

**Decide what "which cell" means before building the index.** A street can legitimately occupy several cells. Picking the longest segment is a judgment call, not a technical necessity, and it's the call that determines whether the index is actually useful to someone holding the map.

**Manual is fine for a one-time setup step.** The rectangle geometry could have been corrected with a script. It's drawn once and reused by every map, so the script would have taken longer to write than the fix took to do.

**Cleaned reference data outlives the map it was made for.** The street list was built for one layout and now drives the public Trash Day map as well. The dissolve-split-dedupe work was the expensive part, and it only had to happen once.

---

## Media

<div align="center">
    <img src="media/something.jpg" width="100%"><br>
    Standard layout with grid and sidebar street index
</div><br>

---

[← All Projects](README.md)

<!-- link to trash day map on site, talk about how trash day map list is drawn vs regular street list, discuss initial grid creation process more -->