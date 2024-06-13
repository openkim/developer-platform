.. _doc.appendices:

=======================================
Appendix: AFLOW prototypes and symmetry
=======================================

.. _doc.appendices.aflowproto:

AFLOW prototype designation
---------------------------

See slide 5 of http://aflow.org/aflow-school/past_schools/20210906/03_aflow_school_prototypes.pdf or the section titled *Problem of the ideal prototype* in |XtalFinder-paper|_. For example, the AFLOW prototype designation of the Wurtzite structure is the prototype ``AB_hP4_186_b_b``, accompanied by free parameters `a` = 3.82, `c/a` = 1.64, `z1` = 0.37, and `z2` = 0. This describes a unit cell with 4 atoms, restricting the numerical parameters to degrees of freedom to those allowed by symmetry. This is how crystal structures are designated in this package and other Crystal Genome tests and properties. This representation is not only shorter than writing the full 6 lattice parameters coordinates of every atom in the unit cell, but also explicitly conveys the crystal symmetry, which is especially important for the human-readable property instance.

.. _doc.appendices.aflowlibproto:

AFLOW library prototype
-----------------------

AFLOW also maintains a curated library of prototype designations corresponding to known compounds and their human-readable "short names". It is supplied with the ``aflow++`` code and duplicated in the ``crystal-genome-util`` package. The library prototype is typically designated by a prototype label with a suffix, e.g. ``AB_hP4_186_b_b-001`` is specifically "Wurtzite", and implies the free parameters listed in the previous section. Note that library prototypes are defined only up to a scaling factor, i.e. they do not include the `a` parameter. Because of this, library prototypes of cubic crystals that only have the `a` parameter do not have a suffix, i.e. the library prototype for the "Face-Centered Cubic" structure is ``A_cF4_225_a``.


.. _doc.appendices.symchanges:

Symmetry changes
----------------

It is possible for a crystal to increase its symmetry during the structural relaxation in the test. In this case, we do not write a property instance for that relaxation, Because the changed crystal structure is no longer in line with the property definition. It is also possible for rounding errors during test generation to cause a symmetry increase. We check for this during test generation and do not include those structures in test generation.

.. _doc.appendices.equivrep:

Equivalent representations
--------------------------
For many space groups, a non-unique choice of origin and axis orientation leads to non-unique Wyckoff labelings. The AFLOW symmetry detection routines explore these possibilities and choose the alphabetically lowest possible prototype label to ensure consistent labeling. For triclinic and monoclinic groups, exploring origin and orientation choices for a given set of lattice vectors is not sufficient, as there are an infinite number of symmetry-respecting unit cells due to the arbitrary angles in these types of crystals. While AFLOW attempts to standardize the choice of unit cell, rounding errors at any step of the classification, test generation, and relaxation process mean that occasional inconsistent prototype labels are unavoidable. These changes will be flagged as an error and will not write a property instance. However, the user may inspect the test output to check for whether the symmetry change is real or due to this unavoidable inconsistency.

Note that, even for space groups that are not monoclinic or triclinic, the AFLOW library prototype label may not be consistent with the detected label of the crystal. This is because the AFLOW prototype library is a curated database of prototypes which are labeled consistently with the traditional chemical formula of the material that the prototype represents.



.. |XtalFinder-paper| replace:: Hicks *et al.*, npj Comput. Mater. **7**, 30 (2021)
.. _XtalFinder-paper: https://www.nature.com/articles/s41524-020-00483-4