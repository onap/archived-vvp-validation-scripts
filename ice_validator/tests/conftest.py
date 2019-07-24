# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2019 AT&T Intellectual Property. All rights reserved.
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

import csv
import datetime
import hashlib
import io
import json
import os
import re
import time
try:
    from html import escape
except ImportError:
    from cgi import escape
from collections import defaultdict

import traceback

import docutils.core
import jinja2
import pytest
from more_itertools import partition
import xlsxwriter
from six import string_types

# noinspection PyUnresolvedReferences
import version
import logging

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.ERROR)

__path__ = [os.path.dirname(os.path.abspath(__file__))]

DEFAULT_OUTPUT_DIR = "{}/../output".format(__path__[0])

HEAT_REQUIREMENTS_FILE = os.path.join(__path__[0], "..", "heat_requirements.json")
TEST_SCRIPT_SITE = (
    "https://github.com/onap/vvp-validation-scripts/blob/master/ice_validator/tests/"
)
VNFRQTS_ID_URL = (
    "https://docs.onap.org/en/latest/submodules/vnfrqts/requirements.git/docs/"
)

REPORT_COLUMNS = [
    ("Error #", "err_num"),
    ("Input File", "file"),
    ("Requirements", "req_description"),
    ("Error Message", "message"),
    ("Test", "test_file"),
]

COLLECTION_FAILURE_WARNING = """WARNING: The following unexpected errors occurred
while preparing to validate the the input files. Some validations may not have been
executed. Please refer these issue to the VNF Validation Tool team.
"""

COLLECTION_FAILURES = []

# Captures the results of every test run
ALL_RESULTS = []


def get_output_dir(config):
    """
    Retrieve the output directory for the reports and create it if necessary
    :param config: pytest configuration
    :return: output directory as string
    """
    output_dir = config.option.output_dir or DEFAULT_OUTPUT_DIR
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    return output_dir


def extract_error_msg(rep):
    """
    If a custom error message was provided, then extract it otherwise
    just show the pytest assert message
    """
    if rep.outcome != "failed":
        return ""
    try:
        full_msg = str(rep.longrepr.reprcrash.message)
        match = re.match(
            "AssertionError:(.*)^assert.*", full_msg, re.MULTILINE | re.DOTALL
        )
        if match:  # custom message was provided
            # Extract everything between AssertionError and the start
            # of the assert statement expansion in the pytest report
            msg = match.group(1)
        elif "AssertionError:" in full_msg:
            msg = full_msg.split("AssertionError:")[1]
        else:
            msg = full_msg
    except AttributeError:
        msg = str(rep)

    return msg


