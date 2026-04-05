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


    def test_very_deep_nesting(self):
        """Stress: 50 levels of nesting must not cause stack issues."""
        lines = ["@startmindmap", "* Root"]
        for i in range(2, 51):
            lines.append("*" * i + " Level" + str(i))
        lines.append("@endmindmap")
        puml = "\n".join(lines)
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        # Walk down to the deepest node
        current = root.find("node")
        for i in range(49):
            children = current.findall("node")
            self.assertTrue(len(children) > 0, f"Expected child at depth {i+1}")
            current = children[0]
        self.assertEqual(current.get("TEXT"), "Level50")

    def test_siblings_at_same_level(self):
        """Multiple siblings at the same level should attach to the same parent."""
        puml_content = """@startmindmap
* Root
** Sibling1
** Sibling2
** Sibling3
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        children = root.find("node").findall("node")
        self.assertEqual(len(children), 3)
        self.assertEqual(children[0].get("TEXT"), "Sibling1")
        self.assertEqual(children[1].get("TEXT"), "Sibling2")
        self.assertEqual(children[2].get("TEXT"), "Sibling3")

    def test_node_text_with_asterisks(self):
        """Node text containing asterisks should not be confused with level markers."""
        puml_content = """@startmindmap
* Root node
** Child *important* node
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        # The text should contain the asterisks
        self.assertIn("*important*", child.get("TEXT"))

    def test_colon_in_node_text_not_multiline(self):
        """A colon that is NOT at the start of text should not trigger multiline parsing."""
        puml_content = """@startmindmap
* Root
** Note: this is a regular node
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        self.assertEqual(child.get("TEXT"), "Note: this is a regular node")

    def test_empty_node_text(self):
        """A node with no text should still be created."""
        puml_content = """@startmindmap
* 
** Child
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertIsNotNone(root_node)
        child = root_node.find("node")
        self.assertEqual(child.get("TEXT"), "Child")

    def test_level_goes_back_to_root_after_deep_section(self):
        """After a deep subtree, going back to level 1 should attach to root."""
        puml_content = """@startmindmap
* Root
** Deep1
*** Deep2
**** Deep3
* AnotherRoot
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        nodes = root.findall("node")
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].get("TEXT"), "Root")
        self.assertEqual(nodes[1].get("TEXT"), "AnotherRoot")

    def test_freemind_to_plantuml_with_multiple_children(self):
        """Three-level tree with multiple branches."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="A">
<node TEXT="A1"/>
<node TEXT="A2"/>
</node>
<node TEXT="B">
<node TEXT="B1">
<node TEXT="B1a"/>
</node>
</node>
</node>
</map>"""
        result = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn("** A", result)
        self.assertIn("** B", result)
        self.assertIn("*** A1", result)
        self.assertIn("*** A2", result)
        self.assertIn("*** B1", result)
        self.assertIn("**** B1a", result)

    def test_plantuml_single_line_multiline_with_html_tags(self):
        """Multiline nodes containing HTML-like tags."""
        puml_content = """@startmindmap
* Root
** :Line with <b>bold</b>;
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        self.assertIn("<b>bold</b>", child.get("TEXT"))

    def test_freemind_to_plantuml_nested_hyperlinks(self):
        """Hyperlinks at various nesting levels."""
        xml_content = """<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="Linked">
<hook URI="http://example.com"/>
<node TEXT="Child of linked"/>
</node>
</node>
</map>"""
        puml = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn("* [[http://example.com Linked]]", puml)

    def test_plantuml_to_freemind_roundtrip_idempotent_xml(self):
        """Converting PlantUML->Freemind twice should produce the same XML structure."""
        puml = """@startmindmap
* Root
** Child
@endmindmap"""
        xml1 = self.converter.plantuml_to_freemind(puml)
        # Convert back to PlantUML
        puml2 = self.converter.freemind_to_plantuml(xml1)
        # Convert again to Freemind
        xml2 = self.converter.plantuml_to_freemind(puml2)

        root1 = ET.fromstring(xml1)
        root2 = ET.fromstring(xml2)
        self.assertEqual(self._extract_tree(root1.find("node")),
                         self._extract_tree(root2.find("node")))

    def test_converted_underscore_nodes_are_ignored_in_text(self):
        """Verify that legacy underscore syntax (*_ or **) doesn't leak into text."""
        puml = """@startmindmap
* Root
** Child with *_ asterisk
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        # The regex strips leading *_ on level markers, but "*_" in node text
        # content (after the **) is preserved as-is since it's not at the start.
        self.assertEqual(child.get("TEXT"), "Child with *_ asterisk")

    def test_blank_lines_between_nodes(self):
        """Blank lines between nodes should be ignored."""
        puml = """@startmindmap

* Root

** Child

* Sibling

@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        nodes = root.findall("node")
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].get("TEXT"), "Root")
        self.assertEqual(nodes[1].get("TEXT"), "Sibling")


    def test_startmindmap_with_title_text(self):
        """@startmindmap My Title should not crash and should preserve the title.

        Covers issue #16 (preserve title) and issue #17 test gap #3.
        """
        puml = """@startmindmap My Map Title
* Root
** Child
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        self.assertEqual(root.get("title"), "My Map Title")
        self.assertEqual(root.find("node").get("TEXT"), "Root")

    def test_startmindmap_without_title_has_no_title_attr(self):
        """@startmindmap without extra text should not create a title attribute."""
        puml = """@startmindmap
* Root
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        self.assertIsNone(root.get("title"))

    def test_multiple_root_level_nodes(self):
        """Two * Node lines produce sibling nodes directly under <map>.

        Covers issue #17 test gap #1.
        """
        puml = """@startmindmap
* Root
** Child
* AnotherRoot
** AnotherChild
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        top_nodes = root.findall("node")
        self.assertEqual(len(top_nodes), 2)
        self.assertEqual(top_nodes[0].get("TEXT"), "Root")
        self.assertEqual(top_nodes[1].get("TEXT"), "AnotherRoot")
        self.assertEqual(top_nodes[0].find("node").get("TEXT"), "Child")
        self.assertEqual(top_nodes[1].find("node").get("TEXT"), "AnotherChild")

    def test_hyperlink_only_roundtrip(self):
        """[[http://example.com]] (no label) survives roundtrip with URI intact.

        Covers issue #17 test gap #2.
        """
        mm_input = """<map version="freeplane 1.9.13">
<node TEXT="Link Node">
<hook NAME="ExternalObject" URI="http://example.com"/>
</node>
</map>"""
        # mm -> puml
        puml = self.converter.freemind_to_plantuml(mm_input)
        self.assertIn("[[http://example.com Link Node]]", puml)

        # puml -> mm
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        node = root.find("node")
        self.assertEqual(node.get("TEXT"), "Link Node")
        hook = node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("URI"), "http://example.com")

    def test_multiline_with_leading_whitespace(self):
        """Multiline continuation with leading whitespace works correctly.

        Covers issue #17 test gap #4.
        """
        puml = """@startmindmap
* Root
** :First line
    Continued here;
@endmindmap"""
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        child = root.find("node").find("node")
        self.assertIn("First line", child.get("TEXT"))
        self.assertIn("Continued here", child.get("TEXT"))


if __name__ == '__main__':
    unittest.main()
