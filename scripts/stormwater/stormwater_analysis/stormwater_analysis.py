"""
stormwater_analysis.py  --  Town of Braintree Stormwater Analysis Tools

VOLUME METHODOLOGY
==================
All three depth fields are measured downward from the rim:

    basin_depth      rim -> concrete floor of the basin
    invert_depth     rim -> bottom of the outlet pipe
    sediment_depth   rim -> top of the accumulated sediment

Sediment occupies the space between sediment_depth and basin_depth:

    thickness = basin_depth - sediment_depth
    volume    = pi * (48/2)^2 * thickness

At 48 inch diameter, one inch of sediment is 1,809.56 cubic inches,
or 0.0388 cubic yards.

DATA LINEAGE
============
Records from 2019 through November 2024 were migrated from a previous
GIS system whose inlet inventory carried only structural depths (rim to
invert, sump depth, and total finished depth in feet). It held no
sediment measurement. During the restructure the total finished depth
was written to both basin_depth on the parent and sediment_depth on the
service record, so those two fields match exactly on roughly 87% of
historical records and the derived thickness is structurally zero.

Those records are excluded from volume by name and reported in the
exclusion list. Independent field measurement begins December 2024,
where the migration copy rate falls from 92.9% to 4.2%.

WHAT IS AND IS NOT A MEASUREMENT
================================
  Cleaning and basin counts   valid for every year. They depend only on
                              record existence and inspection date.
  Volume, Dec 2024 onward     a real measurement.
  Volume before Dec 2024      estimated by applying the measured
                              per-basin average to the cleaning counts.
                              Disclose the method when reporting.

Source depths were recorded in whole feet on 82% of basins, so
basin_depth carries roughly +/- 6 inches of quantization. That averages
out across the sample but makes any single basin's volume imprecise.
"""

import os
import sys

# Try to fix DLL loading issues by adding library paths
try:
    python_path = os.path.dirname(sys.executable)
    os.environ['PATH'] = os.path.join(python_path, 'Library', 'bin') + os.pathsep + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        for path in [
            os.path.join(python_path, 'Library', 'bin'),
            os.path.join(python_path),
            os.path.join(python_path, 'DLLs')
        ]:
            if os.path.exists(path):
                os.add_dll_directory(path)
except Exception as e:
    print(f"Warning: Could not set up DLL paths: {e}")

try:
    import arcgis
    print("Successfully imported arcgis")
except ImportError as e:
    print(f"ERROR: {e}")
    print("This usually means your ArcGIS Pro installation needs repair.")
    print("Please ensure you're signed in to ArcGIS Pro and try again.")
    input("Press Enter to exit...")
    sys.exit(1)

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime as dt, timezone
from statistics import mean, median, stdev
from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from arcgis.gis import GIS
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


# ======================================================================
# UI CONSTANTS
# ======================================================================
MAIN_BG_COLOR = "#7eaed6"
ENTRY_BG_COLOR = "#DCDAD5"
BUTTON_BG_COLOR = "#2a87a1"
HOVER_COLOR = "#21b8ab"
TEXT_COLOR = "#FFFFFF"
INPUT_TEXT_COLOR = "#000000"

LAUNCHER_WINDOW_WIDTH_PERCENT = 40
LAUNCHER_WINDOW_HEIGHT_PERCENT = 30
ANALYSIS_WINDOW_WIDTH_PERCENT = 58
ANALYSIS_WINDOW_HEIGHT_PERCENT = 82
MIN_WIDTH_PERCENT = 30
MIN_HEIGHT_PERCENT = 30


# ======================================================================
# ANALYSIS CONSTANTS
# ======================================================================
BASIN_DIAMETER_IN = 48.0
COPY_TOLERANCE_IN = 0.01
MAX_PLAUSIBLE_DEPTH_IN = 240.0

# MS4 permit effective 7/1/2018 -> PY1 = 7/1/2018-6/30/2019.
PERMIT_YEAR_EPOCH = 2017
# Town fiscal year named for the ending year (7/1/2025-6/30/2026 = FY2026)
FISCAL_YEAR_OFFSET = 1

DATA_CUTOVER = dt(2024, 12, 1, tzinfo=timezone.utc)

COPY_RATE_UNRELIABLE = 0.50
COPY_RATE_MIXED = 0.05

UNIT_FACTORS = {
    "cubic_feet": 1.0 / 1728.0,
    "cubic_yards": 1.0 / 46656.0,
}

# When frozen by PyInstaller, __file__ points inside the temporary extraction
# directory, which is wiped on exit. Config must sit beside the executable so it
# stays editable and survives restarts.
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPT_DIR = APP_DIR
ITEM_IDS_FILE = os.path.join(APP_DIR, "item_ids.json")


def load_item_ids():
    if os.path.exists(ITEM_IDS_FILE):
        with open(ITEM_IDS_FILE, 'r') as f:
            return json.load(f)
    default_ids = {"catchbasins": "YOUR_ITEM_ID_HERE"}
    os.makedirs(os.path.dirname(ITEM_IDS_FILE) or ".", exist_ok=True)
    with open(ITEM_IDS_FILE, 'w') as f:
        json.dump(default_ids, f)
    return default_ids


ITEM_IDS = load_item_ids()


def verify_arcgis_connection():
    print("Attempting to connect to ArcGIS...")
    try:
        gis = GIS("home")
        _ = gis.properties
        print("Connection successful!")
        return gis
    except Exception as e:
        print(f"Connection failed: {e}")
        raise Exception("ArcGIS Authentication Error: Please sign in to ArcGIS Pro and try again.")


def get_resource_path(relative_path):
    """Resolve a bundled resource, e.g. "img/icon.ico" or "txt/about.txt".

    Searches, in order: the PyInstaller extraction dir, the folder holding this
    script or executable, that folder's "src" subdir, and its parent. This works
    unchanged whether running from source or from a frozen build.
    """
    roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(meipass)
    here = os.path.dirname(os.path.abspath(__file__))
    roots += [here, os.path.join(here, "src"), os.path.dirname(here)]
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        roots += [exe_dir, os.path.join(exe_dir, "src")]

    for root in roots:
        candidate = os.path.join(root, relative_path)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(roots[0], relative_path)


SCREEN_WIDTH = None
SCREEN_HEIGHT = None


