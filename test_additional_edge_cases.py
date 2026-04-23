"""Additional edge case tests for mindmapconverter parser.

This file contains tests for:
- main() CLI function with argparse (file I/O paths)
- Multiple top-level nodes in Freemind maps
- Malformed link patterns in create_xml_node
- Edge cases in freemind_to_markdown and markdown_to_freemind
- Boundary conditions in the conversion logic
"""

import unittest
import xml.etree.ElementTree as ET
import os
import sys
import tempfile
from io import StringIO
from unittest.mock import patch

from mindmapconverter import MindMapConverter, main


class TestMainCLI(unittest.TestCase):
    """Tests for the main() CLI entry point with file I/O."""

    def setUp(self):
        self.converter = MindMapConverter()
        self.temp_dir = tempfile.mkdtemp()

    def _write_input(self, content: str, filename: str) -> str:
        path = os.path.join(self.temp_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_mm_file_to_plantuml_stdout(self):
        """CLI: .mm input outputs PlantUML to stdout."""
        xml_content = '<map version="freeplane 1.9.13"><node TEXT="Root"/></map>'
        input_path = self._write_input(xml_content, "test.mm")

        with patch("sys.argv", ["mindmapconverter", input_path]), \
             patch("sys.stdout", new_callable=StringIO) as stdout:
            main()
            output = stdout.getvalue()
            self.assertIn("@startmindmap", output)
            self.assertIn("Root", output)
            self.assertIn("@endmindmap", output)

    def test_puml_file_to_freemind_stdout(self):
        """CLI: .puml input outputs Freemind XML to stdout."""
        puml = "@startmindmap\n* Root\n@endmindmap\n"
        input_path = self._write_input(puml, "test.puml")

        with patch("sys.argv", ["mindmapconverter", input_path]), \
             patch("sys.stdout", new_callable=StringIO) as stdout:
            main()
            output = stdout.getvalue()
            root = ET.fromstring(output)
            self.assertEqual(root.tag, "map")
            self.assertEqual(root.find("node").get("TEXT"), "Root")

    def test_mm_file_to_md_with_flag(self):
        """CLI: .mm with --to-md outputs Markdown to stdout."""
        xml_content = '<map version="freeplane 1.9.13"><node TEXT="Root"><node TEXT="Child"/></node></map>'
        input_path = self._write_input(xml_content, "test.mm")

        with patch("sys.argv", ["mindmapconverter", input_path, "--to-md"]), \
             patch("sys.stdout", new_callable=StringIO) as stdout:
            main()
            output = stdout.getvalue()
            self.assertEqual(output.strip(), "# Root\n- Child")

    def test_md_file_to_freemind(self):
        """CLI: .md input outputs Freemind XML to stdout."""
        md_content = "# Root\n- Child\n"
        input_path = self._write_input(md_content, "test.md")

        with patch("sys.argv", ["mindmapconverter", input_path]), \
             patch("sys.stdout", new_callable=StringIO) as stdout:
            main()
            output = stdout.getvalue()
            root = ET.fromstring(output)
            self.assertEqual(root.find("node").get("TEXT"), "Root")

    def test_md_file_to_freemind_with_flag(self):
        """CLI: any extension with --from-md forces Markdown parsing."""
        md_content = "# Root\n- Child\n"
        input_path = self._write_input(md_content, "test.txt")

        with patch("sys.argv", ["mindmapconverter", input_path, "--from-md"]), \
             patch("sys.stdout", new_callable=StringIO) as stdout:
            main()
            output = stdout.getvalue()
            root = ET.fromstring(output)
            self.assertEqual(root.find("node").get("TEXT"), "Root")

    def test_file_not_found_exits_1(self):
        """CLI: nonexistent file prints error and exits with code 1."""
        with patch("sys.argv", ["mindmapconverter", "/nonexistent/file.mm"]), \
             patch("sys.stderr", new_callable=StringIO) as stderr:
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)
            self.assertIn("not found", stderr.getvalue())

    def test_mm_to_file_output(self):
        """CLI: -o flag writes output to file."""
        xml_content = '<map version="freeplane 1.9.13"><node TEXT="Test"/></map>'
        input_path = self._write_input(xml_content, "test.mm")
        output_path = os.path.join(self.temp_dir, "output.puml")

        with patch("sys.argv", ["mindmapconverter", input_path, "-o", output_path]), \
             patch("sys.stdout", new_callable=StringIO) as stdout:
            main()
            # Nothing should go to stdout
            self.assertEqual(stdout.getvalue(), "")

        with open(output_path) as f:
            output = f.read()
        self.assertIn("@startmindmap", output)
        self.assertIn("Test", output)

    def test_md_to_file_output(self):
        """CLI: .md to .mm with -o writes XML output."""
        md_content = "# Root\n- A\n- B\n"
        input_path = self._write_input(md_content, "test.md")
        output_path = os.path.join(self.temp_dir, "output.mm")

        with patch("sys.argv", ["mindmapconverter", input_path, "-o", output_path]):
            main()

        with open(output_path) as f:
            output = f.read()
        root = ET.fromstring(output)
        self.assertEqual(root.find("node").get("TEXT"), "Root")
        children = root.find("node").findall("node")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "A")
        self.assertEqual(children[1].get("TEXT"), "B")

    def test_invalid_md_raises_value_error(self):
        """CLI: invalid .md content (no H1) exits with code 1."""
        md_content = "Just text, no header"
        input_path = self._write_input(md_content, "test.md")

        with patch("sys.argv", ["mindmapconverter", input_path]), \
             patch("sys.stderr", new_callable=StringIO) as stderr:
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)
            self.assertIn("No H1 header", stderr.getvalue())


