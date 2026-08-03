Aaron Portanova<br>
*August 2026*

# **Analyzing Utility Data**

EPA's MS4 permit requires municipalities to report volumes of material cleaned from drainage system catchbasins as part of annual reporting. Stormwater field staff record cleaning events in ArcGIS Field Maps, taking three measurements at each basin - clean basin depth (rim to floor, no material), depth to deepest sump (rim to the bottom rim of the deepest outflow pipe), and depth to material (rim to top of sediment) - which together allow us to estimate the volume of material cleaned per basin over time.

I developed a Python-based tool using the arcpy and arcgis modules to summarize those cleaning events on demand. It's a standalone Tkinter GUI program with buttons for 'catchbasin cleaning analysis' and 'sump depth analysis', reporting the number of catchbasins cleaned, estimated total sediment volume over a specified time interval, and other summaries of the stormwater infrastructure we maintain in ArcGIS Online. It runs on any machine with ArcGIS Pro installed and signed in to Braintree's ArcGIS organization, as long as the member has the required layers shared with them, and the Stormwater department uses it to pull reportable sediment volumes directly.