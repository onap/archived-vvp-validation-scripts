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

from tests.structures import ContrailV2VirtualMachineInterfaceProcessor
from tests.helpers import validates
from tests.utils.ports import check_parameter_format

RE_EXTERNAL_PARAM_AAP = re.compile(  # match pattern
    r"(?P<vm_type>.+)_(?P<network_role>.+)_floating(_v6)?_ip$"
)

RE_INTERNAL_PARAM_AAP = re.compile(  # match pattern
    r"(?P<vm_type>.+)_int_(?P<network_role>.+)_floating(_v6)?_ip$"
)

RE_INTERNAL_PARAM_AAPS = re.compile(  # match pattern
    r"(?P<vm_type>.+)_int_(?P<network_role>.+)_floating(_v6)?_ips$"
)

aap_regx_dict = {
    "external": {
        "string": {
            "readable": "{vm-type}_{network-role}_floating_ip or {vm-type}_{network-role}_floating_v6_ip",
            "machine": RE_EXTERNAL_PARAM_AAP,
        }
    },
    "internal": {
        "string": {
            "readable": "{vm-type}_int_{network-role}_floating_ip or {vm-type}_int_{network-role}_floating_v6_ip",
            "machine": RE_INTERNAL_PARAM_AAP,
        },
        "comma_delimited_list": {
            "readable": "{vm-type}_int_{network-role}_floating_ips or {vm-type}_int_{network-role}_floating_v6_ips",
            "machine": RE_INTERNAL_PARAM_AAPS,
        },
    },
    "parameter_to_resource_comparisons": ["vm_type", "network_role"],
}


@validates("R-100310", "R-100330", "R-100350")
def test_contrail_external_vmi_aap_parameter(yaml_file):
    check_parameter_format(yaml_file,
                           aap_regx_dict,
                           "external",
                           ContrailV2VirtualMachineInterfaceProcessor,
                           "virtual_machine_interface_allowed_address_pairs",
                           "virtual_machine_interface_allowed_address_pairs_allowed_address_pair",
                           "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip",
                           "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip_ip_prefix")


@validates("R-100360", "R-100370")
def test_contrail_internal_vmi_aap_parameter(yaml_file):
    check_parameter_format(yaml_file,
                           aap_regx_dict,
                           "internal",
                           ContrailV2VirtualMachineInterfaceProcessor,
                           "virtual_machine_interface_allowed_address_pairs",
                           "virtual_machine_interface_allowed_address_pairs_allowed_address_pair",
                           "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip",
                           "virtual_machine_interface_allowed_address_pairs_allowed_address_pair_ip_ip_prefix")
