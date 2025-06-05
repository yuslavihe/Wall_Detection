import ezdxf
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
import matplotlib.collections as mcollections
import numpy as np
import math
from scipy.spatial.distance import pdist, squareform
from collections import defaultdict


def is_horizontal_or_vertical(coords, tolerance=1.0):
    """Check if a line is horizontal or vertical within tolerance."""
    if len(coords) < 2:
        return False

    x1, y1 = coords[0]
    x2, y2 = coords[-1]

    # Check if horizontal (delta Y is small)
    if abs(y2 - y1) <= tolerance:
        return True
    # Check if vertical (delta X is small)
    if abs(x2 - x1) <= tolerance:
        return True

    return False


def distance_point_to_line_segment(px, py, x1, y1, x2, y2):
    """Calculate distance from point to line segment."""
    line_mag_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if line_mag_sq < 1e-12:  # Treat as point if segment is very short
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_mag_sq))
    closest_x = x1 + t * (x2 - x1)
    closest_y = y1 + t * (y2 - y1)
    return math.hypot(px - closest_x, py - closest_y)


def line_segments_are_connected(line1_coords, line2_coords, tolerance=2.0):
    """Check if two line segments are connected (share an endpoint within tolerance)."""
    for p1 in [line1_coords[0], line1_coords[-1]]:
        for p2 in [line2_coords[0], line2_coords[-1]]:
            if math.hypot(p1[0] - p2[0], p1[1] - p2[1]) <= tolerance:
                return True
    return False


def is_rectangular_box(coords, tolerance=2.0):
    """Check if coordinates form a rectangular box."""
    if len(coords) < 4:
        return False

    # For closed polylines, remove duplicate last point if it equals first
    if len(coords) > 4 and math.hypot(coords[0][0] - coords[-1][0], coords[0][1] - coords[-1][1]) < tolerance:
        coords = coords[:-1]

    if len(coords) != 4:
        return False

    # Calculate all side lengths
    sides = []
    for i in range(4):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % 4]
        sides.append(math.hypot(x2 - x1, y2 - y1))

    # Check if opposite sides are equal (rectangle property)
    if (abs(sides[0] - sides[2]) < tolerance and abs(sides[1] - sides[3]) < tolerance):
        # Check if adjacent sides are perpendicular
        for i in range(4):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % 4]
            x3, y3 = coords[(i + 2) % 4]

            # Vectors for adjacent sides
            v1 = (x2 - x1, y2 - y1)
            v2 = (x3 - x2, y3 - y2)

            # Dot product should be near zero for perpendicular lines
            dot_product = v1[0] * v2[0] + v1[1] * v2[1]
            if abs(dot_product) > tolerance * 10:  # Allow some tolerance
                return False
        return True

    return False


def get_box_center(coords):
    """Calculate center of a box."""
    if len(coords) > 4 and math.hypot(coords[0][0] - coords[-1][0], coords[0][1] - coords[-1][1]) < 1.0:
        coords = coords[:-1]

    x_coords = [p[0] for p in coords]
    y_coords = [p[1] for p in coords]
    return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))


def connect_nearest_neighbors(centers, max_connections_per_box=3):
    """Connect each box center to its nearest neighbors, avoiding duplicates."""
    if len(centers) < 2:
        return []

    connections = []
    center_list = list(centers)

    # Calculate distance matrix
    distances = pdist(center_list)
    dist_matrix = squareform(distances)

    connected_pairs = set()

    for i, center in enumerate(center_list):
        # Get indices of nearest neighbors (excluding self)
        neighbor_distances = [(dist_matrix[i][j], j) for j in range(len(center_list)) if i != j]
        neighbor_distances.sort()

        # Connect to nearest neighbors (up to max_connections_per_box)
        connections_made = 0
        for dist, j in neighbor_distances:
            if connections_made >= max_connections_per_box:
                break

            # Create a pair tuple (always smaller index first to avoid duplicates)
            pair = (min(i, j), max(i, j))

            if pair not in connected_pairs:
                connected_pairs.add(pair)
                connections.append((center_list[i], center_list[j]))
                connections_made += 1

    return connections


def point_on_line(px, py, line_start, line_end, tolerance=0.5):
    """Check if a point is on a line segment within tolerance."""
    x1, y1 = line_start
    x2, y2 = line_end

    distance = distance_point_to_line_segment(px, py, x1, y1, x2, y2)
    return distance <= tolerance


