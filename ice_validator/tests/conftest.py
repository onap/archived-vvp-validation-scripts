# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2018 AT&T Intellectual Property. All rights reserved.
# ===================================================================
#
# Unless otherwise specified, all software contained herein is licensed
# under the Apache License, Version 2.0 (the "License");
# you may not use this software except in compliance with the License.
# You may obtain a copy of the License at
#
#             http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
#
# Unless otherwise specified, all documentation contained herein is licensed
# under the Creative Commons License, Attribution 4.0 Intl. (the "License");
# you may not use this documentation except in compliance with the License.
# You may obtain a copy of the License at
#
#             https://creativecommons.org/licenses/by/4.0/
#
# Unless required by applicable law or agreed to in writing, documentation
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ============LICENSE_END============================================

import collections
import csv
import datetime
import hashlib
import io
import json
import os
import sys
import time

import docutils.core
import pytest
from more_itertools import partition
from six import string_types
import xlsxwriter

__path__ = [os.path.dirname(os.path.abspath(__file__))]

resolution_steps_file = "resolution_steps.json"
requirements_file = "requirements.json"

FAILURE_DATA = {}

report_columns = [
    ("Input File", "file"),
    ("Test", "test_file"),
    ("Requirements", "req_description"),
    ("Resolution Steps", "resolution_steps"),
    ("Error Message", "message"),
    ("Raw Test Output", "raw_output"),
]
report = collections.OrderedDict(report_columns)


def extract_error_msg(rep):
    msg = str(rep.longrepr.reprcrash)
    if "AssertionError:" in msg:
        return msg.split("AssertionError:")[1]
    else:
        return msg


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):

    outcome = yield
    rep = outcome.get_result()

    output_dir = "{}/../output".format(__path__[0])
    if rep.outcome == "failed":
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        if hasattr(item.function, "requirement_ids"):
            requirement_ids = item.function.requirement_ids
        else:
            requirement_ids = ""

        if "environment_pair" in item.fixturenames:
            resolved_pair = "{} environment pair".format(
                item.funcargs["environment_pair"]["name"]
            )
        elif "heat_volume_pair" in item.fixturenames:
            resolved_pair = "{} volume pair".format(
                item.funcargs["heat_volume_pair"]["name"]
            )
        elif "heat_templates" in item.fixturenames:
            resolved_pair = item.funcargs["heat_templates"]
        elif "yaml_files" in item.fixturenames:
            resolved_pair = item.funcargs["yaml_files"]
        else:
            resolved_pair = rep.nodeid.split("[")[1][:-1]

        FAILURE_DATA[len(FAILURE_DATA)] = {
            "file": resolved_pair,
            "vnfrqts": requirement_ids,
            "test": item.function.__name__,
            "test_file": item.function.__module__.split(".")[-1],
            "raw_output": str(rep.longrepr),
            "message": extract_error_msg(rep),
        }

        with open("{}/failures".format(output_dir), "w") as f:
            json.dump(FAILURE_DATA, f, indent=4)

def make_timestamp():
    timezone = time.tzname[time.localtime().tm_isdst]
    return "{} {}".format(str(datetime.datetime.now()), timezone)


def pytest_sessionfinish(session, exitstatus):
    if not session.config.option.template_dir:
        return
    template_path = os.path.abspath(session.config.option.template_dir[0])
    profile_name = session.config.option.validation_profile_name
    generate_report(
        "{}/../output".format(__path__[0]),
        template_path,
        profile_name,
        session.config.option.report_format,
    )


def pytest_runtest_setup(item):
    profile = item.session.config.option.validation_profile
    markers = set(m.name for m in item.iter_markers())
    if not profile and markers:
        pytest.skip("No validation profile selected. Skipping tests with marks.")
    if profile and markers and profile not in markers:
        pytest.skip("Doesn't match selection validation profile")


def make_href(path):
    paths = [path] if isinstance(path, string_types) else path
    links = []
    for p in paths:
        abs_path = os.path.abspath(p)
        filename = os.path.split(abs_path)[1]
        links.append(
            "<a href='file://{abs_path}' target='_blank'>{filename}</a>".format(
                abs_path=abs_path, filename=filename
            )
        )
    return "<br/>".join(links)