class TestResult:
    """
    Wraps the test case and result to extract necessary metadata for
    reporting purposes.
    """

    RESULT_MAPPING = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}

    def __init__(self, item, outcome):
        self.item = item
        self.result = outcome.get_result()
        self.files = self._get_files()
        self.error_message = self._get_error_message()

    @property
    def requirement_ids(self):
        """
        Returns list of requirement IDs mapped to the test case.

        :return: Returns a list of string requirement IDs the test was
                 annotated with ``validates`` otherwise returns and empty list
        """
        is_mapped = hasattr(self.item.function, "requirement_ids")
        return self.item.function.requirement_ids if is_mapped else []

    @property
    def markers(self):
        """
        :return: Returns a set of pytest marker names for the test or an empty set
        """
        return set(m.name for m in self.item.iter_markers())

    @property
    def is_base_test(self):
        """
        :return: Returns True if the test is annotated with a pytest marker called base
        """
        return "base" in self.markers

    @property
    def is_failed(self):
        """
        :return: True if the test failed
        """
        return self.outcome == "FAIL"

    @property
    def outcome(self):
        """
        :return: Returns 'PASS', 'FAIL', or 'SKIP'
        """
        return self.RESULT_MAPPING[self.result.outcome]

    @property
    def test_case(self):
        """
        :return: Name of the test case method
        """
        return self.item.function.__name__

    @property
    def test_module(self):
        """
        :return: Name of the file containing the test case
        """
        return self.item.function.__module__.split(".")[-1]

    @property
    def test_id(self):
        """
        :return: ID of the test (test_module + test_case)
        """
        return "{}::{}".format(self.test_module, self.test_case)

    @property
    def raw_output(self):
        """
        :return: Full output from pytest for the given test case
        """
        return str(self.result.longrepr)

    def requirement_text(self, curr_reqs):
        """
        Creates a text summary for the requirement IDs mapped to the test case.
        If no requirements are mapped, then it returns the empty string.

        :param curr_reqs: mapping of requirement IDs to requirement metadata
                          loaded from the VNFRQTS projects needs.json output
        :return: ID and text of the requirements mapped to the test case
        """
        text = (
            "\n\n{}: \n{}".format(r_id, curr_reqs[r_id]["description"])
            for r_id in self.requirement_ids
            if r_id in curr_reqs
        )
        return "".join(text)

    def requirements_metadata(self, curr_reqs):
        """
        Returns a list of dicts containing the following metadata for each
        requirement mapped:

        - id: Requirement ID
        - text: Full text of the requirement
        - keyword: MUST, MUST NOT, MAY, etc.

        :param curr_reqs: mapping of requirement IDs to requirement metadata
                          loaded from the VNFRQTS projects needs.json output
        :return: List of requirement metadata
        """
        data = []
        for r_id in self.requirement_ids:
            if r_id not in curr_reqs:
                continue
            data.append(
                {
                    "id": r_id,
                    "text": curr_reqs[r_id]["description"],
                    "keyword": curr_reqs[r_id]["keyword"],
                }
            )
        return data

    def _get_files(self):
        """
        Extracts the list of files passed into the test case.
        :return: List of absolute paths to files
        """
        if "environment_pair" in self.item.fixturenames:
            return [
                "{} environment pair".format(
                    self.item.funcargs["environment_pair"]["name"]
                )
            ]
        elif "heat_volume_pair" in self.item.fixturenames:
            return [
                "{} volume pair".format(self.item.funcargs["heat_volume_pair"]["name"])
            ]
        elif "heat_templates" in self.item.fixturenames:
            return [os.path.basename(f) for f in self.item.funcargs["heat_templates"]]
        elif "yaml_files" in self.item.fixturenames:
            return [os.path.basename(f) for f in self.item.funcargs["yaml_files"]]
        else:
            parts = self.result.nodeid.split("[")
            return [""] if len(parts) == 1 else [os.path.basename(parts[1][:-1])]

    def _get_error_message(self):
        """
        :return: Error message or empty string if the test did not fail or error
        """
        if self.is_failed:
            return extract_error_msg(self.result)
        else:
            return ""