class TestMultipleRootNodes(unittest.TestCase):
    """Tests for Freemind maps with multiple top-level nodes."""

    def setUp(self):
        self.converter = MindMapConverter()

    def test_freemind_with_multiple_top_level_nodes_to_plantuml(self):
        """Freemind with multiple root <node> elements converts to separate PlantUML roots."""
        xml_content = '''<map version="freeplane 1.9.13">
<node TEXT="Root1"><node TEXT="Child A"/></node>
<node TEXT="Root2"><node TEXT="Child B"/></node>
</map>'''
        puml = self.converter.freemind_to_plantuml(xml_content)
        # Should have both root nodes at level 1
        self.assertIn("* Root1", puml)
        self.assertIn("* Root2", puml)
        self.assertIn("** Child A", puml)
        self.assertIn("** Child B", puml)

    def test_freemind_with_multiple_top_level_nodes_to_markdown(self):
        """Freemind with multiple root nodes converts first root to H1."""
        xml_content = '''<map version="freeplane 1.9.13">
<node TEXT="First Root"><node TEXT="A"/></node>
<node TEXT="Second Root"><node TEXT="B"/></node>
</map>'''
        md = self.converter.freemind_to_markdown(xml_content)
        self.assertIn("# First Root", md)
        self.assertIn("- A", md)

    def test_single_node_as_root_element(self):
        """A single <node> element as root (without <map> wrapper) converts correctly."""
        xml_content = '<node TEXT="Root"><node TEXT="Child"/></node>'
        puml = self.converter.freemind_to_plantuml(xml_content)
        self.assertIn("* Root", puml)
        self.assertIn("** Child", puml)

        md = self.converter.freemind_to_markdown(xml_content)
        self.assertIn("# Root", md)
        self.assertIn("- Child", md)


