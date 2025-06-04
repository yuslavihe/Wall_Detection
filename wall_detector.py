import ezdxf
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import math

# ---------------------------
# User step: Extract legend info from PDF manually using AI
# ---------------------------
print("=== Manual AI-assisted Legend Extraction ===")
print("Please use the following prompt to query an AI (e.g., ChatGPT) with your explanatory PDF content:")
print("""
Prompt:
"I have a PDF explaining wall types in a building plan. 
Please extract a legend mapping wall type names (in Japanese or English) to typical CAD layer names or keywords that identify those walls in a CAD drawing.
For example:
- '外壁' (Exterior wall): Layer 'A - WALL'
- '内壁' (Inner wall): Layer 'WALL_P'
Return the mapping as a JSON or dictionary format."
""")
print("After you get the mapping, please input it below as a Python dictionary.")
print("Example:")
print("{'外壁': 'A - WALL', '内壁': 'WALL_P'}")

# User inputs the legend mapping here:
legend_mapping = {
    "外壁部": "A - WALL",  # Example: Exterior walls might be on layer "A - WALL"
    "Retaining walls": "RETW",  # Example: Retaining walls on "RETW"
    "Boundary walls": "WALL",  # Example: General boundary walls on "WALL"
    "Doors": "A - DOOR",  # Included based on your input, but typically not rendered as 'walls'
    "Windows": "A - GLAZ"  # Included based on your input, but typically not rendered as 'walls'
    # Add more mappings based on your PDF and actual DXF layers
    # e.g., "Internal Partition": "WALL_INTERNAL"
}

# ---------------------------
# Load DXF and extract entities
# ---------------------------

DXF_FILE = "sample.dxf"  # Replace with your converted DXF filename

try:
    doc = ezdxf.readfile(DXF_FILE)
except IOError:
    print(f"Cannot open DXF file: {DXF_FILE}")
    exit(1)
except ezdxf.DXFStructureError:
    print(f"Invalid or corrupted DXF file: {DXF_FILE}")
    exit(1)

msp = doc.modelspace()

# --- Print all unique layer names from the DXF for debugging ---
all_layers = set()
for entity in msp:
    try:
        all_layers.add(entity.dxf.layer)
    except AttributeError:
        # Some entities might not have a layer attribute directly
        pass
print("\n=== Unique Layer Names Found in DXF ===")
if all_layers:
    for layer_name in sorted(list(all_layers)):
        print(layer_name)
else:
    print("No layers found or no entities with layer attribute in modelspace.")
print("========================================\n")
print("Please compare these layer names with the values in your 'legend_mapping' dictionary.")
print("Ensure the layer names in your DXF *exactly* match the values in the legend_mapping.\n")

# For testing: Extract ALL LINE, LWPOLYLINE, POLYLINE entities
# The goal is to render something to verify the pipeline.
potential_wall_entities = []
for e in msp:
    if e.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE'):
        potential_wall_entities.append(e)

if not potential_wall_entities:
    print(f"No LINE, LWPOLYLINE, or POLYLINE entities found in the modelspace of {DXF_FILE}.")
    print("Check if the DXF file contains these entity types or if they are in a different space (e.g., paperspace).")
    # exit(1) # You might want to exit if nothing to render

# Extract text labels (wall type names) and their positions
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

def distance_point_to_line_segment(px, py, x1, y1, x2, y2):
    line_mag_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if line_mag_sq < 1e-12:  # Treat as point if segment is very short
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_mag_sq))
    closest_x = x1 + t * (x2 - x1)
    closest_y = y1 + t * (y2 - y1)
    return math.hypot(px - closest_x, py - closest_y)


ASSOCIATION_DISTANCE_THRESHOLD = 200  # Adjust as needed based on CAD units

# Build reverse legend mapping: layer -> wall type name
layer_to_type_name = {v: k for k, v in legend_mapping.items()}

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
        is_closed = entity.is_closed  # ezdxf property for LWPOLYLINE
    elif entity.dxftype() == 'POLYLINE':
        coords = [(point[0], point[1]) for point in entity.get_points()]
        is_closed = entity.is_closed  # ezdxf property for POLYLINE
    else:
        continue

    if not coords:  # Skip if no coordinates extracted
        continue

    # Attempt to refine type using nearby text labels
    assigned_label_text = None
    min_dist_to_label = float('inf')

    for text_info in text_entities:
        label_text_content = text_info['text']
        label_px, label_py = text_info['insert']

        current_min_dist_to_entity = float('inf')
        if len(coords) == 2:  # Line
            current_min_dist_to_entity = distance_point_to_line_segment(label_px, label_py, coords[0][0], coords[0][1],
                                                                        coords[1][0], coords[1][1])
        elif len(coords) > 2:  # Polyline
            for i in range(len(coords)):
                p1 = coords[i]
                p2 = coords[(i + 1) % len(coords)]  # Loop back for closed polylines if necessary
                dist_to_segment = distance_point_to_line_segment(label_px, label_py, p1[0], p1[1], p2[0], p2[1])
                current_min_dist_to_entity = min(current_min_dist_to_entity, dist_to_segment)

        if current_min_dist_to_entity < ASSOCIATION_DISTANCE_THRESHOLD and current_min_dist_to_entity < min_dist_to_label:
            # Check if the text_info['text'] corresponds to a known type in the legend_mapping keys
            if label_text_content in legend_mapping:
                assigned_label_text = label_text_content
                min_dist_to_label = current_min_dist_to_entity

    if assigned_label_text:
        element_type = assigned_label_text  # Override type if a relevant label is found nearby

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

# Define colors for wall types (add more as needed for your specific types)
color_map = {
    "外壁部": "darkred",  # Typical for exterior walls
    "Retaining walls": "saddlebrown",
    "Boundary walls": "darkgreen",
    "Doors": "blueviolet",  # Doors (if you want to render them)
    "Windows": "deepskyblue",  # Windows (if you want to render them)
    "Unknown Wall": "gray",  # Default for walls not in legend or unidentified
    # Add other specific types from your legend_mapping here
    # e.g., "Internal Partition": "dodgerblue"
}

plt.figure(figsize=(15, 10))  # Increased figure size
ax = plt.gca()
ax.set_aspect('equal')
ax.set_title(f'DXF Rendering - All LINEs & POLYLINEs from {DXF_FILE}')

if not classified_elements:
    print("No elements were classified for rendering. The plot will be empty.")
    ax.text(0.5, 0.5, "No elements found or classified for rendering.",
            horizontalalignment='center', verticalalignment='center',
            transform=ax.transAxes, fontsize=12, color='red')

# Draw elements
rendered_labels_legend = set()  # To avoid duplicate legend entries

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
    # Use stored is_closed flag if available, else assume False
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


        # Optional: Add text label on the plot at the centroid
        # if coords:
        #     poly_np = np.array(coords)
        #     centroid = poly_np.mean(axis=0)
        #     ax.text(centroid[0], centroid[1], element_display_type, fontsize=8, color=color, ha='center', va='center', alpha=0.7)

# Create a legend with unique entries
handles, labels = ax.get_legend_handles_labels()
if handles:  # Only show legend if there's something to show
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper left', bbox_to_anchor=(1, 1))

plt.xlabel('X coordinate')
plt.ylabel('Y coordinate')
plt.grid(True)

plt.xlim(2500, 2800)  # Adjust these numbers as needed
plt.ylim(1800, 2200)

plt.tight_layout(rect=[0, 0, 0.85, 1])  # Adjust layout to make space for legend outside
plt.show()

