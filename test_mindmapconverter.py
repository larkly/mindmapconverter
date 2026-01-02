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

if __name__ == '__main__':
    unittest.main()
