import ezdxf
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.collections as mcollections
import numpy as np  # For min/max, and handling potential empty lists


def plot_selected_dxf_entities(doc_msp, selected_layers, dxf_filepath):
    """
    Plots selected entities (LINE, LWPOLYLINE, POLYLINE) from specified layers in a DXF modelspace.
    Adjusts plot limits to focus on the selected entities.
    """
    fig, ax = plt.subplots(figsize=(10, 8))  # Adjust figure size as needed

    all_selected_points_x = []
    all_selected_points_y = []
    plotted_something = False

    # This set tracks layers for which a legend entry has already been prepared
    # to avoid duplicate legend entries from multiple entities on the same layer.
    layers_with_legend_entry = set()

    for entity in doc_msp:
        if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'layer') and \
                entity.dxf.layer in selected_layers:

            current_entity_points_x = []
            current_entity_points_y = []

            # Determine label for legend: only provide it for the first entity of a layer
            label_for_legend = ""
            if entity.dxf.layer not in layers_with_legend_entry:
                label_for_legend = entity.dxf.layer
                layers_with_legend_entry.add(entity.dxf.layer)

            if entity.dxftype() == 'LINE':
                start_point = entity.dxf.start
                end_point = entity.dxf.end
                line = mlines.Line2D([start_point[0], end_point[0]],
                                     [start_point[1], end_point[1]],
                                     label=label_for_legend)
                ax.add_line(line)
                current_entity_points_x.extend([start_point[0], end_point[0]])
                current_entity_points_y.extend([start_point[1], end_point[1]])
                plotted_something = True

            elif entity.dxftype() == 'LWPOLYLINE':
                # get_points(format='xy') returns list of (x, y) tuples
                points = list(entity.get_points(format='xy'))
                if points:
                    segments = []
                    for i in range(len(points) - 1):
                        segments.append([points[i], points[i + 1]])
                    if entity.is_closed and len(points) > 1:  # Check len > 1 for closed polyline
                        segments.append([points[-1], points[0]])

                    if segments:
                        lc = mcollections.LineCollection(segments, label=label_for_legend)
                        ax.add_collection(lc)
                        plotted_something = True

                    for p_x, p_y in points:
                        current_entity_points_x.append(p_x)
                        current_entity_points_y.append(p_y)

            elif entity.dxftype() == 'POLYLINE':
                # For older POLYLINE entities, iterate through vertices
                points = [(v.dxf.location[0], v.dxf.location[1]) for v in entity.vertices]
                if points:
                    segments = []
                    for i in range(len(points) - 1):
                        segments.append([points[i], points[i + 1]])
                    if entity.is_closed and len(points) > 1:
                        segments.append([points[-1], points[0]])

                    if segments:
                        lc = mcollections.LineCollection(segments, label=label_for_legend)
                        ax.add_collection(lc)
                        plotted_something = True

                    for p_x, p_y in points:
                        current_entity_points_x.append(p_x)
                        current_entity_points_y.append(p_y)

            all_selected_points_x.extend(current_entity_points_x)
            all_selected_points_y.extend(current_entity_points_y)

    if plotted_something and all_selected_points_x and all_selected_points_y:
        min_x, max_x = min(all_selected_points_x), max(all_selected_points_x)
        min_y, max_y = min(all_selected_points_y), max(all_selected_points_y)

        width = max_x - min_x
        height = max_y - min_y

        # Add a margin (e.g., 10% of the span, or a fixed value if span is 0)
        margin_x = width * 0.1 if width > 0 else 10  # Adjust '10' as needed for your coordinate scale
        margin_y = height * 0.1 if height > 0 else 10  # Adjust '10' as needed

        ax.set_xlim(min_x - margin_x, max_x + margin_x)
        ax.set_ylim(min_y - margin_y, max_y + margin_y)
    elif plotted_something:  # Plotted something, but maybe no geometric points (e.g. only text, not handled here)
        ax.autoscale_view()  # Fallback to autoscale
    else:
        print("\nNo plottable entities (LINE, LWPOLYLINE, POLYLINE) found on the selected layers.")
        print("Displaying an empty plot with default axes.")
        ax.set_xlim(0, 100)  # Default view if nothing is plotted
        ax.set_ylim(0, 100)

    ax.set_xlabel('X coordinate')
    ax.set_ylabel('Y coordinate')
    ax.set_title(f'Selected Walls/Layers from: {dxf_filepath}')
    ax.grid(True)
    ax.set_aspect('equal', adjustable='box')

    if layers_with_legend_entry:  # Only show legend if there are items with labels
        ax.legend()

    plt.show()


def main():
    dxf_filepath = input("Enter the path to your DXF file (e.g., sample.dxf): ").strip()

    try:
        doc = ezdxf.readfile(dxf_filepath)
        msp = doc.modelspace()
    except IOError:
        print(f"Error: Cannot open DXF file '{dxf_filepath}'. Check path and permissions.")
        return
    except ezdxf.DXFStructureError:
        print(f"Error: Invalid or corrupted DXF file '{dxf_filepath}'.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the DXF file: {e}")
        return

    # Get all unique layer names from the modelspace entities that have a layer attribute
    all_layers = sorted(list(set(entity.dxf.layer
                                 for entity in msp
                                 if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'layer'))))

    if not all_layers:
        print("No layers found in the DXF file's modelspace.")
        return

    print("\nAvailable layers (interpreted as wall names):")
    for i, layer_name in enumerate(all_layers):
        print(f"  {i + 1}. {layer_name}")

    selected_layers_names = []
    while True:
        user_input = input(f"\nEnter the numbers of the layers you want to render (e.g., 1,3), "
                           f"or type 'all' to render all ({len(all_layers)} layers): ").strip().lower()

        if user_input == 'all':
            selected_layers_names = all_layers
            print(f"Selected all {len(all_layers)} layers.")
            break

        if not user_input:  # Empty input
            print("No selection. Please enter layer numbers or 'all'.")
            continue

        try:
            selected_indices = [int(i.strip()) - 1 for i in user_input.split(',')]

            temp_selected_layers = []
            valid_selection = True
            for index in selected_indices:
                if 0 <= index < len(all_layers):
                    temp_selected_layers.append(all_layers[index])
                else:
                    print(f"Error: Number {index + 1} is out of range (1 to {len(all_layers)}).")
                    valid_selection = False
                    break  # Stop processing this input string

            if valid_selection:
                # Use set to ensure uniqueness if user enters same number multiple times, then convert to list
                selected_layers_names = sorted(list(set(temp_selected_layers)))
                if selected_layers_names:
                    print(f"You selected layers: {', '.join(selected_layers_names)}")
                    break
                else:  # e.g. user entered numbers but they were all invalid or resulted in empty list after processing
                    print("No valid layers selected from your input. Please try again.")
            else:
                # An invalid index was found, loop again for new input
                pass

        except ValueError:
            print("Invalid input. Please enter numbers separated by commas (e.g., 1,3) or 'all'.")
        except Exception as e:  # Catch any other unexpected error during selection
            print(f"An error occurred during selection: {e}")

    if selected_layers_names:
        plot_selected_dxf_entities(msp, selected_layers_names, dxf_filepath)
    else:
        print("No layers were ultimately selected for rendering.")


if __name__ == "__main__":
    main()
