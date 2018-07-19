'''test env file has no resource_registry
'''

import yaml

from .helpers import validates

VERSION = '1.0.0'


@validates('R-70112', 'R-67231')
def test_env_no_resource_registry(env_files):
    '''
    A VNF's Heat Orchestration template's Environment File's
    **MUST NOT** contain the "resource_registry:" section.
    '''
    for filename in env_files:
        with open(filename) as fi:
            yml = yaml.load(fi)
        assert 'resource_registry' not in yml, (
                '%s contains "resource_registry"' % filename)