def get_screen_dimensions():
    global SCREEN_WIDTH, SCREEN_HEIGHT
    if SCREEN_WIDTH is not None and SCREEN_HEIGHT is not None:
        return SCREEN_WIDTH, SCREEN_HEIGHT
    temp_root = tk.Tk()
    temp_root.withdraw()
    temp_root.attributes('-alpha', 0.0)
    temp_root.update_idletasks()
    SCREEN_WIDTH = temp_root.winfo_screenwidth()
    SCREEN_HEIGHT = temp_root.winfo_screenheight()
    temp_root.destroy()
    return SCREEN_WIDTH, SCREEN_HEIGHT


def calculate_window_geometry(width_percent, height_percent):
    sw, sh = get_screen_dimensions()
    w = int(sw * width_percent / 100)
    h = int(sh * height_percent / 100)
    return f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}"


def set_app_icon(window):
    icon_path = get_resource_path(os.path.join("img", "icon.ico"))
    if os.path.exists(icon_path):
        try:
            window.iconbitmap(icon_path)
        except Exception:
            pass


# ======================================================================
# HELPERS
# ======================================================================
def epoch_to_utc(ms) -> Optional[dt]:
    """AGOL stores dates as epoch milliseconds UTC. Naive conversion moves a
    7/1 date into the previous reporting year in US Eastern."""
    if ms in (None, ""):
        return None
    try:
        return dt.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except (ValueError, OSError, TypeError):
        return None


def norm_guid(g) -> Optional[str]:
    return g.strip("{}").upper() if isinstance(g, str) else None


def reporting_year(d: dt) -> int:
    return d.year if d.month >= 7 else d.year - 1


def fy_label(y: int) -> str:
    return f"FY{y + FISCAL_YEAR_OFFSET}"


def py_label(y: int) -> str:
    return f"PY{y - PERMIT_YEAR_EPOCH}"


def period_label(y: int) -> str:
    return f"07/{y}-06/{y + 1}"


def sql_in(field_name: str, values: Sequence[str]) -> str:
    esc = ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)
    return f"{field_name} IN ({esc})"


# ======================================================================
# DOMAIN OBJECTS
# ======================================================================
@dataclass
class Inlet:
    object_id: int
    global_id: str
    inlet_type: Optional[str]
    ownership: Optional[str]
    basin_depth: Optional[float]
    invert_depth: Optional[float]

    @property
    def sump_depth(self) -> Optional[float]:
        if self.basin_depth is None or self.invert_depth is None:
            return None
        return self.basin_depth - self.invert_depth


@dataclass
class ServiceRecord:
    object_id: int
    parent_gid: Optional[str]
    insp_date: Optional[dt]
    sediment_depth: Optional[float]
    clean_method: Optional[str]
    condition: Optional[str]
    activity_type: Optional[str]


@dataclass
class YearBucket:
    start_year: int
    cleanings: int = 0
    basins: Set[int] = field(default_factory=set)
    volume: float = 0.0
    measured_n: int = 0
    thicknesses: List[float] = field(default_factory=list)
    pct_full: List[float] = field(default_factory=list)
    records_paired: int = 0
    records_copied: int = 0

    @property
    def copy_rate(self) -> Optional[float]:
        if not self.records_paired:
            return None
        return self.records_copied / self.records_paired

    @property
    def quality(self) -> str:
        cr = self.copy_rate
        if cr is None:
            return "NO DATA"
        if cr >= COPY_RATE_UNRELIABLE:
            return "UNRELIABLE"
        if cr >= COPY_RATE_MIXED:
            return "MIXED"
        return "GOOD"

    @property
    def is_measurable(self) -> bool:
        return self.quality == "GOOD" and self.measured_n > 0

    @property
    def mean_measured_volume(self) -> Optional[float]:
        if not self.measured_n:
            return None
        return self.volume / self.measured_n

    @property
    def median_thickness(self) -> Optional[float]:
        return median(self.thicknesses) if self.thicknesses else None

    @property
    def median_pct_full(self) -> Optional[float]:
        return median(self.pct_full) if self.pct_full else None


