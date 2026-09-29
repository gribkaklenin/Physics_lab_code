"""Qt-independent geometry for the Atwood machine drawing.
The geometry is kept separate from painting so edge cases (window resizing,
large travel distances, and ruler alignment) can be tested without a display.
Coordinates are integer pixels except for calculated mass positions.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_DISTANCE_CM = 100
RULER_MAX_CM = 100


@dataclass(frozen=True)
class MachineGeometry:
    width: int
    height: int
    stand_x: int
    pulley_y: int
    pulley_radius: int
    gate_y: int
    ruler_x: int
    pixels_per_cm: float
    block_width: int
    block_height: int
    left_x: int
    right_x: int
    top_clearance: int


@dataclass(frozen=True)
class MassPositions:
    start_lower_edge_y: float
    left_top_y: float
    left_lower_edge_y: float
    right_top_y: float
    right_lower_edge_y: float


def machine_geometry(width: int, height: int) -> MachineGeometry:
    """Return a fixed ruler scale that keeps both masses on the track.

    The scale is based on the largest allowed travel, not the selected H, so
    changing H cannot make the ruler itself stretch or move the masses into
    the pulley. The full 100 cm ruler remains visible in the drawing.
    """
    if width < 300 or height < 300:
        raise ValueError("Machine drawing area must be at least 300 by 300 px")

    stand_x = int(width * 0.50)
    pulley_y = max(54, int(height * 0.075))
    pulley_radius = max(24, min(42, int(min(width, height) * 0.04)))
    gate_y = height - 82
    block_width = max(44, min(104, int(width * 0.052)))
    block_height = max(46, min(76, int(height * 0.058)))
    top_clearance = pulley_y + pulley_radius + 14

    # h2 marks the lower edge of the right mass at the start. The two hanging
    # sections share a fixed 100 cm total length: z_right=H and
    # z_left=100-H, measured upward from h1. This lets the masses move
    # oppositely when H changes and keeps the full scale within the apparatus.
    pixels_per_cm = (
        gate_y - top_clearance - block_height
    ) / RULER_MAX_CM
    if pixels_per_cm <= 0:
        raise ValueError("Machine drawing area is too short for the ruler")

    left_x = stand_x - max(70, int(width * 0.14))
    right_x = stand_x + max(42, int(width * 0.10))
    # Leave space to the right of the scale for its H label and tick numbers.
    ruler_x = min(width - 110,
                  right_x + block_width + max(42, int(width * 0.05)))
    return MachineGeometry(
        width=width,
        height=height,
        stand_x=stand_x,
        pulley_y=pulley_y,
        pulley_radius=pulley_radius,
        gate_y=gate_y,
        ruler_x=ruler_x,
        pixels_per_cm=pixels_per_cm,
        block_width=block_width,
        block_height=block_height,
        left_x=left_x,
        right_x=right_x,
        top_clearance=top_clearance,
    )


def mass_positions(geometry: MachineGeometry, distance_cm: int,
                   progress: float) -> MassPositions:
    """Return block edges through a run; h2 attaches to the right block's bottom.

    At progress=0, the right block is H above h1 and the left block is
    (100-H) above h1. Their total rope length is constant. During the run they
    move equal distances in opposite directions; at the end, the right block
    reaches h1 and the left reaches the 100 cm mark.
    """
    if not 1 <= distance_cm <= MAX_DISTANCE_CM:
        raise ValueError(f"H must be between 1 and {MAX_DISTANCE_CM} cm")
    p = max(0.0, min(1.0, float(progress)))
    travel = distance_cm * geometry.pixels_per_cm
    start_lower = geometry.gate_y - travel
    left_lower = (geometry.gate_y
                  - (RULER_MAX_CM - distance_cm) * geometry.pixels_per_cm
                  - travel * p)
    right_lower = start_lower + travel * p
    block_h = geometry.block_height
    return MassPositions(
        start_lower_edge_y=start_lower,
        left_top_y=left_lower - block_h,
        left_lower_edge_y=left_lower,
        right_top_y=right_lower - block_h,
        right_lower_edge_y=right_lower,
    )
