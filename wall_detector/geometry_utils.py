# wall_detector/geometry_utils.py
"""
This module provides helper functions for geometric operations on CAD entities,
primarily using the shapely library.
"""
from typing import List, Dict, Any, Optional, Tuple

from shapely.geometry import LineString, Polygon, MultiLineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union, snap


# Placeholder for DXF entity types if not using ezdxf directly here
# For example, if entities are passed as dictionaries
# from ezdxf.entities import DXFEntity, Line as DXFLine, LWPolyline as DXFLWPolyline, Text as DXFText


def dxf_entity_to_shapely(entity: Dict[str, Any]) -> Optional[BaseGeometry]:
    """
    Converts a simplified DXF entity dictionary to a Shapely geometry.
    Assumes entity dict has 'type' and 'vertices'.
    'vertices' is a list of (x, y) tuples.
    """
    entity_type = entity.get('type')
    vertices = entity.get('vertices')

    if not entity_type or not vertices:
        return None

    if entity_type in ['LINE', 'POLYLINE', 'LWPOLYLINE']:
        if len(vertices) < 2:
            return None
        line = LineString(vertices)
        if entity_type in ['POLYLINE', 'LWPOLYLINE']:
            if vertices[0] == vertices[-1] and len(vertices) >= 4:  # Closed polyline
                # Ensure it's a valid polygon
                try:
                    poly = Polygon(vertices)
                    if poly.is_valid:
                        return poly
                    else:  # Try to make it valid
                        poly_buffered = poly.buffer(0)
                        if poly_buffered.is_valid and isinstance(poly_buffered, Polygon):
                            return poly_buffered
                        return line  # Fallback to linestring if polygon is not simple/valid
                except Exception:
                    return line  # Fallback if polygon creation fails
            return line  # Open polyline
        return line  # LINE
    return None


def merge_lines_to_polygons(line_strings: List[LineString], tol: float) -> List[Polygon]:
    """
    Takes a list of shapely.geometry.LineString, attempts to merge them
    and form polygons.

    Args:
        line_strings: A list of Shapely LineString objects.
        tol: Tolerance value for snapping/merging operations.

    Returns:
        A list of Shapely Polygon objects.
    """
    if not line_strings:
        return []

    # Use unary_union to merge overlapping/touching lines
    # Snapping might be needed if lines are close but not exactly touching
    # For simplicity, unary_union is a good start.
    # More robust merging might involve iterative snapping or buffering.

    # Snap all linestrings to each other within tolerance
    snapped_lines = []
    if len(line_strings) > 1:
        temp_union = unary_union(line_strings)  # Union to handle them together
        if isinstance(temp_union, MultiLineString):
            geoms_to_snap = list(temp_union.geoms)
        elif isinstance(temp_union, LineString):
            geoms_to_snap = [temp_union]
        else:  # if it's some other geometry type, or empty
            geoms_to_snap = line_strings  # fallback to original lines

        # Perform snapping iteratively (simplified: snap all to the union of all)
        # A more robust approach might be pairwise or grid-based snapping.
        for line in geoms_to_snap:
            snapped_line = snap(line, temp_union, tolerance=tol)
            if isinstance(snapped_line, LineString) and not snapped_line.is_empty:
                snapped_lines.append(snapped_line)
            elif isinstance(snapped_line, MultiLineString):
                for sub_line in snapped_line.geoms:
                    if isinstance(sub_line, LineString) and not sub_line.is_empty:
                        snapped_lines.append(sub_line)

    else:  # Single line string cannot form a polygon by itself unless it's closed
        snapped_lines = line_strings
        if isinstance(snapped_lines[0], LineString) and snapped_lines[0].is_closed:
            try:
                poly = Polygon(snapped_lines[0].coords)
                if poly.is_valid:
                    return [poly]
            except Exception:
                pass  # Not a simple polygon
        return []

    if not snapped_lines:
        return []

    # Union of line segments
    # unary_union can simplify and merge connected/overlapping lines
    merged_geometry = unary_union(snapped_lines)

    # Polygonize the merged lines
    # polygonize returns an iterator of polygons
    polygons = list(polygonize(merged_geometry))

    valid_polygons = []
    for poly in polygons:
        if isinstance(poly, Polygon) and poly.is_valid and poly.area > tol * tol:  # Ensure non-degenerate
            cleaned_poly = snap_and_clean(poly, tol)
            if isinstance(cleaned_poly, Polygon) and cleaned_poly.is_valid and cleaned_poly.area > tol * tol:
                valid_polygons.append(cleaned_poly)

    return valid_polygons


