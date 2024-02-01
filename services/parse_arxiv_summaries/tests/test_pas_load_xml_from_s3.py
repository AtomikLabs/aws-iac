import unittest
import defusedxml.ElementTree as ET
from collections import defaultdict
from io import StringIO
from unittest.mock import patch, mock_open
from services.parse_arxiv_summaries.src.parse_arxiv_summaries import parse_xml

class TestParseXML(unittest.TestCase):
    def setUp(self):
        with open("services/parse_arxiv_summaries/tests/resources/20240131-072844.json", "r") as file:
            self.xml_data = file.read()

    def test_valid_xml_data(self):
        xml_tree = ET.parse(StringIO(self.xml_data))
        result = parse_xml(xml_tree)
        self.assertIsInstance(result, dict)
        self.assertIn('records', result)
        self.assertTrue(len(result['records']) > 0)

    def test_invalid_xml_data(self):
        invalid_xml_data = "<invalid></invalid>"
        with self.assertRaises(ET.ParseError):
            parse_xml(ET.fromstring(invalid_xml_data))

    def test_empty_xml_data(self):
        empty_xml_data = "<root></root>"
        result = parse_xml(ET.fromstring(empty_xml_data))
        self.assertEqual(result, {'records': []})

    def test_xml_data_with_missing_elements(self):
        # Modify the XML to have missing elements like identifiers, authors, or categories
        modified_xml_data = "<root><record></record></root>"
        result = parse_xml(ET.fromstring(modified_xml_data))
        self.assertIn('records', result)
        for record in result['records']:
            self.assertIn('identifier', record)
            self.assertIn('authors', record)
            self.assertIn('primary_category', record)

    def test_xml_data_with_special_characters(self):
        special_char_xml = "<root><record><title>Test &amp; Title</title></record></root>"
        result = parse_xml(ET.fromstring(special_char_xml))
        self.assertIn('records', result)
        for record in result['records']:
            self.assertIn('title', record)
            self.assertEqual(record['title'], "Test & Title")

    def test_handling_of_namespace(self):
        # Use XML with namespaces to test namespace handling
        ns_xml_data = "<root xmlns:dc='http://purl.org/dc/elements/1.1/'><record><dc:title>Title</dc:title></record></root>"
        result = parse_xml(ET.fromstring(ns_xml_data))
        self.assertIn('records', result)

    def test_output_structure(self):
        xml_tree = ET.parse(StringIO(self.xml_data))
        result = parse_xml(xml_tree)
        self.assertTrue(all(isinstance(record, dict) for record in result['records']))

    def test_performance_on_large_xml_data(self):
        # Use a large XML file for testing performance
        large_xml_data = "<root>" + self.xml_data * 10 + "</root>"
        xml_tree = ET.parse(StringIO(large_xml_data))
        result = parse_xml(xml_tree)
        self.assertTrue(len(result['records']) > 0)

if __name__ == '__main__':
    unittest.main()