# noinspection PyUnusedLocal
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Captures the test results for later reporting.  This will also halt testing
    if a base failure is encountered (can be overridden with continue-on-failure)
    """
    outcome = yield
    if outcome.get_result().when != "call":
        return  # only capture results of test cases themselves
    result = TestResult(item, outcome)
    if (
        not item.config.option.continue_on_failure
        and result.is_base_test
        and result.is_failed
    ):
        msg = "!!Base Test Failure!! Halting test suite execution...\n{}".format(
            result.error_message
        )
        result.error_message = msg
        ALL_RESULTS.append(result)
        pytest.exit("{}\n{}\n{}".format(msg, result.files, result.test_case))

    ALL_RESULTS.append(result)


def make_timestamp():
    """
    :return: String make_iso_timestamp in format:
             2019-01-19 10:18:49.865000 Central Standard Time
    """
    timezone = time.tzname[time.localtime().tm_isdst]
    return "{} {}".format(str(datetime.datetime.now()), timezone)


# noinspection PyUnusedLocal
def pytest_sessionstart(session):
    ALL_RESULTS.clear()
    COLLECTION_FAILURES.clear()


# noinspection PyUnusedLocal
def pytest_sessionfinish(session, exitstatus):
    """
    If not a self-test run, generate the output reports
    """
    if not session.config.option.template_dir:
        return

    if session.config.option.template_source:
        template_source = session.config.option.template_source[0]
    else:
        template_source = os.path.abspath(session.config.option.template_dir[0])

    categories_selected = session.config.option.test_categories or ""
    generate_report(
        get_output_dir(session.config),
        template_source,
        categories_selected,
        session.config.option.report_format,
    )


# noinspection PyUnusedLocal
def pytest_collection_modifyitems(session, config, items):
    """
    Selects tests based on the categories requested.  Tests without
    categories will always be executed.
    """
    config.traceability_items = list(items)  # save all items for traceability
    if not config.option.self_test:
        for item in items:
            # checking if test belongs to a category
            if hasattr(item.function, "categories"):
                if config.option.test_categories:
                    test_categories = getattr(item.function, "categories")
                    passed_categories = config.option.test_categories
                    if not all(
                        category in passed_categories for category in test_categories
                    ):
                        item.add_marker(
                            pytest.mark.skip(
                                reason=(
                                    "Test categories do not match "
                                    "all the passed categories"
                                )
                            )
                        )
                else:
                    item.add_marker(
                        pytest.mark.skip(
                            reason=(
                                "Test belongs to a category but "
                                "no categories were passed"
                            )
                        )
                    )

    items.sort(
        key=lambda x: (0, x.name)
        if "base" in set(m.name for m in x.iter_markers())
        else (1, x.name)
    )


def make_href(paths, base_dir=None):
    """
    Create an anchor tag to link to the file paths provided.
    :param paths: string or list of file paths
    :param base_dir: If specified this is pre-pended to each path
    :return: String of hrefs - one for each path, each seperated by a line
             break (<br/).
    """
    paths = [paths] if isinstance(paths, string_types) else paths
    if base_dir:
        paths = [os.path.join(base_dir, p) for p in paths]
    links = []
    for p in paths:
        abs_path = os.path.abspath(p)
        name = abs_path if os.path.isdir(abs_path) else os.path.split(abs_path)[1]
        links.append(
            "<a href='file://{abs_path}' target='_blank'>{name}</a>".format(
                abs_path=abs_path, name=name
            )
        )
    return "<br/>".join(links)


def generate_report(outpath, template_path, categories, output_format="html"):
    """
    Generates the various output reports.

    :param outpath: destination directory for all reports
    :param template_path: directory containing the Heat templates validated
    :param categories: Optional categories selected
    :param output_format: One of "html", "excel", or "csv". Default is "html"
    :raises: ValueError if requested output format is unknown
    """
    failures = [r for r in ALL_RESULTS if r.is_failed]
    generate_failure_file(outpath)
    output_format = output_format.lower().strip() if output_format else "html"
    generate_json(outpath, template_path, categories)
    if output_format == "html":
        generate_html_report(outpath, categories, template_path, failures)
    elif output_format == "excel":
        generate_excel_report(outpath, categories, template_path, failures)
    elif output_format == "json":
        return
    elif output_format == "csv":
        generate_csv_report(outpath, categories, template_path, failures)
    else:
        raise ValueError("Unsupported output format: " + output_format)


def write_json(data, path):
    """
    Pretty print data as JSON to the output path requested

    :param data: Data structure to be converted to JSON
    :param path: Where to write output
    """
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def generate_failure_file(outpath):
    """
    Writes a summary of test failures to a file named failures.
    This is for backwards compatibility only.  The report.json offers a
    more comprehensive output.
    """
    failure_path = os.path.join(outpath, "failures")
    failures = [r for r in ALL_RESULTS if r.is_failed]
    data = {}
    for i, fail in enumerate(failures):
        data[str(i)] = {
            "file": fail.files[0] if len(fail.files) == 1 else fail.files,
            "vnfrqts": fail.requirement_ids,
            "test": fail.test_case,
            "test_file": fail.test_module,
            "raw_output": fail.raw_output,
            "message": fail.error_message,
        }
    write_json(data, failure_path)


def generate_csv_report(output_dir, categories, template_path, failures):
    rows = [["Validation Failures"]]
    headers = [
        ("Categories Selected:", categories),
        ("Tool Version:", version.VERSION),
        ("Report Generated At:", make_timestamp()),
        ("Directory Validated:", template_path),
        ("Checksum:", hash_directory(template_path)),
        ("Total Errors:", len(failures) + len(COLLECTION_FAILURES)),
    ]
    rows.append([])
    for header in headers:
        rows.append(header)
    rows.append([])

    if COLLECTION_FAILURES:
        rows.append([COLLECTION_FAILURE_WARNING])
        rows.append(["Validation File", "Test", "Fixtures", "Error"])
        for failure in COLLECTION_FAILURES:
            rows.append(
                [
                    failure["module"],
                    failure["test"],
                    ";".join(failure["fixtures"]),
                    failure["error"],
                ]
            )
        rows.append([])

    # table header
    rows.append([col for col, _ in REPORT_COLUMNS])

    reqs = load_current_requirements()

    # table content
    for i, failure in enumerate(failures, start=1):
        rows.append(
            [
                i,
                "\n".join(failure.files),
                failure.requirement_text(reqs),
                failure.error_message,
                failure.test_id,
            ]
        )

    output_path = os.path.join(output_dir, "report.csv")
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def generate_excel_report(output_dir, categories, template_path, failures):
    output_path = os.path.join(output_dir, "report.xlsx")
    workbook = xlsxwriter.Workbook(output_path)
    bold = workbook.add_format({"bold": True, "align": "top"})
    code = workbook.add_format(
        {"font_name": "Courier", "text_wrap": True, "align": "top"}
    )
    normal = workbook.add_format({"text_wrap": True, "align": "top"})
    heading = workbook.add_format({"bold": True, "font_size": 18})
    worksheet = workbook.add_worksheet("failures")
    worksheet.write(0, 0, "Validation Failures", heading)

    headers = [
        ("Categories Selected:", ",".join(categories)),
        ("Tool Version:", version.VERSION),
        ("Report Generated At:", make_timestamp()),
        ("Directory Validated:", template_path),
        ("Checksum:", hash_directory(template_path)),
        ("Total Errors:", len(failures) + len(COLLECTION_FAILURES)),
    ]
    for row, (header, value) in enumerate(headers, start=2):
        worksheet.write(row, 0, header, bold)
        worksheet.write(row, 1, value)

    worksheet.set_column(0, len(headers) - 1, 40)
    worksheet.set_column(len(headers), len(headers), 80)

    if COLLECTION_FAILURES:
        collection_failures_start = 2 + len(headers) + 2
        worksheet.write(collection_failures_start, 0, COLLECTION_FAILURE_WARNING, bold)
        collection_failure_headers = ["Validation File", "Test", "Fixtures", "Error"]
        for col_num, col_name in enumerate(collection_failure_headers):
            worksheet.write(collection_failures_start + 1, col_num, col_name, bold)
        for row, data in enumerate(COLLECTION_FAILURES, collection_failures_start + 2):
            worksheet.write(row, 0, data["module"])
            worksheet.write(row, 1, data["test"])
            worksheet.write(row, 2, ",".join(data["fixtures"]))
            worksheet.write(row, 3, data["error"], code)

    # table header
    start_error_table_row = 2 + len(headers) + len(COLLECTION_FAILURES) + 4
    worksheet.write(start_error_table_row, 0, "Validation Failures", bold)
    for col_num, (col_name, _) in enumerate(REPORT_COLUMNS):
        worksheet.write(start_error_table_row + 1, col_num, col_name, bold)

    reqs = load_current_requirements()

    # table content
    for col, width in enumerate((20, 30, 60, 60, 40)):
        worksheet.set_column(col, col, width)
    err_num = 1
    for row, failure in enumerate(failures, start=start_error_table_row + 2):
        worksheet.write(row, 0, str(err_num), normal)
        worksheet.write(row, 1, "\n".join(failure.files), normal)
        worksheet.write(row, 2, failure.requirement_text(reqs), normal)
        worksheet.write(row, 3, failure.error_message.replace("\n", "\n\n"), normal)
        worksheet.write(row, 4, failure.test_id, normal)
        err_num += 1
    worksheet.autofilter(
        start_error_table_row + 1,
        0,
        start_error_table_row + 1 + err_num,
        len(REPORT_COLUMNS) - 1,
    )
    workbook.close()


def make_iso_timestamp():
    """
    Creates a timestamp in ISO 8601 format in UTC format.  Used for JSON output.
    """
    now = datetime.datetime.utcnow()
    now.replace(tzinfo=datetime.timezone.utc)
    return now.isoformat()


def aggregate_results(outcomes, r_id=None):
    """
    Determines the aggregate result for the conditions provided.  Assumes the
    results have been filtered and collected for analysis.

    :param outcomes: set of outcomes from the TestResults
    :param r_id: Optional requirement ID if known
    :return: 'ERROR', 'PASS', 'FAIL', or 'SKIP'
             (see aggregate_requirement_adherence for more detail)
    """
    if not outcomes:
        return "PASS"
    elif "ERROR" in outcomes:
        return "ERROR"
    elif "FAIL" in outcomes:
        return "FAIL"
    elif "PASS" in outcomes:
        return "PASS"
    elif {"SKIP"} == outcomes:
        return "SKIP"
    else:
        pytest.warns(
            "Unexpected error aggregating outcomes ({}) for requirement {}".format(
                outcomes, r_id
            )
        )
        return "ERROR"


def aggregate_run_results(collection_failures, test_results):
    """
    Determines overall status of run based on all failures and results.

    * 'ERROR' - At least one collection failure occurred during the run.
    * 'FAIL' - Template failed at least one test
    * 'PASS' - All tests executed properly and no failures were detected

    :param collection_failures: failures occuring during test setup
    :param test_results: list of all test executuion results
    :return: one of 'ERROR', 'FAIL', or 'PASS'
    """
    if collection_failures:
        return "ERROR"
    elif any(r.is_failed for r in test_results):
        return "FAIL"
    else:
        return "PASS"


def relative_paths(base_dir, paths):
    return [os.path.relpath(p, base_dir) for p in paths if p != ""]


# noinspection PyTypeChecker
def generate_json(outpath, template_path, categories):
    """
    Creates a JSON summary of the entire test run.
    """
    reqs = load_current_requirements()
    data = {
        "version": "dublin",
        "template_directory": os.path.splitdrive(template_path)[1].replace(
            os.path.sep, "/"
        ),
        "timestamp": make_iso_timestamp(),
        "checksum": hash_directory(template_path),
        "categories": categories,
        "outcome": aggregate_run_results(COLLECTION_FAILURES, ALL_RESULTS),
        "tests": [],
        "requirements": [],
    }

    results = data["tests"]
    for result in COLLECTION_FAILURES:
        results.append(
            {
                "files": [],
                "test_module": result["module"],
                "test_case": result["test"],
                "result": "ERROR",
                "error": result["error"],
                "requirements": result["requirements"],
            }
        )
    for result in ALL_RESULTS:
        results.append(
            {
                "files": relative_paths(template_path, result.files),
                "test_module": result.test_module,
                "test_case": result.test_case,
                "result": result.outcome,
                "error": result.error_message if result.is_failed else "",
                "requirements": result.requirements_metadata(reqs),
            }
        )

    # Build a mapping of requirement ID to the results
    r_id_results = defaultdict(lambda: {"errors": set(), "outcomes": set()})
    for test_result in results:
        test_reqs = test_result["requirements"]
        r_ids = (
            [r["id"] if isinstance(r, dict) else r for r in test_reqs]
            if test_reqs
            else ("",)
        )
        for r_id in r_ids:
            item = r_id_results[r_id]
            item["outcomes"].add(test_result["result"])
            if test_result["error"]:
                item["errors"].add(test_result["error"])

    requirements = data["requirements"]
    for r_id, r_data in reqs.items():
        requirements.append(
            {
                "id": r_id,
                "text": r_data["description"],
                "keyword": r_data["keyword"],
                "result": aggregate_results(r_id_results[r_id]["outcomes"]),
                "errors": list(r_id_results[r_id]["errors"]),
            }
        )

    if r_id_results[""]["errors"] or r_id_results[""]["outcomes"]:
        requirements.append(
            {
                "id": "Unmapped",
                "text": "Tests not mapped to requirements (see tests)",
                "result": aggregate_results(r_id_results[""]["outcomes"]),
                "errors": list(r_id_results[""]["errors"]),
            }
        )

    report_path = os.path.join(outpath, "report.json")
    write_json(data, report_path)


def generate_html_report(outpath, categories, template_path, failures):
    reqs = load_current_requirements()
    fail_data = []
    for failure in failures:
        fail_data.append(
            {
                "file_links": make_href(failure.files, template_path),
                "test_id": failure.test_id,
                "error_message": escape(failure.error_message).replace("\n",
                                                                       "<br/><br/>"),
                "raw_output": escape(failure.raw_output),
                "requirements": docutils.core.publish_parts(
                    writer_name="html", source=failure.requirement_text(reqs)
                )["body"],
            }
        )
    pkg_dir = os.path.split(__file__)[0]
    j2_template_path = os.path.join(pkg_dir, "report.html.jinja2")
    with open(j2_template_path, "r") as f:
        report_template = jinja2.Template(f.read())
        contents = report_template.render(
            version=version.VERSION,
            num_failures=len(failures) + len(COLLECTION_FAILURES),
            categories=categories,
            template_dir=make_href(template_path),
            checksum=hash_directory(template_path),
            timestamp=make_timestamp(),
            failures=fail_data,
            collection_failures=COLLECTION_FAILURES,
        )
    with open(os.path.join(outpath, "report.html"), "w") as f:
        f.write(contents)


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
        "--template-source",
        dest="template_source",
        action="append",
        help="Source Directory which holds the templates for validation",
    )

    parser.addoption(
        "--self-test",
        dest="self_test",
        action="store_true",
        help="Test the unit tests against their fixtured data",
    )

    parser.addoption(
        "--report-format",
        dest="report_format",
        action="store",
        help="Format of output report (html, csv, excel, json)",
    )

    parser.addoption(
        "--continue-on-failure",
        dest="continue_on_failure",
        action="store_true",
        help="Continue validation even when structural errors exist in input files",
    )

    parser.addoption(
        "--output-directory",
        dest="output_dir",
        action="store",
        default=None,
        help="Alternate ",
    )

    parser.addoption(
        "--category",
        dest="test_categories",
        action="append",
        help="optional category of test to execute",
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

    # noinspection PyBroadException
    try:
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
    except Exception as e:
        # If an error occurs in the collection phase, then it won't be logged as a
        # normal test failure.  This means that failures could occur, but not
        # be seen on the report resulting in a false positive success message.  These
        # errors will be stored and reported separately on the report
        COLLECTION_FAILURES.append(
            {
                "module": metafunc.module.__name__,
                "test": metafunc.function.__name__,
                "fixtures": metafunc.fixturenames,
                "error": traceback.format_exc(),
                "requirements": getattr(metafunc.function, "requirement_ids", []),
            }
        )
        raise e


def hash_directory(path):
    """
    Create md5 hash using the contents of all files under ``path``
    :param path: string directory containing files
    :return: string MD5 hash code (hex)
    """
    md5 = hashlib.md5()  # nosec
    for dir_path, sub_dirs, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(dir_path, filename)
            with open(file_path, "rb") as f:
                md5.update(f.read())
    return md5.hexdigest()


def load_current_requirements():
    """Loads dict of current requirements or empty dict if file doesn't exist"""
    with io.open(HEAT_REQUIREMENTS_FILE, encoding="utf8", mode="r") as f:
        data = json.load(f)
        version = data["current_version"]
        return data["versions"][version]["needs"]


