.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. Copyright 2018 AT&T Intellectual Property.  All rights reserved.

Manual Heat Template Validation
===============================

validation-scripts
------------------

This project contains validation scripts to test
that a set of Heat Templates adheres to
the ONAP VNF Heat Orchestration Template guidelines.

For more information on the ONAP Heat Orchestration
Template Guidelines, vist the `Heat Guidelines <https://onap.readthedocs.io/en/latest/submodules/vnfrqts/requirements.git/docs/Chapter5/Heat/index.html>`__

About
_____

The validation scripts project allows performing heat template
validation without installing the full VVP platform. The following
instructions apply to running these validation scripts in that manner.


Installation
____________

This software is not platform dependent and can be run in a Windows, Unix or
OS X environment.

Satisfy Dependencies
####################


 These can be installed using pip (assuming pip is installed) with the command:

``$ pip install -r requirements.txt``

Use
___

Clone this project.

To validate Heat templates just run this the command under the folder ``ice_validator``:

``</path/to/validation-scripts/ice_validator>$ pytest --tap-stream --template-directory=<Directory>``

where ``<Directory>`` is the full path to a folder containing heat templates.

Output
______

After performing a validation, an output folder will be created.

``/path/to/validation-scripts/ice_validator/output/``

This folder will contain a file ``report.html`` which contains a list of all
of the ONAP VNF Heat Template Guideline violations. If there are no violations,
the report will say ``No validation errors found.``

Interpreting the Output
_______________________

The report file will have 4 columns for details about a violation, and one
row for each violation. Below contains details about each column.

File
####

This is the file(s) that contained the violation

Error Message
#############

This shows the test and brief error message from the validation script that
contained the violation. There is a ``Full Details`` button to show the
complete raw test output. The error message will also contain details
about what element is involved with the violation (such as the parameter
name, resource id, etc...).

Requirement(s)
##############

This column contains the requirement(s) that each test/violation is
mapped to. These requirements are taken directly from the VNF Requirements
project Heat Orchestration Template Guidelines section.


Resolution Steps
################

For some violations, there are pre-defined resolution steps that
indicate what action the user should take to resolve the violation.

**Note**: Not all violations will have resolution steps. Most violations
can be resolved simply by reviewing the requirements that have been violated
in the previous column.


Self-Test Suite
_______________

The ``ice_validator`` includes an extensive self-test suite. It is a
**requirement** for any additions or changes to the test suite to
successfully and cleanly complete a tox run. Simply run ``tox`` from
the project root as:

``$ tox``

You can also run it under the folder ``ice_validator``:

``$ pytest --self-test``

