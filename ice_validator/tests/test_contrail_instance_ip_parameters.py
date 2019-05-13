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
import re

from tests.structures import ContrailV2InstanceIpProcessor
from tests.helpers import validates
from tests.utils.ports import check_parameter_format

RE_EXTERNAL_PARAM_IIP = re.compile(  # match pattern
    r"(?P<vm_type>.+)_(?P<network_role>.+?)(_v6)?_ip_(?P<ip_index>.+)$"
)

RE_EXTERNAL_PARAM_IIPS = re.compile(  # match pattern
    r"(?P<vm_type>.+)_(?P<network_role>.+?)(_v6)?_ips$"
)

RE_INTERNAL_PARAM_IIP = re.compile(  # match pattern
    r"(?P<vm_type>.+)_int_(?P<network_role>.+?)(_v6)?_ip_(?P<ip_index>.+)$"
)

RE_INTERNAL_PARAM_IIPS = re.compile(  # match pattern
    r"(?P<vm_type>.+)_int_(?P<network_role>.+?)(_v6)?_ips$"
)

iip_regx_dict = {
    "external": {
        "string": {
            "readable": "{vm-type}_{network-role}_ip_{ip-index} or {vm-type}_{network-role}_v6_ip_{ip-index}",
            "machine": RE_EXTERNAL_PARAM_IIP,
        },
        "comma_delimited_list": {
            "readable": "{vm-type}_{network-role}_ips or {vm-type}_{network-role}_v6_ips",
            "machine": RE_EXTERNAL_PARAM_IIPS,
        },
    },
    "internal": {
        "string": {
            "readable": "{vm-type}_int_{network-role}_ip_{ip-index} or {vm-type}_int_{network-role}_v6_ip_{ip-index}",
            "machine": RE_INTERNAL_PARAM_IIP,
        },
        "comma_delimited_list": {
            "readable": "{vm-type}_int_{network-role}_ips or {vm-type}_int_{network-role}_v6_ips",
            "machine": RE_INTERNAL_PARAM_IIPS,
        },
    },
    "parameter_to_resource_comparisons": ["vm_type", "network_role"],
}


RE_EXTERNAL_PARAM_SID = re.compile(  # match pattern
    r"(?P<network_role>.+?)(_v6)?_subnet_id$"
)

RE_INTERNAL_PARAM_SID = re.compile(  # match pattern
    r"int_(?P<network_role>.+?)(_v6)?_subnet_id$"
)

sid_regx_dict = {
    "external": {
        "string": {
            "readable": "{network-role}_subnet_id or {network-role}_v6_subnet_id",
            "machine": RE_EXTERNAL_PARAM_SID,
        },
    },
    "internal": {
        "string": {
            "readable": "int_{network-role}_subnet_id or int_{network-role}_v6_subnet_id",
            "machine": RE_INTERNAL_PARAM_SID,
        },
    },
    "parameter_to_resource_comparisons": ["network_role"],
}


@validates("R-100000", "R-100010", "R-100030", "R-100150", "R-100070")
def test_contrail_external_instance_ip_address_parameter(yaml_file):
    check_parameter_format(yaml_file, iip_regx_dict, "external", ContrailV2InstanceIpProcessor, "instance_ip_address")


@validates("R-100000", "R-100090", "R-100110", "R-100130", "R-100180")
def test_contrail_internal_instance_ip_address_parameter(yaml_file):
    check_parameter_format(yaml_file, iip_regx_dict, "internal", ContrailV2InstanceIpProcessor, "instance_ip_address")


@validates("R-100190", "R-100200", "R-100220")
def test_contrail_external_instance_subnet_id_parameter(yaml_file):
    check_parameter_format(yaml_file, sid_regx_dict, "external", ContrailV2InstanceIpProcessor, "subnet_uuid")


@validates("R-100190", "R-100240", "R-100260")
def test_contrail_internal_instance_subnet_id_parameter(yaml_file):
    check_parameter_format(yaml_file, sid_regx_dict, "internal", ContrailV2InstanceIpProcessor, "subnet_uuid")