# ======================================================================
# CLEANING ANALYZER
# ======================================================================
class CleaningAnalyzer:

    def __init__(self, item_id: str = None, basin_diameter_in: float = BASIN_DIAMETER_IN):
        self.item_id = item_id or ITEM_IDS["catchbasins"]
        self.diameter = basin_diameter_in
        self.area_in2 = math.pi * (basin_diameter_in / 2.0) ** 2
        self.gis = None
        self.inlets: Dict[str, Inlet] = {}
        self.records: List[ServiceRecord] = []
        self.scope_note = ""

    def load(self, town_only: bool = True, catchbasins_only: bool = True) -> str:
        self.gis = verify_arcgis_connection()
        item = self.gis.content.get(self.item_id)
        if item is None:
            raise Exception(f"Item with ID '{self.item_id}' not found.")
        if not item.layers:
            raise Exception(f"Item '{self.item_id}' has no layers.")
        if not item.tables:
            raise Exception(f"Item '{self.item_id}' has no related table.")

        clauses = []
        if town_only:
            clauses.append("ownership = 'Town'")
        if catchbasins_only:
            clauses.append(sql_in("inlettype", ["Catchbasin"]))
        where = " AND ".join(clauses) if clauses else "1=1"
        self.scope_note = where

        inlet_fs = item.layers[0].query(
            where=where,
            out_fields="OBJECTID,GlobalID,inlettype,ownership,basin_depth,invert_depth",
            return_all_records=True,
        )
        self.inlets = {}
        for f in inlet_fs.features:
            a = f.attributes
            gid = norm_guid(a.get("GlobalID"))
            if not gid:
                continue
            self.inlets[gid] = Inlet(
                object_id=a.get("OBJECTID"),
                global_id=gid,
                inlet_type=a.get("inlettype"),
                ownership=a.get("ownership"),
                basin_depth=a.get("basin_depth"),
                invert_depth=a.get("invert_depth"),
            )

        table = item.tables[0]
        fields = {fl.name.lower() for fl in table.properties.fields}
        rec_fields = ["OBJECTID", "ParentGlobalID", "inspectiondate",
                      "sediment_depth", "clean_meth", "condition"]
        if "activity_type" in fields:
            rec_fields.append("activity_type")

        rec_fs = table.query(where="1=1", out_fields=",".join(rec_fields),
                             return_all_records=True)
        self.records = []
        for f in rec_fs.features:
            a = f.attributes
            self.records.append(ServiceRecord(
                object_id=a.get("OBJECTID"),
                parent_gid=norm_guid(a.get("ParentGlobalID")),
                insp_date=epoch_to_utc(a.get("inspectiondate")),
                sediment_depth=a.get("sediment_depth"),
                clean_method=(a.get("clean_meth") or None),
                condition=(a.get("condition") or None),
                activity_type=(a.get("activity_type") or None),
            ))

        return (f"Connected. {len(self.inlets)} inlets in scope, "
                f"{len(self.records)} service records.")

    @staticmethod
    def is_cleaning(rec: ServiceRecord) -> bool:
        """Activity Type when populated, otherwise sediment depth > 0.

        The earlier field form made Cleaning Method a required entry, so
        inspection-only visits carry a method they did not earn. Counting on
        that field overstates cleanings, which is why it is not used here.
        """
        if rec.activity_type:
            return rec.activity_type.strip().lower() == "cleaning"
        return rec.sediment_depth is not None and rec.sediment_depth > 0

    def thickness(self, rec: ServiceRecord, inlet: Inlet
                  ) -> Tuple[Optional[float], Optional[str]]:
        sd = rec.sediment_depth
        if sd is None:
            return None, "no sediment depth recorded"
        if sd == 0:
            return None, "sediment depth 0 (inspection-only convention)"
        if sd > MAX_PLAUSIBLE_DEPTH_IN:
            return None, "sediment depth implausibly large"
        if inlet.basin_depth is None:
            return None, "parent has no basin depth"
        if abs(inlet.basin_depth - sd) < COPY_TOLERANCE_IN:
            return None, "basin_depth identical to sediment_depth (migration copy)"
        t = inlet.basin_depth - sd
        if t < 0:
            return None, "sediment below recorded floor (stale or rounded basin_depth)"
        return t, None

    def analyze(self, units: str = "cubic_yards"
                ) -> Tuple[Dict[int, YearBucket], Counter]:
        factor = UNIT_FACTORS[units]
        years: Dict[int, YearBucket] = {}
        rejects: Counter = Counter()

        for rec in self.records:
            if rec.parent_gid is None:
                rejects["no ParentGlobalID"] += 1
                continue
            inlet = self.inlets.get(rec.parent_gid)
            if inlet is None:
                rejects["parent outside the selected scope"] += 1
                continue
            if rec.insp_date is None:
                rejects["no inspection date"] += 1
                continue
            if not self.is_cleaning(rec):
                rejects["not a cleaning (inspection or repair)"] += 1
                continue

            key = reporting_year(rec.insp_date)
            yb = years.setdefault(key, YearBucket(start_year=key))
            yb.cleanings += 1
            yb.basins.add(inlet.object_id)

            if inlet.basin_depth is not None and rec.sediment_depth is not None:
                yb.records_paired += 1
                if abs(inlet.basin_depth - rec.sediment_depth) < COPY_TOLERANCE_IN:
                    yb.records_copied += 1

            t, reason = self.thickness(rec, inlet)
            if t is None:
                rejects[reason] += 1
                continue

            yb.measured_n += 1
            yb.thicknesses.append(t)
            yb.volume += self.area_in2 * t * factor
            sump = inlet.sump_depth
            if sump and sump > 0:
                yb.pct_full.append(100.0 * t / sump)

        return years, rejects

    def sample_stats(self, units: str = "cubic_yards") -> Optional[dict]:
        factor = UNIT_FACTORS[units]
        vals = []
        for rec in self.records:
            if rec.insp_date is None or rec.insp_date < DATA_CUTOVER:
                continue
            inlet = self.inlets.get(rec.parent_gid) if rec.parent_gid else None
            if inlet is None or not self.is_cleaning(rec):
                continue
            t, _ = self.thickness(rec, inlet)
            if t is not None and t > 0:
                vals.append(t)
        if len(vals) < 3:
            return None
        vols = [self.area_in2 * t * factor for t in vals]
        se = stdev(vols) / math.sqrt(len(vols))
        return {
            "n": len(vals),
            "mean_thickness": mean(vals),
            "median_thickness": median(vals),
            "mean_volume": mean(vols),
            "median_volume": median(vols),
            "ci_low": mean(vols) - 1.96 * se,
            "ci_high": mean(vols) + 1.96 * se,
        }

    @staticmethod
    def reportable(years: Dict[int, YearBucket], sample: Optional[dict]
                   ) -> Dict[int, Tuple[float, str]]:
        """One figure per year: {start_year: (volume, basis)}.

        Measurable years use their own per-basin average scaled to the full
        cleaning count, since not every cleaning carries a depth reading.
        All other years use the pooled measured sample.
        """
        out: Dict[int, Tuple[float, str]] = {}
        for key, y in years.items():
            if y.is_measurable:
                out[key] = (y.mean_measured_volume * y.cleanings, "measured")
            elif sample:
                out[key] = (sample["mean_volume"] * y.cleanings, "estimated")
            else:
                out[key] = (0.0, "no basis")
        return out


# ======================================================================
# SUMP DEPTH ANALYZER
# ======================================================================
class SumpDepthAnalyzer:
    def __init__(self, item_id: str = None):
        self.item_id = item_id or ITEM_IDS["catchbasins"]
        self.gis = None
        self.layer = None

    def connect(self):
        try:
            self.gis = verify_arcgis_connection()
            item = self.gis.content.get(self.item_id)
            if item is None:
                raise Exception(f"Item with ID '{self.item_id}' not found.")
            if not getattr(item, "layers", None):
                raise Exception(f"Item '{self.item_id}' has no layers.")
            self.layer = item.layers[0]
            return "Connected to ArcGIS Online successfully."
        except Exception as e:
            return str(e)

    def _where(self, town_only: bool, catchbasins_only: bool) -> str:
        clauses = []
        if town_only:
            clauses.append("ownership = 'Town'")
        if catchbasins_only:
            # Filter positively. The old "inlettype <> 'Sump Pump'" clause also
            # silently dropped rows with a null inlettype.
            clauses.append("inlettype = 'Catchbasin'")
        return " AND ".join(clauses) if clauses else "1=1"

    @staticmethod
    def check_depth_condition(sump_depth, criteria, threshold1, threshold2=None) -> bool:
        if criteria == ">=":
            return sump_depth >= threshold1
        if criteria == "<=":
            return sump_depth <= threshold1
        lower = min(threshold1, threshold2) if threshold2 is not None else threshold1
        upper = max(threshold1, threshold2) if threshold2 is not None else threshold1
        return lower <= sump_depth <= upper

    def analyze_sump_depths(self, criteria="<=", threshold1=36, threshold2=None,
                            town_only=True, catchbasins_only=True):
        if not self.gis or not self.layer:
            msg = self.connect()
            if not self.layer:
                raise Exception(msg)
        fs = self.layer.query(
            where=self._where(town_only, catchbasins_only),
            out_fields="OBJECTID,basin_depth,invert_depth,ownership,inlettype",
            return_all_records=True,
        )
        total = matching = outliers = nulls = 0
        matched: Dict[int, float] = {}
        for f in fs.features:
            a = f.attributes
            total += 1
            bd, ivd = a.get("basin_depth"), a.get("invert_depth")
            if bd is None and ivd is None:
                nulls += 1
                continue
            if bd is None or ivd is None:
                outliers += 1
                continue
            sump = bd - ivd
            if self.check_depth_condition(sump, criteria, threshold1, threshold2):
                matching += 1
                matched[a["OBJECTID"]] = sump
        return total, matching, outliers, nulls, matched

    def analyze_sump_depth_distribution(self, town_only=True, catchbasins_only=True):
        if not self.gis or not self.layer:
            msg = self.connect()
            if not self.layer:
                raise Exception(msg)
        fs = self.layer.query(
            where=self._where(town_only, catchbasins_only),
            out_fields="OBJECTID,basin_depth,invert_depth",
            return_all_records=True,
        )
        ranges = {"unknown": set(), "ge_48": set(), "36_to_48": set(),
                  "24_to_36": set(), "12_to_24": set(), "lt_12": set()}
        for f in fs.features:
            a = f.attributes
            oid = a["OBJECTID"]
            bd, ivd = a.get("basin_depth"), a.get("invert_depth")
            if bd is None or ivd is None:
                ranges["unknown"].add(oid)
                continue
            sump = bd - ivd
            if sump >= 48:
                ranges["ge_48"].add(oid)
            elif sump >= 36:
                ranges["36_to_48"].add(oid)
            elif sump >= 24:
                ranges["24_to_36"].add(oid)
            elif sump >= 12:
                ranges["12_to_24"].add(oid)
            else:
                ranges["lt_12"].add(oid)
        return ranges


