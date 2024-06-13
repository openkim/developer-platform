.. _doc.refdata_gen_format:

Format of a reference data generator
------------------------------------

Below is the format of a reference data generator -- an output of :mod:`build_tests_refdata_from_aflow`. This data is used by the ``kimgenie`` utility to generate reference data. The fields in the generator are used to populate ``kimspec.edn`` and locate the ``data.edn`` file. This entire generator would be a single line in a reference data generator file. 

.. data:: species
    :noindex:

    the atomic species of the material(s) in this test. These are always in alphabetical order.

    :type: list[str]
    
.. data:: prototype_label
    :noindex:

    the AFLOW prototype label of the material(s) in this test

    :type: string

.. data:: library_prototype_label
    :noindex:

    The closest, if any, matching AFLOW library prototype label

    :type: str

.. data:: short_name
    :noindex:

    the human-readable name for the structure described by the closest matching library prototype, if any

    :type: str

.. data:: hyperparams_dict 
    
    Selected DFT hyperparameters of this AFLOW calculation and their values

    :type: dict

.. data:: aflow_version
    :noindex:

    Version of the ``aflow++`` executable used for detecting the material's AFLOW prototype designation

    :type: str

.. data:: auid
    :noindex:

    AFLOW Unique IDentifier

    :type: str

.. data:: url
    :noindex:

    The exact URL that the atomic coordinates were downloaded from

    :type: str

.. data:: kimnum
    :noindex:

    12-digit KIM number

    :type: str

.. data:: kim_user_id
    :noindex:

    KIM user ID of the person running the script

    :type: str

.. data:: access_year
    :noindex:

    Access year

    :type: str

.. data:: access_date
    :noindex:

    Access month and day

    :type: str

.. data:: FILES_TO_COPY
    :noindex:

    Generic field containing paths of files for ``kimgenie`` to copy into the rendered item directory. In this case, it contains a single path to the ``data.edn`` file containing a single instance each of the ``binding-energy-crystal`` and ``crystal-structure-npt`` properties.

    :type: list[str]
    

Example reference data generator
================================

As mentioned above, the entire generator entry entry is written to a single line. Here the formatting is beautified into a multi-line dictionary for clarity. 

.. code-block:: json
    
    {
    "hyperparams_dict": {
        "dft_type": [
        "PAW_PBE"
        ],
        "ldau_type": 2
    },
    "aflow_version": "3.2.13 w/private patch from D. Hicks",
    "auid": "aflow:211010b0b4e6eea8",
    "url": "http://aflowlib.duke.edu/AFLOWDATA/ICSD_WEB/RHL/S2W1_ICSD_202367/CONTCAR.relax.vasp",
    "species": [
        "S",
        "W"
    ],
    "kimnum": "585999763606",
    "kim_user_id": "4ad03136-ed7f-4316-b586-1e94ccceb311",
    "access_year": "2023",
    "access_date": "1-20",
    "FILES_TO_COPY": [
        "Refdata/585999763606/data.edn"
    ]
    }
