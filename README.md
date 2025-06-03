# Wall_Detection

Below is a suggested way to structure and organize your Python‐based “wall‐type detection” project. You can adapt or expand each section as your needs evolve, but this outline should help you see the end‐to‐end workflow, required components, and how they fit together.

---

## 1. Project Overview & Goals

1. **Objective**

   * Read a CAD file (e.g., `.jff` or equivalent) containing a building/structure graph.
   * Detect all wall‐elements (polylines, line segments or closed loops) in that CAD.
   * Classify each wall by “type” (e.g., load‐bearing, partition, shear wall, etc.) based on labeling conventions (from the CAD layer/name/text or from an explanatory PDF).
   * Extract precise 2D (or 3D) coordinates for each wall (so they can be ingested downstream).
   * Produce a rendered visualization (e.g., a matplotlib or DXF preview) where each detected wall is colored by its computed type and annotated with its label.
   * Output a structured data file (e.g., JSON or CSV) listing, for every wall:

     * Unique ID
     * Wall type
     * Coordinates (start/end points or polygon vertices)
     * Any additional metadata (thickness, layer, textual note)

2. **Key Inputs & Outputs**

   * **Inputs**

     1. **CAD file** (e.g., `.jff` or convert to a DXF‐compatible format if needed)
     2. **Explanatory PDF** (describes how wall types are labeled, thickness conventions, symbol legend)
   * **Outputs**

     1. **Visualization image/PDF** with walls colored by type and labeled
     2. **Data export** (JSON/CSV) with coordinates + wall‐type metadata
     3. (Optionally) A small report summary or log file indicating how many of each wall type were found, any unclassified elements, etc.

---

## 2. High‐Level Workflow

1. **Project Initialization**

   * Create a new Git repository (or your preferred version control system).
   * Establish the directory structure (see Section 5).
   * Define a `requirements.txt` or Conda environment file listing needed Python packages.

2. **CAD File Ingestion & Preprocessing**

   * **CAD → Python**:

     * If your `.jff` is not directly supported by any Python library, convert it to DXF (or DWG) first.

       * Tools: AutoCAD export, LibreCAD, or a command‐line converter that can output DXF.
     * In Python, use a library such as **ezdxf** (for DXF) or **pyautocad** (if you have AutoCAD installed).
   * **Extract Geometry Primitives**:

     * Read all relevant entities—lines, polylines, arcs—that correspond to “walls.”
     * Group contiguous line segments that form thick‐line polylines or closed outlines.
   * **Parse Text & Layer Information**:

     * For each wall‐polyline or line‐segment group, check if there are **TEXT** or **MTEXT** entities nearby on the same layer, or if the polyline itself is on a layer named after a wall type (e.g., “WALL\_LB” for load‐bearing).
     * Build a preliminary mapping from each geometric object → label string (if present).

3. **Explanatory PDF Parsing & Label Interpretation**

   * Use a lightweight PDF parser (e.g., **pdfminer.six** or **PyPDF2**) to extract raw text.
   * Manually inspect the PDF once; identify exactly how wall types are encoded:

     * Are there codes like “B‐01,” “P‐02,” etc., explained in a legend?
     * Are wall thicknesses tied to types (e.g., any polyline thicker than 200 mm = shear wall)?
   * Hard‐code (or store in a small JSON) a dictionary mapping:

     ```json
     {
       "B‐01": "Load‐Bearing Wall",
       "P‐02": "Partition Wall",
       "SW‐01": "Shear Wall",
       ... 
     }
     ```
   * If the PDF contains multiple pages of notes or tables, focus on the legend table and copy that section into a plain JSON/YAML so your code can look up type‐names by label.

4. **Wall Detection & Geometry Extraction**

   * **Identify all wall‐like entities**

     1. Filter by layer name conventions, e.g., any entity on layer `WALL_*`
     2. Alternatively, find closed polylines whose thickness (line weight) exceeds a threshold
     3. If the CAD draws walls as pairs of offset lines, cluster lines that lie less than a small gap apart (e.g., 5 mm) to reconstruct a “wall corridor.”
   * **Group primitives into contiguous wall segments**

     * Use a spatial clustering approach (e.g., **Shapely**, or a custom union of line segments) to merge colinear/adjacent line segments into continuous polygons or multi‐line objects.
     * For each group, compute its polygonal outline and thickness (distance between parallel lines).
   * **Assign Unique IDs** (e.g., `WALL_0001`, `WALL_0002`, …).