# ======================================================================
# STYLING
# ======================================================================
def apply_styles(style: ttk.Style):
    style.theme_use('clam')
    style.configure("TLabel", background=MAIN_BG_COLOR, foreground=TEXT_COLOR,
                    padding=6, font=('Arial', 10))
    style.configure("TFrame", background=MAIN_BG_COLOR)
    style.configure("TNotebook", background=MAIN_BG_COLOR, tabmargins=0)
    style.configure("TNotebook.Tab", background=BUTTON_BG_COLOR,
                    foreground=TEXT_COLOR, padding=[8, 6], borderwidth=2)
    style.configure("Custom.TButton", background=BUTTON_BG_COLOR,
                    foreground=TEXT_COLOR, padding=3, font=('Helvetica', 10, 'bold'))
    style.map("Custom.TButton", background=[('active', HOVER_COLOR)],
              foreground=[('active', TEXT_COLOR)])
    style.configure("TEntry", fieldbackground=ENTRY_BG_COLOR, foreground=INPUT_TEXT_COLOR)
    style.configure("TCombobox", fieldbackground=ENTRY_BG_COLOR, foreground=INPUT_TEXT_COLOR)
    style.configure("Header.TLabelframe", background=MAIN_BG_COLOR,
                    bordercolor=TEXT_COLOR, borderwidth=2, relief="groove")
    style.configure("Header.TLabelframe.Label", foreground=TEXT_COLOR,
                    background=MAIN_BG_COLOR, font=('Helvetica', 11, 'bold'))
    style.configure("TRadiobutton", background=MAIN_BG_COLOR, foreground=TEXT_COLOR)
    style.map("TRadiobutton",
              background=[('active', MAIN_BG_COLOR), ('selected', MAIN_BG_COLOR)],
              foreground=[('active', TEXT_COLOR), ('selected', TEXT_COLOR)])
    style.configure("TCheckbutton", background=MAIN_BG_COLOR, foreground=TEXT_COLOR)
    style.map("TCheckbutton",
              background=[('active', MAIN_BG_COLOR), ('selected', MAIN_BG_COLOR)],
              foreground=[('active', TEXT_COLOR), ('selected', TEXT_COLOR)])


# ======================================================================
# LAUNCHER
# ======================================================================
class LauncherUI(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.withdraw()
        self.title("Stormwater Analysis Launcher")
        set_app_icon(self)
        self.configure(bg=MAIN_BG_COLOR)
        self.current_analysis_window = None
        self.style = ttk.Style()
        apply_styles(self.style)
        self.create_menu_bar()
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_menu_bar(self):
        menu_bar = tk.Menu(self, bg=MAIN_BG_COLOR, fg=TEXT_COLOR)
        self.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=0, bg=MAIN_BG_COLOR, fg=TEXT_COLOR)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_close)
        help_menu = tk.Menu(menu_bar, tearoff=0, bg=MAIN_BG_COLOR, fg=TEXT_COLOR)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Methodology", command=self.show_method)
        help_menu.add_command(label="About", command=self.show_about)

    def _text_window(self, title, body):
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=MAIN_BG_COLOR)
        win.geometry(calculate_window_geometry(58, 70))
        win.transient(self)
        frame = ttk.Frame(win, padding=15)
        frame.grid(row=0, column=0, sticky="nsew")
        win.grid_rowconfigure(0, weight=1)
        win.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        txt = ScrolledText(frame, wrap=tk.WORD, font=('Consolas', 10),
                           bg=ENTRY_BG_COLOR, fg=INPUT_TEXT_COLOR)
        txt.grid(row=0, column=0, sticky="nsew")
        txt.insert(tk.END, body)
        txt.config(state='disabled')
        ttk.Button(frame, text="Close", command=win.destroy,
                   style="Custom.TButton").grid(row=1, column=0, pady=10)

    def show_method(self):
        self._text_window("Methodology", METHODOLOGY_TEXT)

    def show_about(self):
        about_path = get_resource_path(os.path.join("txt", "about.txt"))
        if not os.path.exists(about_path):
            about_path = get_resource_path(os.path.join("txt", "about.txt"))
        try:
            with open(about_path, 'r') as f:
                body = f.read()
        except Exception:
            body = "Stormwater Analysis Tools\nTown of Braintree Engineering Department"
        self._text_window("About Stormwater Analysis", body)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        ttk.Label(main_frame, text="Stormwater Analysis Tools",
                  font=('Helvetica', 16, 'bold')).grid(row=0, column=0, pady=(0, 20),
                                                       sticky="n")
        bf = ttk.Frame(main_frame)
        bf.grid(row=2, column=0, pady=10)
        ttk.Button(bf, text="Catchbasin Cleaning Analysis", width=32,
                   command=lambda: self._launch(CleaningAnalysisUI),
                   style="Custom.TButton").grid(row=0, column=0, pady=5)
        ttk.Button(bf, text="Sump Depth Analysis", width=32,
                   command=lambda: self._launch(SumpDepthAnalysisUI),
                   style="Custom.TButton").grid(row=1, column=0, pady=5)
        ttk.Label(main_frame, text="Town of Braintree Engineering Department",
                  font=('Helvetica', 8)).grid(row=3, column=0, pady=(20, 0), sticky="s")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

    def _launch(self, cls):
        self.withdraw()
        ui = cls(self.root, self)
        self.current_analysis_window = ui.root
        ui.root.protocol("WM_DELETE_WINDOW", lambda: self.show_launcher(ui.root))
        ui.root.update_idletasks()
        ui.root.deiconify()
        ui.root.focus_set()

    def show_launcher(self, analysis_window):
        self.deiconify()
        self.update_idletasks()
        if analysis_window and analysis_window.winfo_exists():
            analysis_window.destroy()
        self.current_analysis_window = None
        self.focus_set()
        self.lift()

    def on_close(self):
        if self.current_analysis_window and self.current_analysis_window.winfo_exists():
            self.current_analysis_window.destroy()
        self.root.destroy()


