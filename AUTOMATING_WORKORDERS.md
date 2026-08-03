Aaron Portanova<br>
*August 2026*

# **Automating Workorders**

Like many municipalities, Braintree tracks workorders, permits, and billing across separate databases that don't talk to each other, and workorders themselves have historically moved on paper - multiple trips to the office to collect, process, and return information about work done by field staff. It's an awkward process with a single point of failure, since paper copies get lost or damaged along the way. In 2025 I began replacing that loop with an ArcGIS Online web map and Experience Builder app that field staff use to record the jobs they do each day.

The solution is built on a hosted feature layer with attachments enabled, so a worker can drop a point where the work was done and photograph the job or the paper workorder itself - the same way they already edit our GIS utility data in the field. A GitHub-based automation checks the layer for new records several times per day, pulls the details from them (work start/end, description, worker names, attachments) into an email, and sends it back to the office, where staff can read each job and click through to view its point on the map. That gives office staff a digital source to reference when entering work into the relevant database, removes the need to carry paper back and forth, and preserves the work on a map for future reference.

[← All Projects](README.md)
