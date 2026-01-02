#!/usr/bin/env python3
import re
import xml.etree.ElementTree as ET
import sys
import os
import argparse
from typing import Optional, Tuple, List, TextIO

class MindMapConverter:
    def __init__(self):
        self.xml_version = "freeplane 1.9.13"

    def parse_xml_node(self, node: ET.Element, level: int) -> str:
        text = node.get("TEXT", "")
        # PlantUML standard syntax: * Node Level 1, ** Node Level 2, etc.
        plantuml_node = f"{'*' * level} {text}"
        for child in node.findall("node"):
            plantuml_node += "\n" + self.parse_xml_node(child, level + 1)
        return plantuml_node

    def freemind_to_plantuml(self, content: str) -> str:
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Error parsing XML content: {e}")

        # If the root is 'map', we iterate over its children 'node'
        # The 'map' element itself isn't a visual node usually in these exports, 
        # but the first child 'node' is the center.
        plantuml_lines = ["@startmindmap"]
        
        # Handle the case where the root might be the map element or a node directly
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

    def parse_plantuml_line(self, line: str) -> Optional[Tuple[int, str]]:
        # Matches lines like:
        # * Root
        # ** Child
        # *_ Root (Legacy support)
        # **_ Child (Legacy support)
        # Also handles indentation spaces if present
        match = re.match(r"^\s*(\*+)(?:_)?\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            return level, text
        return None

    def create_xml_node(self, parent: ET.Element, text: str) -> ET.Element:
        node = ET.SubElement(parent, "node")
        node.set("TEXT", text)
        node.set("FOLDED", "false")
        return node

    def plantuml_to_freemind(self, plantuml_string: str) -> str:
        lines = plantuml_string.strip().split("\n")
        # Basic validation
        valid_start = any(line.strip().startswith("@startmindmap") for line in lines)
        valid_end = any(line.strip().startswith("@endmindmap") for line in lines)
        
        if not (valid_start and valid_end):
             raise ValueError("Input is not a valid PlantUML mindmap (missing @startmindmap or @endmindmap).")

        root = ET.Element("map")
        root.set("version", self.xml_version)
        node_stack: List[ET.Element] = []
        
        first_node_found = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("@startmindmap") or stripped.startswith("@endmindmap"):
                continue
            
            # Skip empty lines or comments if any (simple handling)
            if not stripped or stripped.startswith("'"):
                continue

            level_text = self.parse_plantuml_line(line)
            if level_text:
                level, text = level_text
                
                if not first_node_found:
                    # The first node is the root node of the mindmap.
                    # In Freemind, the first node under <map> is the central topic.
                    # We accept whatever level parsing gives, but typically it should be level 1.
                    root_node = self.create_xml_node(root, text)
                    node_stack.append(root_node)
                    first_node_found = True
                    # We reset the stack to just this root node, effectively ignoring 
                    # whatever absolute level was provided for the root (normalizing it to base)
                    # But if we want to respect hierarchy if multiple roots appear (forest), 
                    # that's complex. Assuming single root for mindmaps.
                    
                    # Correction: node_stack needs to track depth. 
                    # If the first node is `*`, it's level 1.
                    # We put it at stack index 0 (logic level 1).
                    continue

                # Adjust stack for current level
                # If level is 2 (**), we want parent at stack index 0 (level 1).
                # So we pop until stack has 'level - 1' items.
                while len(node_stack) >= level:
                    node_stack.pop()
                
                if not node_stack:
                    # This happens if we have a second root or disjoint tree, 
                    # or level jumped weirdly (e.g. * then * again at top level).
                    # We treat it as a sibling of the previous root? 
                    # Freemind XML usually expects one main root node inside <map>.
                    # We'll just append to map root to be safe, essentially creating multi-root.
                    new_node = self.create_xml_node(root, text)
                    node_stack.append(new_node)
                else:
                    parent_node = node_stack[-1]
                    new_node = self.create_xml_node(parent_node, text)
                    node_stack.append(new_node)

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
