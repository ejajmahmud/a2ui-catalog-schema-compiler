"""Tests for A2UI Catalog Schema Compiler."""
import unittest
from a2ui_catalog_schema_compiler.core import A2UICompiler, A2UIValidationError


class TestA2UICompiler(unittest.TestCase):
    def setUp(self):
        self.compiler = A2UICompiler()

    def test_valid_surface_compiles(self):
        res = self.compiler.compile({
            "surfaceId": "s1",
            "root": {"id": "r", "component": "Card", "props": {"title": "Summary"}, "children": ["b"]},
            "nodes": {"b": {"id": "b", "component": "Button", "props": {"label": "Approve", "actionId": "ok"}}},
        })
        self.assertTrue(res["valid"])
        self.assertEqual(res["nodeCount"], 2)

    def test_blocks_xss_prop_with_fallback(self):
        res = self.compiler.compile({
            "surfaceId": "s2",
            "root": {"id": "r", "component": "Card", "props": {"title": "<script>alert(1)</script>"}},
            "nodes": {},
        })
        self.assertFalse(res["valid"])
        self.assertEqual(res["compiledRoot"]["id"], "fallback-card")

    def test_rejects_unknown_component_strict(self):
        with self.assertRaises(A2UIValidationError):
            self.compiler.compile(
                {"root": {"id": "r", "component": "RawIframe", "props": {}}},
                fallback_on_error=False,
            )

    def test_detects_cycle(self):
        res = self.compiler.compile({
            "root": {"id": "a", "component": "Stack", "props": {}, "children": ["b"]},
            "nodes": {"b": {"id": "b", "component": "Stack", "props": {}, "children": ["a"]}},
        })
        self.assertFalse(res["valid"])
        self.assertTrue(any("Cycle" in err for err in res["errors"]))
