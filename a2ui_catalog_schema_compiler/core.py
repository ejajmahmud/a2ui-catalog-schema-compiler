"""Core declarative A2UI schema validator and safe fallback compiler."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


class A2UIValidationError(Exception):
    """Raised when an A2UI surface fails strict compilation."""


@dataclass
class ComponentSpec:
    name: str
    required_props: Set[str] = field(default_factory=set)
    optional_props: Set[str] = field(default_factory=set)
    allow_children: bool = True


DEFAULT_CATALOG = {
    "Card": ComponentSpec("Card", required_props={"title"}, optional_props={"subtitle", "elevation"}),
    "Text": ComponentSpec("Text", required_props={"text"}, optional_props={"variant", "color"}, allow_children=False),
    "Button": ComponentSpec("Button", required_props={"label", "actionId"}, optional_props={"variant", "disabled"}, allow_children=False),
    "Table": ComponentSpec("Table", required_props={"columns", "rows"}, optional_props={"caption"}, allow_children=False),
    "Stack": ComponentSpec("Stack", required_props=set(), optional_props={"direction", "gap"}),
}

FORBIDDEN_TOKENS = ("<script", "javascript:", "onerror=", "onload=")


class A2UICompiler:
    """Validates and compiles declarative A2UI payloads against a strict component catalog."""

    def __init__(self, catalog: Dict[str, ComponentSpec] = None, max_depth: int = 12):
        self.catalog = dict(catalog or DEFAULT_CATALOG)
        self.max_depth = max_depth

    def _contains_unsafe_markup(self, value: Any) -> bool:
        if isinstance(value, str):
            low = value.lower()
            return any(tok in low for tok in FORBIDDEN_TOKENS)
        if isinstance(value, list):
            return any(self._contains_unsafe_markup(v) for v in value)
        if isinstance(value, dict):
            return any(self._contains_unsafe_markup(v) for v in value.values())
        return False

    def validate_node(self, node: Dict[str, Any], all_nodes: Dict[str, Dict[str, Any]], depth: int = 0, visited: Set[str] = None) -> List[str]:
        errors: List[str] = []
        visited = visited or set()
        if depth > self.max_depth:
            return [f"Max UI nesting depth {self.max_depth} exceeded"]

        node_id = node.get("id", "<missing>")
        if node_id in visited:
            return [f"Cycle detected at node {node_id}"]
        visited = visited | {node_id}

        comp_name = node.get("component")
        if comp_name not in self.catalog:
            errors.append(f"Unknown component '{comp_name}' in node '{node_id}'")
            return errors

        spec = self.catalog[comp_name]
        props = node.get("props", {})
        if not isinstance(props, dict):
            errors.append(f"Props must be a dict on node '{node_id}'")
            return errors

        if self._contains_unsafe_markup(props):
            errors.append(f"Unsafe markup or script pattern detected in node '{node_id}'")

        missing = spec.required_props - set(props.keys())
        if missing:
            errors.append(f"Node '{node_id}' ({comp_name}) missing required props: {sorted(missing)}")

        allowed = spec.required_props | spec.optional_props
        unknown = set(props.keys()) - allowed
        if unknown:
            errors.append(f"Node '{node_id}' ({comp_name}) has unknown props: {sorted(unknown)}")

        children = node.get("children", [])
        if children and not spec.allow_children:
            errors.append(f"Node '{node_id}' ({comp_name}) does not allow children")
        for child_id in children:
            if child_id not in all_nodes:
                errors.append(f"Missing child node '{child_id}' referenced by '{node_id}'")
            else:
                errors.extend(self.validate_node(all_nodes[child_id], all_nodes, depth + 1, visited))
        return errors

    def compile(self, payload: Dict[str, Any], fallback_on_error: bool = True) -> Dict[str, Any]:
        root = payload.get("root")
        nodes = dict(payload.get("nodes", {}))
        if not isinstance(root, dict):
            errors = ["Missing root component dictionary"]
        else:
            nodes[root.get("id", "__root__")] = root
            errors = self.validate_node(root, nodes)

        if errors:
            if not fallback_on_error:
                raise A2UIValidationError("; ".join(errors))
            return {
                "surfaceId": payload.get("surfaceId", "fallback"),
                "valid": False,
                "errors": errors,
                "nodeCount": 2,
                "compiledRoot": {
                    "id": "fallback-card",
                    "component": "Card",
                    "props": {"title": "Safe Fallback Surface"},
                    "children": ["fallback-text"],
                },
                "nodes": {
                    "fallback-text": {
                        "id": "fallback-text",
                        "component": "Text",
                        "props": {"text": f"Blocked invalid UI payload ({len(errors)} issue(s))."},
                    }
                },
            }

        return {
            "surfaceId": payload.get("surfaceId", "default"),
            "valid": True,
            "errors": [],
            "nodeCount": len(nodes),
            "compiledRoot": root,
            "nodes": nodes,
        }
