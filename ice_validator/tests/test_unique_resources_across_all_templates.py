# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
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
#

import collections
import os

from tests import cached_yaml as yaml

from .helpers import validates


@validates("R-16447")
def test_unique_resources_across_all_yaml_files(yaml_files):
    """
    Check that all instance names are unique
    across all yaml files.
    """
    resources_ids = collections.defaultdict(set)
    for yaml_file in yaml_files:
        with open(yaml_file) as fh:
            yml = yaml.load(fh)
        if "resources" not in yml:
            continue
        for resource_id in yml["resources"]:
            resources_ids[resource_id].add(os.path.split(yaml_file)[1])

    dup_ids = {r_id: files for r_id, files in resources_ids.items() if len(files) > 1}

    msg = "The following resource IDs are duplicated in one or more files: "
    errors = [
        "ID ({}) appears in {}.".format(r_id, ", ".join(files))
        for r_id, files in dup_ids.items()
    ]
    msg += ", ".join(errors)
    assert not dup_ids, msg
