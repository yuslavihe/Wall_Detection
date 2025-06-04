"""
data_loader.py - Module for loading and processing CAD files (DWG/DXF)

This module handles reading CAD files, with special support for DWG files that need
conversion to DXF format. It also provides visualization capabilities for testing.
"""

import os
import sys
import subprocess
import tempfile
from typing import Dict, List, Tuple, Any, Optional
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
from pathlib import Path


class CADEntity:
    """Wrapper class for CAD entities with decoded text support"""

    def __init__(self, entity_type: str, entity: Any):
        self.type = entity_type
        self.entity = entity
        self.text_content = None

        # Extract text content if applicable
        if entity_type in ['TEXT', 'MTEXT']:
            try:
                self.text_content = entity.dxf.text
            except:
                self.text_content = ""


def ensure_output_directory(base_path: str) -> Path:
    """
    Ensure the output_test directory exists

    Args:
        base_path: Base directory path

    Returns:
        Path object for the output directory
    """
    output_dir = Path(base_path) / "output_test"
    output_dir.mkdir(exist_ok=True)
    return output_dir


def convert_dwg_to_dxf(dwg_filepath: str, output_filepath: Optional[str] = None) -> str:
    """
    Convert DWG file to DXF format using ODA File Converter or LibreDWG

    Args:
        dwg_filepath: Path to the input DWG file
        output_filepath: Optional path for the output DXF file

    Returns:
        Path to the converted DXF file

    Raises:
        RuntimeError: If conversion fails or converter is not available
    """
    if output_filepath is None:
        # Generate output path in output_test folder
        base_dir = os.path.dirname(dwg_filepath)
        output_dir = ensure_output_directory(base_dir)
        base_name = os.path.splitext(os.path.basename(dwg_filepath))[0]
        output_filepath = str(output_dir / f"{base_name}.dxf")

    # Try ODA File Converter first (Windows/Linux)
    oda_converter_paths = [r"C:\Program Files\ODA\ODAFileConverter 26.4.0\ODAFileConverter.exe"]
    for converter_path in oda_converter_paths:
        try:
            # ODA converter requires input/output directories and format specs
            input_dir = os.path.dirname(dwg_filepath)
            output_dir = os.path.dirname(output_filepath)
            input_file = os.path.basename(dwg_filepath)

            cmd = [
                converter_path,
                input_dir,
                output_dir,
                "ACAD2018",  # Output version
                "DXF",  # Output format
                "0",  # Recurse folders (0 = no)
                "1",  # Audit (1 = yes)
                input_file  # Specific file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # ODA converter might change the output name slightly
                expected_output = os.path.join(output_dir,
                                               os.path.splitext(input_file)[0] + ".dxf")
                if os.path.exists(expected_output):
                    if expected_output != output_filepath:
                        os.rename(expected_output, output_filepath)
                    return output_filepath
        except FileNotFoundError:
            continue

    # Try LibreDWG as fallback
    try:
        cmd = ["dwg2dxf", "-o", output_filepath, dwg_filepath]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return output_filepath
    except FileNotFoundError:
        pass

    # If we get here, no converter was found
    raise RuntimeError(
        "No DWG to DXF converter found. Please install either:\n"
        "1. ODA File Converter: https://www.opendesign.com/guestfiles/oda_file_converter\n"
        "2. LibreDWG: https://www.gnu.org/software/libredwg/"
    )


def load_cad(filepath: str, encoding: str = 'utf-8') -> Dict[str, List[CADEntity]]:
    """
    Load a CAD file (DWG or DXF) and extract relevant entities

    Args:
        filepath: Path to the CAD file
        encoding: Text encoding for the file (default: utf-8 for Japanese support)

    Returns:
        Dictionary with entity types as keys and lists of CADEntity objects as values
        Keys include: 'lines', 'polylines', 'arcs', 'circles', 'texts', 'blocks'

    Raises:
        FileNotFoundError: If the input file doesn't exist
        ValueError: If the file format is not supported
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CAD file not found: {filepath}")

    file_ext = os.path.splitext(filepath)[1].lower()

    # Handle DWG files by converting to DXF first
    if file_ext == '.dwg':
        print(f"Converting DWG to DXF format...")
        dxf_filepath = convert_dwg_to_dxf(filepath)
        print(f"Conversion complete. DXF saved to: {dxf_filepath}")
    elif file_ext == '.dxf':
        dxf_filepath = filepath
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")

    # Load the DXF file with proper encoding for Japanese characters
    try:
        doc = ezdxf.readfile(dxf_filepath, encoding=encoding)
    except Exception as e:
        # Try with alternative encodings if UTF-8 fails
        for alt_encoding in ['shift_jis', 'cp932', 'euc-jp']:
            try:
                doc = ezdxf.readfile(dxf_filepath, encoding=alt_encoding)
                print(f"Successfully loaded with {alt_encoding} encoding")
                break
            except:
                continue
        else:
            raise ValueError(f"Failed to load DXF file with any encoding: {e}")

    # Extract entities from modelspace
    msp = doc.modelspace()

    entities = {
        'lines': [],
        'polylines': [],
        'arcs': [],
        'circles': [],
        'texts': [],
        'blocks': []
    }

    # Process all entities
    for entity in msp:
        entity_type = entity.dxftype()

        if entity_type == 'LINE':
            entities['lines'].append(CADEntity('LINE', entity))
        elif entity_type in ['LWPOLYLINE', 'POLYLINE']:
            entities['polylines'].append(CADEntity('POLYLINE', entity))
        elif entity_type == 'ARC':
            entities['arcs'].append(CADEntity('ARC', entity))
        elif entity_type == 'CIRCLE':
            entities['circles'].append(CADEntity('CIRCLE', entity))
        elif entity_type in ['TEXT', 'MTEXT']:
            entities['texts'].append(CADEntity(entity_type, entity))
        elif entity_type == 'INSERT':  # Block reference
            entities['blocks'].append(CADEntity('INSERT', entity))

    # Print summary
    print("\nEntity Summary:")
    for entity_type, entity_list in entities.items():
        if entity_list:
            print(f"  {entity_type}: {len(entity_list)} entities")

    # Print sample of Japanese text if found
    japanese_texts = [e for e in entities['texts']
                      if e.text_content and any(ord(c) > 127 for c in e.text_content)]
    if japanese_texts:
        print(f"\nFound {len(japanese_texts)} text entities with non-ASCII characters")
        print("Sample texts:")
        for i, text_entity in enumerate(japanese_texts[:5]):
            print(f"  {i + 1}. {text_entity.text_content}")

    return entities


def render_cad_preview(filepath: str, show_plot: bool = True) -> None:
    """
    Render a preview of the CAD file for testing purposes

    Args:
        filepath: Path to the CAD file (DWG or DXF)
        show_plot: Whether to display the plot (True) or just generate it
    """
    # Load the file
    entities = load_cad(filepath)

    # Get the DXF document for rendering
    file_ext = os.path.splitext(filepath)[1].lower()
    if file_ext == '.dwg':
        base_dir = os.path.dirname(filepath)
        output_dir = ensure_output_directory(base_dir)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        dxf_filepath = str(output_dir / f"{base_name}.dxf")
    else:
        dxf_filepath = filepath

    # Load DXF for rendering
    doc = ezdxf.readfile(dxf_filepath)

    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 8))

    # Set up the rendering context
    ctx = RenderContext(doc)

    # Configure backend
    backend = MatplotlibBackend(ax)

    # Create frontend
    frontend = Frontend(ctx, backend)

    # Draw all entities
    frontend.draw_layout(doc.modelspace(), finalize=True)

    # Configure plot appearance
    ax.set_aspect('equal')
    ax.set_title(f'CAD Preview: {os.path.basename(filepath)}', fontsize=14)

    # Set background color
    ax.set_facecolor('#f0f0f0')
    fig.patch.set_facecolor('white')

    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')

    # Adjust layout
    plt.tight_layout()

    if show_plot:
        plt.show()
    else:
        plt.close()

    print(f"\nPreview rendered successfully")


def extract_wall_entities(entities: Dict[str, List[CADEntity]],
                          wall_layers: Optional[List[str]] = None) -> List[CADEntity]:
    """
    Extract potential wall entities from the loaded entities

    Args:
        entities: Dictionary of categorized entities from load_cad()
        wall_layers: Optional list of layer names to filter for walls

    Returns:
        List of CADEntity objects that might represent walls
    """
    wall_candidates = []

    # Default wall layer patterns if none provided
    if wall_layers is None:
        wall_layers = ['WALL', 'WALLS', '壁', 'W-', 'A-WALL']

    # Check lines and polylines for wall candidates
    for entity_list in [entities['lines'], entities['polylines']]:
        for cad_entity in entity_list:
            entity = cad_entity.entity
            try:
                layer_name = entity.dxf.layer.upper()
                # Check if layer name contains any wall pattern
                if any(pattern.upper() in layer_name for pattern in wall_layers):
                    wall_candidates.append(cad_entity)
                # Also check for thick lines that might be walls
                elif hasattr(entity.dxf, 'thickness') and entity.dxf.thickness > 50:
                    wall_candidates.append(cad_entity)
            except:
                continue

    return wall_candidates


# Test function for direct module execution
if __name__ == "__main__":
    # Test with sample.dwg
    test_file = "sample.dwg"

    if os.path.exists(test_file):
        print(f"Testing with {test_file}")

        try:
            # Load and convert the file
            entities = load_cad(test_file)

            # Render preview
            render_cad_preview(test_file, show_plot=True)

            # Extract wall candidates
            wall_entities = extract_wall_entities(entities)
            print(f"\nFound {len(wall_entities)} potential wall entities")

        except Exception as e:
            print(f"Error processing file: {e}")
            import traceback

            traceback.print_exc()
    else:
        print(f"Test file '{test_file}' not found in current directory")
        print(f"Current directory: {os.getcwd()}")
