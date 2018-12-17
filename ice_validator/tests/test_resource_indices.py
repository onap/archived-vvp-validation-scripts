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
import collections
from itertools import chain
from .structures import Heat
from .helpers import validates


def has_next(seq, index):
    """
    Returns true if there is at least one more item after the current
    index in the sequence
    """
    next_index = index + 1
    return len(seq) > next_index


@validates("R-11690")
def test_indices_start_at_0_increment(yaml_files):
    resources_ids = chain.from_iterable(Heat(f).resources.keys() for f in yaml_files)
    prefix_indices = collections.defaultdict(set)
    for r_id in resources_ids:
        parts = r_id.split("_")
        prefix_parts = []
        for i, part in enumerate(parts):
            if part.isdigit():
                # It's an index so let's record it and its prefix
                prefix = "_".join(prefix_parts) + "_"
                index = int(part)
                prefix_indices[prefix].add(index)
            prefix_parts.append(part)
    errors = []
    for prefix, indices in prefix_indices.items():
        indices = sorted(indices)
        if indices[0] != 0:
            errors.append(
                (
                    "Index values associated with resource ID "
                    + "prefix {} do not start at 0".format(prefix)
                )
            )
        elif indices[-1] != (len(indices) - 1):
            errors.append(
                (
                    "Index values associated with resource ID "
                    + "prefix {} are not contiguous: {}"
                ).format(prefix, indices)
            )
    assert not errors, ". ".join(errors)
