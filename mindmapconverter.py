import re
import xml.etree.ElementTree as ET
import sys
import os
import argparse

def parse_node(node, level):
    text = node.get("TEXT")
    plantuml_node = f"{'*' * level}_ {text}"
    for child in node.findall("node"):
        plantuml_node += "\n" + parse_node(child, level + 1)
    return plantuml_node

def freemind_to_plantuml(file_path):
    try:
        tree = ET.parse(file_path)
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        sys.exit(1)

    root = tree.getroot()
    plantuml = "@startmindmap\n"
    for child in root.findall("node"):
        plantuml += parse_node(child, 1)
    plantuml += "\n@endmindmap"
    return plantuml

def parse_line(line):
    match = re.match(r"(\*+)_ (.+)", line.strip())
    if match:
        level = len(match.group(1))
        text = match.group(2)
        return level, text
    return None, None

def create_node(parent, level, text):
    node = ET.SubElement(parent, "node")
    node.set("TEXT", text)
    node.set("FOLDED", "false")
    return node

def plantuml_to_freemind(plantuml_string):
    lines = plantuml_string.strip().split("\n")
    root = ET.Element("map")
    root.set("version", "freeplane 1.9.13")
    node_stack = []

    for line in lines:
        if line.startswith("@startmindmap") or line.startswith("@endmindmap"):
            continue

        level, text = parse_line(line)
        if level is not None and text:
            while len(node_stack) >= level:
                node_stack.pop()
            parent_node = node_stack[-1] if node_stack else root
            new_node = create_node(parent_node, level, text)
            node_stack.append(new_node)

    return ET.tostring(root, encoding="unicode", method="xml")

def main():
    parser = argparse.ArgumentParser(description="Convert between Freemind and PlantUML mindmaps.")
    parser.add_argument("input_file", help="Path to the input file.")
    parser.add_argument("-o", "--output_file", help="Path to the output file. If not provided, output will be printed to stdout.")
    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output_file
    file_extension = os.path.splitext(input_file)[1]

    if file_extension == ".mm":
        try:
            plantuml_mindmap = freemind_to_plantuml(input_file)
            if output_file:
                with open(output_file, "w") as file:
                    file.write(plantuml_mindmap)
            else:
                print(plantuml_mindmap)
        except FileNotFoundError:
            print(f"Error: Input file not found at '{input_file}'")
            sys.exit(1)
    else:
        try:
            with open(input_file, "r") as file:
                content = file.read()
            if "@startmindmap" in content and "@endmindmap" in content:
                freemind_xml = plantuml_to_freemind(content)
                if output_file:
                    with open(output_file, "w") as file:
                        file.write(freemind_xml)
                else:
                    print(freemind_xml)
            else:
                print("Error: Input file is not a valid PlantUML mindmap.")
                sys.exit(1)
        except FileNotFoundError:
            print(f"Error: Input file not found at '{input_file}'")
            sys.exit(1)

if __name__ == "__main__":
    main()