def generate_report(outpath, template_path, profile_name, output_format):
    failures = "{}/failures".format(outpath)
    faildata = None
    rdata = None
    hdata = None

    if os.path.exists(failures):
        with open(failures, "r") as f:
            faildata = json.loads(f.read())
    else:
        faildata = {}

    resolution_steps = "{}/../{}".format(__path__[0], resolution_steps_file)
    if os.path.exists(resolution_steps):
        with open(resolution_steps, "r") as f:
            rdata = json.loads(f.read())

    heat_requirements = "{}/../{}".format(__path__[0], requirements_file)
    if os.path.exists(heat_requirements):
        with open(heat_requirements, "r") as f:
            hdata = json.loads(f.read())

    # point requirements at the most recent version
    current_version = hdata["current_version"]
    hdata = hdata["versions"][current_version]["needs"]
    # mapping requirement IDs from failures to requirement descriptions
    for k, v in faildata.items():
        req_text = ""
        if v["vnfrqts"] != "":
            for req in v["vnfrqts"]:
                if req in hdata:
                    req_text += "\n\n{}: \n{}".format(req, hdata[req]["description"])
        faildata[k]["req_description"] = req_text

    # mapping resolution steps to module and test name
    for k, v in faildata.items():
        resolution_step = ""
        faildata[k]["resolution_steps"] = ""
        for rs in rdata:
            if v["test_file"] == rs["module"] and v["test"] == rs["function"]:
                faildata[k]["resolution_steps"] = "\n{}: \n{}".format(
                    rs["header"], rs["resolution_steps"]
                )
    output_format = output_format.lower().strip() if output_format else "html"
    if output_format == "html":
        generate_html_report(outpath, profile_name, template_path, faildata)
    elif output_format == "excel":
        generate_excel_report(outpath, profile_name, template_path, faildata)
    elif output_format == "csv":
        generate_csv_report(outpath, profile_name, template_path, faildata)
    else:
        raise ValueError("Unsupported output format: " + output_format)


def generate_csv_report(output_dir, profile_name, template_path, faildata):
    rows = []
    rows.append(["Validation Failures"])
    headers = [
        ("Profile Selected:", profile_name),
        ("Report Generated At:", make_timestamp()),
        ("Directory Validated:", template_path),
        ("Checksum:", hash_directory(template_path)),
        ("Total Errors:", len(faildata)),
    ]

    rows.append([])
    for header in headers:
        rows.append(header)
    rows.append([])

    # table header
    rows.append([col for col, _ in report_columns])

    # table content
    for data in faildata.values():
        rows.append(
            [
                data.get("file", ""),
                data.get("test_file", ""),
                data.get("req_description", ""),
                data.get("resolution_steps", ""),
                data.get("message", ""),
                data.get("raw_output", ""),
            ]
        )

    output_path = os.path.join(output_dir, "report.csv")
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def generate_excel_report(output_dir, profile_name, template_path, faildata):
    output_path = os.path.join(output_dir, "report.xlsx")
    workbook = xlsxwriter.Workbook(output_path)
    bold = workbook.add_format({"bold": True})
    code = workbook.add_format(({"font_name": "Courier", "text_wrap": True}))
    normal = workbook.add_format({"text_wrap": True})
    heading = workbook.add_format({"bold": True, "font_size": 18})
    worksheet = workbook.add_worksheet("failures")
    worksheet.write(0, 0, "Validation Failures", heading)

    headers = [
        ("Profile Selected:", profile_name),
        ("Report Generated At:", make_timestamp()),
        ("Directory Validated:", template_path),
        ("Checksum:", hash_directory(template_path)),
        ("Total Errors:", len(faildata)),
    ]
    for row, (header, value) in enumerate(headers, start=2):
        worksheet.write(row, 0, header, bold)
        worksheet.write(row, 1, value)

    worksheet.set_column(0, len(headers) - 1, 40)
    worksheet.set_column(len(headers), len(headers), 80)

    # table header
    start_error_table_row = 2 + len(headers) + 2
    for col_num, (col_name, _) in enumerate(report_columns):
        worksheet.write(start_error_table_row, col_num, col_name, bold)

    # table content
    for row, data in enumerate(faildata.values(), start=start_error_table_row + 1):
        for col, key in enumerate(report.values()):
            if key == "file":
                paths = (
                    [data[key]] if isinstance(data[key], string_types) else data[key]
                )
                contents = "\n".join(paths)
                worksheet.write(row, col, contents, normal)
            elif key == "raw_output":
                worksheet.write_string(row, col, data[key], code)
            else:
                worksheet.write(row, col, data[key], normal)

    workbook.close()