def compute_thickness(polygon: Polygon, method: str = 'area_over_length') -> Optional[float]:
    """
    Computes the thickness of a wall polygon.

    Args:
        polygon: A Shapely Polygon object representing the wall.
        method: The method to use for thickness computation.
                Currently supports 'area_over_length'.

    Returns:
        The computed thickness as a float, or None if computation fails.
    """
    if not isinstance(polygon, Polygon) or not polygon.is_valid or polygon.is_empty:
        return None

    if method == 'area_over_length':
        area = polygon.area
        length = polygon.length  # Perimeter for a simple polygon

        # For a long, thin rectangle (wall), area = length_centerline * thickness
        # And perimeter approx 2 * length_centerline (if thickness is small)
        # So, thickness approx area / (perimeter / 2) = 2 * area / perimeter
        # This formula is often used for average thickness for non-perfect rectangles.
        # The plan mentions polygon.area / polygon.length. This might imply polygon.length is the centerline length,
        # not perimeter. If polygon is a double-line wall, its `length` is its perimeter.
        # A common approximation for thickness of a polygon representing a double-line wall is:
        # thickness = Area / (Perimeter / 2 - sqrt((Perimeter/2)^2 - 4*Area)) / 2  -- this is too complex for now.
        # Or, if 'length' refers to the longer side of a rectangle:
        # For a near-rectangle, if `polygon.length` is perimeter:
        # Let L be centerline length, T be thickness. Area = L*T. Perimeter = 2L + 2T.
        # If T << L, Perimeter ~ 2L. So T ~ Area / (Perimeter/2) = 2 * Area / Perimeter.
        # If the plan's `polygon.length` means the length of the wall (centerline), then `Area / Length` is correct.
        # Let's assume `polygon.length` means perimeter as per Shapely docs.
        # A simple interpretation of "polygon.area / polygon.length" might be an error in the plan,
        # or it refers to a specific definition of "length".
        # If the wall is truly a thin rectangle of length L and thickness T, Area=L*T, Perimeter P = 2(L+T).
        # Area/Perimeter = LT / (2(L+T)). This is not T.
        # If it implies `min_dimension_of_bounding_box`, that's another way.
        # Let's stick to `2 * area / perimeter` if `polygon.length` is perimeter.
        # Or, if the polygon is thin, its minimum rotational caliper width.
        # For now, as per plan document: `polygon.area / polygon.length` (assuming length = major axis).
        # This is ambiguous. Let's try `2 * area / perimeter` as a robust general approximation.
        if length == 0:
            return None
        # Heuristic: Assume the "length" in "area / length" refers to the longer dimension.
        # We can approximate this from the minimum bounding rectangle.
        mbr = polygon.minimum_rotated_rectangle
        if mbr.is_empty or not isinstance(mbr, Polygon):
            return 2 * area / length if length > 0 else None  # Fallback if MBR fails

        # Get coordinates of MBR
        coords = list(mbr.exterior.coords)
        # Calculate side lengths of MBR
        side1_len = Point(coords[0]).distance(Point(coords[1]))
        side2_len = Point(coords[1]).distance(Point(coords[2]))

        # Assume thickness is the shorter side, length_centerline is the longer side
        centerline_approx_length = max(side1_len, side2_len)
        approx_thickness = min(side1_len, side2_len)

        # The plan's "polygon.area / polygon.length" is potentially using "length" as the centerline path length.
        # If the input `polygon` is a narrow strip, `approx_thickness` from MBR is a good candidate.
        return approx_thickness

    # Placeholder for other methods if needed
    return None


