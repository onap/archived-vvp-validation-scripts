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
#

"""heat parameters
"""

import collections

import pytest

from .structures import CinderVolumeAttachmentProcessor
from .structures import NovaServerProcessor
from .structures import get_all_resources
from .helpers import validates

VERSION = "2.0.0"


class VmClassValidator(object):
    """validate VM class has unique type
    """

    def __init__(self):
        self.vm_counts = None
        self.vm_classes = None
        self.vm_rids = None
        self.vm_types = None
        self.va_count = None

    def __call__(self, resources):
        """return (possibly empty) list of error message strings
        """
        if not resources:
            pytest.skip("No resources found")
        self.vm_counts = collections.defaultdict(set)
        self.vm_classes = collections.defaultdict(set)
        self.vm_rids = collections.defaultdict(set)
        self.vm_types = collections.defaultdict(set)
        va_config, self.va_count = CinderVolumeAttachmentProcessor.get_config(resources)
        if not va_config:
            pytest.skip("No Cinder Volume Attachment configurations found")
        for rid, resource in resources.items():
            vm_class = NovaServerProcessor.get_vm_class(resource)
            if vm_class:
                vm_class["cinder_volume_attachment"] = va_config.get(rid)
                match = NovaServerProcessor.get_rid_match_tuple(rid)[1]
                if match:
                    vm_type = match.groupdict().get("vm_type")
                    if vm_type:
                        self.vm_classes[vm_class].add(rid)
                        self.vm_types[vm_type].add(vm_class)
                        self.vm_counts[vm_type].add(self.va_count.get(rid))
                        self.vm_rids[vm_type].add(rid)
        if not self.vm_classes:
            pytest.skip("No vm_classes found")
        return self.get_errors()

    def get_errors(self):
        """return (possibly empty) list of error message strings
        """
        errors = []
        for k, v in self.vm_types.items():
            if len(v) > 1:
                errors.append(
                    "vm-type %s has class conflict %s"
                    % (k, ", ".join(str(list(self.vm_classes[c])) for c in v))
                )
                classes = list(v)
                errors.append(
                    "Differences %s"
                    % ", ".join([str(key_diff(classes[0], c)) for c in classes[1:]])
                )
        for k, v in self.vm_counts.items():
            if len(v) > 1:
                errors.append(
                    "Attachment count conflict %s"
                    % ({rid: self.va_count.get(rid) for rid in self.vm_rids[k]})
                )
        return errors


def key_diff(d1, d2, prefix=""):
    """Return list of keys which differ between d1 and d2 (dicts)
    """
    diff = [prefix + k for k in d1 if k not in d2]
    diff.extend(prefix + k for k in d2 if k not in d1)
    if isinstance(d1, dict) and isinstance(d2, dict):
        for k, v1 in d1.items():
            if k in d2 and v1 != d2[k]:
                v2 = d2[k]
                if isinstance(v1, type(v2)) and isinstance(v1, (dict, frozenset)):
                    diff.extend(key_diff(v1, v2, prefix=prefix + k + "."))
                else:
                    diff.append(prefix + k)
    return diff


@validates("R-01455")
def test_vm_class_has_unique_type(yaml_files):
    """
    When a VNF’s Heat Orchestration Template creates a Virtual
    Machine (i.e., OS::Nova::Server), each “class” of VMs MUST be
    assigned a VNF unique vm-type; where “class” defines VMs that
    MUST have the following identical characteristics:

    1.  OS::Nova::Server resource property flavor value
    2.  OS::Nova::Server resource property image value
    3.  Cinder Volume attachments
        Each VM in the “class” MUST have the identical Cinder
        Volume configuration
    4.  Network attachments and IP address requirements
        Each VM in the “class” MUST have the the identical number of
        ports connecting to the identical networks and requiring the
        identical IP address configuration
    """
    resources = get_all_resources(yaml_files)
    errors = VmClassValidator()(resources)
    assert not errors, "\n".join(errors)
