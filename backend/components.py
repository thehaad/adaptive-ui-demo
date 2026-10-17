"""Catalog of components Claude may use. Mirrors the frontend registry (src/demo/registry.ts)."""

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
        "description": "A labelled set of selectable option chips, e.g. workout duration, focus area or training place.",
        "container": False,
        "props": {
            "label": {"type": "str", "max_len": 80},
            "options": {"type": "str_list", "min_items": 2, "max_items": 8, "max_len": 40},
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
    return f"list of {spec['min_items']}-{spec['max_items']} strings (<= {spec['max_len']} chars each)"
