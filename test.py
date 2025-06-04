import ezdxf
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib.collections as mcollections
import numpy as np
import math


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
        '8-F': 'wall_centers'  # red-dots inside walls (always in middle of walls)
    }

    # Set render limits
    render_xlim = (2500, 2700)

    # Step 1: Collect all 8-F dots (wall center points)
    wall_center_dots = []
    wall_boundary_lines = []
    door_lines = []
    labelling_entities = []
    polls_entities = []

    all_plot_points_x = []
    all_plot_points_y = []

    for entity in msp:
        if not (hasattr(entity, 'dxf') and hasattr(entity.dxf, 'layer')):
            continue

        layer = entity.dxf.layer
        if layer not in target_layers:
            continue

        coords = []

        # Extract coordinates based on entity type
        if entity.dxftype() == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end
            coords = [(start.x, start.y), (end.x, end.y)]
        elif entity.dxftype() == 'LWPOLYLINE':
            coords = [(point[0], point[1]) for point in entity.get_points()]
        elif entity.dxftype() == 'POLYLINE':
            coords = [(point[0], point[1]) for point in entity.points()]
        elif entity.dxftype() == 'POINT':
            coords = [(entity.dxf.location.x, entity.dxf.location.y)]
        elif entity.dxftype() in ('TEXT', 'MTEXT'):
            coords = [(entity.dxf.insert.x, entity.dxf.insert.y)]

        if not coords:
            continue

        # Filter by X coordinate range
        entity_in_range = any(render_xlim[0] <= x <= render_xlim[1] for x, y in coords)
        if not entity_in_range:
            continue

        # Collect points for Y axis scaling
        for p_x, p_y in coords:
            if render_xlim[0] <= p_x <= render_xlim[1]:
                all_plot_points_x.append(p_x)
                all_plot_points_y.append(p_y)

        # Categorize entities by layer
        if layer == '8-F':  # Wall center dots
            for coord in coords:
                wall_center_dots.append(coord)
        elif layer == '8-4':  # Potential wall boundaries
            wall_boundary_lines.append({
                'coordinates': coords,
                'entity_type': entity.dxftype(),
                'is_closed': getattr(entity, 'is_closed', False)
            })
        elif layer == '8-1':  # Door lines
            door_lines.append({
                'coordinates': coords,
                'entity_type': entity.dxftype(),
                'is_closed': getattr(entity, 'is_closed', False)
            })
        elif layer == '8-2':  # Labelling
            labelling_entities.append({
                'coordinates': coords,
                'entity_type': entity.dxftype(),
                'text': getattr(entity.dxf, 'text', '') if hasattr(entity.dxf, 'text') else ''
            })
        elif layer == '8-3':  # Polls
            polls_entities.append({
                'coordinates': coords,
                'entity_type': entity.dxftype(),
                'is_closed': getattr(entity, 'is_closed', False)
            })

    print(f"Found {len(wall_center_dots)} wall center dots (8-F)")
    print(f"Found {len(wall_boundary_lines)} potential wall boundary lines (8-4)")
    print(f"Found {len(door_lines)} door lines (8-1)")
    print(f"Found {len(labelling_entities)} labelling entities (8-2)")

    # Step 2: Filter 8-4 lines that are 1.5 units away from 8-F dots
    WALL_DETECTION_DISTANCE = 1.5
    validated_wall_boundaries = []

    for wall_line in wall_boundary_lines:
        coords = wall_line['coordinates']

        # Only keep horizontal or vertical lines
        if not is_horizontal_or_vertical(coords, tolerance=2.0):
            continue

        # Check if this line is within 1.5 units of any wall center dot
        line_near_wall_center = False

        for dot_x, dot_y in wall_center_dots:
            if len(coords) >= 2:
                # For lines, check distance to line segment
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

    print(f"Validated {len(validated_wall_boundaries)} wall boundary lines near wall centers")

    # Step 3: Filter 8-1 door lines - keep only horizontal/vertical ones connected to wall boundaries
    validated_door_lines = []

    for door_line in door_lines:
        coords = door_line['coordinates']

        # Only keep horizontal or vertical lines
        if not is_horizontal_or_vertical(coords, tolerance=2.0):
            continue

        # Check if this door line is connected to any validated wall boundary
        connected_to_wall = False

        for wall_boundary in validated_wall_boundaries:
            if line_segments_are_connected(coords, wall_boundary['coordinates'], tolerance=3.0):
                connected_to_wall = True
                break

        if connected_to_wall:
            validated_door_lines.append(door_line)

    print(f"Validated {len(validated_door_lines)} door lines connected to walls")

    # Step 4: Visualization
    plt.figure(figsize=(150, 100))
    ax = plt.gca()
    ax.set_aspect('equal')
    ax.set_title(f'Wall Detection Analysis - {DXF_FILE}')

    # Render validated wall boundaries (8-4) in purple
    for wall_boundary in validated_wall_boundaries:
        coords = wall_boundary['coordinates']
        if len(coords) >= 2:
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color='purple', linewidth=3,
                    label='Wall Boundaries' if 'Wall Boundaries' not in [t.get_text() for t in
                                                                         ax.texts] else "_nolegend_")

    # Render validated door lines (8-1) in light blue
    for door_line in validated_door_lines:
        coords = door_line['coordinates']
        if len(coords) >= 2:
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color='lightblue', linewidth=2,
                    label='Doors' if 'Doors' not in [t.get_text() for t in ax.texts] else "_nolegend_")

    # Render wall center dots (8-F) in red
    for dot_x, dot_y in wall_center_dots:
        ax.plot(dot_x, dot_y, 'ro', markersize=6,
                label='Wall Centers' if 'Wall Centers' not in [t.get_text() for t in ax.texts] else "_nolegend_")

    # Render all labelling entities (8-2) in red
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

    # Render polls (8-3) in orange
    for poll_entity in polls_entities:
        coords = poll_entity['coordinates']
        if len(coords) >= 2:
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color='orange', linewidth=1.5,
                    label='Polls' if 'Polls' not in [t.get_text() for t in ax.texts] else "_nolegend_")

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
        # Remove duplicate labels
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(),
                  loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0.)

    plt.xlabel('X coordinate')
    plt.ylabel('Y coordinate')
    plt.grid(True, alpha=0.3)
    plt.tight_layout(rect=[0, 0, 0.85, 1])

    print(f"\nDetection Summary:")
    print(f"- Wall center dots (8-F): {len(wall_center_dots)}")
    print(f"- Validated wall boundaries (8-4): {len(validated_wall_boundaries)}")
    print(f"- Validated doors (8-1): {len(validated_door_lines)}")
    print(f"- Labels (8-2): {len(labelling_entities)}")
    print(f"- Polls (8-3): {len(polls_entities)}")

    plt.show()


if __name__ == "__main__":
    main()
