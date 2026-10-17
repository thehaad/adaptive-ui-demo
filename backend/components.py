"""Catalog of components Claude may use. Mirrors the frontend registry (src/demo/registry.ts)."""

import json
from pathlib import Path

# Product Capability Manifest: shared with the Expo app (src/demo/capabilities.ts).
# Assumes backend and frontend live in the same repo.
OPTION_SETS: dict[str, dict] = json.loads(
    (Path(__file__).parent.parent / "capabilities.json").read_text()
)["optionSets"]

MAX_CHILDREN = 6

CATALOG = {
    "Row": {
        "description": "Container. Lays children out side by side when the screen is at least "
        "`breakpoint` px wide and `direction` is 'row'; otherwise stacks them.",
        "container": True,
        "props": {
            "direction": {"type": "enum", "values": ["row", "column"]},
            "breakpoint": {"type": "int", "min": 320, "max": 1200},
        },
    },
    "WelcomeCard": {
        "description": "A card with a heading and a short message, e.g. a motivational heading or a plan summary.",
        "container": False,
        "props": {
            "title": {"type": "str", "max_len": 80},
            "message": {"type": "str", "max_len": 240},
        },
    },
    "PreferenceSelector": {
        "description": "A labelled set of selectable option chips. The choices come from the host app's option set; never invent choices.",
        "container": False,
        "props": {
            "label": {"type": "str", "max_len": 80},
            "optionSet": {"type": "option_set"},
        },
    },
}


def catalog_prompt() -> str:
    lines = []
    for name, spec in CATALOG.items():
        props = ", ".join(f"{p}: {_describe(s)}" for p, s in spec["props"].items())
        lines.append(f"- {name}: {spec['description']} Props: {{{props}}}")
    return "\n".join(lines)


def _describe(spec: dict) -> str:
    kind = spec["type"]
    if kind == "enum":
        return " | ".join(f'"{v}"' for v in spec["values"])
    if kind == "int":
        return f"integer {spec['min']}-{spec['max']}"
    if kind == "str":
        return f"string (<= {spec['max_len']} chars)"
    sets = "; ".join(f'"{key}" ({", ".join(s["options"])})' for key, s in OPTION_SETS.items())
    return f"one of the host app's option sets: {sets}"
