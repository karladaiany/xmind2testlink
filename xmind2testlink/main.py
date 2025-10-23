"""
A tool to parse xmind file into testlink xml file, which will help
you generate a testlink recognized xml file, then you can import it
into testlink as test suites.

Usage:
 xmind2testlink [path_to_xmind_file] [-json]

Example:
 xmind2testlink C:\\tests\\testcase.xmind       => output xml
 xmind2testlink C:\\tests\\testcase.xmind -json => output json

"""

import json
import argparse

from xmind2testlink.testlink_parser import to_testlink_xml_file
from xmind2testlink.xmind_parser import xmind_to_suite, xmind_to_flat_dict


def xmind_to_testlink(xmind, req_xml=None):
    xml_out = xmind[:-5] + 'xml'
    suite = xmind_to_suite(xmind)
    to_testlink_xml_file(suite, xml_out, req_xml)
    return xml_out


def xmind_to_json(xmind):
    json_out = xmind[:-5] + 'json'
    with open(json_out, 'w', encoding='utf8') as f:
        f.write(json.dumps(xmind_to_flat_dict(xmind), indent=2))

    return json_out


def main():
    parser = argparse.ArgumentParser(description='Parse xmind file into testlink xml file.')
    parser.add_argument('xmind_file', help='The path to the xmind file.')
    parser.add_argument('-json', action='store_true', help='Output in json format.')
    parser.add_argument('--req-xml', help='The path to the requirement specification xml file.')
    args = parser.parse_args()

    if args.xmind_file.endswith('.xmind'):
        if args.json:
            file_out = xmind_to_json(args.xmind_file)
        else:
            file_out = xmind_to_testlink(args.xmind_file, args.req_xml)

        print('Generated: "{}"'.format(file_out))
    else:
        print('Please provide a valid .xmind file.')
        print(__doc__)


if __name__ == '__main__':
    main()
