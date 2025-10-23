"""
Module to parse test suite objects into testlink xml.
"""
import os
from codecs import open
from io import BytesIO
from os.path import exists
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment
from xml.sax.saxutils import escape

from xml.dom import minidom

from .datatype import TestStep, TestSuite, TestCase, cache


class Tags():
    xml = 'xml'
    testsuite = "testsuite"
    details = 'details'
    testcase = 'testcase'
    summary = 'summary'
    precoditions = 'preconditions'
    steps = 'steps'
    step = 'step'
    step_number = 'step_number'
    actions = 'actions'
    expected = 'expectedresults'
    execution_type = 'execution_type'
    importance = 'importance'
    requirements = 'requirements'
    requirement = 'requirement'
    req_spec_title = 'req_spec_title'
    doc_id = 'doc_id'
    version = 'version'
    title = 'title'


class Attributes():
    name = 'name'


def parse_requirements_xml(req_xml_file):
    """Parses a TestLink requirements XML file and returns a dict."""
    requirements = {}
    if not req_xml_file or not exists(req_xml_file):
        return requirements

    try:
        tree = ElementTree.parse(req_xml_file)
        root = tree.getroot()
        # Find all requirement nodes
        for req_node in root.findall('.//requirement'):
            doc_id_node = req_node.find('doc_id')
            if doc_id_node is not None and doc_id_node.text:
                doc_id = doc_id_node.text.strip()
                requirements[doc_id] = {
                    'req_spec_title': req_node.findtext('req_spec_title', default='').strip(),
                    'title': req_node.findtext('title', default='').strip(),
                    'version': req_node.findtext('version', default='').strip(),
                }
    except ElementTree.ParseError as e:
        # Handle potential XML parsing errors
        print(f"Error parsing requirements XML file: {e}")
        return {}

    return requirements


def to_testlink_xml_file(testsuite, path_to_xml, req_xml=None):
    """Save test suite object to testlink xml file."""
    content = to_testlink_xml_content(testsuite, req_xml)
    if exists(path_to_xml):
        os.remove(path_to_xml)

    with open(path_to_xml, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(content))


def _convert_importance(importance_value):
    mapping = {1: '3', 2: '2', 3: '1'}
    if importance_value in mapping.keys():
        return mapping[importance_value]
    else:
        return '2'


def should_skip(item):
    return item is None or not isinstance(item, str) or item.strip() == '' or item.startswith('!')


def should_parse(item):
    return (isinstance(item, str) and not item.startswith('!')) or isinstance(item, int)


def to_testlink_xml_content(testsuite, req_xml=None):
    assert isinstance(testsuite, TestSuite)
    requirements = parse_requirements_xml(req_xml)
    root_suite = Element(Tags.testsuite)
    root_suite.set(Attributes.name, testsuite.name)
    cache['testcase_count'] = 0

    for suite in testsuite.sub_suites:
        assert isinstance(suite, TestSuite)

        if should_skip(suite.name):
            continue

        suite_element = SubElement(root_suite, Tags.testsuite)
        suite_element.set(Attributes.name, suite.name)
        build_text_field(suite_element, Tags.details, suite.details)
        build_testcase_xml(suite, suite_element, requirements)

    tree = ElementTree.ElementTree(root_suite)
    f = BytesIO()
    tree.write(f, encoding='utf-8', xml_declaration=True)
    return f.getvalue()


def build_text_field(element, tag, value):
    if should_parse(value):
        e = SubElement(element, tag)
        set_text(e, value)


def build_testcase_xml(suite, suite_element, requirements=None):
    if requirements is None:
        requirements = {}
    for testcase in suite.testcase_list:
        assert isinstance(testcase, TestCase)

        if should_skip(testcase.name):
            continue

        cache['testcase_count'] += 1
        testcase_element = SubElement(suite_element, Tags.testcase)
        testcase_element.set(Attributes.name, testcase.name)

        build_text_field(testcase_element, Tags.summary, testcase.summary)
        build_text_field(testcase_element, Tags.precoditions, testcase.preconditions)
        build_text_field(testcase_element, Tags.execution_type, testcase.execution_type)

        e = SubElement(testcase_element, Tags.importance)
        e.text = _convert_importance(testcase.importance)

        build_requirements_xml(testcase, testcase_element, requirements)
        build_step_xml(testcase, testcase_element)


def build_requirements_xml(testcase, testcase_element, requirements):
    """Builds the requirements XML block for a testcase."""
    if testcase.doc_id and testcase.doc_id in requirements:
        req_data = requirements[testcase.doc_id]
        requirements_element = SubElement(testcase_element, Tags.requirements)
        requirement_element = SubElement(requirements_element, Tags.requirement)
        build_text_field(requirement_element, Tags.req_spec_title, req_data.get('req_spec_title'))
        build_text_field(requirement_element, Tags.doc_id, testcase.doc_id)
        build_text_field(requirement_element, Tags.version, req_data.get('version'))
        build_text_field(requirement_element, Tags.title, req_data.get('title'))


def build_step_xml(testcase, testcase_element):
    if testcase.steps:
        steps_element = SubElement(testcase_element, Tags.steps)

        for step in testcase.steps:
            assert isinstance(step, TestStep)

            if should_skip(step.action):
                continue
            else:
                step_element = SubElement(steps_element, Tags.step)

            build_text_field(step_element, Tags.actions, step.action)
            build_text_field(step_element, Tags.expected, step.expected)
            build_text_field(step_element, Tags.execution_type, step.execution_type)

            e = SubElement(step_element, Tags.step_number)
            e.text = str(step.number)


def set_text(element, content):
    if isinstance(content, int):
        element.text = str(content)
    elif content:
        content = escape(content, entities={'\r\n': '<br />'})  # retain html tags in text
        content = content.replace("\n", "<br />")  # replace new line for *nix system
        content = content.replace("<br />", "<br />\n")  # add the line break in source to make it readable

        # trick to add CDATA for element tree lib
        element.append(Comment(' --><![CDATA[' + content.replace(']]>', ']]]]><![CDATA[>') + ']]><!-- '))


def prettify_xml(xml_string):
    """Return a pretty-printed XML string for the Element.
    """
    parsed = minidom.parseString(xml_string)
    return parsed.toprettyxml(indent="\t")