# ======================================================================
# CLEANING ANALYSIS UI
# ======================================================================
class CleaningAnalysisUI:
    def __init__(self, root, launcher=None):
        self.root = tk.Toplevel(root)
        self.root.withdraw()
        self.launcher = launcher
        self.root.title("Catch Basin Cleaning Analysis")
        set_app_icon(self.root)
        self.root.geometry(calculate_window_geometry(
            ANALYSIS_WINDOW_WIDTH_PERCENT, ANALYSIS_WINDOW_HEIGHT_PERCENT))
        sw, sh = get_screen_dimensions()
        self.root.minsize(int(sw * MIN_WIDTH_PERCENT / 100),
                          int(sh * MIN_HEIGHT_PERCENT / 100))
        self.root.configure(bg=MAIN_BG_COLOR)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.style = ttk.Style()
        apply_styles(self.style)
        self.analyzer = None
        self.create_widgets()

    def create_widgets(self):
        c = ttk.Frame(self.root)
        c.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(2, weight=1)

        ttk.Label(c, text="Catch Basin Cleaning Analysis",
                  font=('Helvetica', 14, 'bold')).grid(row=0, column=0, pady=10)

        opts = ttk.LabelFrame(c, text="Options", padding=10, style="Header.TLabelframe")
        opts.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        opts.grid_columnconfigure(3, weight=1)

        ttk.Label(opts, text="Volume Units:").grid(row=0, column=0, sticky="w")
        self.volume_var = tk.StringVar(value="cubic_yards")
        rf = ttk.Frame(opts)
        rf.grid(row=0, column=1, sticky="w")
        for i, (label, val) in enumerate([("Cubic Yards", "cubic_yards"),
                                          ("Cubic Feet", "cubic_feet")]):
            ttk.Radiobutton(rf, text=label, value=val,
                            variable=self.volume_var).grid(row=0, column=i, padx=8)

        self.town_only_var = tk.BooleanVar(value=True)
        self.cb_only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Town-owned only",
                        variable=self.town_only_var).grid(row=0, column=2, sticky="w", padx=12)
        ttk.Checkbutton(opts, text="Catchbasins only",
                        variable=self.cb_only_var).grid(row=0, column=3, sticky="w")

        res = ttk.LabelFrame(c, text="Results", padding=10, style="Header.TLabelframe")
        res.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        res.grid_columnconfigure(0, weight=1)
        res.grid_rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(res)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        sf = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(sf, text="Report")
        sf.grid_columnconfigure(0, weight=1)
        sf.grid_rowconfigure(0, weight=1)
        self.results_text = ScrolledText(sf, wrap=tk.NONE, font=('Consolas', 9),
                                         height=20, bg=ENTRY_BG_COLOR, fg=INPUT_TEXT_COLOR)
        self.results_text.grid(row=0, column=0, sticky="nsew")
        xs = ttk.Scrollbar(sf, orient="horizontal", command=self.results_text.xview)
        xs.grid(row=1, column=0, sticky="ew")
        self.results_text.configure(xscrollcommand=xs.set)

        gf = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(gf, text="Graph")
        gf.grid_columnconfigure(0, weight=1)
        gf.grid_rowconfigure(0, weight=1)
        self.fig = Figure(figsize=(9, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=gf)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        tbf = ttk.Frame(gf)
        tbf.grid(row=1, column=0, sticky="ew")
        self.toolbar = NavigationToolbar2Tk(self.canvas, tbf)
        self.toolbar.grid(row=0, column=0, sticky="w")

        bfo = ttk.Frame(c)
        bfo.grid(row=3, column=0, pady=(10, 0), sticky="ew")
        bfo.grid_columnconfigure(0, weight=1)
        bfo.grid_columnconfigure(2, weight=1)
        bf = ttk.Frame(bfo)
        bf.grid(row=0, column=1)
        ttk.Button(bf, text="Run Analysis", command=self.run_analysis,
                   style="Custom.TButton").grid(row=0, column=0, padx=5)
        ttk.Button(bf, text="Copy Report", command=self.copy_report,
                   style="Custom.TButton").grid(row=0, column=1, padx=5)
        ttk.Button(bf, text="Clear", command=self.clear_results,
                   style="Custom.TButton").grid(row=0, column=2, padx=5)

        self.status_var = tk.StringVar()
        ttk.Label(c, textvariable=self.status_var,
                  font=('Helvetica', 9)).grid(row=4, column=0, pady=(0, 10))

    def clear_results(self):
        self.results_text.delete(1.0, tk.END)
        self.status_var.set("")
        self.fig.clear()
        self.canvas.draw()

    def copy_report(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.results_text.get(1.0, tk.END))
        self.status_var.set("Report copied to clipboard.")

    # ---- report ------------------------------------------------------
    def build_report(self, years, rejects, sample, units) -> str:
        u = units.replace("_", " ")
        area = math.pi * (BASIN_DIAMETER_IN / 2) ** 2
        per_inch = area * UNIT_FACTORS[units]
        rep = CleaningAnalyzer.reportable(years, sample)
        L = []

        L.append("=" * 86)
        L.append("CATCH BASIN CLEANING ANALYSIS")
        L.append(f"Town of Braintree Engineering Department        "
                 f"generated {dt.now().strftime('%m/%d/%Y')}")
        L.append("=" * 86)
        L.append(f"Scope       : {self.analyzer.scope_note}")
        L.append(f"Inlets      : {len(self.analyzer.inlets)}")
        L.append(f"Records     : {len(self.analyzer.records)}")
        L.append(f"Basin model : {BASIN_DIAMETER_IN:.0f} in circular, "
                 f"{per_inch:.4f} {u} per inch of sediment")
        L.append("")

        # ---- reportable figures -------------------------------------
        L.append("REPORTABLE FIGURES")
        h = (f"  {'PERIOD':<16}{'FY':>8}{'PY':>6}{'CLEANINGS':>11}"
             f"{'BASINS':>8}{'VOLUME':>12}  BASIS")
        L.append(h)
        L.append("  " + "-" * (len(h) - 2))
        tot_c = 0
        tot_v = 0.0
        allb: Set[int] = set()
        for k in sorted(years):
            y = years[k]
            vol, basis = rep[k]
            L.append(f"  {period_label(k):<16}{fy_label(k):>8}{py_label(k):>6}"
                     f"{y.cleanings:>11}{len(y.basins):>8}{vol:>12,.1f}  {basis}")
            tot_c += y.cleanings
            tot_v += vol
            allb |= y.basins
        L.append("  " + "-" * (len(h) - 2))
        L.append(f"  {'TOTAL':<16}{'':>8}{'':>6}{tot_c:>11}{len(allb):>8}{tot_v:>12,.1f}")
        L.append("")
        L.append(f"  Volumes in {u}. 'measured' uses that period's own per-basin average")
        L.append("  scaled to its full cleaning count. 'estimated' applies the pooled")
        L.append("  measured average to the cleaning count; disclose the method when")
        L.append("  reporting those periods.")

        # ---- supporting detail --------------------------------------
        L.append("")
        L.append("SUPPORTING DETAIL")
        h2 = (f"  {'PERIOD':<16}{'MEASURED':>10}{'MEAS VOL':>11}{'MED THK':>9}"
              f"{'MED %FULL':>11}{'COPY RATE':>11}  QUALITY")
        L.append(h2)
        L.append("  " + "-" * (len(h2) - 2))
        for k in sorted(years):
            y = years[k]
            thk = f'{y.median_thickness:.0f}"' if y.median_thickness is not None else "-"
            pf = f"{y.median_pct_full:.0f}%" if y.median_pct_full is not None else "-"
            cr = f"{100 * y.copy_rate:.1f}%" if y.copy_rate is not None else "-"
            L.append(f"  {period_label(k):<16}{y.measured_n:>10}{y.volume:>11,.1f}"
                     f"{thk:>9}{pf:>11}{cr:>11}  {y.quality}")
        L.append("")
        L.append("  MEASURED is the count of cleanings with an independent depth reading.")
        L.append("  MEAS VOL is the volume from those records only.")
        L.append("  COPY RATE is the share of records where basin_depth exactly equals")
        L.append("  sediment_depth, an artifact of the pre-2025 data migration that makes")
        L.append("  the derived thickness structurally zero. Independent field measurement")
        L.append(f"  begins {DATA_CUTOVER.strftime('%B %Y')}. Cleaning and basin counts")
        L.append("  remain valid for every period regardless of copy rate.")

        # ---- sample --------------------------------------------------
        if sample:
            L.append("")
            L.append("MEASUREMENT SAMPLE")
            L.append(f"  n = {sample['n']} cleanings with an independent depth reading")
            L.append(f"  sediment thickness   mean {sample['mean_thickness']:.1f} in   "
                     f"median {sample['median_thickness']:.1f} in")
            L.append(f"  volume per basin     mean {sample['mean_volume']:.3f} {u}   "
                     f"median {sample['median_volume']:.3f} {u}")
            L.append(f"  95% CI on the mean   {sample['ci_low']:.3f} to "
                     f"{sample['ci_high']:.3f} {u}")
            lo = sum(sample["ci_low"] * years[k].cleanings
                     for k in years if not years[k].is_measurable)
            hi = sum(sample["ci_high"] * years[k].cleanings
                     for k in years if not years[k].is_measurable)
            meas = sum(rep[k][0] for k in years if years[k].is_measurable)
            L.append(f"  total range implied by the CI: {meas + lo:,.0f} to "
                     f"{meas + hi:,.0f} {u}")
            L.append("")
            L.append("  Limitations to disclose: the sample is modest; if crews measure")
            L.append("  basins that visibly needed attention it is biased high; a 48 in")
            L.append("  circular basin is assumed throughout; and source depths were")
            L.append("  recorded in whole feet on most basins, giving basin_depth about")
            L.append("  +/- 6 in of quantization. Cross-check against vactor and clamshell")
            L.append("  load counts and disposal manifests where they exist. Catch basin")
            L.append("  grit runs roughly 2,400-2,700 lb per cubic yard wet.")

        if rejects:
            L.append("")
            L.append("RECORDS EXCLUDED FROM VOLUME, BY REASON")
            for reason, n in rejects.most_common():
                L.append(f"  {n:>6}  {reason}")

        L.append("")
        L.append("=" * 86)
        return "\n".join(L)

    def create_graph(self, years, sample, units):
        self.fig.clear()
        if not years:
            self.canvas.draw()
            return
        rep = CleaningAnalyzer.reportable(years, sample)
        keys = sorted(years)
        labels = [f"{fy_label(k)}\n{py_label(k)}" for k in keys]
        vols = [rep[k][0] for k in keys]
        counts = [years[k].cleanings for k in keys]
        measured = [years[k].is_measurable for k in keys]

        ax1 = self.fig.add_subplot(111)
        x = np.arange(len(keys))
        w = 0.38
        colors = ['#2a87a1' if m else '#9dc3d4' for m in measured]
        b1 = ax1.bar(x - w / 2, vols, w, color=colors, edgecolor='white')
        ax1.set_ylabel(f"Sediment removed ({units.replace('_', ' ')})")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=8)
        ax1.grid(True, linestyle='--', alpha=0.5, axis='y')

        ax2 = ax1.twinx()
        b2 = ax2.bar(x + w / 2, counts, w, color='#8fbf6f', edgecolor='white')
        ax2.set_ylabel("Catch basins cleaned")

        for bar in b1:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, h, f"{h:,.0f}",
                         ha='center', va='bottom', fontsize=7)
        for bar in b2:
            h = bar.get_height()
            if h > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2, h, f"{int(h)}",
                         ha='center', va='bottom', fontsize=7)

        from matplotlib.patches import Patch
        ax1.legend(handles=[
            Patch(facecolor='#2a87a1', label='Volume (measured)'),
            Patch(facecolor='#9dc3d4', label='Volume (estimated)'),
            Patch(facecolor='#8fbf6f', label='Cleanings'),
        ], loc='upper right', fontsize=8)
        ax1.set_title("Catch Basin Cleaning by Reporting Year", fontsize=11)
        self.fig.tight_layout()
        self.canvas.draw()

    def run_analysis(self):
        self.status_var.set("Loading from ArcGIS Online...")
        self.root.update()
        try:
            self.analyzer = CleaningAnalyzer()
            msg = self.analyzer.load(town_only=self.town_only_var.get(),
                                     catchbasins_only=self.cb_only_var.get())
            self.status_var.set(msg + "  Analyzing...")
            self.root.update()

            units = self.volume_var.get()
            years, rejects = self.analyzer.analyze(units=units)
            sample = self.analyzer.sample_stats(units=units)

            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END,
                                     self.build_report(years, rejects, sample, units))
            self.create_graph(years, sample, units)
            self.status_var.set("Analysis complete.")
        except Exception as e:
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"{e}")
            self.status_var.set("Analysis failed. See message above.")


