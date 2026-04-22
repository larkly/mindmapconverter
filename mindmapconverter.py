#!/usr/bin/env python3
import re
import xml.etree.ElementTree as ET
import sys
import os
import argparse
from typing import Optional, Tuple, List

class MindMapConverter:
    """Bidirectional converter between Freemind/Freeplane (.mm), PlantUML (.puml), and Markdown (.md) formats."""

    def __init__(self):
        self.xml_version = "freeplane 1.9.13"

    def parse_xml_node(self, node: ET.Element, level: int) -> str:
        """Recursively convert a Freemind XML node (and its children) to PlantUML lines."""
        text = node.get("TEXT", "")

        # Check for hyperlinks
        # Freeplane stores links in a hook element
        link = None
        for hook in node.findall("hook"):
            if hook.get("URI"):
                link = hook.get("URI")
                break

        if link:
            # PlantUML format: [[url label]]
            # If text matches url, just [[url]]
            if text == link:
                text = f"[[{link}]]"
            else:
                text = f"[[{link} {text}]]"

        # Check for multiline
        if "\n" in text:
            # PlantUML arithmetic/multiline syntax
            # * :Line 1
            # Line 2;
            plantuml_node = f"{'*' * level} :{text};"
        else:
            plantuml_node = f"{'*' * level} {text}"

        for child in node.findall("node"):
            plantuml_node += "\n" + self.parse_xml_node(child, level + 1)
        return plantuml_node

    def freemind_to_plantuml(self, content: str) -> str:
        """Convert Freemind/Freeplane XML content to a PlantUML mindmap string."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Error parsing XML content: {e}")

        plantuml_lines = ["@startmindmap"]

        if root.tag == 'map':
            nodes = root.findall("node")
        elif root.tag == 'node':
            nodes = [root]
        else:
            nodes = []

        for child in nodes:
            plantuml_lines.append(self.parse_xml_node(child, 1))

        plantuml_lines.append("@endmindmap")
        return "\n".join(plantuml_lines)

    def _xml_node_to_markdown(self, node: ET.Element, depth: int, lines: List[str]) -> None:
        """Recursively convert a Freemind XML node to Markdown lines.

        Args:
            node: The XML element to convert.
            depth: Current depth (0 = root/H1, 1+ = list items).
            lines: List to append generated lines to.
        """
        text = node.get("TEXT", "")

        # Check for hyperlinks
        link = None
        for hook in node.findall("hook"):
            if hook.get("URI"):
                link = hook.get("URI")
                break

        if link:
            display_text = f"[{text}]({link})"
        else:
            display_text = text

        # Handle multiline text: replace newlines with <br> for markdown
        if "\n" in display_text:
            display_text = display_text.replace("\n", "<br>")

        if depth == 0:
            lines.append(f"# {display_text}")
        else:
            indent = "  " * (depth - 1)
            lines.append(f"{indent}- {display_text}")

        for child in node.findall("node"):
            self._xml_node_to_markdown(child, depth + 1, lines)

    def freemind_to_markdown(self, content: str) -> str:
        """Convert Freemind/Freeplane XML content to a Markdown nested list string.

        The root node becomes an H1 header. Child nodes become nested list items
        using ``-`` markers with 2-space indentation. Hyperlinks are rendered as
        ``[text](url)``. Multiline node text uses ``<br>`` tags.

        Args:
            content: Freemind/Freeplane XML string.

        Returns:
            Markdown string with H1 header and nested lists.
        """
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Error parsing XML content: {e}")

        if root.tag == 'map':
            nodes = root.findall("node")
        elif root.tag == 'node':
            nodes = [root]
        else:
            nodes = []

        if not nodes:
            return ""

        lines: List[str] = []
        for node in nodes:
            self._xml_node_to_markdown(node, 0, lines)

        return "\n".join(lines)

    def parse_plantuml_line(self, line: str) -> Optional[Tuple[int, str, bool]]:
        """Parse a single PlantUML node line.

        Handles `* text`, `** text`, `*_ text` (legacy), and `:multiline start` forms.
        Returns (level, text, is_multiline_start) or None if the line is not a node.
        """
        match = re.match(r"^\s*(\*+)(?:_)?\s*(.*)$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            is_multiline_start = text.startswith(":")
            if is_multiline_start:
                text = text[1:].strip() # Remove leading :
            return level, text, is_multiline_start
        return None

    def _is_multiline_terminator(self, lines: List[str], line_idx: int, end_idx: int) -> bool:
        """Return True if the `;` at the end of ``lines[line_idx]`` terminates a multi-line node.

        A trailing `;` is the real terminator when the next non-empty line is a new node
        marker, a comment, a meta directive, or end-of-content. Otherwise the `;` is
        internal to the node's text and multi-line collection should continue.
        """
        peek_i = line_idx + 1
        while peek_i < end_idx and not lines[peek_i].strip():
            peek_i += 1
        if peek_i >= end_idx:
            return True
        stripped = lines[peek_i].strip()
        return stripped.startswith("*") or stripped.startswith("'") or stripped.startswith("@")

    def create_xml_node(self, parent: ET.Element, text: str) -> ET.Element:
        """Create a Freemind XML node under parent, extracting any [[url label]] hyperlink."""
        # Extract the first [[url label]] or [[url]] hyperlink; only one URI per node is supported.

        link_match = re.search(r"\[\[(.*?)(?: (.*?))?\]\]", text)
        uri = None
        if link_match:
            raw_url = link_match.group(1)
            label = link_match.group(2)

            if label:
                # Replace the whole [[...]] block with just the label
                text = text.replace(link_match.group(0), label)
                uri = raw_url
            else:
                # [[url]] -> Label is url
                text = text.replace(link_match.group(0), raw_url)
                uri = raw_url

        node = ET.SubElement(parent, "node")
        node.set("TEXT", text)
        node.set("FOLDED", "false")

        if uri:
            hook = ET.SubElement(node, "hook")
            hook.set("NAME", "ExternalObject")
            hook.set("URI", uri)

        return node

    def plantuml_to_freemind(self, plantuml_string: str) -> str:
        """Convert a PlantUML mindmap string to Freemind/Freeplane XML."""
        # Normalize line endings (\r\n from Windows, \r from legacy Mac) to \n
        # so split("\n") produces one logical line per source line.
        plantuml_string = plantuml_string.replace("\r\n", "\n").replace("\r", "\n")
        lines = plantuml_string.strip().split("\n")
        stripped_lines = [line.strip() for line in lines]
        try:
            start_idx = next(i for i, l in enumerate(stripped_lines) if l.startswith("@startmindmap"))
            end_idx = next(i for i, l in enumerate(stripped_lines) if l.startswith("@endmindmap"))
        except StopIteration:
            raise ValueError("Input is not a valid PlantUML mindmap (missing @startmindmap or @endmindmap).")
        if end_idx <= start_idx:
            raise ValueError("Input is not a valid PlantUML mindmap (@endmindmap must come after @startmindmap).")

        root = ET.Element("map")
        root.set("version", self.xml_version)
        node_stack: List[ET.Element] = []

        first_node_found = False

        i = start_idx + 1
        while i < end_idx:
            line = lines[i]
            stripped = line.strip()

            if not stripped or stripped.startswith("'"):
                i += 1
                continue

            parsed = self.parse_plantuml_line(line)
            if parsed:
                level, text, is_multiline_start = parsed
                i_advanced = False

                if is_multiline_start:
                    # A trailing `;` is the multiline terminator only when followed by a
                    # new node/comment/meta directive or EOF. Otherwise it is internal
                    # to the node's text; this preserves `;\n` mid-text on round-trip.
                    if text.endswith(";") and self._is_multiline_terminator(lines, i, end_idx):
                        text = text[:-1]
                    else:
                        multiline_text = [text]
                        i += 1
                        while i < end_idx:
                            current_line = lines[i].strip()
                            if current_line.endswith(";") and self._is_multiline_terminator(lines, i, end_idx):
                                multiline_text.append(current_line[:-1])
                                i += 1
                                break
                            else:
                                multiline_text.append(current_line)
                                i += 1
                        else:
                            raise ValueError(
                                "Unterminated multiline node: missing closing ';'."
                            )
                        text = "\n".join(multiline_text)
                        # i is already positioned past the closing ; line
                        i_advanced = True

                if not first_node_found:
                    root_node = self.create_xml_node(root, text)
                    node_stack.append(root_node)
                    first_node_found = True
                    if not i_advanced:
                        i += 1
                    continue

                while len(node_stack) >= level:
                    node_stack.pop()

                if not node_stack:
                    new_node = self.create_xml_node(root, text)
                    node_stack.append(new_node)
                else:
                    parent_node = node_stack[-1]
                    new_node = self.create_xml_node(parent_node, text)
                    node_stack.append(new_node)

                if not i_advanced:
                    i += 1
            else:
                i += 1

        return ET.tostring(root, encoding="unicode", method="xml")

    def _create_md_xml_node(self, parent: ET.Element, text: str) -> ET.Element:
        """Create a Freemind XML node from Markdown text, extracting ``[text](url)`` links.

        Args:
            parent: Parent XML element.
            text: Markdown text (may contain a ``[label](url)`` link).

        Returns:
            The newly created XML ``<node>`` element.
        """
        uri = None

        # Extract markdown link [text](url)
        link_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", text)
        if link_match:
            label = link_match.group(1)
            url = link_match.group(2)
            text = text[:link_match.start()] + label + text[link_match.end():]
            uri = url

        # Convert <br> back to newlines
        text = text.replace("<br>", "\n")

        node = ET.SubElement(parent, "node")
        node.set("TEXT", text)
        node.set("FOLDED", "false")

        if uri:
            hook = ET.SubElement(node, "hook")
            hook.set("NAME", "ExternalObject")
            hook.set("URI", uri)

        return node

    def markdown_to_freemind(self, content: str) -> str:
        """Convert a Markdown nested list string to Freemind/Freeplane XML.

        The first ``# H1`` header becomes the root node. Nested list items
        (``-``, ``*``, ``+``) become child nodes. Indentation determines depth
        (any consistent indentation works). ``[text](url)`` links are converted
        to Freemind hook elements. ``<br>`` tags in text are converted to newlines.

        Args:
            content: Markdown string with an H1 header and nested lists.

        Returns:
            Freemind XML string.

        Raises:
            ValueError: If no H1 header is found in the content.
        """
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        lines = content.split("\n")

        root = ET.Element("map")
        root.set("version", self.xml_version)

        # Stack of (indent_level, ET.Element) for tracking hierarchy.
        # The root node uses indent_level -1 so all list items are its children.
        node_stack: List[Tuple[int, ET.Element]] = []
        root_found = False

        for line in lines:
            if not line.strip():
                continue

            # Check for H1 header (root node)
            if not root_found:
                h1_match = re.match(r"^#\s+(.+)$", line.strip())
                if h1_match:
                    text = h1_match.group(1).strip()
                    root_node = self._create_md_xml_node(root, text)
                    node_stack = [(-1, root_node)]
                    root_found = True
                    continue

            # Check for list item (-, *, or + markers)
            list_match = re.match(r"^(\s*)([-*+])\s+(.+)$", line)
            if list_match and root_found:
                indent = len(list_match.group(1))
                text = list_match.group(3).strip()

                # Pop stack until we find a parent with a strictly lower indent
                while len(node_stack) > 1 and node_stack[-1][0] >= indent:
                    node_stack.pop()

                parent = node_stack[-1][1]
                new_node = self._create_md_xml_node(parent, text)
                node_stack.append((indent, new_node))

        if not root_found:
            raise ValueError("No H1 header found in Markdown content for root node.")

        return ET.tostring(root, encoding="unicode", method="xml")

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert between Freemind, PlantUML, and Markdown mindmaps.")
    parser.add_argument("input_file", help="Path to the input file.")
    parser.add_argument("-o", "--output_file", help="Path to the output file. If not provided, output will be printed to stdout.")
    parser.add_argument("--to-md", action="store_true", help="Force output to Markdown format (input must be .mm).")
    parser.add_argument("--from-md", action="store_true", help="Force input from Markdown format (output will be .mm XML).")
    args = parser.parse_args()

    input_path: str = args.input_file
    output_path: Optional[str] = args.output_file

    converter = MindMapConverter()

    try:
        _, ext = os.path.splitext(input_path)
        out_ext = os.path.splitext(output_path)[1].lower() if output_path else ""

        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        if args.from_md or ext.lower() == ".md":
            output_content = converter.markdown_to_freemind(content)
        elif args.to_md or (ext.lower() == ".mm" and out_ext == ".md"):
            output_content = converter.freemind_to_markdown(content)
        elif ext.lower() == ".mm":
            output_content = converter.freemind_to_plantuml(content)
        else:
            output_content = converter.plantuml_to_freemind(content)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_content)
        else:
            print(output_content)

    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_path}'", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
