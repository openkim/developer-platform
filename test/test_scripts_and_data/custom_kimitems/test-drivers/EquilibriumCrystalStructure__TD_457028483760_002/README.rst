=======================================
EquilibriumCrystalStructure Test Driver
======================================= 
This driver calculates equilibrium crystal structure and energy at zero temperature and pressure. Supports arbitrary crystal prototypes specified using the AFLOW prototype designation. Also included are utilities for generating and postprocessing tests and reference data.

Python packages required for all scripts and modules are found in ``requirements.txt``. You may need to install the ``pkg-config`` and/or ``python3-pip`` utilities using your package manager first. The ``kimpy`` package requires the KIM API to be installed, see `<https://github.com/openkim/kimpy>`_. ``kimpy`` is not required if you are only building tests and/or reference data and not running the driver. Both building and running the tests require the AFLOW executable to be in ``PATH``. The required version is not publicly available yet.

From this directory, install them using (requirements include a github repo, so can't pass entire file to pip at once):
    
    .. code-block:: bash

      xargs -L 1 pip install < requirements.txt

To build the documentation:

  1) Install the Python requirements as above (including ``kimpy``, otherwise the documentation will not build)
  2) Install Sphinx packages:
    .. code-block:: bash

      cd docs; pip install -r requirements_docs.txt

    You may need to add ``~/.local/bin`` to your ``PATH`` environment variable.
  3) If you downloaded the Test Driver from openkim.org, you need to add the following symlink for Sphinx to understand that ``runner`` is a Python file (run the command from the ``docs`` directory):
    .. code-block:: bash

      ln -s ../runner links/runner.py

  4) Build the documentation:
    .. code-block:: bash

      make html

The documentation is located at ``docs/build/html/index.html``
  