#!/bin/bash

# ================================================================================
# Copyright (c) 2017 AT&T Intellectual Property. All rights reserved.
# ================================================================================
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============LICENSE_END=========================================================
#
# ECOMP is a trademark and service mark of AT&T Intellectual Property.

set -ex


echo "running script: [$0] for module [$1] at stage [$2]"

MVN_PROJECT_MODULEID="$1"
MVN_PHASE="$2"
PROJECT_ROOT=$(dirname $0)

run_tox_test () {
  CURDIR=$(pwd)
  TOXINIS=$(find . -name "tox.ini")
  for TOXINI in "${TOXINIS[@]}"; do
    DIR=$(echo "$TOXINI" | rev | cut -f2- -d'/' | rev)
    cd "${CURDIR}/${DIR}"
    rm -rf ./venv-tox ./.tox
    virtualenv ./venv-tox
    source ./venv-tox/bin/activate
    pip install --upgrade pip
    pip install --upgrade tox argparse
    pip freeze
    tox
    deactivate
    rm -rf ./venv-tox ./.tox
  done
}

# Customize the section below for each project
case $MVN_PHASE in
test)
  echo "==> test phase script"
  run_tox_test
  ;;
*)
  echo "==> unprocessed phase"
  ;;
esac