def generate_html_report(outpath, profile_name, template_path, faildata):
    with open("{}/report.html".format(outpath), "w") as of:
        body_begin = """
        <style type="text/css">
        h1, li {{
            font-family:Arial, sans-serif;
        }}
        .tg  {{border-collapse:collapse;border-spacing:0;}}
        .tg td{{font-family:Arial, sans-serif;font-size:8px;padding:10px 5px;border-style:solid;border-width:1px;overflow:hidden;word-break:normal;border-color:black;}}
        .tg th{{font-family:Arial, sans-serif;font-size:14px;font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:hidden;word-break:normal;border-color:black;}}
        .tg .tg-rwj1{{font-size:10px;font-family:Arial, Helvetica, sans-serif !important;;border-color:inherit;vertical-align:top}}
        </style>
        <h1>Validation Failures</h1>
        <ul>
            <li><b>Profile Selected: </b> <tt>{profile}</tt></li>
            <li><b>Report Generated At:</b> <tt>{timestamp}</tt></li>
            <li><b>Directory Validated:</b> <tt>{template_dir}</tt></li>
            <li><b>Checksum:</b> <tt>{checksum}</tt></li>
            <li><b>Total Errors:</b> {num_failures}</li>
        </ul>
        
        """.format(
            profile=profile_name,
            timestamp=make_timestamp(),
            checksum=hash_directory(template_path),
            template_dir=template_path,
            num_failures=len(faildata),
        )
        of.write(body_begin)

        if len(faildata) == 0:
            of.write("<p>Success! No validation failures detected.</p>")
            return

        table_begin = '<table class="tg">'
        of.write(table_begin)

        # table headers
        of.write("<tr>")
        for k, v in report.items():
            of.write('<th class="tg-rwj1">{}</th>'.format(k))
        of.write("</tr>")

        # table content
        for k, v in faildata.items():
            of.write("<tr>")
            for rk, rv in report.items():
                if rv == "file":
                    value = make_href(v[rv])
                elif rv == "raw_output":
                    value = "<pre>{}</pre>".format(v[rv])
                elif rv == "req_description":
                    parts = docutils.core.publish_parts(writer_name="html", source=v[rv])
                    value = parts["body"]
                else:
                    value = v[rv].replace("\n", "<br />")
                of.write("  <td>{}</td>".format(value))
            of.write("</tr>")

        of.write("</table>")


def pytest_addoption(parser):
    """
    Add needed CLI arguments
    """
    parser.addoption(
        "--template-directory",
        dest="template_dir",
        action="append",
        help="Directory which holds the templates for validation",
    )

    parser.addoption(
        "--self-test",
        dest="self_test",
        action="store_true",
        help="Test the unit tests against their fixtured data",
    )

    parser.addoption(
        "--validation-profile",
        dest="validation_profile",
        action="store",
        help="Runs all unmarked tests plus test with a matching marker",
    )

    parser.addoption(
        "--validation-profile-name",
        dest="validation_profile_name",
        action="store",
        help="Friendly name of the validation profile used in reports",
    )

    parser.addoption(
        "--report-format",
        dest="report_format",
        action="store",
        help="Format of output report (html, csv, excel)",
    )


def pytest_configure(config):
    """
    Ensure that we are receive either `--self-test` or
    `--template-dir=<directory` as CLI arguments
    """
    if config.getoption("template_dir") and config.getoption("self_test"):
        raise Exception('"--template-dir", and "--self-test"' " are mutually exclusive")
    if not (
        config.getoption("template_dir")
        or config.getoption("self_test")
        or config.getoption("help")
    ):
        raise Exception('One of "--template-dir" or' ' "--self-test" must be specified')


