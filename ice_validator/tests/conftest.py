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
import sys
import time
from collections import defaultdict
from itertools import chain

import traceback

import docutils.core
import jinja2
import pytest
from more_itertools import partition
import xlsxwriter
from six import string_types

import version

__path__ = [os.path.dirname(os.path.abspath(__file__))]

DEFAULT_OUTPUT_DIR = "{}/../output".format(__path__[0])

RESOLUTION_STEPS_FILE = "resolution_steps.json"
HEAT_REQUIREMENTS_FILE = os.path.join(__path__[0], "..", "heat_requirements.json")

REPORT_COLUMNS = [
    ("Input File", "file"),
    ("Test", "test_file"),
    ("Requirements", "req_description"),
    ("Resolution Steps", "resolution_steps"),
    ("Error Message", "message"),
    ("Raw Test Output", "raw_output"),
]

COLLECTION_FAILURE_WARNING = """WARNING: The following unexpected errors occurred
while preparing to validate the the input files. Some validations may not have been
executed. Please refer these issue to the VNF Validation Tool team.
"""

COLLECTION_FAILURES = []

# Captures the results of every test run
ALL_RESULTS = []


def get_output_dir(config):
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
        else:
            msg = str(rep.longrepr.reprcrash)
            if "AssertionError:" in msg:
                msg = msg.split("AssertionError:")[1]
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
        self.files = [os.path.normpath(p) for p in self._get_files()]
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

    def resolution_steps(self, resolutions):
        """
        :param resolutions: Loaded from contents for resolution_steps.json
        :return: Header and text for the resolution step associated with this
                 test case.  Returns empty string if no resolutions are
                 provided.
        """
        text = (
            "\n{}: \n{}".format(entry["header"], entry["resolution_steps"])
            for entry in resolutions
            if self._match(entry)
        )
        return "".join(text)

    def _match(self, resolution_entry):
        """
        Returns True if the test result maps to the given entry in
        the resolutions file
        """
        return (
            self.test_case == resolution_entry["function"]
            and self.test_module == resolution_entry["module"]
        )

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
            return self.item.funcargs["heat_templates"]
        elif "yaml_files" in self.item.fixturenames:
            return self.item.funcargs["yaml_files"]
        else:
            return [self.result.nodeid.split("[")[1][:-1]]

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
    ALL_RESULTS.append(result)
    if (
        not item.config.option.continue_on_failure
        and result.is_base_test
        and result.is_failed
    ):
        msg = "!!Base Test Failure!! Halting test suite execution...\n{}".format(
            result.error_message
        )
        pytest.exit("{}\n{}\n{}".format(msg, result.files, result.test_case))


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
                                reason="Test categories do not match all the passed categories"
                            )
                        )
                else:
                    item.add_marker(
                        pytest.mark.skip(
                            reason="Test belongs to a category but no categories were passed"
                        )
                    )
    items.sort(
        key=lambda item: 0 if "base" in set(m.name for m in item.iter_markers()) else 1
    )


def make_href(paths):
    """
    Create an anchor tag to link to the file paths provided.
    :param paths: string or list of file paths
    :return: String of hrefs - one for each path, each seperated by a line
             break (<br/).
    """
    paths = [paths] if isinstance(paths, string_types) else paths
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