class TestCreateXmlNodeEdgeCases(unittest.TestCase):
    """Edge cases for the create_xml_node link extraction."""

    def setUp(self):
        self.converter = MindMapConverter()

    def test_multiple_link_patterns_only_first_extracted(self):
        """When text contains multiple [[url label]] patterns, only the first is extracted."""
        parent = ET.Element("map")
        text_with_two = "[[http://first.com First]] some text [[http://second.com Second]]"
        node = self.converter.create_xml_node(parent, text_with_two)
        # Second pattern should remain in TEXT (not extracted)
        self.assertIn("First", node.get("TEXT"))
        hook = node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("URI"), "http://first.com")

    def test_malformed_link_double_bracket_no_close(self):
        """Malformed [[ without closing ]] is left in TEXT as-is."""
        parent = ET.Element("map")
        node = self.converter.create_xml_node(parent, "text [[no close")
        self.assertEqual(node.get("TEXT"), "text [[no close")
        self.assertIsNone(node.find("hook"))

    def test_link_with_special_characters_in_url(self):
        """URL with query params and special chars is extracted correctly."""
        parent = ET.Element("map")
        node = self.converter.create_xml_node(parent, "[[https://example.com/path?q=1&b=2 Link]]")
        self.assertEqual(node.get("TEXT"), "Link")
        hook = node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("URI"), "https://example.com/path?q=1&b=2")
        self.assertIsNone(node.get("URI"))  # URI is on hook, not node

    def test_link_with_empty_label(self):
        """[[url ]] with trailing space and a space as label."""
        parent = ET.Element("map")
        node = self.converter.create_xml_node(parent, "[[http://example.com ]]")
        # Regex: \[\[(.*?)(?: (.*?))?\]\] against "[[http://example.com ]]"
        # group(1)="http://example.com", group(2)="" (the space after label is captured by optional space,
        # then .*? matches empty, and ]] follows)
        # Actually: let me check - regex finds [[ then (.*?) greedily takes "http", then space and empty label
        # Since group(2)="" is falsy, the else branch is taken: URI="http://example.com", TEXT="http://example.com"
        self.assertEqual(node.get("TEXT"), "http://example.com")
        hook = node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("URI"), "http://example.com")

    def test_link_with_empty_url(self):
        """[[]] with empty content."""
        parent = ET.Element("map")
        # [[]] - regex won't match because (.*?) needs something between [[ and ]]
        # Actually it would match with empty string
        text = "some [[]] text"
        node = self.converter.create_xml_node(parent, text)
        self.assertEqual(node.get("TEXT"), "some  text")


class TestFreemindToMarkdownEdgeCases(unittest.TestCase):
    """Edge cases specific to freemind_to_markdown conversion."""

    def setUp(self):
        self.converter = MindMapConverter()

    def test_empty_nodes_list_returns_empty_string(self):
        """Freemind XML with no <node> at root level returns empty string."""
        xml = '<empty version="freeplane 1.9.13"/>'
        result = self.converter.freemind_to_markdown(xml)
        self.assertEqual(result, "")

    def test_multiline_text_renders_as_br_in_markdown(self):
        """Multiline text in Freemind renders with <br> in Markdown output."""
        xml = '''<map version="freeplane 1.9.13">
<node TEXT="Line1&#10;Line2&#10;Line3"/>
</map>'''
        result = self.converter.freemind_to_markdown(xml)
        self.assertIn("Line1<br>Line2<br>Line3", result)

    def test_nested_multiline_text_with_links(self):
        """Combined: nested nodes with multiline text and hyperlinks."""
        xml = '''<map version="freeplane 1.9.13">
<node TEXT="Root">
<node TEXT="Line1&#10;Line2">
<node TEXT="Nested Link">
<hook URI="http://example.com"/>
</node>
</node>
</node>
</map>'''
        result = self.converter.freemind_to_markdown(xml)
        self.assertIn("Line1<br>Line2", result)
        self.assertIn("[Nested Link](http://example.com)", result)

    def test_unicode_in_freemind_to_markdown_deep_hierarchy(self):
        """Unicode text at various depths renders correctly."""
        xml = '''<map version="freeplane 1.9.13">
<node TEXT="日本語 Root">
<node TEXT="Émoji 🎯">
<node TEXT="中文测试"/>
</node>
</node>
</map>'''
        result = self.converter.freemind_to_markdown(xml)
        self.assertIn("日本語 Root", result)
        self.assertIn("Émoji 🎯", result)
        self.assertIn("中文测试", result)


