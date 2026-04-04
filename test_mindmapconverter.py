import unittest
import xml.etree.ElementTree as ET
from mindmapconverter import MindMapConverter

class TestMindMapConverter(unittest.TestCase):
    def setUp(self):
        self.converter = MindMapConverter()

    def test_freemind_to_plantuml(self):
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="Child 1"/>
<node TEXT="Child 2">
<node TEXT="Grandchild"/>
</node>
</node>
</map>"""
        expected_puml = """@startmindmap
* Root
** Child 1
** Child 2
*** Grandchild
@endmindmap"""
        result = self.converter.freemind_to_plantuml(xml_content)
        self.assertEqual(result.strip(), expected_puml.strip())

    def test_plantuml_to_freemind_standard(self):
        puml_content = """@startmindmap
* Root
** Child 1
** Child 2
*** Grandchild
@endmindmap"""

        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)

        self.assertEqual(root.tag, 'map')
        # Check structure
        # map -> node(Root) -> [node(Child 1), node(Child 2) -> node(Grandchild)]
        root_node = root.find("node")
        self.assertIsNotNone(root_node)
        self.assertEqual(root_node.get("TEXT"), "Root")

        children = root_node.findall("node")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "Child 1")
        self.assertEqual(children[1].get("TEXT"), "Child 2")

        grandchild = children[1].find("node")
        self.assertIsNotNone(grandchild)
        self.assertEqual(grandchild.get("TEXT"), "Grandchild")

    def test_plantuml_to_freemind_legacy_underscore(self):
        puml_content = """@startmindmap
*_ Root
**_ Child 1
**_ Child 2
***_ Grandchild
@endmindmap"""

        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)

        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        children = root_node.findall("node")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "Child 1")

    def test_invalid_plantuml(self):
        puml_content = "Invalid content"
        with self.assertRaises(ValueError):
            self.converter.plantuml_to_freemind(puml_content)

    def test_plantuml_with_comments_and_spaces(self):
        puml_content = """@startmindmap
' This is a comment
  * Root
    ** Child 1
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        child = root_node.find("node")
        self.assertEqual(child.get("TEXT"), "Child 1")

    def test_plantuml_multiline(self):
        puml_content = """@startmindmap
* Root
** :Child line 1
Child line 2;
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        self.assertIn("Child line 1", child.get("TEXT"))
        self.assertIn("Child line 2", child.get("TEXT"))
        self.assertIn("\n", child.get("TEXT"))

    def test_freemind_multiline_to_plantuml(self):
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="Line 1&#10;Line 2"/>
</node>
</map>"""
        puml_output = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn("** :Line 1", puml_output)
        self.assertIn("Line 2;", puml_output)

    def test_hyperlinks_plantuml_to_freemind(self):
        puml_content = """@startmindmap
* [[http://example.com Link]]
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        node = root.find("node")
        self.assertEqual(node.get("TEXT"), "Link")
        hook = node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("NAME"), "ExternalObject")
        self.assertEqual(hook.get("URI"), "http://example.com")

    def test_hyperlinks_freemind_to_plantuml(self):
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Link">
<hook URI="http://example.com"/>
</node>
</map>"""
        puml_output = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn("* [[http://example.com Link]]", puml_output)

    def test_robust_regex_extra_spaces(self):
        puml_content = """@startmindmap
  *   Root
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        self.assertEqual(root.find("node").get("TEXT"), "Root")

    def test_single_line_multiline_node(self):
        """Single-line multiline syntax `:text;` must not loop and must strip the semicolon."""
        puml_content = """@startmindmap
* Root
** :Single line;
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        self.assertIsNotNone(child)
        self.assertEqual(child.get("TEXT"), "Single line")

    def test_reversed_markers_invalid(self):
        """@endmindmap appearing before @startmindmap must raise ValueError."""
        puml_content = """@endmindmap
* Root
@startmindmap"""
        with self.assertRaises(ValueError):
            self.converter.plantuml_to_freemind(puml_content)

    def test_skipped_hierarchy_levels(self):
        """Jumping from level 1 directly to level 3 should attach the deep node under root."""
        puml_content = """@startmindmap
* Root
*** Deep
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        # Deep node should exist somewhere in the tree
        all_nodes = root_node.iter("node")
        texts = [n.get("TEXT") for n in all_nodes]
        self.assertIn("Deep", texts)

    def test_xml_special_characters_roundtrip(self):
        """Node text containing XML special characters should survive a roundtrip."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="A &amp; B &lt;tag&gt;"/>
