# wall_detector/wall_classifier.py
"""
This module classifies wall candidates by type based on labels, layer names,
or geometric properties (like thickness).
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict

# Use TYPE_CHECKING to avoid runtime import error if shapely is not installed
# For actual use, shapely is a dependency.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shapely.geometry import Polygon

# Assuming geometry_utils will be in the same package or sys.path is configured
try:
    from . import geometry_utils  # Relative import if part of a package
except ImportError:
    import geometry_utils  # Fallback for standalone execution (like temp_main.py)


@dataclass
class Wall:
    """
    Represents a detected and classified wall.
    """
    id: str
    geometry: Any  # shapely.geometry.Polygon; using Any for broader compatibility in stub
    raw_label: Optional[str]
    layer_name: str
    type_name: Optional[str] = None
    assigned_rule: Optional[str] = None
    thickness: Optional[float] = None
    # Add other relevant fields like coordinates if processed here
    # For example:
    # centroid: Optional[Tuple[float,float]] = field(default=None, init=False)
    # bounds: Optional[Tuple[float,float,float,float]] = field(default=None, init=False)

    # def __post_init__(self):
    #     if self.geometry:
    #         self.centroid = geometry_utils.get_polygon_centroid(self.geometry)
    #         self.bounds = geometry_utils.get_polygon_bounds(self.geometry)


def classify_walls(
        candidates: List[Wall],
        legend_dict: Dict[str, Dict[str, Any]],
        thickness_tolerance: float = 1.0  # e.g., +/- 1mm for thickness comparison
) -> List[Wall]:
    """
    Classifies a list of wall candidates based on a legend dictionary.

    The legend_dict is assumed to have entries where keys can be:
    1. Specific text labels found in CAD (e.g., "B-01"). The value dict
       would contain {"name": "Wall Type Name"}.
    2. Generic rule identifiers (e.g., "GeneralLoadBearingLayerRule"). The value dict
       could contain {"name": "Wall Type Name", "layer_pattern": "REGEX",
                      "thickness_min": float, "thickness_max": float}.

    Classification order:
    1. Direct Text Label Matching.
    2. Layer-based classification.
    3. Thickness-based rules.
    4. Default to 'Unknown'.

    Args:
        candidates: A list of Wall dataclass objects.
        legend_dict: A dictionary containing classification rules.
                     Example:
                     {
                         "B-01": {"name": "Load-Bearing Wall"}, // Label rule
                         "PartitionRuleLayer": {"name": "Partition Wall", "layer_pattern": "^WALL_P.*"},
                         "ShearWallRuleThick": {"name": "Shear Wall", "thickness_min": 150, "thickness_max": 250}
                     }
        thickness_tolerance: Tolerance for comparing thicknesses.

    Returns:
        The list of Wall objects with updated `type_name` and `assigned_rule` fields.
    """
    for wall in candidates:
        classified = False

        # 1. Direct Text Label Matching
        if wall.raw_label and wall.raw_label in legend_dict:
            rule_details = legend_dict[wall.raw_label]
            # Check if this rule is primarily for labels (optional: add a flag in legend_dict)
            # For now, assume any key match is a label match if raw_label exists.
            wall.type_name = rule_details.get("name", "Unknown type for label")
            wall.assigned_rule = f"label: {wall.raw_label}"
            classified = True
            # If thickness is defined for this label, store it
            if wall.thickness is None and "thickness" in rule_details:
                wall.thickness = rule_details["thickness"]
            elif wall.thickness is None:  # If not in rule, compute if geometry exists
                if wall.geometry:
                    wall.thickness = geometry_utils.compute_thickness(wall.geometry)

        # 2. Layer-based classification (if not classified by label)
        if not classified:
            for rule_key, rule_details in legend_dict.items():
                if "layer_pattern" in rule_details:
                    pattern = rule_details["layer_pattern"]
                    try:
                        if re.match(pattern, wall.layer_name, re.IGNORECASE):
                            wall.type_name = rule_details.get("name", f"Unknown type for layer pattern {pattern}")
                            wall.assigned_rule = f"layer: {wall.layer_name} (matches {pattern})"
                            classified = True
                            if wall.thickness is None and wall.geometry:  # Compute thickness if not already set
                                wall.thickness = geometry_utils.compute_thickness(wall.geometry)
                            break
                    except re.error:
                        print(f"Warning: Invalid regex pattern in legend: {pattern}")
                        continue

        # 3. Thickness-based rules (if not classified by label or layer)
        if not classified:
            if wall.thickness is None and wall.geometry:  # Ensure thickness is computed
                wall.thickness = geometry_utils.compute_thickness(wall.geometry)

            if wall.thickness is not None:
                for rule_key, rule_details in legend_dict.items():
                    # Ensure this rule is intended for thickness-based classification
                    # (i.e., not a label-specific entry being misused)
                    # This check might be refined by adding specific flags to rule_details
                    # For now, if it has thickness_min or thickness_max, it's a candidate.

                    has_min = "thickness_min" in rule_details
                    has_max = "thickness_max" in rule_details

                    if has_min or has_max:  # This rule involves thickness
                        t_min = rule_details.get("thickness_min", float('-inf'))
                        t_max = rule_details.get("thickness_max", float('inf'))

                        # Apply tolerance: wall.thickness should be in [t_min - tol, t_max + tol)
                        # Or more strictly: [t_min, t_max) then check with tolerance
                        # Let's use: (t_min - tol) <= wall.thickness < (t_max + tol)

                        min_check = (wall.thickness >= t_min - thickness_tolerance) if has_min else True
                        # Max check usually exclusive for upper bound, but legend might vary
                        # Assume [min, max) interval for legend.
                        max_check = (wall.thickness < t_max + thickness_tolerance) if has_max else True

                        if min_check and max_check:
                            # Avoid re-classifying if a more specific thickness rule (e.g., from label) existed
                            # This logic gets complex if legend has overlapping thickness rules.
                            # Simplification: first matching thickness rule applies.
                            wall.type_name = rule_details.get("name", f"Unknown type for thickness {wall.thickness}")
                            wall.assigned_rule = f"thickness: {wall.thickness:.2f} (range {t_min}-{t_max})"
                            classified = True
                            break

        # 4. Default to 'Unknown'
        if not classified:
            wall.type_name = "Unknown"
            wall.assigned_rule = "unclassified"
            if wall.thickness is None and wall.geometry:  # Compute thickness for 'Unknown' walls too for record
                wall.thickness = geometry_utils.compute_thickness(wall.geometry)

    return candidates