def select_heat_requirements(reqs):
    """Filters dict requirements to only those requirements pertaining to Heat"""
    return {k: v for k, v in reqs.items() if "heat" in v["docname"].lower()}


def is_testable(reqs):
    """Filters dict requirements to only those which are testable"""
    for key, values in reqs.items():
        if ("MUST" in values.get("keyword", "").upper()) and (
            "none" not in values.get("validation_mode", "").lower()
        ):
            reqs[key]["testable"] = True
        else:
            reqs[key]["testable"] = False
    return reqs


def build_rst_json(reqs):
    """Takes requirements and returns list of only Heat requirements"""
    for key, values in list(reqs.items()):
        if values["testable"]:
            # Creates links in RST format to requirements and test cases
            if values["test_case"]:
                mod = values["test_case"].split(".")[-1]
                val = TEST_SCRIPT_SITE + mod + ".py"
                rst_value = "`" + mod + " <" + val + ">`_"
                title = (
                    "`"
                    + values["id"]
                    + " <"
                    + VNFRQTS_ID_URL
                    + values["docname"].replace(" ", "%20")
                    + ".html#"
                    + values["id"]
                    + ">`_"
                )
                reqs[key].update({"full_title": title, "test_case": rst_value})
            else:
                title = (
                    "`"
                    + values["id"]
                    + " <"
                    + VNFRQTS_ID_URL
                    + values["docname"].replace(" ", "%20")
                    + ".html#"
                    + values["id"]
                    + ">`_"
                )
                reqs[key].update(
                    {
                        "full_title": title,
                        "test_case": "No test for requirement",
                        "validated_by": "static",
                    }
                )
        else:
            del reqs[key]
    return reqs