# ======================================================================
# SUMP DEPTH ANALYSIS UI
# ======================================================================
class SumpDepthAnalysisUI:
    def __init__(self, root, launcher=None):
        self.root = tk.Toplevel(root)
        self.root.withdraw()
        self.launcher = launcher
        self.root.title("Sump Depth Analysis")
        set_app_icon(self.root)
        self.root.geometry(calculate_window_geometry(
            ANALYSIS_WINDOW_WIDTH_PERCENT, ANALYSIS_WINDOW_HEIGHT_PERCENT))
        sw, sh = get_screen_dimensions()
        self.root.minsize(int(sw * MIN_WIDTH_PERCENT / 100),
                          int(sh * MIN_HEIGHT_PERCENT / 100))
        self.root.configure(bg=MAIN_BG_COLOR)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.style = ttk.Style()
        apply_styles(self.style)
        self.analyzer = SumpDepthAnalyzer()
        self.create_widgets()

    def create_widgets(self):
        c = ttk.Frame(self.root)
        c.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(2, weight=1)

        ttk.Label(c, text="Stormwater Inlet Sump Depth Analysis",
                  font=('Helvetica', 14, 'bold')).grid(row=0, column=0, pady=10)

        self.town_only_var = tk.BooleanVar(value=True)
        self.cb_only_var = tk.BooleanVar(value=True)
        self.criteria_var = tk.StringVar(value="<=")
        self.threshold1_var = tk.DoubleVar(value=36.0)
        self.threshold2_var = tk.DoubleVar(value=48.0)

        mode = ttk.LabelFrame(c, text="Analysis Mode", padding=10,
                              style="Header.TLabelframe")
        mode.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        mode.grid_columnconfigure(0, weight=1)
        self.mode_notebook = ttk.Notebook(mode)
        self.mode_notebook.grid(row=0, column=0, sticky="nsew")

        crit = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(crit, text="Criteria-Based Analysis")
        dist = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(dist, text="Distribution Analysis")
        self.mode_notebook.select(crit)

        of = ttk.LabelFrame(crit, text="Analysis Options", padding=10,
                            style="Header.TLabelframe")
        of.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        of.grid_columnconfigure(2, weight=1)
        ttk.Checkbutton(of, text="Town-owned only",
                        variable=self.town_only_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(of, text="Catchbasins only",
                        variable=self.cb_only_var).grid(row=0, column=1, sticky="w")
        ttk.Label(of, text="Comparison Type:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Combobox(of, textvariable=self.criteria_var, state="readonly", width=10,
                     values=[">=", "<=", "between"]).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(of, text="Threshold 1 (inches):").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(of, textvariable=self.threshold1_var, width=10).grid(
            row=2, column=1, sticky="w", padx=5)
        ttk.Label(of, text="Threshold 2 (inches):").grid(row=3, column=0, sticky="w", pady=5)
        t2 = ttk.Entry(of, textvariable=self.threshold2_var, width=10)
        t2.grid(row=3, column=1, sticky="w", padx=5)

        def upd(*_):
            t2.config(state="normal" if self.criteria_var.get() == "between" else "disabled")
        self.criteria_var.trace_add("write", upd)
        upd()

        ofd = ttk.LabelFrame(dist, text="Analysis Options", padding=10,
                             style="Header.TLabelframe")
        ofd.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Checkbutton(ofd, text="Town-owned only",
                        variable=self.town_only_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(ofd, text="Catchbasins only",
                        variable=self.cb_only_var).grid(row=1, column=0, sticky="w")
        ttk.Label(ofd, text="Groups inlets into sump depth ranges.").grid(
            row=2, column=0, sticky="w", pady=5)

        res = ttk.LabelFrame(c, text="Results", padding=10, style="Header.TLabelframe")
        res.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        res.grid_columnconfigure(0, weight=1)
        res.grid_rowconfigure(0, weight=1)
        self.results_text = ScrolledText(res, wrap=tk.WORD, font=('Consolas', 10),
                                         height=15, bg=ENTRY_BG_COLOR, fg=INPUT_TEXT_COLOR)
        self.results_text.grid(row=0, column=0, sticky="nsew")

        bfo = ttk.Frame(c)
        bfo.grid(row=3, column=0, pady=(10, 0), sticky="ew")
        bfo.grid_columnconfigure(0, weight=1)
        bfo.grid_columnconfigure(2, weight=1)
        bf = ttk.Frame(bfo)
        bf.grid(row=0, column=1)
        ttk.Button(bf, text="Run Analysis", command=self.run_analysis,
                   style="Custom.TButton").grid(row=0, column=0, padx=5)
        ttk.Button(bf, text="Clear Results", command=self.clear_results,
                   style="Custom.TButton").grid(row=0, column=1, padx=5)

        self.status_var = tk.StringVar()
        ttk.Label(c, textvariable=self.status_var,
                  font=('Helvetica', 9)).grid(row=4, column=0, pady=(0, 10))

    def clear_results(self):
        self.results_text.delete(1.0, tk.END)
        self.status_var.set("")

    def run_analysis(self):
        self.status_var.set("Analysis in progress...")
        self.root.update()
        try:
            msg = self.analyzer.connect()
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, msg + "\n")
            town = self.town_only_var.get()
            cb = self.cb_only_var.get()
            scope = ("town-owned " if town else "") + ("catchbasins" if cb else "inlets")

            if self.mode_notebook.tab(self.mode_notebook.select(), "text") \
                    == "Criteria-Based Analysis":
                crit = self.criteria_var.get()
                t1 = self.threshold1_var.get()
                t2 = self.threshold2_var.get() if crit == "between" else None
                desc = {">=": f">= {t1}", "<=": f"<= {t1}",
                        "between": f"between {t1} and {t2}"}[crit]
                self.results_text.insert(
                    tk.END, f"Analyzing {scope} with sump depth {desc} inches...\n")
                total, matching, outliers, nulls, matched = self.analyzer.analyze_sump_depths(
                    criteria=crit, threshold1=t1, threshold2=t2,
                    town_only=town, catchbasins_only=cb)
                self.results_text.insert(tk.END, "\nResults:\n")
                self.results_text.insert(tk.END, f"Total {scope} analyzed: {total}\n")
                self.results_text.insert(tk.END, f"Sump depth {desc}: {matching}\n")
                self.results_text.insert(tk.END, f"One depth field null: {outliers}\n")
                self.results_text.insert(tk.END, f"Both depth fields null: {nulls}\n")
                if total:
                    self.results_text.insert(
                        tk.END, f"Percent matching: {100 * matching / total:.1f}%\n")
                if messagebox.askyesno("Details", "Show ObjectIDs of matching inlets?"):
                    self.results_text.insert(tk.END, "\nMatching inlets:\n")
                    for oid, sump in sorted(matched.items()):
                        self.results_text.insert(
                            tk.END, f"ObjectID: {oid}, Sump Depth: {sump} inches\n")
            else:
                self.results_text.insert(
                    tk.END, f"Analyzing {scope} sump depth distribution...\n")
                r = self.analyzer.analyze_sump_depth_distribution(
                    town_only=town, catchbasins_only=cb)
                total = sum(len(v) for v in r.values())
                self.results_text.insert(tk.END, f"\nTotal Features: {total}\n")
                self.results_text.insert(
                    tk.END,
                    f"Unique ObjectIDs: {len(set().union(*r.values())) if total else 0}\n")
                self.results_text.insert(tk.END, "\nBreakdown:\n")
                for key, label in [("unknown", "Unknown Sump Depth"),
                                   ("ge_48", '>= 48"'),
                                   ("36_to_48", '>= 36" and < 48"'),
                                   ("24_to_36", '>= 24" and < 36"'),
                                   ("12_to_24", '>= 12" and < 24"'),
                                   ("lt_12", '< 12"')]:
                    self.results_text.insert(tk.END, f"{label}: {len(r[key])}\n")
                if messagebox.askyesno("Details", "Show ObjectIDs for each range?"):
                    names = {"unknown": "Unknown Sump Depth", "ge_48": ">= 48 inches",
                             "36_to_48": "36-48 inches", "24_to_36": "24-36 inches",
                             "12_to_24": "12-24 inches", "lt_12": "< 12 inches"}
                    for key, ids in r.items():
                        if ids:
                            self.results_text.insert(tk.END, f"\n{names[key]} ObjectIDs:\n")
                            oids = sorted(ids)
                            for i in range(0, len(oids), 10):
                                self.results_text.insert(
                                    tk.END, ", ".join(map(str, oids[i:i + 10])) + "\n")
            self.status_var.set("Analysis completed successfully!")
        except Exception as e:
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"{e}")
            self.status_var.set("Analysis failed. See error message above.")