def group_lines_by_endpoint(lines, tol=1e-2, min_length=1.0):  # Added min_length
    """Group lines by endpoints for rectangle detection, filter short lines."""
    points = []
    valid_lines = []  # List to hold lines that meet the minimum length criteria
    for line in lines:
        start = (round(line.dxf.start.x, 3), round(line.dxf.start.y, 3))
        end = (round(line.dxf.end.x, 3), round(line.dxf.end.y, 3))

        # Calculate line length
        length = math.hypot(end[0] - start[0], end[1] - start[1])

        # Filter out lines shorter than min_length
        if length >= min_length:
            points.extend([start, end])
            valid_lines.append(line)  # Store the valid line

    # Count occurrences of each point
    point_counts = defaultdict(int)
    for pt in points:
        point_counts[pt] += 1

    # Rectangle corners appear exactly twice (each used by two lines)
    corners = [pt for pt, count in point_counts.items() if count == 2]

    if len(corners) == 4:
        return corners  # Likely a rectangle
    return None


def main():
    DXF_FILE = "sample.dxf"

    try:
        doc = ezdxf.readfile(DXF_FILE)
    except IOError:
        print(f"Error: Cannot open DXF file: {DXF_FILE}")
        exit(1)
    except ezdxf.DXFStructureError:
        print(f"Error: Invalid or corrupted DXF file: {DXF_FILE}")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while reading the DXF file: {e}")
        exit(1)

    msp = doc.modelspace()

    # Define target layers
    target_layers = {
        '8-1': 'doors',  # doors
        '8-2': 'labelling',  # labelling
        '8-3': 'polls',  # polls that can be used to separate sections
        '8-4': 'walls',  # major wall boundaries
        '8-F': 'wall_centers'  # red-dots inside walls (actually circles with r=0.25)
    }

    # Set render limits
    render_xlim = (2500, 2700)

    # Step 1: Collect and filter entities
    wall_center_circles = []  # Changed from dots to circles
    wall_boundary_lines = []
    door_lines = []
    labelling_entities = []
    pole_boxes = []

    all_plot_points_x = []
    all_plot_points_y = []

    # Collect circle entities for Wall Centers by Layer 8-F
    for circle in msp.query('CIRCLE[layer=="8-F"]'):
        if abs(circle.dxf.radius - 0.25) < 0.1:
            wall_center_circles.append({
                'center': (circle.dxf.center.x, circle.dxf.center.y),
                'radius': circle.dxf.radius
            })

    # Collect LINE entities for Wall Boundaries by Layer 8-4
    for line in msp.query('LINE[layer=="8-4"]'):
        start = (line.dxf.start.x, line.dxf.start.y)
        end = (line.dxf.end.x, line.dxf.end.y)
        # Filter for horizontal and vertical lines only
        if is_horizontal_or_vertical([start, end], tolerance=2.0):
            wall_boundary_lines.append({
                'coordinates': [start, end],
                'entity_type': 'LINE',
                'is_closed': False  # Lines are never closed
            })

    # Collect LINE entities for doors by Layer 8-1
    for line in msp.query('LINE[layer=="8-1"]'):
        start = (line.dxf.start.x, line.dxf.start.y)
        end = (line.dxf.end.x, line.dxf.end.y)

        # Filter for horizontal and vertical lines only
        if is_horizontal_or_vertical([start, end], tolerance=2.0):
            door_lines.append({
                'coordinates': [start, end],
                'entity_type': 'LINE',
                'is_closed': False  # Lines are never closed
            })

    # Collect labelling entities (TEXT, MTEXT)
    for text_entity in msp.query('TEXT MTEXT[layer=="8-2"]'):
        if text_entity.dxftype() == 'TEXT':
            coords = [(text_entity.dxf.insert.x, text_entity.dxf.insert.y)]
            labelling_entities.append({
                'coordinates': coords,
                'entity_type': 'TEXT',
                'text': text_entity.dxf.text
            })
        else:  # MTEXT
            coords = [(text_entity.dxf.insert.x, text_entity.dxf.insert.y)]
            labelling_entities.append({
                'coordinates': coords,
                'entity_type': 'MTEXT',
                'text': text_entity.text
            })

    # Collect LINE entities for polls by Layer 8-3
    lines_8_3 = msp.query('LINE[layer=="8-3"]')
    with open('pole_detection_log.txt', 'w') as logfile:
        logfile.write("LINE-Based Detection:\n")
        for line in lines_8_3:
            start = (line.dxf.start.x, line.dxf.start.y)
            end = (line.dxf.end.x, line.dxf.end.y)
            logfile.write(f"  Line: Start={start}, End={end}\n")

            # Add LINE-based rectangle detection
    lines_8_3 = msp.query('LINE[layer=="8-3"]')
    rect_corners = group_lines_by_endpoint(lines_8_3)

    # Add LWPOLYLINE-based detection
    with open('pole_detection_log.txt', 'a') as logfile:
        logfile.write("\nLWPOLYLINE-Based Detection:\n")
        for pline in msp.query('LWPOLYLINE[layer=="8-3"]'):
            num_vertices = len(pline)
            is_closed = pline.is_closed  # Corrected attribute access
            logfile.write(f"  LWPOLYLINE: {pline.dxf.handle}, Vertices={num_vertices}, Closed={is_closed}\n")

            if pline.closed and num_vertices >= 4:  # Ensure at least 4 vertices
                verts = [(x, y) for x, y, *_ in pline.points()]  # Use pline.points()
                logfile.write(f"    LWPOLYLINE Vertices: {verts}\n")
                if is_rectangular_box(verts):
                    center = get_box_center(verts)
                    pole_boxes.append({
                        'coordinates': verts,
                        'center': center,
                        'entity_type': 'RECTANGLE',
                        'is_closed': True
                    })
                    logfile.write("    Detected as rectangular box.\n")
                else:
                    logfile.write("    Not detected as rectangular box.\n")
            else:
                logfile.write("    LWPOLYLINE Skipped: not closed or incorrect vertex count.\n")

    print(f"Found {len(pole_boxes)} rectangular pole boxes (8-3)")
    print(f"Found {len(wall_center_circles)} wall center circles (8-F)")
    print(f"Found {len(wall_boundary_lines)} potential wall boundary lines (8-4)")
    print(f"Found {len(door_lines)} door lines (8-1)")
    print(f"Found {len(labelling_entities)} labelling entities (8-2)")

    # Step 2: Connect pole box centers
    pole_centers = [box['center'] for box in pole_boxes]
    pole_connections = connect_nearest_neighbors(pole_centers, max_connections_per_box=2)

    print(f"Created {len(pole_connections)} connections between pole boxes")

    # Step 3: Filter wall center circles to keep only those on connection lines
    filtered_wall_circles = []
    for circle in wall_center_circles:
        center_x, center_y = circle['center']
        on_connection_line = False

        for line_start, line_end in pole_connections:
            if point_on_line(center_x, center_y, line_start, line_end, tolerance=1.0):
                on_connection_line = True
                break

        if on_connection_line:
            filtered_wall_circles.append(circle)

    print(f"Filtered to {len(filtered_wall_circles)} wall center circles on connection lines")

    # Step 4: Filter wall boundaries based on proximity to filtered circles
    WALL_DETECTION_DISTANCE = 1.5
    validated_wall_boundaries = []

    for wall_line in wall_boundary_lines:
        coords = wall_line['coordinates']

        # Check if this line is within 1.5 units of any filtered wall center circle
        line_near_wall_center = False

        for circle in filtered_wall_circles:
            dot_x, dot_y = circle['center']
            if len(coords) >= 2:
                min_dist = float('inf')
                for i in range(len(coords) - 1):
                    x1, y1 = coords[i]
                    x2, y2 = coords[i + 1]
                    dist = distance_point_to_line_segment(dot_x, dot_y, x1, y1, x2, y2)
                    min_dist = min(min_dist, dist)

                if min_dist <= WALL_DETECTION_DISTANCE:
                    line_near_wall_center = True
                    break

        if line_near_wall_center:
            validated_wall_boundaries.append(wall_line)

    print(f"Validated {len(validated_wall_boundaries)} wall boundary lines near filtered wall centers")

    # Step 5: Filter door lines connected to validated walls
    validated_door_lines = []

    for door_line in door_lines:
        coords = door_line['coordinates']

        # Check if this door line is connected to any validated wall boundary
        connected_to_wall = False

        for wall_boundary in validated_wall_boundaries:
            if line_segments_are_connected(coords, wall_boundary['coordinates'], tolerance=3.0):
                connected_to_wall = True
                break

        if connected_to_wall:
            validated_door_lines.append(door_line)

    print(f"Validated {len(validated_door_lines)} door lines connected to walls")

    # Step 6: Visualization
    plt.figure(figsize=(150, 100))
    ax = plt.gca()
    ax.set_aspect('equal')
    ax.set_title(f'Pole Box Connection Analysis - {DXF_FILE}')

    # Render pole boxes in orange
    for pole_box in pole_boxes:
        coords = pole_box['coordinates']
        if len(coords) >= 3:
            if pole_box['entity_type'] == 'RECTANGLE':
                try:
                    polygon = Polygon(coords, closed=True, fill=False, edgecolor='orange', linewidth=2,
                                      label='Pole Boxes' if 'Pole Boxes' not in [t.get_text() for t in
                                                                                 ax.get_legend().get_texts()] else "_nolegend_")
                except AttributeError:
                    polygon = Polygon(coords, closed=True, fill=False, edgecolor='orange', linewidth=2,
                                      label='Pole Boxes')
            else:
                try:
                    polygon = Polygon(coords, closed=True, fill=False, edgecolor='orange', linewidth=2,
                                      label='Pole Boxes' if 'Pole Boxes' not in [t.get_text() for t in
                                                                                 ax.get_legend().get_texts()] else "_nolegend_")
                except AttributeError:
                    polygon = Polygon(coords, closed=True, fill=False, edgecolor='orange', linewidth=2,
                                      label='Pole Boxes')

            ax.add_patch(polygon)
            # Mark center
            center_x, center_y = pole_box['center']
            ax.plot(center_x, center_y, 'go', markersize=4)

    # Render pole connections in green
    for line_start, line_end in pole_connections:
        ax.plot([line_start[0], line_end[0]], [line_start[1], line_end[1]], 'g-', linewidth=2,
                label='Pole Connections' if 'Pole Connections' not in [t.get_text() for t in
                                                                       ax.texts] else "_nolegend_")

    # Render filtered wall center circles in red
    for circle in filtered_wall_circles:
        center_x, center_y = circle['center']
        radius = circle['radius']
        circle_patch = Circle((center_x, center_y), radius, fill=False, edgecolor='red', linewidth=2,
                              label='Wall Centers' if 'Wall Centers' not in [t.get_text() for t in
                                                                             ax.texts] else "_nolegend_")
        ax.add_patch(circle_patch)

    # Render validated wall boundaries in purple
    for wall_boundary in validated_wall_boundaries:
        coords = wall_boundary['coordinates']
        if len(coords) >= 2:
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color='purple', linewidth=3,
                    label='Wall Boundaries' if 'Wall Boundaries' not in [t.get_text() for t in
                                                                         ax.texts] else "_nolegend_")

    # Render validated door lines in light blue
    for door_line in validated_door_lines:
        coords = door_line['coordinates']
        if len(coords) >= 2:
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color='lightblue', linewidth=2,
                    label='Doors' if 'Doors' not in [t.get_text() for t in ax.texts] else "_nolegend_")

    # Render labelling entities in red
    for label_entity in labelling_entities:
        coords = label_entity['coordinates']
        entity_type = label_entity['entity_type']

        if entity_type in ('TEXT', 'MTEXT'):
            for x, y in coords:
                ax.plot(x, y, 's', color='red', markersize=4,
                        label='Labels' if 'Labels' not in [t.get_text() for t in ax.texts] else "_nolegend_")
        else:
            if len(coords) >= 2:
                xs, ys = zip(*coords)
                ax.plot(xs, ys, color='red', linewidth=1,
                        label='Labels' if 'Labels' not in [t.get_text() for t in ax.texts] else "_nolegend_")

    # Set plot limits
    ax.set_xlim(render_xlim)

    if all_plot_points_y:
        min_y, max_y = min(all_plot_points_y), max(all_plot_points_y)
        height = max_y - min_y
        margin_y = height * 0.1 if height > 1e-6 else 10
        ax.set_ylim(min_y - margin_y, max_y + margin_y)
    else:
        ax.set_ylim(1800, 2200)

    # Create legend
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(),
                  loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0.)

    plt.xlabel('X coordinate')
    plt.ylabel('Y coordinate')
    plt.grid(True, alpha=0.3)
    plt.tight_layout(rect=[0, 0, 0.85, 1])

    print(f"\nFinal Analysis Summary:")
    print(f"- Rectangular pole boxes detected: {len(pole_boxes)}")
    print(f"- Pole connections created: {len(pole_connections)}")
    print(f"- Wall center circles on connections: {len(filtered_wall_circles)}")
    print(f"- Validated wall boundaries: {len(validated_wall_boundaries)}")
    print(f"- Validated doors: {len(validated_door_lines)}")
    print(f"- Labels: {len(labelling_entities)}")

    plt.show()


if __name__ == "__main__":
    main()
