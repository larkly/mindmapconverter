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
                    if text.endswith(";"):
                        # Single-line form: `:text;` — strip the semicolon
                        text = text[:-1]
                    else:
                        # Multi-line form: read continuation lines until one ends with ;
                        multiline_text = [text]
                        i += 1
                        while i < end_idx:
                            next_line = lines[i].strip()
                            if next_line.endswith(";"):
                                multiline_text.append(next_line[:-1])
                                i += 1
                                break
                            else:
                                multiline_text.append(lines[i].rstrip())
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

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert between Freemind and PlantUML mindmaps.")
    parser.add_argument("input_file", help="Path to the input file.")
    parser.add_argument("-o", "--output_file", help="Path to the output file. If not provided, output will be printed to stdout.")
    args = parser.parse_args()

    input_path: str = args.input_file
    output_path: Optional[str] = args.output_file

    converter = MindMapConverter()

    try:
        # Determine conversion direction
        _, ext = os.path.splitext(input_path)

        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        if ext.lower() == ".mm":
            output_content = converter.freemind_to_plantuml(content)
        else:
            # Assume PlantUML if not .mm, or explicit .puml/.plantuml
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