# ======================================================================
METHODOLOGY_TEXT = """CATCH BASIN SEDIMENT VOLUME -- METHODOLOGY


GEOMETRY

All three depth fields are measured downward from the rim:

    basin_depth      rim -> concrete floor of the basin
    invert_depth     rim -> bottom of the outlet pipe
    sediment_depth   rim -> top of the accumulated sediment

Sediment occupies the space between sediment_depth and basin_depth:

    thickness = basin_depth - sediment_depth
    volume    = pi * (48/2)^2 * thickness

At 48 inch diameter, one inch of sediment is 1,809.56 cubic inches, or
0.0388 cubic yards.


DATA LINEAGE

Service records from 2019 through November 2024 were migrated from a
previous GIS system. That system's inlet inventory recorded structural
depths only -- rim to invert, sump depth, and total finished depth, all
in feet. It held no sediment measurement.

During the restructure the total finished depth was written both to
basin_depth on the parent inlet and to sediment_depth on the service
record. Those two fields therefore match exactly on roughly 87% of
historical records, which makes the derived thickness structurally zero.
Records in that condition are excluded from volume by name and listed in
the exclusion report.

Independent field measurement begins in December 2024, where the
migration copy rate falls from 92.9% to 4.2%.


WHAT IS AND IS NOT A MEASUREMENT

  Cleaning and basin counts     Valid for every period. They depend only
                                on record existence and inspection date.

  Volume, Dec 2024 onward       A real measurement. Reported as that
                                period's own per-basin average scaled to
                                its full cleaning count, since not every
                                cleaning carries a depth reading.

  Volume before Dec 2024        Estimated by applying the pooled measured
                                per-basin average to the cleaning count.
                                Disclose the method when reporting.


CLEANING VERSUS INSPECTION

An earlier version of the field form made Cleaning Method a required
entry, so inspection-only visits carry a cleaning method they did not
earn. Counting cleanings on that field overstates them. The rule used
here is Activity Type where it is populated, and sediment depth greater
than zero otherwise, which is correct for both the current form and all
historical data.


KNOWN LIMITATIONS

  - A 48 inch circular basin is assumed for every structure.
  - Source depths were recorded in whole feet on about 82% of basins, so
    basin_depth carries roughly +/- 6 inches of quantization. This
    averages out across the sample but makes any single basin's volume
    imprecise, and it accounts for some records where a measured
    sediment depth falls slightly below the recorded floor.
  - If crews preferentially measure basins that visibly needed
    attention, the sample is biased high.
  - Vactor and clamshell load counts and disposal manifests are a
    stronger source for total volume where they exist. Catch basin grit
    runs roughly 2,400 to 2,700 lb per cubic yard wet.
"""


def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-alpha', 0.0)
    root.update_idletasks()
    launcher = LauncherUI(root)
    set_app_icon(launcher)
    launcher.update_idletasks()
    launcher.geometry(calculate_window_geometry(
        LAUNCHER_WINDOW_WIDTH_PERCENT, LAUNCHER_WINDOW_HEIGHT_PERCENT))
    launcher.deiconify()
    launcher.focus_set()
    launcher.lift()
    root.mainloop()


if __name__ == "__main__":
    main()