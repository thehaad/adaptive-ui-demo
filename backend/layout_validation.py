"""Application-level validation of a layout dict against the component catalog."""

from components import CATALOG, MAX_CHILDREN


def validate_layout(layout: dict) -> list[str]:
    """Return a list of human-readable errors; empty means valid."""
    errors: list[str] = []
    root = layout.get("root")
    if not isinstance(root, dict):
        return ["layout.root must be an object"]
    _validate_node(root, "root", errors, depth=0)
    return errors


def _validate_node(node: dict, path: str, errors: list[str], depth: int) -> None:
    name = node.get("component")
    spec = CATALOG.get(name)
    if spec is None:
        errors.append(f"{path}: unknown component {name!r}; allowed: {sorted(CATALOG)}")
        return

    props = node.get("props", {})
    if not isinstance(props, dict):
        errors.append(f"{path}: props must be an object")
        props = {}
    for key in props:
        if key not in spec["props"]:
            errors.append(f"{path}: {name} has no prop {key!r}")
    for key, rule in spec["props"].items():
        if key not in props:
            errors.append(f"{path}: {name} is missing prop {key!r}")
        else:
            error = _check_prop(props[key], rule)
            if error:
                errors.append(f"{path}.props.{key}: {error}")

    children = node.get("children", [])
    if children and not spec["container"]:
        errors.append(f"{path}: {name} cannot have children")
    elif spec["container"]:
        if not children:
            errors.append(f"{path}: {name} needs at least one child")
        if len(children) > MAX_CHILDREN:
            errors.append(f"{path}: {name} has more than {MAX_CHILDREN} children")
        for i, child in enumerate(children[:MAX_CHILDREN]):
            if depth >= 1:
                errors.append(f"{path}.children[{i}]: nesting deeper than one level is not allowed")
            elif child.get("component") == "Row":
                errors.append(f"{path}.children[{i}]: nested Row is not allowed")
            else:
                _validate_node(child, f"{path}.children[{i}]", errors, depth + 1)


def _check_prop(value, rule: dict) -> str | None:
    kind = rule["type"]
    if kind == "enum":
        return None if value in rule["values"] else f"must be one of {rule['values']}"
    if kind == "int":
        ok = isinstance(value, int) and not isinstance(value, bool) and rule["min"] <= value <= rule["max"]
        return None if ok else f"must be an integer {rule['min']}-{rule['max']}"
    if kind == "str":
        ok = isinstance(value, str) and 0 < len(value.strip()) and len(value) <= rule["max_len"]
        return None if ok else f"must be a non-empty string of at most {rule['max_len']} characters"
    ok = (
        isinstance(value, list)
        and rule["min_items"] <= len(value) <= rule["max_items"]
        and all(isinstance(v, str) and 0 < len(v.strip()) <= rule["max_len"] for v in value)
    )
    return None if ok else (
        f"must be a list of {rule['min_items']}-{rule['max_items']} non-empty strings "
        f"of at most {rule['max_len']} characters"
    )
