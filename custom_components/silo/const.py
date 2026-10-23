"""Constants for the Silo integration."""

DOMAIN = "silo"

CONF_SOURCE = "source"

# The silo's options use Silo Card's option names, so the card can read them straight from the fill sensor.
SHAPE_KEYS = (
    "shape",
    "diameter",
    "rings",
    "ring_height",
    "top",
    "top_height",
    "bottom",
    "bottom_height",
    "outlet",
    "sensor_height",
)
CONTENTS_KEYS = (
    "grain",
    "density",
    "density_unit",
    "capacity",
    "capacity_per",
    "weight_unit",
    "volume_unit",
    "include_roof",
)
LENGTH_KEYS = ("diameter", "ring_height", "top_height", "bottom_height", "outlet", "sensor_height")

MEASURES = ("distance", "level")
LENGTH_UNITS = ("m", "cm", "ft", "in")
SHAPES = ("round", "square")
TOPS = ("cone", "dome", "flat")
BOTTOMS = ("flat", "cone")
DENSITY_UNITS = ("kg/m3", "kg/hL", "lb/bu", "lb/ft3")
WEIGHT_UNITS = ("t", "kg", "ton", "lb")
CAPACITY_PER = ("silo", "ring")
VOLUME_UNITS = ("m3", "L", "ft3", "bu")

DEFAULTS = {
    "measure": "distance",
    "unit": "m",
    "shape": "round",
    "rings": 1,
    "top": "cone",
    "top_height": 0,
    "bottom": "flat",
    "bottom_height": 0,
    "outlet": 0,
    "density_unit": "kg/m3",
    "capacity_per": "silo",
    "weight_unit": "t",
    "volume_unit": "m3",
    "include_roof": False,
}