5. **Wall Type Classification**

   * **Direct Text Labeling**

     * If you found a nearby TEXT entity whose string matches one of the keys from your PDF‐derived legend, assign that `type_label` directly.
   * **Rule‐Based Inference** (fallback)

     * If no text is present, infer from geometry:

       * **Thickness‐based**:

         * `thickness ≥ 200 mm` → “Load‐Bearing”
         * `thickness 100 – 200 mm` → “Shear Wall”
         * `thickness ≤ 100 mm` → “Partition”
       * **Layer‐based**:

         * If the polyline is on layer `WALL_P` → “Partition.”
         * If on `WALL_LB` → “Load‐Bearing.”
       * **Spatial context** (optional; advanced)

         * If a wall crosses a core or intersects grid lines in certain patterns, classify as “Shear.”
   * **Generate a final classification report** showing:

     * How many walls assigned by direct label vs. by rule.
     * Any “unknown” or “ambiguous” walls for which neither text nor rule applied—they go into a “Needs Review” bucket.

6. **Extracting Exact Coordinates**

   * For each wall group (now assigned a type and an ID), extract the coordinates of its boundary polygon or its centerline.

     * E.g., store a JSON array of points:

       ```json
       {
         "id": "WALL_0001",
         "type": "Load‐Bearing",
         "coordinates": [[x1, y1], [x2, y2], …],
         "thickness": 0.2
       }
       ```
   * If the walls are represented as polylines with multiple vertices, you can preserve the vertex list in order. If represented by two offset lines, you may want to compute the centerline polyline (mid‐points between corresponding vertices).

7. **Visualization & Rendering**

   * **Rendering Engine Choice**:

     * Option A: Use **matplotlib** + **Shapely** to draw every wall polygon, color‐coded by `type`. Label each polygon with its ID or type text.
     * Option B: Write back to a new DXF file with colored layers (using **ezdxf**) so that CAD software can display color.
   * **Color Scheme** (example):

     * Load‐Bearing → Red
     * Shear → Blue
     * Partition → Green
     * Unknown → Gray
   * **Annotate** each wall polygon with its type name (e.g., using `plt.text` at the polygon centroid).
   * **Save** the figure as a high‐resolution PNG or PDF (e.g., `wall_detection_result.png`).

