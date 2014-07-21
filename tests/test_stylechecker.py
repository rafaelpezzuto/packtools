#coding: utf-8
import unittest
from StringIO import StringIO
from tempfile import NamedTemporaryFile

from lxml import etree, isoschematron

from packtools import stylechecker
from packtools.errors import StyleError


# valid: <a><b></b></a>
# invalid: anything else
sample_xsd = StringIO('''\
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<xsd:element name="a" type="AType"/>
<xsd:complexType name="AType">
  <xsd:sequence>
    <xsd:element name="b" type="xsd:string" />
  </xsd:sequence>
</xsd:complexType>
</xsd:schema>
''')


sample_sch = StringIO('''\
<schema xmlns="http://purl.oclc.org/dsdl/schematron">
  <pattern id="sum_equals_100_percent">
    <title>Sum equals 100%.</title>
    <rule context="Total">
      <assert test="sum(//Percent)=100">Element 'Total': Sum is not 100%.</assert>
    </rule>
  </pattern>
</schema>
''')


def setup_tmpfile(method):
    def wrapper(self):
        valid_tmpfile = NamedTemporaryFile()
        valid_tmpfile.write(b'<a><b>bar</b></a>')
        valid_tmpfile.seek(0)
        self.valid_tmpfile = valid_tmpfile

        method(self)

        self.valid_tmpfile.close()
    return wrapper


class XMLTests(unittest.TestCase):

    @setup_tmpfile
    def test_initializes_with_filepath(self):
        self.assertTrue(stylechecker.XML(self.valid_tmpfile.name))

    def test_initializes_with_etree(self):
        fp = StringIO(b'<a><b>bar</b></a>')
        et = etree.parse(fp)

        self.assertTrue(stylechecker.XML(et))

    def test_validation(self):
        fp = etree.parse(StringIO(b'<a><b>bar</b></a>'))
        xml = stylechecker.XML(fp)
        xml.xmlschema = etree.XMLSchema(etree.parse(sample_xsd))

        result, errors = xml.validate()
        self.assertTrue(result)
        self.assertFalse(errors)

    def test_invalid(self):
        fp = etree.parse(StringIO(b'<a><c>bar</c></a>'))
        xml = stylechecker.XML(fp)
        xml.xmlschema = etree.XMLSchema(etree.parse(sample_xsd))

        result, _ = xml.validate()
        self.assertFalse(result)

    def test_invalid_errors(self):
        # Default lxml error log.
        fp = etree.parse(StringIO(b'<a><c>bar</c></a>'))
        xml = stylechecker.XML(fp)
        xml.xmlschema = etree.XMLSchema(etree.parse(sample_xsd))

        _, errors = xml.validate()
        for error in errors:
            self.assertIsInstance(error, StyleError)

    def test_annotate_errors(self):
        fp = etree.parse(StringIO(b'<a><c>bar</c></a>'))
        xml = stylechecker.XML(fp)
        xml.xmlschema = etree.XMLSchema(etree.parse(sample_xsd))

        xml.annotate_errors()
        xml_text = xml.read()

        self.assertIn("<!--SPS-ERROR: Element 'c': This element is not expected. Expected is ( b ).-->", xml_text)
        self.assertTrue(isinstance(xml_text, unicode))

    def test_validation_schematron(self):
        fp = etree.parse(StringIO(b'<Total><Percent>70</Percent><Percent>30</Percent></Total>'))
        xml = stylechecker.XML(fp)
        xml.schematron = isoschematron.Schematron(etree.parse(sample_sch))

        result, errors = xml._validate_sch()
        self.assertTrue(result)
        self.assertFalse(errors)

    def test_invalid_schematron(self):
        fp = etree.parse(StringIO(b'<Total><Percent>60</Percent><Percent>30</Percent></Total>'))
        xml = stylechecker.XML(fp)
        xml.schematron = isoschematron.Schematron(etree.parse(sample_sch))

        result, errors = xml._validate_sch()
        self.assertFalse(result)
        self.assertTrue(errors)

    def test_annotate_errors_schematron(self):
        fp = etree.parse(StringIO(b'<Total><Percent>60</Percent><Percent>30</Percent></Total>'))
        xml = stylechecker.XML(fp)
        xml.schematron = isoschematron.Schematron(etree.parse(sample_sch))

        xml.annotate_errors()
        xml_text = xml.read()

        self.assertIn("<!--SPS-ERROR: Element 'Total': Sum is not 100%.-->", xml_text)
        self.assertTrue(isinstance(xml_text, unicode))

