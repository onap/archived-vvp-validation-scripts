# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
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
#
import contextlib
import csv
import io
import json
import os
import subprocess  #nosec
import sys

import pytest
from flake8.main.application import Application

from update_reqs import get_requirements

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_NEEDS_PATH = os.path.join(THIS_DIR, "ice_validator/heat_requirements.json")


class Traceability:

    PATH = os.path.join(THIS_DIR, "ice_validator/output/traceability.csv")
    TEST_FILE = 6
    TEST_NAME = 7
    IS_TESTABLE = 5
    REQ_ID = 0

    def __init__(self):
        with open(self.PATH, "r") as f:
            rows = csv.reader(f)
            next(rows)  # skip header
            self.mappings = list(rows)

    def unmapped_requirement_errors(self):
        """
        Returns list of errors where a requirement is testable, but no test was found.
        """
        testable_mappings = [m for m in self.mappings if m[self.IS_TESTABLE] == "True"]
        return [
            f"Missing test for {m[self.REQ_ID]}"
            for m in testable_mappings
            if not m[self.TEST_NAME]
        ]

    def mapped_non_testable_requirement_errors(self):
        """
        Returns list of errors where the requirement isn't testable, but a test was
        found.
        """
        non_testables = [m for m in self.mappings if m[self.IS_TESTABLE] == "False"]
        return [
            (
                f"No test for {m[0]} is needed, but found: "
                f"{m[self.TEST_FILE]}::{m[self.TEST_NAME]} "
            )
            for m in non_testables
            if m[self.TEST_NAME]
        ]


def current_version(needs):
    """Extracts and returns the needs under the current version"""
    return needs["versions"][needs["current_version"]]["needs"]


def in_scope(_, req_metadata):
    """
    Checks if requirement is relevant to VVP.

    :param: _: not used
    :param req_metadata: needs metadata about the requirement
    :return: True if the requirement is a testable, Heat requirement
    """
    return (
        "Heat" in req_metadata.get("docname", "")
        and "MUST" in req_metadata.get("keyword", "").upper()
        and req_metadata.get("validation_mode", "").lower() != "none"
    )


def select_items(predicate, source_dict):
    """
    Creates a new dict from the source dict where the items match the given predicate
    :param predicate: predicate function that must accept a two arguments (key & value)
    :param source_dict: input dictionary to select from
    :return: filtered dict
    """
    return {k: v for k, v in source_dict.items() if predicate(k, v)}


def check_requirements_up_to_date():
    """
    Checks if the requirements file packaged with VVP has meaningful differences
    to the requirements file published from VNFRQTS.
    :return: list of errors found
    """
    msg = ["heat_requirements.json is out-of-date. Run update_reqs.py to update."]
    latest_needs = json.load(get_requirements())
    with open(CURRENT_NEEDS_PATH, "r") as f:
        current_needs = json.load(f)
    latest_reqs = select_items(in_scope, current_version(latest_needs))
    current_reqs = select_items(in_scope, current_version(current_needs))
    if set(latest_reqs.keys()) != set(current_reqs.keys()):
        return msg
    if not all(
        latest["description"] == current_reqs[r_id]["description"]
        for r_id, latest in latest_reqs.items()
    ):
        return msg
    return None


def check_self_test_pass():
    """
    Run pytest self-test and ensure it passes
    :return:
    """
    original_dir = os.getcwd()
    try:
        os.chdir(os.path.join(THIS_DIR, "ice_validator"))
        if pytest.main(["tests", "--self-test"]) != 0:
            return ["VVP self-test failed. Run pytest --self-test and fix errors."]
    finally:
        os.chdir(original_dir)


def check_testable_requirements_are_mapped():
    tracing = Traceability()
    return tracing.unmapped_requirement_errors()


def check_non_testable_requirements_are_not_mapped():
    tracing = Traceability()
    return tracing.mapped_non_testable_requirement_errors()


def check_flake8_passes():
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        app = Application()
        app.run(["ice_validator"])
    output.seek(0)
    lines = [f"   {l}" for l in output.readlines()]
    return ["flake8 errors detected:"] + lines if lines else []


def check_bandit_passes():
    result = subprocess.run(                                            #nosec
        ["bandit", "-c", "bandit.yaml", "-r", ".", "-x", "./.tox/**"],  #nosec
        encoding="utf-8",                                               #nosec
        stdout=subprocess.PIPE,                                         #nosec
        stderr=subprocess.PIPE,                                         #nosec
    )                                                                   #nosec
    msgs = result.stdout.split("\n") if result.returncode != 0 else []
    return ["bandit errors detected:"] + [f"  {e}" for e in msgs] if msgs else []


if __name__ == "__main__":
    checks = [
        check_self_test_pass,
        check_requirements_up_to_date,
        check_testable_requirements_are_mapped,
        check_non_testable_requirements_are_not_mapped,
        check_flake8_passes,
        check_bandit_passes,
    ]
    results = [check() for check in checks]
    errors = "\n".join("\n".join(msg) for msg in results if msg)
    print(errors or "Everything looks good!")
    sys.exit(1 if errors else 0)
