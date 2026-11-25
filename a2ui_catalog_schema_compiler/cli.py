"""CLI for A2UI Catalog Schema Compiler."""
import argparse
import json
from .core import A2UICompiler


def main():
    parser = argparse.ArgumentParser(description="A2UI Catalog Schema Compiler CLI")
    parser.add_argument("--input", help="Path to A2UI JSON payload")
    parser.add_argument("--demo", action="store_true", help="Compile a sample A2UI surface")
    args = parser.parse_args()

    compiler = A2UICompiler()
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = {
            "surfaceId": "demo-surface",
            "root": {"id": "root", "component": "Card", "props": {"title": "Agent Output"}, "children": ["msg"]},
            "nodes": {"msg": {"id": "msg", "component": "Text", "props": {"text": "Ready for review"}}},
        }
    print(json.dumps(compiler.compile(payload), indent=2))


if __name__ == "__main__":
    main()
