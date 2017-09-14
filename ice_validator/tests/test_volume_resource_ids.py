# -*- coding: utf8 -*-
# ============LICENSE_START=======================================================
# org.onap.vvp/validation-scripts
# ===================================================================
# Copyright © 2017 AT&T Intellectual Property. All rights reserved.
# ===================================================================
#
# Unless otherwise specified, all software contained herein is licensed
# under the Apache License, Version 2.0 (the “License”);
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
# under the Creative Commons License, Attribution 4.0 Intl. (the “License”);
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

import re
import pytest
import yaml
from .utils.vm_types import get_vm_type_for_nova_server


def test_volume_resource_ids(heat_template):
    '''
    Check that all resource ids for cinder volumes follow the right
    naming convention to include the {vm_type} of the
    nova server it is associated to
    '''
    with open(heat_template) as fh:
        yml = yaml.load(fh)

    # skip if resources are not defined
    if "resources" not in yml:
        pytest.skip("No resources specified in the heat template")

    volume_pattern = re.compile(r'(.+?)_volume_id_\d+')
    resources = yml['resources']

    invalid_volumes = []
    for k, v in resources.items():
        if not isinstance(v, dict):
            continue
        if 'type' not in v:
            continue
        if v['type'] not in ['OS::Nova::Server',
                             'OS::Cinder::VolumeAttachment']:
            continue

        if v['type'] == 'OS::Nova::Server':
            # check block_device_mapping and make sure the right
            # {vm_type} is used
            if 'properties' not in v:
                continue
            if 'block_device_mapping' not in v['properties']:
                continue

            vm_type = get_vm_type_for_nova_server(v)
            if not vm_type:
                continue
            vm_type = vm_type.lower()

            # get the volume_id from the block_device_mapping
            properties = v['properties']
            for v2 in properties['block_device_mapping']:
                for k3, v3 in v2.items():
                    if k3 != 'volume_id':
                        continue
                    if not isinstance(v3, dict):
                        continue

                    volume_id = (
                        v3.get('get_param') or
                        v3.get('get_resource'))
                    if not volume_id:
                        continue
                    if isinstance(volume_id, list):
                        volume_id = volume_id[0].lower()
                    else:
                        volume_id = volume_id.lower()

                    if vm_type+"_" not in volume_id:
                        invalid_volumes.append(volume_id)

        elif v['type'] == 'OS::Cinder::VolumeAttachment':
            # check the volume attachment and the {vm_type}
            # of the corresponding nova server
            if 'properties' not in v:
                continue
            if 'volume_id' not in v['properties']:
                continue
            if 'instance_uuid' not in v['properties']:
                continue

            properties = v['properties']

            # get the instance_uuid and when applicable
            # the nova server instance
            instance_uuid = None
            nova_server = None

            if 'get_param' in properties['instance_uuid']:
                continue
            elif 'get_resource' in properties['instance_uuid']:
                instance_uuid = properties['instance_uuid']['get_resource']
                if not resources[instance_uuid]:
                    continue
                nova_server = resources[instance_uuid]
                instance_uuid = instance_uuid.lower()
            else:
                continue

            # get the volume_id
            volume_id = None
            volume_id = (
                properties['volume_id'].get('get_param') or
                properties['volume_id'].get('get_resource'))
            if not volume_id:
                continue
            if isinstance(volume_id, list):
                volume_id = volume_id[0].lower()
            else:
                volume_id = volume_id.lower()

            # do not test the case when the instance_uuid and
            # volume_id are not defined
            if not instance_uuid and not volume_id:
                continue

            if nova_server:
                vm_type = get_vm_type_for_nova_server(nova_server)
                if not vm_type:
                    continue
                vm_type = vm_type.lower()
                if vm_type+"_" not in volume_id:
                    invalid_volumes.append(volume_id)
            else:
                # extract the assumed {vm_type} from volume_id
                m = volume_pattern.match(volume_id)
                if m:
                    vm_type = m.group(1).lower()
                    if vm_type+"_" not in instance_uuid:
                        invalid_volumes.append(volume_id)
                else:
                    continue

    assert not set(invalid_volumes)
