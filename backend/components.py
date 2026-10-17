"""Catalog of components Claude may use. Mirrors the frontend registry (src/demo/registry.ts)."""

import json
from pathlib import Path

# Product Capability Manifest: shared with the Expo app (src/demo/capabilities.ts).
# Assumes backend and frontend live in the same repo.
_MANIFEST = json.loads((Path(__file__).parent.parent / "capabilities.json").read_text())
OPTION_SETS: dict[str, dict] = _MANIFEST["optionSets"]
ACTIONS: dict[str, dict] = _MANIFEST["actions"]

DENSITIES = ["comfortable", "compact"]

MAX_CHILDREN = 6

CATALOG = {
    "Row": {
        "description": "Container that shows all its children at once. Lays them side by side when the "
        "screen is at least `breakpoint` px wide and `direction` is 'row'; otherwise stacks them.",
        "container": True,
        "min_children": 1,
        "props": {
            "direction": {"type": "enum", "values": ["row", "column"]},
            "breakpoint": {"type": "int", "min": 320, "max": 1200},
            "density": {"type": "enum", "values": DENSITIES},
        },
    },
    "Steps": {
        "description": "Container that shows ONE child at a time with Back/Next buttons and a progress "
        "indicator; each child is one step. The completion ActionButton (last child) is not a step: it "
        "is shown beside the last step, which must be a PreferenceSelector.",
        "container": True,
        "min_children": 3,  # at least 2 steps + the completion ActionButton
        "props": {"density": {"type": "enum", "values": DENSITIES}},
    },
    "WelcomeCard": {
        "description": "A card with a heading and a short message, e.g. a motivational heading, an "
        "explanation of the next question, or a plan summary.",
        "container": False,
        "props": {
            "title": {"type": "str", "max_len": 80},
            "message": {"type": "str", "max_len": 240},
        },
    },
    "PreferenceSelector": {
        "description": "A labelled set of selectable option chips. The choices come from the host app's "
        "option set; never invent choices.",
        "container": False,
        "props": {
            "label": {"type": "str", "max_len": 80},
            "optionSet": {"type": "option_set"},
        },
    },
    "ActionButton": {
        "description": "A button that triggers a host-app action. Exactly one is required, as the last "
        "child: the complete_onboarding button that finishes onboarding.",
        "container": False,
        "props": {
            "label": {"type": "str", "max_len": 40},
            "action": {"type": "action"},
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
    if kind == "action":
        actions = "; ".join(f'"{key}" ({a["description"]})' for key, a in ACTIONS.items())
        return f"one of the host app's actions: {actions}"
    sets = "; ".join(
        f'"{key}" ({o["description"]}: {", ".join(o["options"])})' for key, o in OPTION_SETS.items()
    )
    return f"one of the host app's option sets: {sets}"
