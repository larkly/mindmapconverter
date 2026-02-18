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

if __name__ == '__main__':
    unittest.main()
