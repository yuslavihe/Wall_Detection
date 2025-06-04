# Wall Detection System

The Wall Detection System is a Python-based project designed to automatically detect and classify different types of walls from architectural CAD files. It achieves this by analyzing geometric properties, layer information, and associated text labels within the CAD file, then cross-referencing this data with a legend extracted from accompanying PDF documentation.

**Key Features:**
*   Automated extraction of wall geometries (lines, polylines) from DXF files.
*   Parsing of PDF documents to extract wall type legends and classification rules.
*   Classification of walls into types (e.g., load-bearing, partition) based on text labels, layer names, or geometric properties like thickness.
*   Generation of a visual output (image) with walls color-coded by their classified type.
*   Export of detected wall data into structured formats (JSON, CSV) for further analysis or use in other systems.
*   Logging of the detection and classification process, including statistics and any unclassified elements.

## Table of Contents

*   [Project Architecture](#project-architecture)
*   [Prerequisites](#prerequisites)
*   [Installation](#installation)
*   [Usage](#usage)
*   [Configuration](#configuration)
*   [Project Structure](#project-structure)
*   [Module Descriptions](#module-descriptions)
*   [Output Files](#output-files)
*   [Classification Logic](#classification-logic)
*   [Testing](#testing)
*   [Troubleshooting](#troubleshooting)
*   [Contributing](#contributing)
*   [Limitations and Future Improvements](#limitations-and-future-improvements)
*   [License](#license)
*   [Contact/Support](#contactsupport)

## Project Architecture

The Wall Detection System is built with a modular design to separate concerns and enhance maintainability. Each module handles a specific part of the wall detection and classification workflow.

**Key Components:**
*   **Data Loader (`data_loader.py`):** Responsible for reading and parsing the input CAD (DXF) file to extract geometric entities and text information.
*   **PDF Parser (`pdf_parser.py`):** Extracts legend information (wall types, codes, associated rules like thickness) from the provided PDF document.
*   **Geometry Utilities (`geometry_utils.py`):** Provides functions for geometric operations such as merging line segments into polygons, calculating wall thickness, and cleaning geometry.
*   **Wall Classifier (`wall_classifier.py`):** Implements the logic to classify wall candidates based on data from the CAD file and the parsed PDF legend.
*   **Visualizer (`visualizer.py`):** Generates a visual representation of the classified walls, typically an image with color-coding for different wall types.
*   **Exporter (`exporter.py`):** Handles the output of classified wall data into various formats like JSON and CSV, and generates a summary log file.
*   **Main Script (`main.py`):** Orchestrates the entire process, managing the flow of data between modules and handling command-line arguments.

## Prerequisites

*   **Python:** Version 3.8 or higher.
*   **Operating System:** Generally cross-platform (Windows, macOS, Linux).
*   **System Dependencies:** None beyond the Python libraries listed in `requirements.txt`. External tools like LibreCAD or AutoCAD might be needed if your source CAD files are not in DXF format and require conversion.

## Installation

1.  **Clone the repository:**
    ```
    git clone https://github.com/your-username/Wall_Detection.git
    cd Wall_Detection
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    The project dependencies are listed in `requirements.txt`. Install them using pip:
    ```
    pip install -r requirements.txt
    ```

## Usage

To run the Wall Detection System, use the `main.py` script from the `wall_detector` directory.

**Basic Usage Example:**
```
python wall_detector/main.py --cad_file path/to/your/file.dxf --pdf_legend path/to/your/legend.pdf --out_dir path/to/your/results/
```
This command will process the specified DXF file, use the legend from the PDF, and save the output files to the `results/` directory.

**Command-Line Arguments:**
*   `--cad-file`: (Required) Path to the input CAD file in DXF format.
*   `--pdf-legend` or `--legend-pdf`: (Required) Path to the PDF file containing the wall type legend and classification rules.
*   `--output-dir` or `--out-dir`: (Required) Directory where the output files (visualization, data exports, log) will be saved.

**Expected Input Formats:**
*   **CAD File:** A 2D architectural drawing saved in DXF format. The file should contain wall elements represented as lines, polylines, or similar geometric primitives. Associated text labels and layer information are used for classification.
*   **Legend PDF:** A PDF document that clearly defines wall types, their corresponding codes or labels used in the CAD drawing, and any geometric rules (e.g., thickness ranges) for classification.

## Configuration

Several parameters can be configured to tailor the detection and classification process to specific project needs or drawing conventions. These include:
*   **Thickness thresholds:** Values defining thickness ranges for different wall types (e.g., `thickness >= 200mm` for Load-Bearing).
*   **Tolerance values:** Small numerical values used in geometry operations, like snapping nearly collinear segments or merging points.
*   **Layer naming conventions:** Patterns or specific names for layers that indicate wall types (e.g., "WALL_LB" for load-bearing walls).
*   **Color mapping for visualization:** Defines which colors are used to represent different wall types in the output image.

These parameters are typically set within the source code (e.g., in `wall_classifier.py`, `visualizer.py`, or a dedicated configuration module/file). Future versions may support an external configuration file (e.g., `config.json`).

## Project Structure

The project is organized as follows:
```
Wall_Detection/
├── README.md
├── requirements.txt
├── wall_detector/
│   ├── __init__.py
│   ├── main.py
│   ├── data_loader.py
│   ├── pdf_parser.py
│   ├── geometry_utils.py
│   ├── wall_classifier.py
│   ├── visualizer.py
│   ├── exporter.py
│   └── tests/
│       ├── __init__.py
│       ├── test_data_loader.py
│       ├── test_pdf_parser.py
│       ├── test_geometry_utils.py
│       └── test_wall_classifier.py
├── data/
│   ├── sample_converted.dxf
│   ├── legend.pdf
│   └── wall_legend.json
└── results/
    ├── walls_rendered.png
    ├── walls_output.json
    ├── walls_output.csv
    └── log.txt
```

## Module Descriptions

*   **`data_loader.py`:** Handles reading and parsing CAD files (JWW/DXF format). It extracts 
    relevant geometric entities (lines, polylines, arcs) and text entities that may represent walls or their labels.
*   **`pdf_parser.py`:** Responsible for parsing the provided PDF document to extract the legend table. This legend typically maps wall type codes or symbols to descriptive names and associated properties like standard thicknesses.
*   **`geometry_utils.py`:** Contains utility functions for processing geometric data. This includes merging adjacent line segments to form wall polygons, calculating wall thicknesses, finding centroids, and cleaning up geometric inaccuracies.
*   **`wall_classifier.py`:** Implements the core logic for classifying identified wall candidates. It uses information from the `data_loader` (geometry, text, layers) and `pdf_parser` (legend rules) to assign a type to each wall.
*   **`visualizer.py`:** Generates a visual output, typically a PNG image, where detected and classified walls are drawn and color-coded according to their type. Labels or IDs may also be added to the visualization.
*   **`exporter.py`:** Manages the creation of output files containing the results. This includes structured data formats like JSON and CSV for easy use in other software, and a text-based log file summarizing the process.
*   **`main.py`:** The main script that orchestrates the entire wall detection and classification workflow. It handles command-line arguments, initializes modules, and calls their respective functions in the correct sequence.

## Output Files

The system generates the following output files in the specified output directory:
*   **`walls_rendered.png`:** A visual representation of the processed CAD drawing, with detected walls color-coded by their classified type and potentially annotated with labels or IDs.
*   **`walls_output.json`:** A structured JSON file containing detailed information for each classified wall. This typically includes a unique ID, the classified wall type, its geometric coordinates (vertices of the polygon), calculated thickness, and the rule used for classification.
*   **`walls_output.csv`:** A tabular representation of the wall data in CSV format, suitable for import into spreadsheets or databases for analysis. Each row represents a wall and includes its properties.
*   **`log.txt`:** A text file summarizing the processing run. It includes statistics like the total number of wall candidates found, the number of successfully classified walls, a breakdown by wall type, and a list of any walls that could not be classified (marked as 'Unknown').

## Classification Logic

The wall classification process follows a hierarchical approach to determine the type of each potential wall entity:
1.  **Direct Text Label Matching:** If a text entity is found near a wall candidate and its content matches a code or label defined in the PDF-extracted legend, that wall type is assigned directly.
2.  **Layer-Based Classification:** If no direct text label is matched, the system checks if the wall entity resides on a layer whose name corresponds to a predefined wall type convention (e.g., layer "A-WALL-LOAD" for load-bearing walls).
3.  **Thickness-Based Rules:** If neither text nor layer information yields a classification, the system attempts to classify the wall based on its calculated geometric thickness. This thickness is compared against ranges defined in the PDF legend for different wall types.
4.  **Default to 'Unknown':** If none of the above rules can confidently classify a wall, it is assigned to an 'Unknown' category for manual review.

## Testing

The project includes a suite of tests to ensure the reliability and correctness of its components.
*   **How to run tests:** Tests are written using `pytest` and can be executed from the project's root directory:
    ```
    pytest wall_detector/tests/
    ```
*   **Test coverage overview:** Unit tests cover key functionalities such as:
    *   Loading and parsing sample DXF files (`test_data_loader.py`).
    *   Extracting legend information from sample PDF snippets (`test_pdf_parser.py`).
    *   Geometric operations like merging lines and calculating thickness (`test_geometry_utils.py`).
    *   Applying classification rules to dummy wall objects (`test_wall_classifier.py`).
    Visual inspection of the output `walls_rendered.png` for a few sample inputs is also recommended to verify overall correctness.
*   **Adding new tests:** To add new tests, create new test functions in the relevant `test_*.py` file within the `wall_detector/tests/` directory. For new features, create corresponding minimal DXF and PDF sample files in a test data directory and write tests that use these samples to verify the expected behavior.

## Troubleshooting

Common issues and potential solutions:
*   **DXF File Compatibility:**
    *   *Issue:* The system may struggle with very old or unusually structured DXF files, or files containing complex entities not yet supported.
    *   *Solution:* Try re-saving the DXF file from a CAD program in a common version (e.g., AutoCAD 2013-2018 DXF). Ensure the drawing is 2D and primarily uses basic entities like LINE and LWPOLYLINE for walls.
*   **PDF Parsing Limitations:**
    *   *Issue:* Scanned (image-based) PDFs or PDFs with very complex table layouts for the legend might not be parsed correctly.
    *   *Solution:* If possible, use a PDF with selectable text for the legend. For complex layouts, manual extraction of the legend into a structured format (e.g., the `wall_legend.json` file) might be necessary as an interim step. The `pdf_parser.py` could be adapted to read this JSON directly.
*   **Memory Issues with Large CAD Files:**
    *   *Issue:* Processing very large and complex CAD files can lead to high memory consumption.
    *   *Solution:* Ensure your system has sufficient RAM. Future optimizations might include processing the CAD file in chunks or more memory-efficient data structures.
*   **Geometry Processing Edge Cases:**
    *   *Issue:* Curved walls, overlapping polylines, or very small gaps between line segments can sometimes lead to incorrect wall detection or classification. Text labels placed very far from their corresponding walls might also be missed.
    *   *Solution:* Adjust tolerance parameters in `geometry_utils.py` if appropriate. Report specific failing cases as issues for further refinement of the geometry processing logic.

## Contributing

We welcome contributions to the Wall Detection System! To contribute:
1.  Fork the repository on GitHub.
2.  Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name` or `bugfix/your-bug-fix-name`.
3.  Make your changes, adhering to the project's code style.
4.  Write unit tests for any new functionality or to cover bug fixes.
5.  Ensure all tests pass by running `pytest wall_detector/tests/`.
6.  Commit your changes with clear and descriptive messages.
7.  Push your branch to your fork: `git push origin feature/your-feature-name`.
8.  Submit a pull request to the main repository.

**Code Style and Standards:**
*   Follow PEP 8 guidelines for Python code.
*   Include clear docstrings for all modules, classes, and functions, explaining their purpose, arguments, and return values.
*   Add inline comments for complex or non-obvious sections of code.

## License

This project is licensed under the []. Please see the `LICENSE` file in the root directory for full details. (If no license file exists, state: License information is TBD.)