class TestMarkdownToFreemindEdgeCases(unittest.TestCase):
    """Edge cases specific to markdown_to_freemind conversion."""

    def setUp(self):
        self.converter = MindMapConverter()

    def test_non_header_non_list_lines_ignored(self):
        """Lines that are neither H1 nor list items are silently ignored."""
        md = "# Root\nSome regular text\n- Child\nMore text\n- Child2"
        xml_output = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml_output)
        children = root.find("node").findall("node")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "Child")
        self.assertEqual(children[1].get("TEXT"), "Child2")

    def test_h1_after_list_items_ignored(self):
        """H1 headers after the first one are ignored (treated as regular lines)."""
        md = "# Root\n- Child\n## Not a root\n- Another child"
        xml_output = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml_output)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        children = root_node.findall("node")
        # The ## Not a root is ignored, so Another Child is still a sibling of Child
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "Child")
        self.assertEqual(children[1].get("TEXT"), "Another child")

    def test_empty_list_item_text(self):
        """List item with only whitespace after marker is handled."""
        md = "# Root\n   "
        xml_output = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml_output)
        # The whitespace-only line should not match the list pattern
        self.assertEqual(root.find("node").get("TEXT"), "Root")
        self.assertEqual(len(root.find("node").findall("node")), 0)

    def test_link_text_with_bracket_chars_not_extracted(self):
        """Markdown link text containing ] chars: regex cannot match, text is preserved as-is."""
        md = "# Root\n- [A.B*C+?|()[] Test](http://example.com)"
        xml_output = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml_output)
        node = root.find("node").find("node")
        # The regex r'\[([^\]]+)\]\(([^)]+)\)' fails when the link text contains ']'
        # So the entire bracket expression is kept as raw TEXT
        self.assertEqual(node.get("TEXT"), "[A.B*C+?|()[] Test](http://example.com)")
        self.assertIsNone(node.find("hook"))

    def test_multiline_text_with_br_in_markdown_input(self):
        """Multiple <br> tags in Markdown convert to actual newlines."""
        md = "# Root\n- Line1<br>Line2<br>Line3"
        xml_output = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml_output)
        node = root.find("node").find("node")
        self.assertEqual(node.get("TEXT"), "Line1\nLine2\nLine3")


class TestPlantumlToFreemindEdgeCases(unittest.TestCase):
    """Edge cases for plantuml_to_freemind conversion."""

    def setUp(self):
        self.converter = MindMapConverter()

    def test_multiple_root_nodes_in_plantuml(self):
        """PlantUML with multiple level-1 nodes at the same level."""
        puml = "@startmindmap\n* Root1\n* Root2\n@endmindmap"
        xml = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml)
        nodes = root.findall("node")
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].get("TEXT"), "Root1")
        self.assertEqual(nodes[1].get("TEXT"), "Root2")

    def test_deep_nesting_with_level_decrease_then_increase(self):
        """PlantUML: deep nest, go shallow, then deep again."""
        puml = """@startmindmap
* Root
** Level2
*** Level3
** BackTo2
*** DeepAgain
@endmindmap"""
        xml = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml)
        root_node = root.find("node")
        self.assertEqual(root_node.get("TEXT"), "Root")
        children = root_node.findall("node")
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].get("TEXT"), "Level2")
        self.assertEqual(children[1].get("TEXT"), "BackTo2")

    def test_multiline_with_empty_continuation_lines(self):
        """Multiline node with empty continuation line."""
        puml = """@startmindmap
* Root
** :Line 1

Line 3;
@endmindmap"""
        xml = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml)
        child = root.find("node").find("node")
        text = child.get("TEXT")
        self.assertIn("Line 1", text)
        self.assertIn("Line 3", text)

    def test_multiline_single_line_form_empty_text(self):
        """Multiline node that is just `:;` produces empty text."""
        puml = "@startmindmap\n* :\n@endmindmap"
        # This creates an empty multiline start which then waits for continuation
        # Actually with just `* :` it sets is_multiline_start=True and text=""
        # Then waits for continuation - if no continuation found before @endmindmap, raises ValueError
        with self.assertRaises(ValueError):
            self.converter.plantuml_to_freemind(puml)

    def test_plantuml_with_tab_characters_before_asterisk(self):
        """Tabs before asterisk at line start are handled."""
        puml = "@startmindmap\n\t* Root\n@endmindmap"
        xml = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml)
        self.assertEqual(root.find("node").get("TEXT"), "Root")

    def test_link_with_text_containing_double_brackets(self):
        """Link text that itself contains [[ triggers only the outer pattern."""
        puml = "@startmindmap\n* [[http://example.com Text with [[inner]] brackets]]\n@endmindmap"
        xml = self.converter.plantuml_to_freemind(puml)
        root = ET.fromstring(xml)
        node = root.find("node")
        # The regex \[\[(.*?)(?: (.*?))?\]\] is non-greedy: it captures "http://example.com" as URI
        # and "Text with [[inner" as label. The remaining "]] brackets]]" stays in TEXT.
        # Actually the replace replaces the first match of [[http://example.com Text with [[inner]] brackets]]
        # which replaces everything including the inner ]], leaving " brackets]]" -> wait
        # Let's just verify the observed behavior
        self.assertIn("[[inner brackets", node.get("TEXT"))
        self.assertIn("Text with", node.get("TEXT"))
        hook = node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(hook.get("URI"), "http://example.com")