</map>"""
        puml_output = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn("A & B <tag>", puml_output)

    def _extract_tree(self, element: ET.Element):
        """Recursively extract (TEXT, [children]) from an XML node element."""
        return (element.get("TEXT"), [self._extract_tree(c) for c in element.findall("node")])

    def test_roundtrip_mm_to_puml_to_mm(self):
        """A 3-level Freemind map survives a .mm → .puml → .mm roundtrip with identical structure."""
        original_xml = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="Child 1"/>
<node TEXT="Child 2">
<node TEXT="Grandchild"/>
</node>
</node>
</map>"""
        puml = self.converter.freemind_to_plantuml(original_xml)
        roundtripped_xml = self.converter.plantuml_to_freemind(puml)

        original_root = ET.fromstring(original_xml).find("node")
        roundtripped_root = ET.fromstring(roundtripped_xml).find("node")
        self.assertEqual(self._extract_tree(original_root), self._extract_tree(roundtripped_root))

    def test_empty_map_to_plantuml(self):
        """An empty Freemind map produces exactly @startmindmap\\n@endmindmap."""
        xml_content = '<map version="freeplane 1.9.13" />'
        result = self.converter.freemind_to_plantuml(xml_content)
        self.assertEqual(result.strip(), "@startmindmap\n@endmindmap")

    def test_empty_plantuml_to_map(self):
        """An empty PlantUML mindmap produces a <map> with zero child nodes."""
        puml_content = "@startmindmap\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        self.assertEqual(root.tag, "map")
        self.assertEqual(len(root.findall("node")), 0)

    def test_content_before_startmindmap_is_ignored(self):
        """Lines before @startmindmap must not produce nodes."""
        puml_content = """* Intruder
@startmindmap
* Root
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        all_texts = [n.get("TEXT") for n in root.iter("node")]
        self.assertNotIn("Intruder", all_texts)

    def test_content_after_endmindmap_is_ignored(self):
        """Lines after @endmindmap must not produce nodes."""
        puml_content = """@startmindmap
* Root
@endmindmap
* Trailer"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        all_texts = [n.get("TEXT") for n in root.iter("node")]
        self.assertNotIn("Trailer", all_texts)

    def test_unterminated_multiline_raises_value_error(self):
        """A multiline node with no closing ';' must raise ValueError."""
        puml_content = """@startmindmap
* Root
** :Line 1
Line 2
@endmindmap"""
        with self.assertRaises(ValueError) as ctx:
            self.converter.plantuml_to_freemind(puml_content)
        self.assertIn("Unterminated", str(ctx.exception))

    def test_multiline_continuation_leading_whitespace_stripped(self):
        """Leading whitespace on multiline continuation lines must be stripped."""
        puml_content = """@startmindmap
* Root
** :Line 1
    indented continuation;
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        self.assertIn("Line 1", child.get("TEXT"))
        self.assertIn("indented continuation", child.get("TEXT"))
        self.assertNotIn("    indented", child.get("TEXT"))

    # ---- Markdown ↔ Freemind tests ----

    def test_freemind_to_markdown_basic(self):
        """Basic Freemind XML converts to Markdown with H1 and nested lists."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="Child 1"/>
