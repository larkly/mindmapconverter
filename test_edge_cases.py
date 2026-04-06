import unittest
import xml.etree.ElementTree as ET
from mindmapconverter import MindMapConverter


class TestMindMapConverterEdgeCases(unittest.TestCase):
    """Edge case tests for the mindmapconverter parser covering:
    - Malformed PlantUML input (incomplete nodes, missing closers)
    - Empty input / whitespace-only input
    - Deeply nested hierarchies (100+ levels)
    - Special characters (unicode, emojis, XML entities)
    - Very long node labels
    - Files with mixed line endings
    - Additional parser edge cases for parse_plantuml_line and create_xml_node
    """

    def setUp(self):
        self.converter = MindMapConverter()

    # =========================================================================
    # Empty / Whitespace-only input
    # =========================================================================

    def test_empty_string_plantuml_to_freemind(self):
        """Empty string input must raise ValueError (missing @startmindmap)."""
        with self.assertRaises(ValueError):
            self.converter.plantuml_to_freemind("")

    def test_whitespace_only_plantuml_to_freemind(self):
        """Whitespace-only input must raise ValueError."""
        with self.assertRaises(ValueError):
            self.converter.plantuml_to_freemind("   \n  \n\t ")

    def test_whitespace_only_markdown_to_freemind(self):
        """Whitespace-only Markdown must raise ValueError (no H1 header)."""
        with self.assertRaises(ValueError):
            self.converter.markdown_to_freemind("   \n  \n\t ")

    def test_only_startmindmap_raises(self):
        """Input with @startmindmap but no @endmindmap must raise ValueError."""
        with self.assertRaises(ValueError):
            self.converter.plantuml_to_freemind("@startmindmap\n* Root")

    def test_only_endmindmap_raises(self):
        """Input with @endmindmap but no @startmindmap must raise ValueError."""
        with self.assertRaises(ValueError):
            self.converter.plantuml_to_freemind("@endmindmap")

    def test_empty_string_freemind_to_plantuml(self):
        """Empty string Freemind XML must raise ValueError (ET.ParseError)."""
        with self.assertRaises(ValueError):
            self.converter.freemind_to_plantuml("")

    def test_whitespace_only_freemind_to_plantuml(self):
        """Whitespace-only Freemind XML must raise ValueError."""
        with self.assertRaises(ValueError):
            self.converter.freemind_to_plantuml("   \n  \n")

    def test_empty_string_freemind_to_markdown(self):
        """Empty string Freemind XML must raise ValueError."""
        with self.assertRaises(ValueError):
            self.converter.freemind_to_markdown("")

    # =========================================================================
    # Malformed PlantUML input (incomplete nodes, missing closers)
    # =========================================================================

    def test_malformed_xml_freemind_to_plantuml(self):
        """Malformed XML (not well-formed) must raise ValueError."""
        with self.assertRaises(ValueError):
            self.converter.freemind_to_plantuml("<not xml><unclosed>")

    def test_plantuml_with_only_comments_has_no_nodes(self):
        """PlantUML with only comments between markers produces zero nodes."""
        xml_output = self.converter.plantuml_to_freemind(
            "@startmindmap\n' comment line\n' another comment\n@endmindmap"
        )
        root = ET.fromstring(xml_output)
        self.assertEqual(len(root.findall("node")), 0)

    def test_plantuml_with_no_text_node_content(self):
        """A node with only asterisks and no text produces an empty TEXT attribute."""
        xml_output = self.converter.plantuml_to_freemind(
            "@startmindmap\n*\n@endmindmap"
        )
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertIsNotNone(root_node)
        self.assertEqual(root_node.get("TEXT"), "")

    def test_plantuml_unterminated_multiline_at_eof(self):
        """Multiline started right before @endmindmap (missing ';') must raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.converter.plantuml_to_freemind(
                "@startmindmap\n* Root\n** :start of multi\n@endmindmap"
            )
        self.assertIn("Unterminated", str(ctx.exception))

    # =========================================================================
    # Deeply nested hierarchies (100+ levels)
    # =========================================================================

    def test_100_level_plantuml_nesting(self):
        """PlantUML with 100 levels of nesting converts correctly."""
        puml_lines = ["@startmindmap"]
        for i in range(1, 101):
            puml_lines.append("*" * i + f" Level{i}")
        puml_lines.append("@endmindmap")
        puml_content = "\n".join(puml_lines)

        xml_output = self.converter.plantuml_to_freemind(puml_content)
        root = ET.fromstring(xml_output)

        # Walk the tree to verify all 100 levels exist
        node = root.find("node")
        self.assertIsNotNone(node)
        self.assertEqual(node.get("TEXT"), "Level1")
        for level in range(2, 101):
            children = node.findall("node")
            self.assertEqual(len(children), 1, f"Level {level} should have exactly 1 child")
            node = children[0]
            self.assertEqual(node.get("TEXT"), f"Level{level}")

    def test_100_level_freemind_to_markdown(self):
        """Freemind with 100 levels of nesting converts to Markdown."""
        # Build deep XML with 100 levels
        xml_parts = ['<map version="freeplane 1.9.13">', '<node TEXT="Root">']
        for i in range(1, 101):
            xml_parts.append('<node TEXT="' + f"L{i}" + '">')
        xml_parts[-1] = '<node TEXT="L100"/>'  # Replace last open with self-closing
        for _ in range(100):
            xml_parts.append("</node>")
        xml_parts.append("</map>")
        xml_content = "\n".join(xml_parts)

        result = self.converter.freemind_to_markdown(xml_content)
        lines = result.split("\n")
        self.assertEqual(lines[0], "# Root")
        # indent = "  " * (depth - 1); L1 is depth 1 (indent ""), L100 is depth 100
        # L1 at index 1, L100 at index 100
        expected_indent = "  " * 99  # depth 100 - 1 = 99
        self.assertEqual(lines[100], f"{expected_indent}- L100")

    def test_100_level_markdown_to_freemind(self):
        """Markdown with 100 levels of nesting converts to Freemind."""
        md_parts = ["# Root"]
        for i in range(1, 101):
            indent = "  " * (i - 1)
            md_parts.append(f"{indent}- Level{i}")
        md_content = "\n".join(md_parts)

        xml_output = self.converter.markdown_to_freemind(md_content)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")

        # Walk the tree
        node = root_node
        for i in range(1, 101):
            children = node.findall("node")
            self.assertEqual(len(children), 1, f"Level {i} should have exactly 1 child")
            node = children[0]
            self.assertEqual(node.get("TEXT"), f"Level{i}")

    def test_deep_freemind_to_plantuml(self):
        """Freemind with deep hierarchy converts to proper PlantUML indentation."""
        # Build moderate depth XML (20 levels)
        xml_parts = ['<map version="freeplane 1.9.13">', '<node TEXT="Root">']
        for i in range(1, 21):
            xml_parts.append(f'<node TEXT="D{i}">')
        xml_parts[-1] = '<node TEXT="D20"/>'
        for _ in range(20):
            xml_parts.append("</node>")
        xml_parts.append("</map>")
        xml_content = "\n".join(xml_parts)

        puml = self.converter.freemind_to_plantuml(xml_content)
        # Root is *, D20 should be twenty asterisks
        self.assertIn("* Root", puml)
        expected = "*" * 20 + " D20"
        self.assertIn(expected, puml)

    # =========================================================================
    # Special characters in node text (unicode, emojis, XML entities)
    # =========================================================================

    def test_unicode_characters_in_plantuml(self):
        """Unicode characters in PlantUML node text are preserved."""
        puml = '@startmindmap\n* 日本語テスト\n** émojis café\n@endmindmap'
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "日本語テスト")
        child = root_node.find("node")
        self.assertEqual(child.get("TEXT"), "émojis café")

    def test_emoji_in_plantuml_node(self):
        """Emojis in PlantUML node text are preserved."""
        puml = "@startmindmap\n* 🌳 Root 🌳\n** 🍃 Child 1 🍃\n** 🌺 Child 2\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "🌳 Root 🌳")
        children = root_node.findall("node")
        self.assertEqual(children[0].get("TEXT"), "🍃 Child 1 🍃")
        self.assertEqual(children[1].get("TEXT"), "🌺 Child 2")

    def test_unicode_in_freemind_xml(self):
        """Unicode in Freemind XML TEXT attributes survives conversion."""
        xml_content = '<map version="freeplane 1.9.13"><node TEXT="Über naïve résumé 日本語"/></map>'
        result = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn("Über naïve résumé 日本語", result)

    def test_xml_entities_in_plantuml_node(self):
        """Common XML entity-like text in PlantUML nodes is preserved."""
        # PlantUML uses raw text, not XML. &, <, > should pass through.
        puml = "@startmindmap\n* A & B < C > D\n** E=F\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertIn("&", root_node.get("TEXT"))
        self.assertIn("<", root_node.get("TEXT"))
        self.assertIn(">", root_node.get("TEXT"))
        child = root_node.find("node")
        self.assertEqual(child.get("TEXT"), "E=F")

    def test_emoji_in_markdown_to_freemind(self):
        """Emojis in Markdown input are preserved in Freemind XML."""
        md = "# 🏠 Home\n- 🛏️ Bedroom\n- 🍳 Kitchen"
        xml_output = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "🏠 Home")
        children = root_node.findall("node")
        self.assertEqual(children[0].get("TEXT"), "🛏️ Bedroom")
        self.assertEqual(children[1].get("TEXT"), "🍳 Kitchen")

    def test_emoji_in_freemind_to_markdown(self):
        """Emojis in Freemind XML survive conversion to Markdown."""
        xml = '<map version="freeplane 1.9.13"><node TEXT="🎯 Target"><node TEXT="✅ Done"/></node></map>'
        md = self.converter.freemind_to_markdown(xml)
        self.assertIn("🎯 Target", md)
        self.assertIn("✅ Done", md)

    def test_special_chars_roundtrip_plantuml_to_freemind(self):
        """Special characters (+, -, #, @, $) in PlantUML survive roundtrip."""
        puml = "@startmindmap\n* +plus -minus #hash @at $dollar\n@endmindmap"
        xml = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml)
        root_node = root.find("node")
        self.assertIn("+plus", root_node.get("TEXT"))
        self.assertIn("-minus", root_node.get("TEXT"))
        self.assertIn("#hash", root_node.get("TEXT"))
        self.assertIn("@at", root_node.get("TEXT"))
        self.assertIn("$dollar", root_node.get("TEXT"))

    def test_tab_characters_in_node_text(self):
        """Tab characters in node text survive conversion."""
        puml = "@startmindmap\n* text\twith\ttabs\n@endmindmap"
        xml = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml)
        self.assertIn("\t", root.find("node").get("TEXT"))

    # =========================================================================
    # Very long node labels
    # =========================================================================

    def test_very_long_node_label_plantuml(self):
        """A node label with 10000 characters is handled correctly."""
        long_text = "A" * 10000
        puml = f"@startmindmap\n* {long_text}\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        self.assertEqual(root.find("node").get("TEXT"), long_text)

    def test_very_long_label_in_freemind_xml(self):
        """A Freemind node with 10000 character TEXT is converted correctly."""
        long_text = "X" * 10000
        xml_content = f'<map version="freeplane 1.9.13"><node TEXT="{long_text}"/></map>'
        result = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn(long_text, result)

    def test_many_siblings_at_same_level(self):
        """100 siblings at the same level are handled."""
        children = "\n".join(["* Child" + str(i) for i in range(100)])
        puml = f"@startmindmap\n* Root\n{children}\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        siblings = root_node.findall("node")
        self.assertEqual(len(siblings), 100)
        for i in range(100):
            self.assertEqual(siblings[i].get("TEXT"), f"Child{i}")

    # =========================================================================
    # Mixed line endings
    # =========================================================================

    def test_plantuml_with_crlf_line_endings(self):
        """PlantUML with \\r\\n (Windows) line endings is parsed correctly."""
        puml = "@startmindmap\r\n* Root\r\n** Child 1\r\n** Child 2\r\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        children = root_node.findall("node")
        self.assertEqual(len(children), 2)

    def test_plantuml_with_cr_only_line_endings(self):
        """PlantUML with \\r (old Mac) line endings is parsed correctly."""
        # This tests how split('\\n') handles \\r-only line endings
        puml = "@startmindmap\r* Root\r** Child\r@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        child = root_node.find("node")
        self.assertEqual(child.get("TEXT"), "Child")

    def test_plantuml_with_mixed_line_endings(self):
        """PlantUML with mixed \\r\\n and \\n line endings is parsed correctly."""
        puml = "@startmindmap\r\n* Root\r\n** Child 1\r** Child 2\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        children = root_node.findall("node")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "Child 1")
        self.assertEqual(children[1].get("TEXT"), "Child 2")

    # =========================================================================
    # parse_plantuml_line edge cases (direct unit tests)
    # =========================================================================

    def test_parse_plantuml_line_basic_star(self):
        """Basic single-asterisk node parsing."""
        result = self.converter.parse_plantuml_line("* Root")
        self.assertEqual(result, (1, "Root", False))

    def test_parse_plantuml_line_multiple_stars(self):
        """Triple-asterisk node parsing."""
        result = self.converter.parse_plantuml_line("*** Deep")
        self.assertEqual(result, (3, "Deep", False))

    def test_parse_plantuml_line_legacy_underscore(self):
        """Legacy *_ syntax is parsed correctly."""
        result = self.converter.parse_plantuml_line("*_ Root")
        self.assertEqual(result, (1, "Root", False))

    def test_parse_plantuml_line_multiline_start(self):
        """Single-colon notation marks as multiline start."""
        result = self.converter.parse_plantuml_line("* :text with colons;")
        self.assertEqual(result, (1, "text with colons;", True))

    def test_parse_plantuml_line_non_node_returns_none(self):
        """Non-node lines (comments, markers, blank) return None."""
        self.assertIsNone(self.converter.parse_plantuml_line("' comment"))
        self.assertIsNone(self.converter.parse_plantuml_line("@startmindmap"))
        self.assertIsNone(self.converter.parse_plantuml_line("not a node"))

    def test_parse_plantuml_line_stripped_whitespace(self):
        """Lines with leading whitespace are matched."""
        result = self.converter.parse_plantuml_line("  ** Indented Child")
        self.assertEqual(result, (2, "Indented Child", False))

    def test_parse_plantuml_line_empty_text_after_stars(self):
        """Asterisks with nothing after them yield empty text."""
        result = self.converter.parse_plantuml_line("* ")
        self.assertEqual(result, (1, "", False))

    def test_parse_plantuml_line_colon_only(self):
        """A line like `* :` is parsed as multiline start with empty text."""
        result = self.converter.parse_plantuml_line("* :")
        self.assertEqual(result, (1, "", True))

    # =========================================================================
    # create_xml_node edge cases
    # =========================================================================

    def test_create_xml_node_with_link(self):
        """A note with a [[url label]] hyperlink creates a hook element."""
        parent = ET.Element("map")
        node = self.converter.create_xml_node(parent, "[[http://example.com Example]]")
        # The [[url label]] form replaces the whole block with just the label
        self.assertEqual(node.get("TEXT"), "Example")
        hook = node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("URI"), "http://example.com")

    def test_create_xml_node_with_url_only_link(self):
        """A [[url]] form without label sets text and URI to the URL."""
        parent = ET.Element("map")
        node = self.converter.create_xml_node(parent, "[[http://example.com]]")
        self.assertEqual(node.get("TEXT"), "http://example.com")
        hook = node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("URI"), "http://example.com")

    def test_create_xml_node_no_link(self):
        """A node without any link has no hook element."""
        parent = ET.Element("map")
        node = self.converter.create_xml_node(parent, "Plain text")
        self.assertEqual(node.get("TEXT"), "Plain text")
        self.assertIsNone(node.find("hook"))

    def test_create_xml_node_empty_text(self):
        """A node with empty TEXT is created properly."""
        parent = ET.Element("map")
        node = self.converter.create_xml_node(parent, "")
        self.assertEqual(node.get("TEXT"), "")
        self.assertEqual(node.get("FOLDED"), "false")

    # =========================================================================
    # Additional edge cases for converter behavior
    # =========================================================================

    def test_plantuml_with_only_whitespace_between_markers(self):
        """Only whitespace between @startmindmap and @endmindmap yields no nodes."""
        puml = "@startmindmap\n  \n \n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        self.assertEqual(len(root.findall("node")), 0)

    def test_freemind_to_plantuml_node_tag_as_root(self):
        """Freemind with <node> as root element converts correctly."""
        xml_content = '<node TEXT="Root"><node TEXT="Child"/></node>'
        puml = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn("* Root", puml)
        self.assertIn("** Child", puml)

    def test_freemind_to_plantuml_unexpected_root_tag(self):
        """Freemind with unknown root tag produces only markers (no nodes)."""
        xml_content = '<unexpected><node TEXT="Ignored"/></unexpected>'
        puml = self.converter.freemind_to_plantuml(xml_content)
        self.assertEqual(puml.strip(), "@startmindmap\n@endmindmap")

    def test_freemind_to_markdown_unexpected_root_tag(self):
        """Freemind with unknown root tag produces an empty string."""
        xml_content = '<unexpected><node TEXT="Ignored"/></unexpected>'
        result = self.converter.freemind_to_markdown(xml_content)
        self.assertEqual(result, "")

    def test_multiple_nodes_at_root_level_markdown(self):
        """Multiple root-level nodes in Markdown: only the first H1 is used."""
        md = "# Root\n- Child 1\n# Ignored Header\n- Child 2"
        xml_output = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        children = root_node.findall("node")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "Child 1")
        self.assertEqual(children[1].get("TEXT"), "Child 2")

    def test_plantuml_node_with_only_asterisks(self):
        """A line with just asterisks and no text produces a valid (empty TEXT) node."""
        puml = "@startmindmap\n*****\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertIsNotNone(root_node)
        self.assertEqual(root_node.get("TEXT"), "")

    def test_emoji_roundtrip_plantuml_to_freemind(self):
        """Emojis survive the full PlantUML -> Freemind -> PlantUML roundtrip."""
        original = "@startmindmap\n* 🌳 Tree\n** 🍃 Leaf\n@endmindmap"
        xml = self.converter.plantuml_to_freemind(original)
        roundtripped = self.converter.freemind_to_plantuml(xml)
        self.assertIn("🌳 Tree", roundtripped)
        self.assertIn("🍃 Leaf", roundtripped)

    def test_plantuml_with_bracket_characters_in_text(self):
        """Brackets in node text that don't form valid links are preserved."""
        puml = "@startmindmap\n* [text] (not a link)\n@endmindmap"
        xml_output = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "[text] (not a link)")

    def test_freemind_with_node_missing_text_attribute(self):
        """Freemind node without TEXT attribute defaults to empty string."""
        xml_content = '<map version="freeplane 1.9.13"><node><node TEXT="Child"/></node></map>'
        puml = self.converter.freemind_to_plantuml(xml_content)
        # The root node should have empty text
        self.assertIn("* ", puml)
        self.assertIn("** Child", puml)


if __name__ == "__main__":
    unittest.main()
