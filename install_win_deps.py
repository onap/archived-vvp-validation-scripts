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
import os
import platform
import subprocess #nosec
import sys
import tempfile
from urllib import request

PREBUILT_DOWNLOAD_SITE = "https://download.lfd.uci.edu/pythonlibs/n5jyqt7p/"
PREBUILT_WIN_LIBS = [
    "yappi-1.0-cp{python_version}-cp{python_version}m-{arch}.whl",
    "setproctitle-1.1.10-cp{python_version}-cp{python_version}m-{arch}.whl"
]


def is_windows():
    return os.name == 'nt'


def python_version():
    return sys.version[:3].replace(".", "")


def system_architecture():
    arch = platform.architecture()
    return "win32" if arch[0] != "64bit" else "win_amd64"


def download_url(url):
    resp = request.urlopen(url) #nosec
    return resp.read()


def read_file(path):
    with open(path, "r") as f:
        return f.read()


def write_file(data, path, mode="w"):
    with open(path, mode) as f:
        f.write(data)


def install_prebuilt_binaries_on_windows():
    if not is_windows():
        return
    temp_dir = tempfile.mkdtemp()
    for lib in PREBUILT_WIN_LIBS:
        filename = lib.format(python_version=python_version(),
                              arch=system_architecture())
        url = PREBUILT_DOWNLOAD_SITE + filename
        print(f"Downloading {url}")
        contents = download_url(url)
        file_path = os.path.join(temp_dir, filename)
        write_file(contents, file_path, mode="wb")
        print("Download complete. Installing dependency.")
        subprocess.call(["pip", "install", file_path]) #nosec


if __name__ == "__main__":
    install_prebuilt_binaries_on_windows()