def load_resolutions_file():
    """
    :return: dict of data loaded from resolutions_steps.json
    """
    resolution_steps = "{}/../{}".format(__path__[0], RESOLUTION_STEPS_FILE)
    if os.path.exists(resolution_steps):
        with open(resolution_steps, "r") as f:
            return json.loads(f.read())


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
    if output_format == "html":
        generate_html_report(outpath, categories, template_path, failures)
    elif output_format == "excel":
        generate_excel_report(outpath, categories, template_path, failures)
    elif output_format == "json":
        generate_json(outpath, template_path, categories)
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
    resolutions = load_resolutions_file()

    # table content
    for failure in failures:
        rows.append(
            [
                "\n".join(failure.files),
                failure.test_module,
                failure.requirement_text(reqs),
                failure.resolution_steps(resolutions),
                failure.error_message,
                failure.raw_output,
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
    bold = workbook.add_format({"bold": True})
    code = workbook.add_format(({"font_name": "Courier", "text_wrap": True}))
    normal = workbook.add_format({"text_wrap": True})
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
    resolutions = load_resolutions_file()

    # table content
    for row, failure in enumerate(failures, start=start_error_table_row + 2):
        worksheet.write(row, 0, "\n".join(failure.files), normal)
        worksheet.write(row, 1, failure.test_module, normal)
        worksheet.write(row, 2, failure.requirement_text(reqs), normal)
        worksheet.write(row, 3, failure.resolution_steps(resolutions), normal)
        worksheet.write(row, 4, failure.error_message, normal)
        worksheet.write(row, 5, failure.raw_output, code)

    workbook.close()


def make_iso_timestamp():
    """
    Creates a timestamp in ISO 8601 format in UTC format.  Used for JSON output.
    """
    now = datetime.datetime.utcnow()
    now.replace(tzinfo=datetime.timezone.utc)
    return now.isoformat()


def aggregate_requirement_adherence(r_id, collection_failures, test_results):
    """
    Examines all tests associated with a given requirement and determines
    the aggregate result (PASS, FAIL, ERROR, or SKIP) for the requirement.

    * ERROR - At least one ERROR occurred
    * PASS -  At least one PASS and no FAIL or ERRORs.
    * FAIL -  At least one FAIL occurred (no ERRORs)
    * SKIP - All tests were SKIP


    :param r_id: Requirement ID to examing
    :param collection_failures: Errors that occurred during test setup.
    :param test_results: List of TestResult
    :return: 'PASS', 'FAIL', 'SKIP', or 'ERROR'
    """
    errors = any(r_id in f["requirements"] for f in collection_failures)
    outcomes = set(r.outcome for r in test_results if r_id in r.requirement_ids)
    return aggregate_results(errors, outcomes, r_id)


def aggregate_results(has_errors, outcomes, r_id=None):
    """
    Determines the aggregate result for the conditions provided.  Assumes the
    results have been filtered and collected for analysis.

    :param has_errors: True if collection failures occurred for the tests being
                       analyzed.
    :param outcomes: set of outcomes from the TestResults
    :param r_id: Optional requirement ID if known
    :return: 'ERROR', 'PASS', 'FAIL', or 'SKIP'
             (see aggregate_requirement_adherence for more detail)
    """
    if has_errors:
        return "ERROR"

    if not outcomes:
        return "PASS"
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


def error(failure_or_result):
    """
    Extracts the error message from a collection failure or test result
    :param failure_or_result: Entry from COLLECTION_FAILURE or a TestResult
    :return: Error message as string
    """
    if isinstance(failure_or_result, TestResult):
        return failure_or_result.error_message
    else:
        return failure_or_result["error"]


def req_ids(failure_or_result):
    """
    Extracts the requirement IDs from a collection failure or test result
    :param failure_or_result: Entry from COLLECTION_FAILURE or a TestResult
    :return: set of Requirement IDs.  If no requirements mapped, then an empty set
    """
    if isinstance(failure_or_result, TestResult):
        return set(failure_or_result.requirement_ids)
    else:
        return set(failure_or_result["requirements"])


def collect_errors(r_id, collection_failures, test_result):
    """
    Creates a list of error messages from the collection failures and
    test results.  If r_id is provided, then it collects the error messages
    where the failure or test is associated with that requirement ID.  If
    r_id is None, then it collects all errors that occur on failures and
    results that are not mapped to requirements
    """

    def selector(item):
        if r_id:
            return r_id in req_ids(item)
        else:
            return not req_ids(item)

    errors = (error(x) for x in chain(collection_failures, test_result) if selector(x))
    return [e for e in errors if e]


def generate_json(outpath, template_path, categories):
    """
    Creates a JSON summary of the entire test run.
    """
    reqs = load_current_requirements()
    data = {
        "version": "dublin",
        "template_directory": template_path,
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
                "files": result.files,
                "test_module": result.test_module,
                "test_case": result.test_case,
                "result": result.outcome,
                "error": result.error_message if result.is_failed else "",
                "requirements": result.requirements_metadata(reqs),
            }
        )

    requirements = data["requirements"]
    for r_id, r_data in reqs.items():
        result = aggregate_requirement_adherence(r_id, COLLECTION_FAILURES, ALL_RESULTS)
        if result:
            requirements.append(
                {
                    "id": r_id,
                    "text": r_data["description"],
                    "keyword": r_data["keyword"],
                    "result": result,
                    "errors": collect_errors(r_id, COLLECTION_FAILURES, ALL_RESULTS),
                }
            )
    # If there are tests that aren't mapped to a requirement, then we'll
    # map them to a special entry so the results are coherent.
    unmapped_outcomes = {r.outcome for r in ALL_RESULTS if not r.requirement_ids}
    has_errors = any(not f["requirements"] for f in COLLECTION_FAILURES)
    if unmapped_outcomes or has_errors:
        requirements.append(
            {
                "id": "Unmapped",
                "text": "Tests not mapped to requirements (see tests)",
                "result": aggregate_results(has_errors, unmapped_outcomes),
                "errors": collect_errors(None, COLLECTION_FAILURES, ALL_RESULTS),
            }
        )

    report_path = os.path.join(outpath, "report.json")
    write_json(data, report_path)


def generate_html_report(outpath, categories, template_path, failures):
    reqs = load_current_requirements()
    resolutions = load_resolutions_file()
    fail_data = []
    for failure in failures:
        fail_data.append(
            {
                "file_links": make_href(failure.files),
                "test_id": failure.test_module,
                "error_message": failure.error_message,
                "raw_output": failure.raw_output,
                "requirements": docutils.core.publish_parts(
                    writer_name="html", source=failure.requirement_text(reqs)
                )["body"],
                "resolution_steps": failure.resolution_steps(resolutions),
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
    md5 = hashlib.md5()
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


def parse_heat_requirements(reqs):
    """Takes requirements and returns list of only Heat requirements"""
    data = json.loads(reqs)
    for key, values in list(data.items()):
        if "Heat" in (values["docname"]):
            if "MUST" not in (values["keyword"]):
                del data[key]
            else:
                if "none" in (values["validation_mode"]):
                    del data[key]
        else:
            del data[key]
    return data


# noinspection PyUnusedLocal
def pytest_report_collectionfinish(config, startdir, items):
    """Generates a simple traceability report to output/traceability.csv"""
    traceability_path = os.path.join(__path__[0], "../output/traceability.csv")
    output_dir = os.path.split(traceability_path)[0]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    reqs = load_current_requirements()
    reqs = json.dumps(reqs)
    requirements = parse_heat_requirements(reqs)
    unmapped, mapped = partition(
        lambda i: hasattr(i.function, "requirement_ids"), items
    )

    req_to_test = defaultdict(set)
    mapping_errors = set()
    for item in mapped:
        for req_id in item.function.requirement_ids:
            if req_id not in req_to_test:
                req_to_test[req_id].add(item)
            if req_id not in requirements:
                mapping_errors.add(
                    (req_id, item.function.__module__, item.function.__name__)
                )

    mapping_error_path = os.path.join(__path__[0], "../output/mapping_errors.csv")
    with compat_open(mapping_error_path) as f:
        writer = csv.writer(f)
        for err in mapping_errors:
            unicode_writerow(writer, err)

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
