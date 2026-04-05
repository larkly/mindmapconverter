#!/usr/bin/env python3
import re
import xml.etree.ElementTree as ET
import sys
import os
import argparse
from typing import Optional, Tuple, List

class MindMapConverter:
    """Bidirectional converter between Freemind/Freeplane (.mm) and PlantUML mindmap (.puml) formats."""

    def __init__(self):
        self.xml_version = "freeplane 1.9.13"

    def parse_xml_node(self, node: ET.Element, level: int) -> str:
        """Recursively convert a Freemind XML node (and its children) to PlantUML lines."""
        text = node.get("TEXT", "")

        # Check for hyperlinks
        link = None
        for hook in node.findall("hook"):
            if hook.get("URI"):
                link = hook.get("URI")
                break

        if link:
            # PlantUML format: [[url label]]
            if text == link:
                text = f"[[{link}]]"
            else:
                text = f"[[{link} {text}]]"

        # Check for multiline
        if "\n" in text:
            # PlantUML arithmetic/multiline syntax
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
                text = text[1:].strip()  # Remove leading :
            return level, text, is_multiline_start
        return None

    def create_xml_node(self, parent: ET.Element, text: str) -> ET.Element:
        """Create a Freemind XML node under parent, extracting any [[url label]] hyperlink."""
        link_match = re.search(r"\[\[(.*?)(?: (.*?))?\]\]", text)
        uri = None
        if link_match:
            raw_url = link_match.group(1)
            label = link_match.group(2)

            if label:
                text = text.replace(link_match.group(0), label)
                uri = raw_url
            else:
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

    def _extract_content(self, lines: List[str]) -> Tuple[List[str], str]:
        """Extract content between @startmindmap and @endmindmap markers.

        Returns
        -------
        tuple[list[str], str]
            The content lines and any title text found on the @startmindmap line.
        """
        stripped_lines = [line.strip() for line in lines]

        try:
            start_idx = next(
                i for i, l in enumerate(stripped_lines) if l.startswith("@startmindmap")
            )
            end_idx = next(
                i for i, l in enumerate(stripped_lines) if l.startswith("@endmindmap")
            )
        except StopIteration:
            raise ValueError(
                "Input is not a valid PlantUML mindmap "
                "(missing @startmindmap or @endmindmap)."
            )

        if end_idx <= start_idx:
            raise ValueError(
                "Input is not a valid PlantUML mindmap "
                "(@endmindmap must come after @startmindmap)."
            )

        # Extract title: anything after "@startmindmap" on the opening line
        title_text = ""
        start_line = stripped_lines[start_idx]
        after_marker = start_line[len("@startmindmap"):].strip()
        if after_marker:
            title_text = after_marker

        return lines[start_idx + 1: end_idx], title_text

    def _collect_multiline(self, text: str, source_lines: List[str],
                           start_pos: int, end_marker: int) -> str:
        """Collect continuation lines for a multiline node.

        Parameters
        ----------
        text : str
            Initial text after the leading colon.
        source_lines : list[str]
            All lines from the original input (indexed identically to *lines* in
            ``plantuml_to_freemind``).
        start_pos : int
            Index of the line that started the multiline block.
        end_marker : int
            Index of the ``@endmindmap`` line (exclusive upper bound).

        Returns
        -------
        str
            The fully assembled multiline text (without the trailing semicolon).
        """
        if text.endswith(";"):
            return text[:-1], start_pos + 1

        parts = [text]
        i = start_pos + 1
        while i < end_marker:
            next_stripped = source_lines[i].strip()
            if next_stripped.endswith(";"):
                parts.append(next_stripped[:-1])
                return "\n".join(parts), i + 1
            parts.append(next_stripped)
            i += 1

        raise ValueError("Unterminated multiline node: missing closing ';'.")

    def plantuml_to_freemind(self, plantuml_string: str) -> str:
        """Convert a PlantUML mindmap string to Freemind/Freeplane XML."""
        lines = plantuml_string.strip().split("\n")
        content_lines, title_text = self._extract_content(lines)

        # Build a quick lookup: for each line in *content_lines* find its
        # index inside the original *lines* list.  This is O(n) overall
        # because both lists share the same ordering.
        orig_indices = []
        ci = 0
        for line in lines:
            if ci < len(content_lines) and line == content_lines[ci]:
                orig_indices.append(ci)
                ci += 1

        root = ET.Element("map")
        root.set("version", self.xml_version)
        if title_text:
            root.set("title", title_text)
        # node_stack[0] is always the root element.
        node_stack: List[ET.Element] = [root]

        idx = 0
        while idx < len(content_lines):
            line = content_lines[idx]
            stripped = line.strip()

            # Skip blank lines and comments
            if not stripped or stripped.startswith("'"):
                idx += 1
                continue

            parsed = self.parse_plantuml_line(line)
            if not parsed:
                idx += 1
                continue

            level, text, is_multiline_start = parsed

            if is_multiline_start:
                text, idx = self._collect_multiline(
                    text, content_lines, idx, len(content_lines)
                )
            else:
                idx += 1

            # Pop back so that stack[-1] is the parent for *level*.
            while len(node_stack) > level:
                node_stack.pop()

            parent = node_stack[-1]
            new_node = self.create_xml_node(parent, text)
            node_stack.append(new_node)

        return ET.tostring(root, encoding="unicode", method="xml")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert between Freemind and PlantUML mindmaps."
    )
    parser.add_argument("input_file", help="Path to the input file.")
    parser.add_argument(
        "-o", "--output_file",
        help="Path to the output file. If not provided, output goes to stdout."
    )
    args = parser.parse_args()

    converter = MindMapConverter()

    try:
        _, ext = os.path.splitext(args.input_file)

        with open(args.input_file, "r", encoding="utf-8") as f:
            content = f.read()

        if ext.lower() == ".mm":
            output_content = converter.freemind_to_plantuml(content)
        else:
            output_content = converter.plantuml_to_freemind(content)

        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(output_content)
        else:
            print(output_content)

    except FileNotFoundError:
        print(f"Error: Input file not found at '{args.input_file}'",
              file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