<node TEXT="Child 2">
<node TEXT="Grandchild"/>
</node>
</node>
</map>"""
        result = self.converter.freemind_to_markdown(xml_content)
        expected = "# Root\n- Child 1\n- Child 2\n  - Grandchild"
        self.assertEqual(result, expected)

    def test_markdown_to_freemind_basic(self):
        """Basic Markdown with H1 and nested lists converts to Freemind XML."""
        md_content = "# Root\n- Child 1\n- Child 2\n  - Grandchild"
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        self.assertEqual(root.tag, "map")
        root_node = root.find("node")
        self.assertIsNotNone(root_node)
        self.assertEqual(root_node.get("TEXT"), "Root")
        children = root_node.findall("node")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "Child 1")
        self.assertEqual(children[1].get("TEXT"), "Child 2")
        grandchild = children[1].find("node")
        self.assertIsNotNone(grandchild)
        self.assertEqual(grandchild.get("TEXT"), "Grandchild")

    def test_freemind_to_markdown_links(self):
        """Freemind hyperlinks are rendered as [text](url) in Markdown."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="My Link">
<hook URI="http://example.com"/>
</node>
</node>
</map>"""
        result = self.converter.freemind_to_markdown(xml_content)
        self.assertIn("[My Link](http://example.com)", result)

    def test_freemind_to_markdown_link_text_equals_url(self):
        """When TEXT equals the URI, Markdown still renders as [url](url)."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="http://example.com">
<hook URI="http://example.com"/>
</node>
</map>"""
        result = self.converter.freemind_to_markdown(xml_content)
        self.assertIn("[http://example.com](http://example.com)", result)

    def test_markdown_to_freemind_links(self):
        """Markdown [text](url) links convert to Freemind hook elements."""
        md_content = "# Root\n- [My Link](http://example.com)"
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        link_node = root.find("node").find("node")
        self.assertEqual(link_node.get("TEXT"), "My Link")
        hook = link_node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("URI"), "http://example.com")

    def test_markdown_to_freemind_special_chars(self):
        """XML special characters in Markdown survive conversion."""
        md_content = "# A & B\n- C < D\n- E > F"
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "A & B")
        children = root_node.findall("node")
        self.assertEqual(children[0].get("TEXT"), "C < D")
        self.assertEqual(children[1].get("TEXT"), "E > F")

    def test_freemind_to_markdown_special_chars(self):
        """XML special characters in Freemind survive conversion to Markdown."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="A &amp; B &lt;tag&gt;"/>
</map>"""
        result = self.converter.freemind_to_markdown(xml_content)
        self.assertIn("A & B <tag>", result)

    def test_markdown_to_freemind_deep_nesting(self):
        """5+ levels of nesting are handled correctly."""
        md_content = (
            "# Root\n"
            "- Level 1\n"
            "  - Level 2\n"
            "    - Level 3\n"
            "      - Level 4\n"
            "        - Level 5\n"
        )
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        # Walk the tree: Root -> L1 -> L2 -> L3 -> L4 -> L5
        node = root.find("node")
        for expected in ["Root", "Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]:
            self.assertIsNotNone(node, f"Expected node '{expected}' not found")
            self.assertEqual(node.get("TEXT"), expected)
            children = node.findall("node")
            node = children[0] if children else None

    def test_freemind_to_markdown_deep_nesting(self):
        """5+ levels of nesting produce correct indentation."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="L1">
<node TEXT="L2">
<node TEXT="L3">
<node TEXT="L4">
<node TEXT="L5"/>
</node>
</node>
</node>
</node>
</node>
</map>"""
        result = self.converter.freemind_to_markdown(xml_content)
        lines = result.split("\n")
        self.assertEqual(lines[0], "# Root")
        self.assertEqual(lines[1], "- L1")
        self.assertEqual(lines[2], "  - L2")
        self.assertEqual(lines[3], "    - L3")
        self.assertEqual(lines[4], "      - L4")
        self.assertEqual(lines[5], "        - L5")

    def test_markdown_to_freemind_different_markers(self):
        """All three list markers (-, *, +) are accepted."""
        md_content = "# Root\n- Dash\n* Star\n+ Plus"
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        children = root.find("node").findall("node")
        self.assertEqual(len(children), 3)
        self.assertEqual(children[0].get("TEXT"), "Dash")
        self.assertEqual(children[1].get("TEXT"), "Star")
        self.assertEqual(children[2].get("TEXT"), "Plus")

    def test_markdown_to_freemind_no_h1_raises(self):
        """Missing H1 header in Markdown raises ValueError."""
        md_content = "- Just a list\n- No header"
        with self.assertRaises(ValueError) as ctx:
            self.converter.markdown_to_freemind(md_content)
        self.assertIn("No H1 header", str(ctx.exception))

    def test_freemind_to_markdown_multiline(self):
        """Multiline node text uses <br> in Markdown output."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="Line 1&#10;Line 2"/>
