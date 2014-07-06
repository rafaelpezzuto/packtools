#coding: utf-8
import unittest
from StringIO import StringIO
from tempfile import NamedTemporaryFile

from lxml import etree, isoschematron

from packtools import stylechecker
from packtools.adapters import StyleError


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


class XMLValidatorTests(unittest.TestCase):

    @setup_tmpfile
    def test_initializes_with_filepath(self):
        self.assertTrue(stylechecker.XMLValidator(self.valid_tmpfile.name, no_doctype=True))

    def test_initializes_with_etree(self):
        fp = StringIO(b'<a><b>bar</b></a>')
        et = etree.parse(fp)

        self.assertTrue(stylechecker.XMLValidator(et, no_doctype=True))

    def test_validation(self):
        fp = etree.parse(StringIO(b'<a><b>bar</b></a>'))
        xml = stylechecker.XMLValidator(fp, no_doctype=True)
        xml.dtd = etree.XMLSchema(etree.parse(sample_xsd))

        result, errors = xml.validate()
        self.assertTrue(result)
        self.assertFalse(errors)

    def test_invalid(self):
        fp = etree.parse(StringIO(b'<a><c>bar</c></a>'))
        xml = stylechecker.XMLValidator(fp, no_doctype=True)
        xml.dtd = etree.XMLSchema(etree.parse(sample_xsd))

        result, _ = xml.validate()
        self.assertFalse(result)

    def test_invalid_errors(self):
        # Default lxml error log.
        fp = etree.parse(StringIO(b'<a><c>bar</c></a>'))
        xml = stylechecker.XMLValidator(fp, no_doctype=True)
        xml.dtd = etree.XMLSchema(etree.parse(sample_xsd))

        _, errors = xml.validate()
        for error in errors:
            self.assertIsInstance(error, StyleError)

    def test_annotate_errors(self):
        fp = etree.parse(StringIO(b'<a><c>bar</c></a>'))
        xml = stylechecker.XMLValidator(fp, no_doctype=True)
        xml.dtd = etree.XMLSchema(etree.parse(sample_xsd))

        err_xml = xml.annotate_errors()
        xml_text = etree.tostring(err_xml)

        self.assertIn("<!--SPS-ERROR: Element 'c': This element is not expected. Expected is ( b ).-->", xml_text)

    def test_validation_schematron(self):
        fp = etree.parse(StringIO(b'<Total><Percent>70</Percent><Percent>30</Percent></Total>'))
        xml = stylechecker.XMLValidator(fp, no_doctype=True)
        xml.schematron = isoschematron.Schematron(etree.parse(sample_sch))

        result, errors = xml._validate_sch()
        self.assertTrue(result)
        self.assertFalse(errors)

    def test_invalid_schematron(self):
        fp = etree.parse(StringIO(b'<Total><Percent>60</Percent><Percent>30</Percent></Total>'))
        xml = stylechecker.XMLValidator(fp, no_doctype=True)
        xml.schematron = isoschematron.Schematron(etree.parse(sample_sch))

        result, errors = xml._validate_sch()
        self.assertFalse(result)
        self.assertTrue(errors)

    def test_annotate_errors_schematron(self):
        fp = etree.parse(StringIO(b'<Total><Percent>60</Percent><Percent>30</Percent></Total>'))
        xml = stylechecker.XMLValidator(fp, no_doctype=True)
        xml.schematron = isoschematron.Schematron(etree.parse(sample_sch))
        xml.dtd = etree.XMLSchema(etree.parse(sample_xsd))

        err_xml = xml.annotate_errors()
        xml_text = etree.tostring(err_xml)

        self.assertIn("<!--SPS-ERROR: Element 'Total': Sum is not 100%.-->", xml_text)

    def test_fails_without_doctype_declaration(self):
        fp = StringIO(b'<a><b>bar</b></a>')
        et = etree.parse(fp)

        self.assertRaises(ValueError, lambda: stylechecker.XMLValidator(et, no_doctype=False))

    def test_checks_allowed_doctype_public_ids(self):
        fp = StringIO(b'<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.0 20120330//EN" "JATS-journalpublishing1.dtd"><a><b>bar</b></a>')
        et = etree.parse(fp)

        self.assertTrue(stylechecker.XMLValidator(et, no_doctype=False))

