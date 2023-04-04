import re
import xml.etree.ElementTree as ET
import sys
import os

def parse_node(node, level):
    text = node.get("TEXT")
    plantuml_node = f"{'*' * level}_ {text}"
    for child in node.findall("node"):
        plantuml_node += "\n" + parse_node(child, level + 1)
    return plantuml_node

def freemind_to_plantuml(file_path):
    tree = ET.parse(file_path)
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
            new_node = create_node(node_stack[-1] if node_stack else root, level, text)
            node_stack.append(new_node)

    return ET.tostring(root, encoding="unicode", method="xml")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mindmapconverter.py <input_file>")
    else:
        input_file = sys.argv[1]
        file_extension = os.path.splitext(input_file)[1]

        if file_extension == ".mm":
            plantuml_mindmap = freemind_to_plantuml(input_file)
            print(plantuml_mindmap)
        else:
            with open(input_file, "r") as file:
                plantuml_mindmap = file.read()
            freemind_xml = plantuml_to_freemind(plantuml_mindmap)
            print(freemind_xml)
