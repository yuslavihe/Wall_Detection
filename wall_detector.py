import ezdxf
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import math

# ---------------------------
# Configuration
# ---------------------------

DXF_FILE = "sample.dxf"

# Legend extraction and mapping
legend_mapping = {
    "外壁部": "A - WALL",
    "Retaining walls": "RETW",
    "Boundary walls": "WALL",
    "Doors": "A - DOOR",
    "Windows": "A - GLAZ"
}

# Association distance threshold
ASSOCIATION_DISTANCE_THRESHOLD = 200

# Reverse legend mapping
layer_to_type_name = {v: k for k, v in legend_mapping.items()}

# Color map
color_map = {
    "外壁部": "darkred",
    "Retaining walls": "saddlebrown",
    "Boundary walls": "darkgreen",
    "Doors": "blueviolet",
    "Windows": "deepskyblue",
    "Unknown Wall": "gray"
}

# Default values
default_dpi = 100
default_xlim = (2500, 2800)
default_ylim = (1800, 2200)

# ---------------------------
# Utility functions
# ---------------------------

def distance_point_to_line_segment(px, py, x1, y1, x2, y2):
    line_mag_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if line_mag_sq < 1e-12:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_mag_sq))
    closest_x = x1 + t * (x2 - x1)
    closest_y = y1 + t * (y2 - y1)
    return math.hypot(px - closest_x, py - closest_y)

# ---------------------------
# Load DXF and extract entities
# ---------------------------

try:
    doc = ezdxf.readfile(DXF_FILE)
except IOError:
    print(f"Cannot open DXF file: {DXF_FILE}")
    exit(1)
except ezdxf.DXFStructureError:
    print(f"Invalid or corrupted DXF file: {DXF_FILE}")
    exit(1)

msp = doc.modelspace()

potential_wall_entities = [e for e in msp if e.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE')]

text_entities = []
for e in msp.query('TEXT MTEXT'):
    text_str = e.plain_text() if e.dxftype() == 'MTEXT' else e.dxf.text
    text_entities.append({
        'text': text_str.strip(),
        'insert': (e.dxf.insert.x, e.dxf.insert.y)
    })

# ---------------------------
# Classify entities
# ---------------------------

classified_elements = []

for entity in potential_wall_entities:
    layer = entity.dxf.layer
    element_type = layer_to_type_name.get(layer, "Unknown Wall")

    coords = []
    is_closed = False

    if entity.dxftype() == 'LINE':
        start = entity.dxf.start
        end = entity.dxf.end
        coords = [(start.x, start.y), (end.x, end.y)]
    elif entity.dxftype() == 'LWPOLYLINE':
        coords = [(point[0], point[1]) for point in entity.get_points()]
        is_closed = entity.is_closed
    elif entity.dxftype() == 'POLYLINE':
        coords = [(point[0], point[1]) for point in entity.get_points()]
        is_closed = entity.is_closed
    else:
        continue

    if not coords:
        continue

    assigned_label_text = None
    min_dist_to_label = float('inf')

    for text_info in text_entities:
        label_text_content = text_info['text']
        label_px, label_py = text_info['insert']

        current_min_dist_to_entity = float('inf')
        if len(coords) == 2:
            current_min_dist_to_entity = distance_point_to_line_segment(label_px, label_py, coords[0][0], coords[0][1],
                                                                        coords[1][0], coords[1][1])
        elif len(coords) > 2:
            for i in range(len(coords)):
                p1 = coords[i]
                p2 = coords[(i + 1) % len(coords)]
                dist_to_segment = distance_point_to_line_segment(label_px, label_py, p1[0], p1[1], p2[0], p2[1])
                current_min_dist_to_entity = min(current_min_dist_to_entity, dist_to_segment)

        if current_min_dist_to_entity < ASSOCIATION_DISTANCE_THRESHOLD and current_min_dist_to_entity < min_dist_to_label:
            if label_text_content in legend_mapping:
                assigned_label_text = label_text_content
                min_dist_to_label = current_min_dist_to_entity

    if assigned_label_text:
        element_type = assigned_label_text

    classified_elements.append({
        'type': element_type,
        'layer': layer,
        'coordinates': coords,
        'entity_type': entity.dxftype(),
        'is_closed': is_closed
    })

# ---------------------------
# Visualization with matplotlib
# ---------------------------

def plot_dxf(dpi, xlim, ylim):
    plt.figure(figsize=(15, 10), dpi=dpi)
    ax = plt.gca()
    ax.set_aspect('equal')
    ax.set_title(f'DXF Rendering - All LINEs & POLYLINEs from {DXF_FILE}')

    if not classified_elements:
        print("No elements were classified for rendering. The plot will be empty.")
        ax.text(0.5, 0.5, "No elements found or classified for rendering.",
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=12, color='red')

    rendered_labels_legend = set()

    for element in classified_elements:
        coords = element['coordinates']
        element_display_type = element['type']
        color = color_map.get(element_display_type, 'black')
        label_for_legend = element_display_type
        if label_for_legend in rendered_labels_legend:
            label_for_legend = "_nolegend_"
        else:
            rendered_labels_legend.add(label_for_legend)

        entity_type = element['entity_type']
        is_closed = element.get('is_closed', True)

        if entity_type == 'LINE' and len(coords) == 2:
            xs, ys = zip(*coords)
            ax.plot(xs, ys, color=color, linewidth=2, label=label_for_legend)
        elif entity_type in ('LWPOLYLINE', 'POLYLINE') and len(coords) > 1:
            if not is_closed:
                xs, ys = zip(*coords)
                ax.plot(xs, ys, color=color, linewidth=2, label=label_for_legend)
            else:
                polygon = Polygon(coords, closed=True, fill=False, edgecolor=color, linewidth=2, label=label_for_legend)
                ax.add_patch(polygon)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper left', bbox_to_anchor=(1, 1))

    ax.set_xlabel('X coordinate')
    ax.set_ylabel('Y coordinate')
    ax.grid(True)

    ax.set_xlim(xlim[0], xlim[1])
    ax.set_ylim(ylim[0], ylim[1])

    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.show()

# ---------------------------
# User input for customization
# ---------------------------

dpi = default_dpi
xlim = default_xlim
ylim = default_ylim

try:
    dpi = int(input(f"Enter DPI for the plot (default {default_dpi}): ") or default_dpi)
    xlim_str = input(f"Enter X limits as xmin,xmax (default {default_xlim[0]},{default_xlim[1]}): ")
    ylim_str = input(f"Enter Y limits as ymin,ymax (default {default_ylim[0]},{default_ylim[1]}): ")

    if xlim_str:
        xlim = tuple(map(float, xlim_str.split(',')))
    if ylim_str:
        ylim = tuple(map(float, ylim_str.split(',')))

except ValueError:
    print("Invalid input. Using default values.")
    dpi = default_dpi
    xlim = default_xlim
    ylim = default_ylim
except Exception as e:
    print(f"An unexpected error occurred: {e}")

# ---------------------------
# Plot with user customization
# ---------------------------

plot_dxf(dpi, xlim, ylim)