def generate_rst_table(output_dir, data):
    """Generate a formatted csv to be used in RST"""
    rst_path = os.path.join(output_dir, "rst.csv")
    with open(rst_path, "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(("Requirement ID", "Requirement", "Test Module", "Test Name"))
        for req_id, metadata in data.items():
            out.writerow(
                (
                    metadata["full_title"],
                    metadata["description"],
                    metadata["test_case"],
                    metadata["validated_by"],
                )
            )


# noinspection PyUnusedLocal
def pytest_report_collectionfinish(config, startdir, items):
    """Generates a simple traceability report to output/traceability.csv"""
    traceability_path = os.path.join(get_output_dir(config), "traceability.csv")
    output_dir = os.path.split(traceability_path)[0]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    reqs = load_current_requirements()
    requirements = select_heat_requirements(reqs)
    testable_requirements = is_testable(requirements)
    unmapped, mapped = partition(
        lambda i: hasattr(i.function, "requirement_ids"), items
    )

    req_to_test = defaultdict(set)
    mapping_errors = set()
    for item in mapped:
        for req_id in item.function.requirement_ids:
            if req_id not in req_to_test:
                req_to_test[req_id].add(item)
                if req_id in requirements:
                    reqs[req_id].update(
                        {
                            "test_case": item.function.__module__,
                            "validated_by": item.function.__name__,
                        }
                    )
            if req_id not in requirements:
                mapping_errors.add(
                    (req_id, item.function.__module__, item.function.__name__)
                )

    mapping_error_path = os.path.join(get_output_dir(config), "mapping_errors.csv")
    with open(mapping_error_path, "w", newline="") as f:
        writer = csv.writer(f)
        for err in mapping_errors:
            writer.writerow(err)

    with open(traceability_path, "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(
            (
                "Requirement ID",
                "Requirement",
                "Section",
                "Keyword",
                "Validation Mode",
                "Is Testable",
                "Test Module",
                "Test Name",
            )
        )
        for req_id, metadata in testable_requirements.items():
            if req_to_test[req_id]:
                for item in req_to_test[req_id]:
                    out.writerow(
                        (
                            req_id,
                            metadata["description"],
                            metadata["section_name"],
                            metadata["keyword"],
                            metadata["validation_mode"],
                            metadata["testable"],
                            item.function.__module__,
                            item.function.__name__,
                        )
                    )
            else:
                out.writerow(
                    (
                        req_id,
                        metadata["description"],
                        metadata["section_name"],
                        metadata["keyword"],
                        metadata["validation_mode"],
                        metadata["testable"],
                        "",  # test module
                        "",
                    )  # test function
                )
        # now write out any test methods that weren't mapped to requirements
        unmapped_tests = {
            (item.function.__module__, item.function.__name__) for item in unmapped
        }
        for test_module, test_name in unmapped_tests:
            out.writerow(
                (
                    "",  # req ID
                    "",  # description
                    "",  # section name
                    "",  # keyword
                    "static",  # validation mode
                    "TRUE",  # testable
                    test_module,
                    test_name,
                )
            )

    generate_rst_table(get_output_dir(config), build_rst_json(testable_requirements))
