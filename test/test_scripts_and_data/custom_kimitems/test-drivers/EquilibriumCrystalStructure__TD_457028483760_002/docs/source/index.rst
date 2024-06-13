.. EquilibriumCrystalStructure documentation master file, created by
   sphinx-quickstart on Sat Jul 30 03:19:13 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to EquilibriumCrystalStructure's documentation!
=======================================================

Introduction
------------

This package contains the test driver ``EquilibriumCrystalStructure__TD_457028483760_002`` (documented in :mod:`runner`), which computes KIM properties `binding-energy-crystal <https://openkim.org/properties/show/2023-02-21/staff@noreply.openkim.org/binding-energy-crystal>`_ and `crystal-structure-npt <https://openkim.org/properties/show/2023-02-21/staff@noreply.openkim.org/crystal-structure-npt>`_, and the utility :mod:`build_tests_refdata_from_aflow`, which is used to generate associated tests and reference data  by pulling data from `<http://aflow.org>`_. For more information, see the `OpenKIM Documentation <https://openkim.org/doc/>`_ and, more specifically, the `Introduction to KIM tests <https://openkim.org/doc/evaluation/kim-tests/>`_.

This test driver is part of the *Crystal Genome* testing framework. The methodology used by Crystal Genome to classify crystal structures uses the AFLOW prototype designation as a crucial component. See :ref:`doc.appendices` for more information.

Use
---

The bulk of the work in generating the tests and reference data can be done independently of any KIM installation, e.g. on a cluster by running multiple instances of :mod:`build_tests_refdata_from_aflow`. Rendering the generated files into OpenKIM tests and reference data must be done in the `KIM Development Platform (KDP) <KDP_>`_ using the ``kimgenie`` utility. See :ref:`doc.testgen` for more information. Both generating and running the tests requires the `aflow executable <AFLOW_>`_ to be in ``PATH``. The required version is not publicly available yet.

.. _KDP: https://openkim.org/doc/evaluation/kim-developer-platform/
.. _AFLOW: http://aflow.org/install-aflow/
   
Package contents
----------------
   
Python files and packages:

   :mod:`build_tests_refdata_from_aflow`:
      This is a script for generating the files to be used by the ``kimgenie`` utility to build tests and reference data.

   :mod:`runner`:
      This is the main executable of the test driver. It can be invoked directly, or through the OpenKIM pipeline

   ``scripts`` directory:
      ``get_species_combos.py``:
         Get all species combinations that OpenKIM has potentials for up to a given number of species. Split it into a requested number of chunks for parallel processing. The chunks are load balanced based on the number of structures for each species combination in the ICSD subset of the AFLOW database. Write ``species_combos_[n].txt``, as well as ``download[n].in`` and ``process[n].in`` -- input files for :mod:`build_tests_refdata_from_aflow` for downloading and processing the structures separately.

      ``get_taken_rd_kimnums.py``:
         A script for regenerating ``taken_rd_kimnums.json`` by querying OpenKIM
      
Data and input files:

   ``taken_rd_kimnums.json``:
      12-digit KIM ID numbers already occupied by reference data in OpenKIM.org. Required to exist in the working directory for :mod:`build_tests_refdata_from_aflow` to generate reference data. 

   ``build_example.in``:
      Pipe this into :mod:`build_tests_refdata_from_aflow` to generate tests and reference data for AlMg

   ``example_work_dir`` directory:
      Example working directory corresponding to ``build_example.in``

      ``species_combos_0.txt``:
         A required file specifying which species combinations :mod:`build_tests_refdata_from_aflow` will build, in this case AlMg

   ``test_template`` directory:
      This directory contains the templating files used by the OpenKIM ``kimgenie`` utility to build tests associated with this test driver
      
   ``refdata_template`` directory:
      This directory contains the file used by the OpenKIM ``kimgenie`` utility to build the ``kimspec.edn`` file for reference data      

Documentation contents
======================

.. toctree::
   :maxdepth: 1

   testgen      
   runner
   test_gen_format
   refdata_gen_format
   appendices

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`