</node>
</map>"""
        result = self.converter.freemind_to_markdown(xml_content)
        self.assertIn("Line 1<br>Line 2", result)

    def test_markdown_to_freemind_br_tags(self):
        """<br> tags in Markdown list items convert to newlines in Freemind."""
        md_content = "# Root\n- Line 1<br>Line 2"
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        self.assertEqual(child.get("TEXT"), "Line 1\nLine 2")

    def test_freemind_to_markdown_empty_map(self):
        """An empty Freemind map produces an empty string."""
        xml_content = '<map version="freeplane 1.9.13" />'
        result = self.converter.freemind_to_markdown(xml_content)
        self.assertEqual(result, "")

    def test_markdown_to_freemind_mixed_indentation(self):
        """Different indentation widths (2 and 4 spaces) are handled."""
        md_content = "# Root\n- A\n    - B\n        - C"
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        a_node = root.find("node").find("node")
        self.assertEqual(a_node.get("TEXT"), "A")
        b_node = a_node.find("node")
        self.assertIsNotNone(b_node)
        self.assertEqual(b_node.get("TEXT"), "B")
        c_node = b_node.find("node")
        self.assertIsNotNone(c_node)
        self.assertEqual(c_node.get("TEXT"), "C")

    def test_roundtrip_mm_to_md_to_mm(self):
        """A Freemind map survives a .mm → .md → .mm roundtrip with identical structure."""
        original_xml = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="Child 1"/>
<node TEXT="Child 2">
<node TEXT="Grandchild"/>
</node>
</node>
</map>"""
        md = self.converter.freemind_to_markdown(original_xml)
        roundtripped_xml = self.converter.markdown_to_freemind(md)

        original_root = ET.fromstring(original_xml).find("node")
        roundtripped_root = ET.fromstring(roundtripped_xml).find("node")
        self.assertEqual(self._extract_tree(original_root), self._extract_tree(roundtripped_root))

    def test_roundtrip_md_to_mm_to_md(self):
        """Markdown content survives a .md → .mm → .md roundtrip."""
        original_md = "# Root\n- Child 1\n- Child 2\n  - Grandchild"
        xml = self.converter.markdown_to_freemind(original_md)
        roundtripped_md = self.converter.freemind_to_markdown(xml)
        self.assertEqual(original_md, roundtripped_md)

    def test_roundtrip_md_links_to_mm_to_md(self):
        """Markdown with links survives a roundtrip."""
        original_md = "# Root\n- [Example](http://example.com)\n- Plain text"
        xml = self.converter.markdown_to_freemind(original_md)
        roundtripped_md = self.converter.freemind_to_markdown(xml)
        self.assertEqual(original_md, roundtripped_md)

    def test_markdown_to_freemind_blank_lines_ignored(self):
        """Blank lines in Markdown input are ignored."""
        md_content = "# Root\n\n- Child 1\n\n- Child 2\n"
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        children = root.find("node").findall("node")
        self.assertEqual(len(children), 2)

    def test_markdown_to_freemind_siblings_at_same_indent(self):
        """Multiple siblings at the same indentation level are all children of the same parent."""
        md_content = "# Root\n- A\n  - A1\n  - A2\n  - A3"
        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        a_node = root.find("node").find("node")
        self.assertEqual(a_node.get("TEXT"), "A")
        grandchildren = a_node.findall("node")
        self.assertEqual(len(grandchildren), 3)
        self.assertEqual(grandchildren[0].get("TEXT"), "A1")
        self.assertEqual(grandchildren[1].get("TEXT"), "A2")
        self.assertEqual(grandchildren[2].get("TEXT"), "A3")

if __name__ == '__main__':
    unittest.main()