class TestFreemindToPlantumlEdgeCases(unittest.TestCase):
    """Edge cases for freemind_to_plantuml conversion."""

    def setUp(self):
        self.converter = MindMapConverter()

    def test_single_node_freemind(self):
        """Freemind with just one node (no children) produces minimal output."""
        xml = '<map version="freeplane 1.9.13"><node TEXT="Only Node"/></map>'
        result = self.converter.freemind_to_plantuml(xml)
        expected = "@startmindmap\n* Only Node\n@endmindmap"
        self.assertEqual(result.strip(), expected)

    def test_node_with_multiple_hooks_picks_first_uri(self):
        """Node with multiple hook elements uses the first URI."""
        xml = '''<map version="freeplane 1.9.13">
<node TEXT="Root">
<hook URI="http://first.com"/>
<hook URI="http://second.com"/>
</node>
</map>'''
        puml = self.converter.freemind_to_plantuml(xml)
        self.assertIn("http://first.com", puml)
        # The second URI should NOT appear
        self.assertNotIn("http://second.com", puml)

    def test_empty_map_tag(self):
        """Freemind with just <map> tag produces minimal PlantUML output."""
        xml = "<map version=\"freeplane 1.9.13\"></map>"
        result = self.converter.freemind_to_plantuml(xml)
        self.assertEqual(result.strip(), "@startmindmap\n@endmindmap")


class TestRoundtripEdgeCases(unittest.TestCase):
    """Roundtrip tests with edge cases."""

    def setUp(self):
        self.converter = MindMapConverter()

    def test_plantuml_to_freemind_to_plantuml_with_multiple_roots(self):
        """PlantUML with multiple roots survives roundtrip."""
        original = "@startmindmap\n* A\n* B\n@endmindmap"
        xml = self.converter.plantuml_to_freemind(original)
        roundtripped = self.converter.freemind_to_plantuml(xml)
        # Note: Freemind wraps multiple roots in a <map>, so PlantUML re-extraction 
        # will produce * A and * B at level 1
        self.assertIn("* A", roundtripped)
        self.assertIn("* B", roundtripped)

    def test_plantuml_roundtrip_with_multiline(self):
        """PlantUML with multiline node survives roundtrip."""
        original = "@startmindmap\n* Root\n** :Line 1\nLine 2;\n@endmindmap"
        xml = self.converter.plantuml_to_freemind(original)
        roundtripped = self.converter.freemind_to_plantuml(xml)
        self.assertIn("* Root", roundtripped)
        self.assertIn("Line 1", roundtripped)
        self.assertIn("Line 2", roundtripped)


