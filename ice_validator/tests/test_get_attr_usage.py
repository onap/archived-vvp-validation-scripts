import os

import pytest

from tests.helpers import validates, traverse, load_yaml
from tests.structures import Resource
from tests.utils import nested_dict


class GetAttrValidator:
    def __init__(self, yaml, base_dir):
        self.yaml = yaml
        self.base_dir = base_dir
        self.errors = []

    @property
    def resources(self):
        return self.yaml.get("resources", {})

    def __call__(self, path, get_attr_arg):
        if not isinstance(get_attr_arg, list):
            self.add_error(path, get_attr_arg, "get_attr argument is not a list")
        elif len(get_attr_arg) < 1:
            self.add_error(
                path, get_attr_arg, "get_attr argument must have a parameter"
            )
        elif get_attr_arg[0] not in self.resources:
            self.add_error(
                path,
                get_attr_arg,
                "Resource ID could not be found.  Please ensure "
                "the resource is spelled correctly and defined "
                "under the resources section of the YAML file.",
            )
        else:
            r_id = get_attr_arg[0]
            r = Resource(r_id, self.yaml["resources"][r_id])
            if not r.is_nested():
                return
            if len(get_attr_arg) < 2:
                self.add_error(
                    path,
                    get_attr_arg,
                    "get_attr used on nested "
                    "resource, but no attribute "
                    "value specified",
                )
                return
            expected_param = get_attr_arg[1]
            nested_yaml = r.get_nested_yaml(self.base_dir)
            param = nested_dict.get(nested_yaml, "outputs", expected_param)
            if not param:
                self.add_error(
                    path,
                    get_attr_arg,
                    "Attribute key "
                    + expected_param
                    + " not found in outputs "
                    + r.get_nested_filename(),
                )

    def add_error(self, path, arg, message):
        path_str = ".".join(path)
        self.errors.append("{} {}: {}".format(path_str, arg, message))

    @property
    def error_message(self):
        errs = ", ".join(self.errors)
        return "Invalid get_attr usage detected: {}".format(errs)


@pytest.mark.base
@validates("R-95303")
def test_08_validate_get_attr_usage(yaml_file):
    """Ensures that every get_attr refers to a valid resource name,
    and if that resource is a nested YAML that the attribute exists as
    an output of the nested YAML file.  It does not validate the
    attribute keys are always valid because of the attributes could
    refer to intrinsic attributes of the resource that are not present
    in the YAML file."""

    yml = load_yaml(yaml_file)
    base_dir, _ = os.path.split(yaml_file)
    validator = GetAttrValidator(yml, base_dir)
    traverse(yml, "get_attr", validator)
    assert not validator.errors, validator.error_message