def snap_and_clean(geom: BaseGeometry, tol: float) -> BaseGeometry:
    """
    Snaps nearby vertices and cleans up geometry.
    Uses buffer(0) for basic cleaning and simplify.

    Args:
        geom: The input Shapely geometry.
        tol: Tolerance value for simplification.

    Returns:
        The cleaned Shapely geometry.
    """
    if geom.is_empty:
        return geom

    # buffer(0) can fix many invalid geometries
    cleaned_geom = geom.buffer(0)
    if cleaned_geom.is_empty:  # if buffer(0) resulted in empty, return original simplified
        return geom.simplify(tol, preserve_topology=True)

    # Simplify the geometry
    simplified_geom = cleaned_geom.simplify(tol, preserve_topology=True)

    if simplified_geom.is_empty:  # if simplify resulted in empty, return the buffer(0) result
        return cleaned_geom

    return simplified_geom


def get_polygon_centroid(polygon: Polygon) -> Optional[Tuple[float, float]]:
    """Helper to compute polygon centroid."""
    if isinstance(polygon, Polygon) and polygon.is_valid:
        return polygon.centroid.x, polygon.centroid.y
    return None


def get_polygon_bounds(polygon: Polygon) -> Optional[Tuple[float, float, float, float]]:
    """Helper to compute polygon bounding box."""
    if isinstance(polygon, Polygon) and polygon.is_valid:
        return polygon.bounds  # (minx, miny, maxx, maxy)
    return None


def extract_wall_candidates(
        dxf_entities: List[Dict[str, Any]],
        text_entities: List[Dict[str, Any]],
        tol: float = 0.01
) -> List[Dict[str, Any]]:
    """
    Extracts potential wall candidates from raw DXF entities.
    Converts DXF geometries to Shapely Polygons, groups lines,
    and attempts basic association with text labels.

    Args:
        dxf_entities: List of DXF geometric entities (as dicts with 'type', 'vertices', 'layer').
        text_entities: List of DXF text entities (as dicts with 'type', 'text', 'insert', 'layer').
        tol: Tolerance for geometric operations.

    Returns:
        A list of dictionaries, where each dictionary represents a wall candidate:
        {'geometry': shapely.geometry.Polygon,
         'layer_name': str,
         'raw_label': Optional[str]}
    """
    wall_candidates = []
    line_segments_by_layer: Dict[str, List[LineString]] = {}

    # Process polygonal entities first (LWPOLYLINE, POLYLINE that are closed)
    for entity_dict in dxf_entities:
        layer_name = entity_dict.get('layer', '0')
        geom = dxf_entity_to_shapely(entity_dict)

        if isinstance(geom, Polygon) and geom.is_valid and geom.area > tol * tol:
            # Attempt to find associated text
            raw_label_text = None
            geom_centroid = geom.centroid
            for text_dict in text_entities:
                text_point = Point(text_dict.get('insert', (0, 0)))
                # Simple association: text centroid inside polygon or very close
                if geom.contains(text_point) or geom.distance(text_point) < tol * 10:  # Heuristic distance
                    raw_label_text = text_dict.get('text')
                    # Optional: remove this text_dict from list to avoid re-association
                    break

            wall_candidates.append({
                'geometry': geom,
                'layer_name': layer_name,
                'raw_label': raw_label_text
            })
        elif isinstance(geom, LineString):
            if layer_name not in line_segments_by_layer:
                line_segments_by_layer[layer_name] = []
            line_segments_by_layer[layer_name].append(geom)

    # Process line segments to form polygons (for double-line walls)
    for layer_name, lines in line_segments_by_layer.items():
        if len(lines) < 2:  # Need at least 2 lines, typically more for a closed polygon
            continue

        polygons_from_lines = merge_lines_to_polygons(lines, tol)
        for poly in polygons_from_lines:
            if isinstance(poly, Polygon) and poly.is_valid and poly.area > tol * tol:
                raw_label_text = None
                geom_centroid = poly.centroid
                for text_dict in text_entities:
                    text_point = Point(text_dict.get('insert', (0, 0)))
                    if poly.contains(text_point) or poly.distance(text_point) < tol * 10:
                        raw_label_text = text_dict.get('text')
                        break

                wall_candidates.append({
                    'geometry': poly,
                    'layer_name': layer_name,
                    'raw_label': raw_label_text
                })

    return wall_candidates

