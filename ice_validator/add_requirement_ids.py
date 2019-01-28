# -*- coding: utf8 -*-
# ============LICENSE_START====================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2017 AT&T Intellectual Property. All rights reserved.
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
# ECOMP is a trademark and service mark of AT&T Intellectual Property.
#

"""Script that will take a file (`requirements.yaml`) containing the
requirements and metadata for VNF requirements, and transform the VVP
test cases to add `validates` decorators to all test cases that have
been mapped to requirements in the YAML file.  The transformed files
are written to the `build` directory.  If the test case does not have
a mapping then no validates decorator is added.  All other files are
copied to their corresponding sub-directory in build as well"""

import os
import re
import shutil

import yaml


def load_yaml(file_path):
    """Load a YAML file from the given `file_path`."""
    with open(file_path, "r") as f:
        return yaml.load(f)


def make_dirs(dir_path):
    """Creates all directories in `dir_path` if they don't already exist"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


class Requirement(object):
    """Wrapper around the requirements metadata to normalize how the
    data is retrieved"""

    def __init__(self, metadata):
        self.data = metadata
        if len(self.test_files) > 1 and self.test_method:
            raise RuntimeError("Ambiguous Requirement Metadata: " + self.data)
        elif self.test_method and not self.test_files:
            raise RuntimeError("Test Method with no file: ", self.data)

    @property
    def test_files(self):
        """Returns a tuple of the test file names associated with the
        requirement if any are mapped."""
        if "test_file" in self.data:
            test_file = self.data["test_file"]
            if not test_file.endswith(".py"):
                test_file = test_file + ".py"
            return (test_file,)
        elif "test_case" in self.data:
            return self._extract_files_from_url()
        else:
            return tuple()

    @property
    def test_method(self):
        test_method = self.data.get("test")
        if not test_method or test_method == "none":
            return None
        else:
            return test_method

    def _extract_files_from_url(self):
        result = []
        if self.data.get("test_case"):
            test_urls = self.data["test_case"].split()
            for url in test_urls:
                match = re.match(r".*/(.*\.py).*", url)
                if match:
                    result.append(match.groups()[0])
        return tuple(result)


class TestCaseMapping(object):
    """Maps test file and methods to requirement IDs"""

    def __init__(self, data):
        self.mapping = self._build_mapping(data)

    @staticmethod
    def _build_mapping(data):
        result = {}
        for req_id, metadata in data.iteritems():
            req = Requirement(metadata)
            for test_file in req.test_files:
                method_data = result.setdefault(test_file, {})
                method = req.test_method or "*"
                method_data.setdefault(method, []).append(req_id)
        return result

    def get_ids(self, test_file, test_method):
        """Returns a list of requirement IDs for the given test_file and
        method.  If no IDs are mapped, then it returns an empty list"""
        if test_file not in self.mapping:
            return []
        file_data = self.mapping[test_file]
        if test_method in file_data:
            return file_data[test_method]
        elif "*" in file_data:
            return file_data["*"]
        else:
            return []


class TestAnnotator(object):
    """Processes a directory of tests, and applies the `@validates`
    decorator to each test method that has a requirement ID mapped to it
    in the associated `TestMapping` instance."""

    TEST_PATTERN = re.compile("^def\s+(test_.*?)\(.*")

    def __init__(self, mappings, base_dir, output_dir):
        """Instantiates a TestAnnotator.

        :param mappings: `TestMapping` that maps Requirement IDs to tests
        :param base_dir: directory containing the test files
        :param output_dir: directory to write the transformed files.  All
                           files in `base_dir` will be copied to their same
                           relative directory in `output_dir`.  Only methods
                           that have a requirements ID mapped will be
                           annotated; all other files will be copied as-is
        """
        assert os.path.isdir(base_dir)
        assert mappings is not None
        make_dirs(output_dir)
        self.mappings = mappings
        self.base_dir = base_dir
        self.output_dir = output_dir

    def _walk_all_files(self):
        """Recursively walk the `base_dir` and yield each file path"""
        for dir_path, sub_dirs, filenames in os.walk(self.base_dir):
            for filename in filenames:
                yield os.path.join(dir_path, filename)

    def annotate(self):
        """Processes all files in `base_dir` copying them to `output_dir`
        while adding `@validates` decorators to any test method that
        is associated with a requirements ID in `mappings`"""
        for source_file in self._walk_all_files():
            self._transform_or_copy(source_file)

    def _transform_or_copy(self, source_file):
        if os.path.split(source_file)[1].startswith("test_"):
            self._process_transform(source_file)
        else:
            self._copy_to_output(source_file)

    def _process_transform(self, source_file):
        """Adds the `@validates` decorator if a test mapping exists for a
        given test method, otherwise it copies the file as is"""
        target = self._make_target_path(source_file)
        with open(source_file, "r") as infile, open(target, "w") as outfile:
            for line in infile:
                if line.startswith("@validates("):
                    continue  # we'll skip this one and generate a new one
                if self._is_test_method(line):
                    annotation = self._get_annotation(source_file, line)
                    if annotation:
                        outfile.write(annotation)
                        outfile.write("\n")
                outfile.write(line)

    def _copy_to_output(self, source_file):
        target_file = self._make_target_path(source_file)
        shutil.copy(source_file, target_file)

    def _make_target_path(self, source_file):
        """Creates any directories needed in `output_dir` and returns
        the full path for the target output file"""
        relative_path = os.path.relpath(source_file, self.base_dir)
        relative_dir, filename = os.path.split(relative_path)
        output_dir = os.path.join(self.output_dir, relative_dir)
        make_dirs(output_dir)
        return os.path.join(output_dir, filename)

    def _is_test_method(self, line):
        return self.TEST_PATTERN.search(line)

    def _get_annotation(self, source_file, line):
        """Returns a formatted `@validates` decorator for the given
        source file and method"""
        filename = os.path.split(source_file)[1]
        method_name = self.TEST_PATTERN.search(line).groups()[0]
        ids = self.mappings.get_ids(filename, method_name)
        if ids:
            quoted_ids = ("'" + r_id + "'" for r_id in ids)
            return "@validates(" + ", ".join(quoted_ids) + ")"
        else:
            return None


if __name__ == "__main__":
    requirements = load_yaml("requirements.yaml")
    mappings = TestCaseMapping(requirements)
    annotator = TestAnnotator(mappings, "tests", "build")
    annotator.annotate()
