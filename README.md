# ice-heat-validation

This project contains a ``pytest`` tool that automatically checks Heat Templates 
are adhering to the AT&T Domain 2.0 Heat Template Guidelines.

# Installation

This software is not platform dependent and can be run in a Windows, Unix or 
OS X environment.

### Satisfy Dependencies

In addition to python, this project requires the following packages:

 - ``pytest``
 - ``PyYAML``
 - ``pytest-tap``
 
 These can be installed using pip (assuming pip is installed) with the command:
 
``$ pip install -r requirements.txt``

# Use

Clone this project.

To validate Heat templates just run this the command under the folder ``ice_validator``:

``$ pytest --tap-stream --template-directory=<Directory>``

where ``<Directory>`` is the absolute path to the folder containing the Heat 
Templates to be verified.


# Self-Test Suite

The ``ice_validator`` includes an extensive self-test suite. It is a 
**requirement** for any additions or changes to the test suite to 
successfully and cleanly complete a tox run. Simply run ``tox`` from 
the project root as:

``$ tox``

You can also run it under the folder ``ice_validator``:

``$ pytest --self-test``