def pytest_generate_tests(metafunc):
    """
    If a unit test requires an argument named 'filename'
    we generate a test for the filenames selected. Either
    the files contained in `template_dir` or if `template_dir`
    is not specified on the CLI, the fixtures associated with this
    test name.
    """
    if "filename" in metafunc.fixturenames:
        from .parametrizers import parametrize_filename

        parametrize_filename(metafunc)

    if "filenames" in metafunc.fixturenames:
        from .parametrizers import parametrize_filenames

        parametrize_filenames(metafunc)

    if "template_dir" in metafunc.fixturenames:
        from .parametrizers import parametrize_template_dir

        parametrize_template_dir(metafunc)

    if "environment_pair" in metafunc.fixturenames:
        from .parametrizers import parametrize_environment_pair

        parametrize_environment_pair(metafunc)

    if "heat_volume_pair" in metafunc.fixturenames:
        from .parametrizers import parametrize_heat_volume_pair

        parametrize_heat_volume_pair(metafunc)

    if "yaml_files" in metafunc.fixturenames:
        from .parametrizers import parametrize_yaml_files

        parametrize_yaml_files(metafunc)

    if "env_files" in metafunc.fixturenames:
        from .parametrizers import parametrize_environment_files

        parametrize_environment_files(metafunc)

    if "yaml_file" in metafunc.fixturenames:
        from .parametrizers import parametrize_yaml_file

        parametrize_yaml_file(metafunc)

    if "env_file" in metafunc.fixturenames:
        from .parametrizers import parametrize_environment_file

        parametrize_environment_file(metafunc)

    if "parsed_yaml_file" in metafunc.fixturenames:
        from .parametrizers import parametrize_parsed_yaml_file

        parametrize_parsed_yaml_file(metafunc)

    if "parsed_environment_file" in metafunc.fixturenames:
        from .parametrizers import parametrize_parsed_environment_file

        parametrize_parsed_environment_file(metafunc)

    if "heat_template" in metafunc.fixturenames:
        from .parametrizers import parametrize_heat_template

        parametrize_heat_template(metafunc)

    if "heat_templates" in metafunc.fixturenames:
        from .parametrizers import parametrize_heat_templates

        parametrize_heat_templates(metafunc)

    if "volume_template" in metafunc.fixturenames:
        from .parametrizers import parametrize_volume_template

        parametrize_volume_template(metafunc)

    if "volume_templates" in metafunc.fixturenames:
        from .parametrizers import parametrize_volume_templates

        parametrize_volume_templates(metafunc)

    if "template" in metafunc.fixturenames:
        from .parametrizers import parametrize_template

        parametrize_template(metafunc)

    if "templates" in metafunc.fixturenames:
        from .parametrizers import parametrize_templates

        parametrize_templates(metafunc)


def hash_directory(path):
    md5 = hashlib.md5()
    for dir_path, sub_dirs, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(dir_path, filename)
            with open(file_path, "rb") as f:
                md5.update(f.read())
    return md5.hexdigest()


def load_current_requirements():
    """Loads dict of current requirements or empty dict if file doesn't exist"""
    path = "requirements.json"
    if not os.path.exists(path):
        return {}
    with io.open(path, encoding="utf8", mode="r") as f:
        data = json.load(f)
        version = data["current_version"]
        return data["versions"][version]["needs"]


def compat_open(path):
    """Invokes open correctly depending on the Python version"""
    if sys.version_info.major < 3:
        return open(path, "wb")
    else:
        return open(path, "w", newline="")


def unicode_writerow(writer, row):
    if sys.version_info.major < 3:
        row = [s.encode("utf8") for s in row]
    writer.writerow(row)


def pytest_report_collectionfinish(config, startdir, items):
    """Generates a simple traceability report to output/traceability.csv"""
    traceability_path = os.path.join(__path__[0], "../output/traceability.csv")
    output_dir = os.path.split(traceability_path)[0]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    requirements = load_current_requirements()
    unmapped, mapped = partition(
        lambda item: hasattr(item.function, "requirement_ids"), items
    )

    req_to_test = collections.defaultdict(set)
    mapping_errors = set()
    for item in mapped:
        for req_id in item.function.requirement_ids:
            req_to_test[req_id].add(item)
            if req_id not in requirements:
                mapping_errors.add(
                    (req_id, item.function.__module__, item.function.__name__)
                )

    mapping_error_path = os.path.join(__path__[0], "../output/mapping_errors.csv")
    with compat_open(mapping_error_path) as f:
        writer = csv.writer(f)
        for error in mapping_errors:
            unicode_writerow(writer, error)

    with compat_open(traceability_path) as f:
        out = csv.writer(f)
        unicode_writerow(
            out,
            ("Requirement ID", "Requirement", "Section", "Test Module", "Test Name"),
        )
        for req_id, metadata in requirements.items():
            if req_to_test[req_id]:
                for item in req_to_test[req_id]:
                    unicode_writerow(
                        out,
                        (
                            req_id,
                            metadata["description"],
                            metadata["section_name"],
                            item.function.__module__,
                            item.function.__name__,
                        ),
                    )
            else:
                unicode_writerow(
                    out,
                    (req_id, metadata["description"], metadata["section_name"], "", ""),
                )
        # now write out any test methods that weren't mapped to requirements
        for item in unmapped:
            unicode_writerow(
                out, ("", "", "", item.function.__module__, item.function.__name__)
            )