class TestMarkdownLinkBalancedParens(unittest.TestCase):
    """Tests for Markdown links whose URLs contain balanced parentheses.

    CommonMark allows unescaped parens inside a link URL as long as they are
    balanced. The naive ``\\[([^\\]]+)\\]\\(([^)]+)\\)`` regex truncates the URL
    at the first ``)`` and corrupts the node text, which broke common URLs such
    as Wikipedia disambiguation links. These tests pin down the corrected
    behaviour and guard against regressions.
    """

    def setUp(self):
        self.converter = MindMapConverter()

    def test_wikipedia_disambiguation_url_preserved(self):
        """URL with a single (...) segment (Wikipedia-style) is preserved."""
        md = (
            "# Root\n"
            "- [Python](https://en.wikipedia.org/wiki/Python_(programming_language))"
        )
        xml = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml)
        python_node = root.find("node").find("node")

        self.assertEqual(python_node.get("TEXT"), "Python")
        hook = python_node.find("hook")
        self.assertIsNotNone(hook)
        self.assertEqual(
            hook.get("URI"),
            "https://en.wikipedia.org/wiki/Python_(programming_language)",
        )

    def test_url_with_parens_survives_md_roundtrip(self):
        """MD → XML → MD → XML roundtrip preserves a paren-containing URL."""
        md = (
            "# Root\n"
            "- [Python](https://en.wikipedia.org/wiki/Python_(programming_language))\n"
            "- Plain"
        )
        xml = self.converter.markdown_to_freemind(md)
        md_back = self.converter.freemind_to_markdown(xml)
        xml_roundtrip = self.converter.markdown_to_freemind(md_back)
        self.assertEqual(xml, xml_roundtrip)

    def test_url_with_nested_balanced_parens(self):
        """URL with nested balanced parens like /foo(bar(baz))/ parses correctly."""
        md = "# Root\n- [label](http://example.com/foo(bar(baz))/path)"
        xml = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml)
        child = root.find("node").find("node")

        self.assertEqual(child.get("TEXT"), "label")
        self.assertEqual(
            child.find("hook").get("URI"),
            "http://example.com/foo(bar(baz))/path",
        )

    def test_plain_url_without_parens_still_works(self):
        """Regression guard: simple URLs continue to parse correctly."""
        md = "# Root\n- [docs](http://example.com/page)"
        xml = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml)
        child = root.find("node").find("node")

        self.assertEqual(child.get("TEXT"), "docs")
        self.assertEqual(
            child.find("hook").get("URI"), "http://example.com/page"
        )

    def test_unbalanced_parens_leaves_link_as_text(self):
        """Link with unbalanced parens (no matching ``)``) is not treated as a link."""
        md = "# Root\n- [bad](http://example.com/unclosed"
        xml = self.converter.markdown_to_freemind(md)
        root = ET.fromstring(xml)
        child = root.find("node").find("node")

        # No hook should be created; the literal text is preserved verbatim.
        self.assertIsNone(child.find("hook"))
        self.assertEqual(child.get("TEXT"), "[bad](http://example.com/unclosed")

    def test_find_markdown_link_returns_none_for_plain_text(self):
        """``_find_markdown_link`` returns None when no link is present."""
        self.assertIsNone(self.converter._find_markdown_link("just plain text"))

    def test_find_markdown_link_returns_spans_and_parts(self):
        """``_find_markdown_link`` returns correct spans, label, and url."""
        text = "see [a](http://x.com/y) now"
        result = self.converter._find_markdown_link(text)
        self.assertIsNotNone(result)
        start, end, label, url = result
        self.assertEqual(text[start:end], "[a](http://x.com/y)")
        self.assertEqual(label, "a")
        self.assertEqual(url, "http://x.com/y")


if __name__ == "__main__":
    unittest.main()
