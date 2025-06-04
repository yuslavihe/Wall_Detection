# wall_detector/main.py
import os
import argparse
import ezdxf
from ezdxf.entities import Line, LWPolyline, Text as DXFText
from shapely.geometry import Polygon, LineString
from typing import List, Dict, Any, Optional

# Make sure the wall_detector package is discoverable
# This might require adding parent directory to sys.path if running as script
import sys
# Assuming main.py is in wall_detector, and modules are in Wall_Detection/wall_detector
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wall_detector import geometry_utils
from wall_detector import wall_classifier
from wall_detector.wall_classifier import Wall # Import Wall dataclass

def main():
    parser = argparse.ArgumentParser(description="Detect and classify walls from a CAD file.")
    parser.add_argument("--cad_file", required=True, help="Path to the input CAD file (DXF format)")
    parser.add_argument("--legend_pdf", required=True, help="Path to the PDF file containing the wall type legend")
    parser.add_argument("--output_dir", required=True, help="Directory where the output files will be saved")

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # 1. Load CAD data (simulating data_loader.py)
    try:
        doc = ezdxf.readfile(args.cad_file)
        msp = doc.modelspace()
    except IOError:
        print(f"Error: Cannot open DXF file at {args.cad_file}.")
        return
    except ezdxf.DXFStructureError:
        print(f"Error: Invalid or corrupt DXF file at {args.cad_file}.")
        return

    raw_geom_entities = []
    raw_text_entities = []

    for entity in msp: # Iterate over all entities in modelspace
        entity_data = {'layer': entity.dxf.layer}
        if entity.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE'):
            if entity.dxftype() == 'LINE':
                entity_data['type'] = 'LINE'
                entity_data['vertices'] = [entity.dxf.start[:2], entity.dxf.end[:2]]
            elif entity.dxftype() == 'LWPOLYLINE':
                entity_data['type'] = 'LWPOLYLINE'
                # LWPolyline points are (x, y, start_width, end_width, bulge)
                entity_data['vertices'] = [(p[0], p[1]) for p in entity.get_points(format='xyseb')]
            # Add POLYLINE handling if necessary (more complex)
            raw_geom_entities.append(entity_data)
        elif entity.dxftype() in ('TEXT', 'MTEXT'):
            entity_data['type'] = entity.dxftype()
            entity_data['text'] = entity.dxf.text if entity.dxftype() == 'TEXT' else entity.dxf.text # MTEXT might need .plain_text()
            entity_data['insert'] = (entity.dxf.insert.x, entity.dxf.insert.y) # Access x, y components directly
            raw_text_entities.append(entity_data)

    print(f"Loaded {len(raw_geom_entities)} geometric entities and {len(raw_text_entities)} text entities.")

    # 2. Extract wall candidates (using geometry_utils.py)
    # Tolerance for geometric operations (e.g., merging lines, snapping)
    # Units depend on DXF file (e.g., mm or inches). Assume consistent units.
    geom_tolerance = 1.0
    extracted_candidates = geometry_utils.extract_wall_candidates(
        raw_geom_entities, raw_text_entities, tol=geom_tolerance
    )
    print(f"Extracted {len(extracted_candidates)} potential wall candidates.")

    # Convert to Wall objects for classifier
    wall_objects_for_classification: List[Wall] = []
    for i, cand_data in enumerate(extracted_candidates):
        if isinstance(cand_data['geometry'], Polygon): # Ensure it's a polygon
            wall_obj = Wall(
                id=f"wall_{i+1:03d}",
                geometry=cand_data['geometry'],
                raw_label=cand_data.get('raw_label'),
                layer_name=cand_data['layer_name']
            )
            wall_objects_for_classification.append(wall_obj)
        else:
            print(f"Warning: Candidate {i+1} is not a polygon, skipping.")


    # 3. Define a sample legend (simulating pdf_parser.py)
    # This legend matches the structure discussed for wall_classifier.py
    legend_dict = {
        "B-01": {"name": "Load-Bearing Wall (from Label)"},
        # Layer rules
        "LBStructRule": {"name": "Load-Bearing Wall (from Layer)", "layer_pattern": "^WALL_LB.*"},
        "PartitionRule": {"name": "Partition Wall (from Layer)", "layer_pattern": "^WALL_PARTITION.*"},
        "GeneralWallRule": {"name": "General Wall (from Layer)", "layer_pattern": "^WALL_GENERAL.*"},
        # Thickness rules (example, may need adjustment based on dummy DXF)
        # Thickness values are in same units as DXF. Example: mm
        "ThickLoadBearing": {"name": "Load-Bearing Wall (from Thickness)", "thickness_min": 200}, # 200+ mm
        "ThickPartition": {"name": "Partition Wall (from Thickness)", "thickness_max": 120},    # < 120 mm
        "ThickStandard": {"name": "Standard Wall (from Thickness)", "thickness_min": 120, "thickness_max": 200} # 120-200mm
    }
    print(f"Using legend: {legend_dict}")

    # 4. Classify walls (using wall_classifier.py)
    classified_walls = wall_classifier.classify_walls(
        wall_objects_for_classification, legend_dict, thickness_tolerance=1.0
    )

    # 5. Print results (for now)
    print("\n--- Classified Walls ---")
    if not classified_walls:
        print("No walls were classified.")
    for wall in classified_walls:
        print(f"ID: {wall.id}")
        print(f"  Type: {wall.type_name}")
        print(f"  Layer: {wall.layer_name}")
        print(f"  Raw Label: {wall.raw_label}")
        if wall.thickness is not None:
            print(f"  Computed Thickness: {wall.thickness:.2f}")
        else:
            print(f"  Computed Thickness: N/A")
        print(f"  Rule: {wall.assigned_rule}")
        # print(f"  Geometry Type: {type(wall.geometry)}")
        # print(f"  Centroid: {geometry_utils.get_polygon_centroid(wall.geometry)}")
        print("-" * 20)

if __name__ == "__main__":
    main()