8. **Data Export & Downstream Integration**

   * **Structured JSON or CSV**

     * Write one file (e.g., `walls_output.json`) that contains a list of objects, each with `_id_, _type_, _coords_, _metadata_`.
     * If consumers downstream (e.g., a simulation tool) require a CSV, produce a CSV where each row is:

       ```
       id, type, xmin, ymin, xmax, ymax, thickness, vertex1_x, vertex1_y, vertex2_x, vertex2_y, … 
       ```

       or break polygons into separate rows.
   * **Logging & Errors**

     * Generate a `log.txt` that lists:

       1. Number of total wall candidates found
       2. Number of successfully classified walls
       3. List of “unknown” walls (by ID) for manual review
       4. Any parsing errors (e.g., “Couldn’t read entity #345 from CAD”)

9. **Testing & Validation**

   * **Unit Tests** (pytest or unittest) for:

     1. CAD‐loading: does it properly extract known lines from a small test‐DXF?
     2. PDF parsing: does the dictionary extraction match expected labels on a sample PDF snippet?
     3. Geometry grouping: given a toy set of line segments, does the script merge them into one polygon?
     4. Classification rules: feed sample thickness values and confirm correct type is returned.
   * **Visual Inspection**

     * Compare a handful of detected walls in the rendered figure against the original CAD in your CAD viewer to ensure correctness.
   * **Edge Cases**

     * Walls drawn with arcs/curves (curved shear walls)
     * Overlapping polylines (e.g., a partition drawn on top of a load‐bearing wall)
     * Text labels placed far from the actual wall (offset annotations)

10. **Documentation & Packaging**

    * **README.md** explaining:

      * How to install dependencies (`pip install -r requirements.txt`)
      * How to run the main script (e.g., `python main.py --cad_file path/to/file.dxf --pdf_legend legend.pdf --out_dir results/`)
      * Explanation of configuration parameters (e.g., thickness thresholds, layer‐name conventions).
    * **Example Data Folder**

      * `data/sample.dxf` (or `sample.jff` if you’re including your original)
      * `data/legend.pdf` (the explanatory PDF)
      * `data/expected_output.json` (small ground‐truth for testing)
    * **Code Docstrings & Inline Comments**

      * Make sure each module/class/function has a short docstring describing inputs, outputs, and behavior.

---

## 3. Suggested Python Module Structure

Below is one possible breakdown of modules and their responsibilities. Create a top‐level folder (e.g., `wall_detector/`) with these submodules:

```
wall_detector/
├── data_loader.py
├── pdf_parser.py
├── geometry_utils.py
├── wall_classifier.py
├── visualizer.py
├── exporter.py
├── main.py
├── tests/
│   ├── test_data_loader.py
│   ├── test_pdf_parser.py
│   └── test_wall_classifier.py
└── requirements.txt
```

1. **data\_loader.py**

   * Functions for reading the CAD file (DXF or converted).
   * Returns raw entity lists (lines, polylines, arcs, text entities).

2. **pdf\_parser.py**

   * Parses the explanatory PDF to extract the “legend table” of wall‐type codes → descriptive names → any thickness rules.
   * Outputs a Python dictionary:

     ```python
     {
       "B-01": {"name": "Load-Bearing", "thickness_min": 200},
       "P-02": {"name": "Partition", "thickness_max": 100},
       …
     }
     ```

3. **geometry\_utils.py**

   * Helpers to:

     * Merge colinear/adjacent line segments (using shapely’s `linemerge` + `polygonize`).
     * Compute polygon centroids, thickness (distance between parallel lines), bounding boxes.
     * Snap nearly‐colinear segments (tolerance threshold).

4. **wall\_classifier.py**

   * Takes a list of “wall candidates” (each candidate = geometry + any raw text label + layer name).
   * Applies:

     1. **Direct Label Rule**: If text label matches a key from the PDF dictionary, classify immediately.
     2. **Layer Name Rule**: If layer name matches a known regex (e.g., `^WALL_LB.*`), assign accordingly.
     3. **Thickness Rule**: If no label, look at polygon thickness and refer to PDF rules (`thickness_min`/`max`).
   * Returns a list of `Wall` objects with fields: `id, geometry, assigned_type, assigned_rule, metadata`.

5. **visualizer.py**

   * Functions to take a list of classified `Wall` objects and produce a colored plot:

     * Map each `assigned_type` to an RGB or NamedColor.
     * Draw polygons/lines with `matplotlib.patches.Polygon` or `LineCollection`.
     * Annotate text at centroids (e.g., `ax.text(xc, yc, wall.type, fontsize=8)`).
     * Save figure to disk.

6. **exporter.py**

   * Write out:

     * `walls_output.json` (dump list of walls as JSON).
     * `walls_output.csv` (flattened CSV format).
     * `log.txt` summarizing classification counts and any issues.

7. **main.py**

   * Parse command‐line arguments (e.g., using `argparse`):

     * `--cad-file <path>`
     * `--legend-pdf <path>`
     * `--output-dir <path>`
   * High‐level flow:

     1. Call `data_loader.load_cad(...)` → raw entities.
     2. Call `pdf_parser.parse_legend(...)` → legend\_dict.
     3. Call `geometry_utils.extract_wall_candidates(...)` → list of raw geometries.
     4. Call `wall_classifier.classify_walls(wall_candidates, legend_dict)` → list of `Wall` objects.
     5. Call `visualizer.render(...)` → colored PNG/PDF.
     6. Call `exporter.export(...)` → JSON/CSV + log.
   * At each major step, print status (`“Loaded 1200 entities from CAD.”`, `“Parsed 5 wall types from PDF.”`, `“Detected 87 wall objects.”`, etc.).

---

## 4. Dependencies & Environment

1. **Python Version**: 3.8+ (ideally 3.9 or 3.10)
2. **Key Libraries**

   * **ezdxf** (or similar) for reading/writing DXF files (CAD geometry)
   * **shapely** for geometry operations (merging, polygonizing, measuring thickness)
   * **matplotlib** for visualization
   * **pdfminer.six** or **PyPDF2** for PDF parsing (extracting text legend)
   * **numpy** (optional, for numeric helpers)
   * **pandas** (optional, if you prefer writing CSV via DataFrame)
   * **pytest** (for unit tests)
   * **argparse** (part of stdlib) for CLI
3. **Directory Layout**

   ```
   /project-root
   ├── data/
   │   ├── sample_converted.dxf
   │   └── legend.pdf
   ├── wall_detector/            ← code modules (from Section 3)
   │   ├── __init__.py
   │   ├── data_loader.py
   │   ├── pdf_parser.py
   │   ├── geometry_utils.py
   │   ├── wall_classifier.py
   │   ├── visualizer.py
   │   ├── exporter.py
   │   ├── main.py
   │   └── tests/
   ├── outputs/                  ← automatically generated (plots, JSON, CSV, logs)
   ├── requirements.txt
   └── README.md
   ```
4. **requirements.txt** (example)

   ```
   ezdxf>=0.17
   shapely>=1.8
   matplotlib>=3.5
   pdfminer.six>=20211012
   numpy>=1.22
   pandas>=1.4
   pytest>=7.0
   ```
5. **Version Control Best Practices**

   * Add `data/` to `.gitignore` if sample data is large or proprietary.
   * Track code under `wall_detector/` and `requirements.txt` and `README.md`.
   * Use meaningful commit messages when you implement each major module or feature.

---

## 5. Detailed Step‐By‐Step Breakdown

Below is a more granular to‐do list. As you implement, tick off these items or adapt them:

1. **Setup & Boilerplate**

   * [ ] Create the Git repository.
   * [ ] Scaffold `wall_detector/` folder and `tests/` subfolder.
   * [ ] Write `README.md` with a short “Project Aim” and setup instructions.

2. **CAD Conversion (if needed)**

   * [ ] If your original file is `.jff` and no Python library reads it directly, convert to DXF.

     * Document how to do this (e.g., “Open in \[AutoCAD/LibreCAD], Export → DXF (R2018)”).
   * [ ] Save a sample “converted.dxf” into `data/` so code can assume DXF as primary.

3. **Implement `data_loader.py`**

   * [ ] Write a function `load_cad(filepath: str) → (entity_list)` that:

     1. Opens the DXF with `ezdxf.readfile(filepath)`
     2. Iterates over modelspace entities
     3. Collects lines, polylines, arcs, text entities into separate lists
   * [ ] Write unit tests: given a small DXF (with 3 lines + 1 text), ensure you extract exactly 4 entities.

4. **Implement `pdf_parser.py`**

   * [ ] Write `parse_legend(filepath: str) → dict` that:

     1. Opens the PDF
     2. Finds the “Legend” section (maybe search for a keyword like “Wall Type Code” or a header)
     3. Extracts each row of “code → type name → thickness rule” into a Python dict
   * [ ] If you can’t reliably auto‐detect the table, you may manual‐copy the legend into a small JSON and have `parse_legend` just do `json.load(...)`.
   * [ ] Unit test: on a tiny sample PDF (2 pages, containing a small “code, description” table), verify the dictionary matches expected.

5. **Implement `geometry_utils.py`**

   * [ ] Write helper `merge_lines_to_polygons(line_list: List[LineEntity], tol: float) → List[Polygon]`

     * Use Shapely: convert each line to `LineString`, apply `unary_union` + `polygonize` to get polygons.
   * [ ] Write `compute_thickness(polygon: Polygon) → float`

     * For “double‐line” walls, you may compute `polygon.area / polygon.length` as an approximation of wall width.
   * [ ] Write `snap_and_clean(geom: BaseGeometry, tol: float) → BaseGeometry`

     * Snap nearby vertices together to avoid tiny slivers (e.g., if two endpoints are within 1 mm).
   * [ ] Unit tests:

     * Given two overlapping line segments, confirm `merge_lines_to_polygons` yields exactly one small rectangle.

6. **Implement `wall_classifier.py`**

   * [ ] Define a `@dataclass Wall` with fields:

     ```python
     @dataclass
     class Wall:
         id: str
         geometry: shapely.geometry.Polygon
         raw_label: Optional[str]
         layer_name: str
         type_name: Optional[str] = None
         assigned_rule: Optional[str] = None
         thickness: Optional[float] = None
     ```
   * [ ] Write `classify_walls(candidates: List[Wall], legend_dict: dict) → List[Wall]` which:

     1. For each `Wall`:

        * Try direct label: if `wall.raw_label in legend_dict`, set `wall.type_name = legend_dict[raw_label]["name"]`, `assigned_rule = "label"`.
        * Else if `wall.layer_name` matches a known prefix (e.g. `WALL_P*`, `WALL_LB*`), set accordingly.
        * Else compute `thickness = compute_thickness(wall.geometry)`, compare to legend rules (`thickness_min`/`max`), assign if it falls in a unique bin.
        * Else leave `type_name = "Unknown"` and `assigned_rule = "unclassified"`.
   * [ ] At end, return the list sorted by `id` or by `type_name` so that it’s easy to inspect.
   * [ ] Unit tests:

     * Create three dummy `Wall` instances: one with `raw_label="B-01"`, one on layer `"WALL_P"`, one with thickness = 50 mm but no label/layer. Verify correct classification.

7. **Implement `visualizer.py`**

   * [ ] Write `render(walls: List[Wall], out_filepath: str)` that:

     1. Creates a blank `fig, ax = plt.subplots()` with equal aspect.
     2. Defines a color map, e.g.:

        ```python
        color_map = {
            "Load-Bearing": "red",
            "Partition": "green",
            "Shear": "blue",
            "Unknown": "gray"
        }
        ```
     3. Loops through `walls`, plotting `ax.add_patch( PolygonPatch( wall.geometry, facecolor=color_map[wall.type_name], edgecolor="black", linewidth=0.5 ) )`.
     4. Computes centroids `xc, yc = wall.geometry.centroid.x, wall.geometry.centroid.y` and does `ax.text(xc, yc, wall.type_name, fontsize=6)`.
     5. Calls `ax.set_aspect("equal")` and `plt.axis("off")`, then `plt.savefig(out_filepath, dpi=300)`.
   * [ ] Unit test (visual inspection): feed in two rectangular polygons of known size/types and confirm a PNG gets produced with two colored blocks.

8. **Implement `exporter.py`**

   * [ ] `export_json(walls: List[Wall], filepath: str)` → writes a JSON array; each element looks like:

     ```json
     {
       "id": "WALL_0001",
       "type": "Load-Bearing",
       "coords": [[x1, y1], [x2, y2], ...],
       "thickness": 0.2,
       "assigned_rule": "thickness"
     }
     ```
   * [ ] `export_csv(walls: List[Wall], filepath: str)` → constructs a pandas DataFrame with columns:

     ```
     id, type, thickness, assigned_rule, vertex_1_x, vertex_1_y, vertex_2_x, vertex_2_y, … 
     ```

     (You can decide how many vertices to include or store them as a single text column like `"[(x1,y1),(x2,y2),…]"`.)
   * [ ] `export_log(walls: List[Wall], filepath: str)` → writes a plain‐text log with summary lines:

     ```
     TOTAL WALLS: 87
     Load-Bearing: 25
     Partition: 40
     Shear: 19
     Unknown: 3

     LIST OF UNKNOWN WALL IDs:
     - WALL_0057
     - WALL_0072
     - WALL_0089
     ```
   * [ ] Unit test: pass in a small list (two walls) and confirm JSON and CSV files have the correct content.

9. **Implement `main.py`**

   * [ ] Use `argparse` to collect:

     * `--cad-file /path/to/file.dxf`
     * `--legend-pdf /path/to/legend.pdf`
     * `--out-dir /path/to/output/`
   * [ ] In `if __name__ == "__main__":` do:

     1. `entities = data_loader.load_cad(args.cad_file)`
     2. `legend = pdf_parser.parse_legend(args.legend_pdf)`
     3. `wall_candidates = geometry_utils.extract_wall_candidates(entities, tol=0.01)`
     4. `classified = wall_classifier.classify_walls(wall_candidates, legend)`
     5. `visualizer.render(classified, out_filepath=os.path.join(args.out_dir, "walls_rendered.png"))`
     6. `exporter.export_json(classified, os.path.join(args.out_dir, "walls_output.json"))`
     7. `exporter.export_csv(classified, os.path.join(args.out_dir, "walls_output.csv"))`
     8. `exporter.export_log(classified, os.path.join(args.out_dir, "log.txt"))`
   * [ ] Add print statements (or use the `logging` module at INFO level) for each major step.

10. **Testing & Validation**

    * [ ] Write Pytest tests under `wall_detector/tests/`.
    * [ ] Create one or two minimal DXF files (e.g., consisting of a rectangle plus text label) for unit tests.
    * [ ] Create a toy “legend.pdf” that’s just a one‐page with a small 2×2 table; test that `parse_legend` extracts it correctly.
    * [ ] Run `pytest` to confirm everything passes before each commit.

11. **Final Touches & Documentation**

    * [ ] Flesh out `README.md` with:

      * Project description
      * Prerequisites (Python version, libraries)
      * How to install (`pip install -r requirements.txt`)
      * Example command‐line invocation and expected output directory structure
      * Explanation of any configuration (e.g., thickness thresholds)
    * [ ] If desired, add a small Jupyter notebook (`demo.ipynb`) showing step‐by‐step usage on the sample data.
    * [ ] (Optional) Dockerize the project by writing a simple `Dockerfile` if you need portability.
    * [ ] Tag your first release in Git once everything is working end‐to‐end.

---

## 6. Tips & Additional Considerations

1. **Handling “JFF” Files**

   * If the `.jff` extension truly corresponds to a CAD format (some “Jw\_cad” variant), search for a command‐line converter to DXF.
   * If you cannot convert locally, consider installing **LibreCAD** (Windows: grab the installer) and export manually. Document that step in your README so collaborators know how to replicate.

2. **Scale & Units**

   * Confirm the CAD’s units (millimeters vs. meters vs. inches). Many DWG/DXF files embed unit information; if not, clarify with whoever provided the drawing.
   * If you assume millimeters but the file is in meters, your thickness rules will be off by a factor of 1000. Always check early.

3. **2D vs. 3D**

   * If your CAD is strictly 2D (plan view), everything above applies. If it’s a 3D model (with walls as 3D solids), you’ll need to project down to the XY plane first.
   * For 3D solids, you can use **ezdxf** to extract the XY footprint by slicing at a fixed Z value (e.g., Z = 0) and looking at cross‐section edges. That is a more advanced step; postpone until the 2D version works.

4. **Robustness to CAD Variations**

   * Real‐world CAD drawings can be messy:

     * Duplicate lines (two identical polylines on top of each other)
     * Tiny gaps that break a closed loop
     * Text labels with typos (e.g., “P‐O2” instead of “P‐02”)
   * Implement small heuristics:

     * Snap lines within 1 mm of each other before merging.
     * Use fuzzy string matching (e.g., Levenshtein distance) for labels if needed.
     * Flag anything that doesn’t match exactly so you can review.

5. **Scalability**

   * If your building plans are huge (thousands of wall segments), consider:

     * Spatial indexing with **rtree** (available via Shapely) so you can quickly find text entities near a given polyline.
     * Breaking the floor plan into grid‐cells (e.g., 10 m×10 m) and processing each cell separately, then merging.
   * Profile performance (e.g., time spent in `merge_lines_to_polygons`).

6. **Versioning of Classification Rules**

   * As wall‐type conventions may evolve, keep your “legend\_dict” external (e.g., a `wall_legend.json` in the repo root). Then `pdf_parser.parse_legend` can optionally update that JSON from the PDF. That way, if a new project has a slightly different legend, you don’t need to recode; just point to the new `legend.json`.

7. **Future Extensions**

   * Integrate this pipeline into a GUI (e.g., PyQt) so a user can click on an unknown wall and manually assign a type.
   * Build a small web service (Flask/FastAPI) that allows you to upload a DXF + PDF, runs the script server‐side, and returns the JSON + PNG.

---

## 7. Folder & File Structure Example

Below is a concrete snapshot of what your folder structure might look like once you’ve implemented everything:

```
.
├── README.md
├── requirements.txt
├── data/
│   ├── sample_converted.dxf      # a small test DXF
│   ├── legend.pdf                # explanatory PDF
│   └── wall_legend.json          # (optional) pre‐converted legend dict
├── wall_detector/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── pdf_parser.py
│   ├── geometry_utils.py
│   ├── wall_classifier.py
│   ├── visualizer.py
│   ├── exporter.py
│   ├── main.py
│   └── tests/
│       ├── test_data_loader.py
│       ├── test_pdf_parser.py
│       ├── test_geometry_utils.py
│       └── test_wall_classifier.py
├── outputs/
│   ├── walls_rendered.png
│   ├── walls_output.json
│   ├── walls_output.csv
│   └── log.txt
└── demo.ipynb                    # (optional) Jupyter notebook walkthrough
```

---

## 8. Summary

By following this outline, you will end up with a well‐modularized Python project that can:

1. **Ingest** a CAD drawing.
2. **Interpret** wall‐type rules from a PDF legend.
3. **Detect** and group wall geometries.
4. **Classify** each wall (label‐based, layer‐based, thickness‐based fallback).
5. **Extract** precise coordinates.
6. **Visualize** the result in a colored, annotated drawing.
7. **Export** data for downstream processing.

Each module has a clearly defined responsibility, which makes testing, maintenance, and future enhancements straightforward. Feel free to adapt naming conventions (e.g., you might call it `floorplan_parser.py` instead of `data_loader.py`), but try to keep a one‐file–one‐responsibility pattern. Good luck with your implementation—once you get this pipeline in place, you’ll be able to plug in new CADs and new legends with minimal tweaks.
