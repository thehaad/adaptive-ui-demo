"""Application-level validation of a layout dict against the component catalog."""

from collections import Counter

from components import ACTIONS, CATALOG, MAX_CHILDREN, OPTION_SETS


def validate_layout(layout: dict) -> list[str]:
    """Return a list of human-readable errors; empty means valid."""
    errors: list[str] = []
    root = layout.get("root")
    if not isinstance(root, dict):
        return ["layout.root must be an object"]
    if not CATALOG.get(root.get("component"), {}).get("container"):
        errors.append(f"root: must be a container ({sorted(n for n, s in CATALOG.items() if s['container'])})")

    leaves: list[dict] = []
    _validate_node(root, "root", errors, leaves)

    children = root.get("children") if isinstance(root.get("children"), list) else []
    for i, child in enumerate(children):
        if child.get("component") == "ActionButton" and i != len(children) - 1:
            errors.append(f"root.children[{i}]: ActionButton must be the last child")
    if root.get("component") == "Steps" and len(children) >= 2 and children[-1].get("component") == "ActionButton":
        if children[-2].get("component") != "PreferenceSelector":
            errors.append(
                "root.children: the last step before the completion button must be a PreferenceSelector"
            )

    actions = [n for n in leaves if n.get("component") == "ActionButton"]
    complete = [n for n in actions if isinstance(n.get("props"), dict) and n["props"].get("action") == "complete_onboarding"]
    if len(complete) != 1 or len(actions) != 1:
        errors.append(
            f"layout must contain exactly one ActionButton with action 'complete_onboarding' "
            f"(found {len(actions)} ActionButtons, {len(complete)} complete_onboarding)"
        )

    sets = Counter(
        n["props"].get("optionSet")
        for n in leaves
        if n.get("component") == "PreferenceSelector" and isinstance(n.get("props"), dict)
    )
    for name, count in sets.items():
        if count > 1:
            errors.append(f"option set {name!r} is used {count} times; use each at most once")
    return errors


def _validate_node(node: dict, path: str, errors: list[str], leaves: list[dict]) -> None:
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
    if not spec["container"]:
        leaves.append(node)
        if children:
            errors.append(f"{path}: {name} cannot have children")
        return

    if len(children) < spec["min_children"]:
        errors.append(f"{path}: {name} needs at least {spec['min_children']} children")
    if len(children) > MAX_CHILDREN:
        errors.append(f"{path}: {name} has more than {MAX_CHILDREN} children")
    for i, child in enumerate(children[:MAX_CHILDREN]):
        child_path = f"{path}.children[{i}]"
        if CATALOG.get(child.get("component"), {}).get("container"):
            errors.append(f"{child_path}: nested containers are not allowed")
        else:
            _validate_node(child, child_path, errors, leaves)


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
    if kind == "action":
        ok = isinstance(value, str) and value in ACTIONS
        return None if ok else f"must be one of the actions {sorted(ACTIONS)}"
    ok = isinstance(value, str) and value in OPTION_SETS
    return None if ok else f"must be one of the option sets {sorted(OPTION_SETS)}"
