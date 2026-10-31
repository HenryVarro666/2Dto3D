"""Equipment-specific schematic priors; these are not measured physical dimensions."""

STRING_INVERTER = {
    "cabinet": {"primitive": "box", "color": "#d5e0e9", "depth_ratio": 0.30, "z": 0.0},
    "bracket": {"primitive": "box", "color": "#738da0", "depth_ratio": 0.12, "z": -0.25},
    "pole": {"primitive": "cylinder", "color": "#536b80", "depth_ratio": 1.0, "z": -0.32},
    "cables": {"primitive": "cable_bundle", "color": "#394851", "depth_ratio": 0.35, "z": 0.22},
    "unknown": {"primitive": "box", "color": "#d3a96e", "depth_ratio": 0.15, "z": 0.0},
}
