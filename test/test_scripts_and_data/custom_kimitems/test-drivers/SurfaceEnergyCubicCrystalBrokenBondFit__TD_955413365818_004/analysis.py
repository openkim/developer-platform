# Python 2-3 compatible code issues
from __future__ import print_function


import pickle as pickle

import numpy as np
from numpy import sin, cos, pi
from scipy.optimize import leastsq
import scipy.optimize
from ase.lattice.cubic import FaceCenteredCubic
from ase import Atoms

# from enthought.mayavi.mlab import *
from scipy.special import sph_harm
import pylab

# this is to analyze the surface energies
# 12-11-2012: put in bcc terms also and fit them...
# 2019-06-14: commented out currently unused variables

def energyVsAngle(fileName, index0, poleaxis):
    """
    plots calculated surfaces choosing family of planes perpendicular to index0, and as function of angle to poleaxis
    """

    f = open(fileName, "r")

    for line in f.readlines()[3:]:
        index, e_unrelaxed, e_relaxed, cell_size = line.split("\t")
        print(cell_size)
        e_unrelaxed = float(e_unrelaxed)
        e_relaxed = float(e_relaxed)
        h = int(index.split(",")[0].strip("["))
        k = int(index.split(",")[1])
        l = int(index.split(",")[2].strip("]"))
        index = [h, k, l]
        if np.dot(index, index0) == 0:
            angle = (
                2.0
                ** np.arccos(
                    np.dot(poleaxis, [h, k, l])
                    / (np.sqrt((h ** 2 + k ** 2 + l ** 2) * np.dot(poleaxis, poleaxis)))
                )
                * 180
                / pi
            )
            pylab.plot(angle, e_unrelaxed, "r.")
            pylab.plot(angle, e_relaxed, "g.")

    fileNameHeader = fileName.split(".")[0] + "index_" + str(index0)

    pylab.savefig(fileNameHeader + "plot.png")

    pylab.show()


def negativeEnergySurface(fileName):
    """
    returns which surfaces are negative in energy as a list
    """
    surfaces = []

    f = open(fileName, "r")

    for line in f.readlines()[3:]:
        index, e_unrelaxed, e_relaxed, cell_size = line.split()
        e_unrelaxed = float(e_unrelaxed)
        e_relaxed = float(e_relaxed)
        h = int(index.split(",")[0].strip("["))
        k = int(index.split(",")[1])
        l = int(index.split(",")[2].strip("]"))
        index = [h, k, l]

        if e_unrelaxed > 0 and e_relaxed > 0:
            surfaces.append(index)

    f.close()

    return surfaces


def angles(h, k, l):

    if h != 0:
        phi = pylab.arctan2(k, h) * 180 / pi
    elif k < 0:
        phi = -90
    elif k > 0:
        phi = 90
    elif k == 0:
        phi = 0

    theta = np.arccos(l / np.sqrt(h ** 2 + k ** 2 + l ** 2)) * 180 / pi

    return phi, theta


def radianangles(h, k, l):
    phidegrees, thetadegrees = angles(h, k, l)

    return phidegrees / 180.0 * pi, thetadegrees / 180.0 * pi


def thetaphis(nvector):

    phi_list = []
    theta_list = []

    if isinstance(nvector, list):
        shaperows = 1
        if isinstance(nvector[0], list):  # in case this is a nested list
            shaperows = len(nvector)
    elif isinstance(nvector, np.ndarray):
        shaperows = nvector.shape[0]

    if shaperows == 1:
        [h, k, l] = nvector
        phi, theta = angles(h, k, l)
        return phi, theta
    elif shaperows > 1:
        for row in range(0, shaperows):
            [h, k, l] = nvector[row]
            phi, theta = angles(h, k, l)
            phi_list.append(phi)
            theta_list.append(theta)

        return phi_list, theta_list


def listofangles(file, index0, poleaxis):

    f = open(file, "r")
    newfile = file.split(".")[0] + str(index0) + "angles.txt"
    g = open(newfile, "w")

    h = poleaxis[0]
    k = poleaxis[1]
    l = poleaxis[2]

    print(poleaxis)

    # phi0, theta0 = angles(h,k,l)

    for line in f.readlines()[3:]:
        index, e_unrelaxed, e_relaxed, cell_size = line.split()
        h = int(index.split(",")[0].strip("["))
        k = int(index.split(",")[1])
        l = int(index.split(",")[2].strip("]"))

        if np.dot([h, k, l], index0) == 0:
            # phi, theta = angles(h,k,l)
            # phi0,theta0 = angles(,1,0)

            # angle = np.arccos(sin(theta)*sin(theta0)*cos(phi-phi0)+cos(theta)*cos(theta0))*180/pi
            angle = (
                np.arccos(
                    np.dot(poleaxis, [h, k, l])
                    / (np.sqrt((h ** 2 + k ** 2 + l ** 2) * np.dot(poleaxis, poleaxis)))
                )
                * 180
                / pi
            )

            g.write(str(index) + "\t" + str(angle) + "\n")

    f.close()
    g.close()


def loadFileIntoLists(fileName):

    f = open(fileName, "r")

    indices = []
    unrel_es = []
    rel_es = []
    sizes = []

    for line in f.readlines()[2:]:
        index, e_unrelaxed, e_relaxed, cell_size = line.split("\t")
        e_unrelaxed = float(e_unrelaxed)
        e_relaxed = float(e_relaxed)
        h = int(index.split(",")[0].strip("["))
        k = int(index.split(",")[1])
        l = int(index.split(",")[2].strip("]"))
        indices.append([h, k, l])
        unrel_es.append(e_unrelaxed)
        rel_es.append(e_relaxed)
        x = int(cell_size.split(",")[0].strip("("))
        y = int(cell_size.split(",")[1])
        z = int(cell_size.split(",")[2].strip(")\n"))
        sizes.append((x, y, z))

    return indices, unrel_es, rel_es, sizes


def normalizedVector(nvector):
    if isinstance(nvector, np.ndarray):
        # normalize nvector
        x = nvector[:, 0] / np.sqrt(np.sum(nvector ** 2, axis=1))
        y = nvector[:, 1] / np.sqrt(np.sum(nvector ** 2, axis=1))
        z = nvector[:, 2] / np.sqrt(np.sum(nvector ** 2, axis=1))
    elif isinstance(nvector, list):
        if len(nvector) == 3:
            x = nvector[0]
            y = nvector[1]
            z = nvector[2]
            x = x / np.sqrt(x ** 2 + y ** 2 + z ** 2)
            y = y / np.sqrt(x ** 2 + y ** 2 + z ** 2)
            z = z / np.sqrt(x ** 2 + y ** 2 + z ** 2)
        else:
            print("index too long")
    else:
        print("index not list or np array, please change")

    return x, y, z


def term110(nvector, p):
    """
    this is function for the 110 neighbor term in the broken-bond model
    for a given parameter vector and for a given direction
    """
    x, y, z = normalizedVector(nvector)
    return (
        p
        * 4
        * (abs(x + y) + abs(x - y) + abs(x + z) + abs(x - z) + abs(z + y) + abs(z - y))
    )


def term100(nvector, p):
    x, y, z = normalizedVector(nvector)
    return p * 8 * (abs(x) + abs(y) + abs(z))


def term112(nvector, p):
    x, y, z = normalizedVector(nvector)
    return p * (
        abs(x + 2 * y + z)
        + abs(x + 2 * y - z)
        + abs(x - 2 * y + z)
        + abs(x - 2 * y - z)
        + abs(2 * x + y + z)
        + abs(2 * x + y - z)
        + abs(2 * x - y + z)
        + abs(2 * x - y - z)
        + abs(x + y + 2 * z)
        + abs(x + y - 2 * z)
        + abs(x - y + 2 * z)
        + abs(x - y - 2 * z)
    )


def term111(nvector, p):
    x, y, z = normalizedVector(nvector)
    return p * 6 * (abs(x + y + z) + abs(x - y - z) + abs(x - y + z) + abs(x + y - z))


def term130(nvector, p):
    x, y, z = normalizedVector(nvector)
    return (
        p
        * 2
        * (
            abs(x + 3 * y)
            + abs(x - 3 * y)
            + abs(y + 3 * z)
            + abs(y - 3 * z)
            + abs(3 * x + y)
            + abs(3 * x - y)
            + abs(3 * x + z)
            + abs(3 * x - z)
            + abs(3 * y + z)
            + abs(3 * y - z)
            + abs(x + 3 * z)
            + abs(x - 3 * z)
        )
    )


def term113(nvector, p):
    x, y, z = normalizedVector(nvector)
    return (
        2
        * p
        * (
            abs(x + 3 * y + z)
            + abs(x + 3 * y - z)
            + abs(x - 3 * y + z)
            + abs(x - 3 * y - z)
            + abs(3 * x + y + z)
            + abs(3 * x - y + z)
            + abs(3 * x + y - z)
            + abs(3 * x - y - z)
            + abs(x + y + 3 * z)
            + abs(x - y + 3 * z)
            + abs(x + y - 3 * z)
            + abs(x - y - 3 * z)
        )
    )


def fitFunction(nvector, p, correction, structure):
    """
    this returns the fit function for either an fcc or bcc structure
    """
    if correction:
        if len(p) == 1 + correction:
            if structure == "fcc":
                return term110(nvector, p[0]) + corrections(nvector, p[1:])
            elif structure == "bcc":
                return term111(nvector, p[0]) + corrections(nvector, p[1:])
        elif len(p) == 2 + correction:
            if structure == "fcc":
                return (
                    term110(nvector, p[0])
                    + term100(nvector, p[1])
                    + corrections(nvector, p[2:])
                )
            elif structure == "bcc":
                return (
                    term111(nvector, p[0])
                    + term100(nvector, p[1])
                    + corrections(nvector, p[2:])
                )
        elif len(p) == 3 + correction:
            if structure == "fcc":
                return (
                    term110(nvector, p[0])
                    + term100(nvector, p[1])
                    + term112(nvector, p[2])
                    + corrections(nvector, p[3:])
                )
            elif structure == "bcc":
                return (
                    term111(nvector, p[0])
                    + term100(nvector, p[1])
                    + term110(nvector, p[2])
                    + corrections(nvector, p[3:])
                )
        elif len(p) == 4 + correction:
            if structure == "fcc":
                return (
                    term110(nvector, p[0])
                    + term100(nvector, p[1])
                    + term112(nvector, p[2])
                    + term130(nvector, p[3])
                    + corrections(nvector, p[4:])
                )
            elif structure == "bcc":
                return (
                    term111(nvector, p[0])
                    + term100(nvector, p[1])
                    + term110(nvector, p[2])
                    + term113(nvector, p[3])
                    + corrections(nvector, p[4:])
                )
        else:
            print("wrong number of parameters specified for fit")
            raise Exception
    else:
        if len(p) == 1:
            if structure == "fcc":
                return term110(nvector, p[0])
            elif structure == "bcc":
                return term111(nvector, p[0])
        elif len(p) == 2:
            if structure == "fcc":
                return term110(nvector, p[0]) + term100(nvector, p[1])
            elif structure == "bcc":
                return term111(nvector, p[0]) + term100(nvector, p[1])
        elif len(p) == 3:
            if structure == "fcc":
                return (
                    term110(nvector, p[0])
                    + term100(nvector, p[1])
                    + term112(nvector, p[2])
                )
            elif structure == "bcc":
                return (
                    term111(nvector, p[0])
                    + term100(nvector, p[1])
                    + term110(nvector, p[2])
                )
        elif len(p) == 4:
            if structure == "fcc":
                return (
                    term110(nvector, p[0])
                    + term100(nvector, p[1])
                    + term112(nvector, p[2])
                    + term130(nvector, p[3])
                )
            elif structure == "bcc":
                return (
                    term111(nvector, p[0])
                    + term100(nvector, p[1])
                    + term110(nvector, p[2])
                    + term113(nvector, p[3])
                )
        else:
            print("wrong number of parameters specified for fit")
            raise Exception


def corrections(nvector, c):
    """
    #return c*term(nvector,0,1.)**3. # step-step interaction
    #return c[0]*term(nvector,0,1.)**3. + c[1]*term(nvector,1,1.)**3. + c[2]*term(nvector,2,1.)**3.
    #return c[0]*term(nvector,0,1.)**3. + c[1]*term(nvector,1,1.)**3.
    #return c[0]*term(nvector,0,1.)**2 + c[1]*term(nvector,1,1.)**2 +c[2]*term(nvector,0,1.)*term(nvector,2,1.) + c[3]*term(nvector,0,1.)*term(nvector,1,1.) + c[4]*term(nvector,0,1.)*term(nvector,2,1.)+c[5]*term(nvector,1,1.)*term(nvector,2,1.) # mixed-step interactions
    #phi, theta = thetaphis(nvector) # spherical harmonics
    """
    if isinstance(nvector, list) and len(nvector) == 3:
        v = np.array(nvector)
        x = nvector[0] / np.sqrt(np.dot(v, v))
        y = nvector[1] / np.sqrt(np.dot(v, v))
        z = nvector[2] / np.sqrt(np.dot(v, v))
    else:
        nvector_array = np.array(nvector)
        nvectornorms = [np.sqrt(np.dot(v, v)) for v in nvector_array]
        x = nvector_array[:, 0] / nvectornorms
        y = nvector_array[:, 1] / nvectornorms
        z = nvector_array[:, 2] / nvectornorms

    if len(c) == 1:
        return c[0]
    elif len(c) == 3:
        return (
            c[0]
            + c[1] * (x ** 4.0 + y ** 4.0 + z ** 4.0)
            + c[2] * (x ** 2.0 * y ** 2.0 + y ** 2.0 * z ** 2.0 + x ** 2.0 * z ** 2.0)
        )
    elif len(c) == 4:
        # this return is to mimic the step-step interaction for fcc surfaces
        return (
            c[0]
            + c[1] * term110(nvector, 1.0) ** 3.0
            + c[2] * term100(nvector, 1.0) ** 3.0
            + c[3] * term112(nvector, 1.0) ** 3.0
        )
    else:
        print("wrong number of corrections specified")
        raise Exception
    # return abs(c[0]*sph_harm(0,0,theta,phi)+c[1]*sph_harm(-4,4,theta,phi)+c[2]*sph_harm(0,4,theta,phi)+c[3]*sph_harm(4,4,theta,phi))


def fitEnergiesFromFile(
    fileName,
    structure="fcc",
    n=2,
    p0=[0.1, -0.2, 0.01],
    correction=0,
    fit_unrelaxed=True,
):

    indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

    indices = np.array(indices)

    bfparams, cov_x, cost, error_range, max_error = fitSurfaceEnergies(
        indices, e_relaxed, structure, n=n, p0=p0, correction=correction
    )

    plotSubSet(
        indices,
        e_relaxed,
        [1, -1, 0],
        [1, 1, 0],
        bfparams,
        structure=structure,
        correction=correction,
    )
    plotSubSet(
        indices,
        e_relaxed,
        [1, -1, 2],
        [1, 1, 0],
        bfparams,
        structure=structure,
        correction=correction,
    )
    plotSubSet(
        indices,
        e_relaxed,
        [1, 1, -1],
        [0, 1, 1],
        bfparams,
        structure=structure,
        correction=correction,
    )

    output_rel = (bfparams, cov_x, cost, error_range, max_error)

    if fit_unrelaxed:
        bfparams, cov_x, cost, error_range, max_error = fitSurfaceEnergies(
            indices, e_unrelaxed, structure=structure, n=n, p0=p0, correction=correction
        )
        plotSubSet(
            indices,
            e_unrelaxed,
            [1, -1, 0],
            [1, 1, 0],
            bfparams,
            structure=structure,
            correction=correction,
        )
        plotSubSet(
            indices,
            e_unrelaxed,
            [1, -1, 2],
            [1, 1, 0],
            bfparams,
            structure=structure,
            correction=correction,
        )
        plotSubSet(
            indices,
            e_unrelaxed,
            [1, 1, -1],
            [0, 1, 1],
            bfparams,
            structure=structure,
            correction=correction,
        )
        output_unrel = (bfparams, cov_x, cost, error_range, max_error)
        return output_rel, output_unrel
    else:
        return output_rel


def fitSurfaceEnergies(
    indices, energies, structure, n=2, p0=[0.1, -0.2, 0.01], correction=0
):
    """
    this is to do a fit of all the indices in the file
    n is to set up to which neighbor...
    """
    bfparams, cov_x, output, mesg, ier = leastsq(
        residual,
        p0[0 : n + correction],
        args=(indices, energies, correction, structure),
        full_output=True,
    )
    cost = np.sum(
        abs(residual(bfparams, indices, energies, correction, structure) / energies)
    ) / len(indices)
    min_e = np.min(energies)
    max_e = np.max(energies)
    error_range = np.sum(
        abs(
            residual(bfparams, indices, energies, correction, structure)
            / (max_e - min_e)
        )
    ) / len(indices)

    max_error = max(
        abs(residual(bfparams, indices, energies, correction, structure) / energies)
    )

    return bfparams, cov_x, cost, error_range, max_error


def setPlotOptions(
    labelsize=20,
    tickmajor=20,
    tickminor=10,
    markersize=10,
    legendsize=20,
    legendspacing=1.5,
    labelsizexy=16,
):
    """
    set plot label size, tick size, line size, markersize
    """

    pylab.rcdefaults()
    pylab.rcParams.update(
        {
            "xtick.labelsize": labelsizexy,
            "xtick.major.size": tickmajor,
            "xtick.minor.size": tickminor,
            "ytick.labelsize": labelsizexy,
            "ytick.major.size": tickmajor,
            "ytick.minor.size": tickminor,
            "lines.markersize": markersize,
            "axes.labelsize": labelsize,
            "legend.fontsize": legendsize,
            "legend.columnspacing": legendspacing,
        }
    )


def plotSubSet(
    indices, energies, index0, poleaxis, params, structure="fcc", correction=0
):
    """
    make plot of a crystallographic zone index0
    """

    # with open("IndexList.pkl", 'r') as f:
    #    biglist = pickle.load(f)

    selected_fit_indices = []
    angles = []
    angles_dict = {}
    selected_energies = []
    selected_indices = []
    other_dict = {}

    for i in range(0, len(indices)):
        index = indices[i]
        index = list(index)
        [h, k, l] = index
        selected_indices.append(index)
        n_vector = np.array([h, k, l]) / np.sqrt(h ** 2 + k ** 2 + l ** 2)
        energy = energies[i]
        if np.abs(np.dot(index, index0)) < 1e-13:
            cos = np.dot(poleaxis, [h, k, l]) / (
                np.sqrt((h ** 2 + k ** 2 + l ** 2) * np.dot(poleaxis, poleaxis))
            )
            sin = np.linalg.norm(np.cross(poleaxis, [h, k, l])) / (
                np.sqrt((h ** 2 + k ** 2 + l ** 2) * np.dot(poleaxis, poleaxis))
            )
            angle = np.arctan2(sin, cos) * 180.0 / pi

            # print np.dot(index0, np.cross(poleaxis, n_vector) / np.sqrt(np.dot(poleaxis, poleaxis)))
            selected_fit_indices.append(list(n_vector))
            angles.append(angle)
            angles_dict[angle] = list(n_vector)
            selected_energies.append(energy)
            if energy > 0.0581:  # temp for sorting out which energy to calculate
                other_dict[str([h, k, l])] = (angle, energy)

    # sort the fit_indices by angle, so that we can connect lines
    angles = sorted(angles_dict.keys())
    sorted_e = []
    fit_e = []
    residuals = []
    # corrs = []
    for angle in angles:
        n_vector = angles_dict[angle]
        listindex = selected_fit_indices.index(n_vector)
        sorted_e.append(selected_energies[listindex])
        fit_e.append(fitFunction(n_vector, params, correction, structure))
        residuals.append(
            residual(
                params, n_vector, selected_energies[listindex], correction, structure
            )
        )
        residuals.append(
            residual(
                params, n_vector, selected_energies[listindex], correction, structure
            )
        )
        # corrs.append(corrections(n_vector,params[3:]))

    fit_angles = []
    fit_energies = []
    for i in range(len(angles) - 1):
        n0 = np.array(angles_dict[angles[i]])
        n1 = np.array(angles_dict[angles[i + 1]])

        ns = [n0 + (n1 - n0) * j for j in np.linspace(0.0, 1.0, 500)]
        cos = [
            np.dot(poleaxis, nvec)
            / (np.sqrt(np.dot(nvec, nvec) * np.dot(poleaxis, poleaxis)))
            for nvec in ns
        ]
        sin = [
            np.linalg.norm(np.cross(poleaxis, nvec))
            / (np.sqrt(np.dot(nvec, nvec) * np.dot(poleaxis, poleaxis)))
            for nvec in ns
        ]
        nangle = [180.0 / pi * np.arctan2(s, c) for s, c in zip(sin, cos)]

        fit_angles.extend([tn for tn in nangle])
        fit_energies.extend(
            [
                fitFunction(list(nvec), params, correction, structure)
                for j, nvec in enumerate(ns)
            ]
        )

    pylab.figure()
    pylab.plot(angles, sorted_e, "bo", label="data")
    pylab.plot(fit_angles, fit_energies, "r-", label="fit")
    pylab.xlabel("angle from " + str(poleaxis))
    pylab.ylabel(r"$eV/\AA^2$")
    pylab.title("surfaces perpendicular to " + str(index0), fontsize=20)
    pylab.legend(loc=0)
    # pylab.figure()
    # pylab.plot(angles,residuals)
    # pylab.figure()
    # pylab.plot(angles,corrs)

    # pylab.show()

    # return selected_indices
    return other_dict


def fitSubset(
    fileName, index0, poleaxis, structure="fcc", n=2, p0=[0.1, -0.2, 0.01], correction=0
):
    """
    to fit a subset of
    surfaces perpendicular to index0
    """

    indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

    indices = np.array(indices)
    # errfunc = lambda p,x,y:(fitFunction(x,p)-y)

    selected_fit_indices = []
    angles = []
    angles_dict = {}
    selected_e_unrel = []
    selected_e_rel = []

    for i in range(0, len(indices)):
        index = indices[i, :]
        index = list(index)
        [h, k, l] = index
        n_vector = np.array([h, k, l]) / np.sqrt(h ** 2 + k ** 2 + l ** 2)
        e_unrel = e_unrelaxed[i]
        e_rel = e_relaxed[i]
        if np.dot(index, index0) == 0:
            angle = (
                2.0
                ** np.arccos(
                    np.dot(poleaxis, [h, k, l])
                    / (np.sqrt((h ** 2 + k ** 2 + l ** 2) * np.dot(poleaxis, poleaxis)))
                )
                * 180
                / pi
            )
            selected_fit_indices.append(n_vector)
            angles.append(angle)
            angles_dict[angle] = n_vector
            selected_e_unrel.append(e_unrel)
            selected_e_rel.append(e_rel)
    # somehow sort the fit_indices by angle
    selected_fit_indices = np.array(selected_fit_indices)

    # output = leastsq(
    #    residual,
    #    p0[0 : n + correction],
    #    args=(selected_fit_indices, selected_e_unrel, correction, structure),
    #    full_output=True,
    # )
    output2 = leastsq(
        residual,
        p0[0 : n + correction],
        args=(selected_fit_indices, selected_e_rel, correction, structure),
        full_output=True,
    )

    # bfparams = output[0]
    bfparamsrel = output2[0]

    # cost = np.sum(
    #    abs(
    #        residual(
    #            bfparamsrel, selected_fit_indices, selected_e_rel, correction, structure
    #        )
    #    )
    #    / selected_e_rel
    # ) / len(selected_fit_indices)
    # min_e = np.min(selected_e_rel)
    # max_e = np.max(selected_e_rel)
    # perc_range = np.sum(
    #    abs(
    #        residual(
    #            bfparamsrel, selected_fit_indices, selected_e_rel, correction, structure
    #        )
    #        / (max_e - min_e)
    #    )
    # ) / len(selected_fit_indices)

    pylab.figure()
    # pylab.plot(angles,selected_e_unrel,'bo')
    # pylab.plot(angles,fitFunction(selected_fit_indices,bfparams,correction,structure),'r+')
    pylab.plot(angles, selected_e_rel, "k+")
    pylab.plot(
        angles,
        fitFunction(selected_fit_indices, bfparamsrel, correction, structure),
        "g^",
    )
    pylab.figure()
    # pylab.plot(angles,residual(bfparams,selected_fit_indices,selected_e_unrel,correction,structure)/selected_e_unrel,'r^')
    pylab.plot(
        angles,
        residual(
            bfparamsrel, selected_fit_indices, selected_e_rel, correction, structure
        )
        / selected_e_rel,
        "k^",
    )

    # return bfparams, bfparamsrel
    return bfparamsrel, angles, selected_fit_indices
    # return bfparamsrel, cost, perc_range


def residualFuncAngle(
    fileName, bfparams, index0, poleaxis, structure="fcc", correction=0
):

    indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

    indices = np.array(indices)

    selected_fit_indices = []
    angle_from_min = []
    angle_from_poleaxis = []
    selected_e_unrel = []
    selected_e_rel = []

    # first select list of indices along crystallographic zone
    for i in range(0, len(indices)):
        index = indices[i, :]
        index = list(index)
        e_unrel = e_unrelaxed[i]
        e_rel = e_relaxed[i]
        if np.dot(index, index0) == 0:
            selected_fit_indices.append(index)
            selected_e_unrel.append(e_unrel)
            selected_e_rel.append(e_rel)

    min_energy = min(selected_e_rel)
    min_index = selected_fit_indices[selected_e_rel.index(min_energy)]

    for index in selected_fit_indices:
        angle = (
            np.arccos(
                np.dot(index, min_index)
                / (np.sqrt(np.dot(index, index) * np.dot(min_index, min_index)))
            )
            * 180
            / pi
        )
        angle_from_min.append(angle)
        angle2 = (
            np.arccos(
                np.dot(index, poleaxis)
                / (np.sqrt(np.dot(index, index) * np.dot(poleaxis, poleaxis)))
            )
            * 180
            / pi
        )
        angle_from_poleaxis.append(angle2)

    selected_fit_indices = np.array(selected_fit_indices)
    selected_e_rel = np.array(selected_e_rel)

    pylab.figure()
    pylab.plot(
        angle_from_min,
        residual(bfparams, selected_fit_indices, selected_e_rel, correction, structure),
        "bo",
    )
    pylab.figure()
    pylab.plot(
        np.tan(np.array(angle_from_min) / 180.0 * pi),
        residual(bfparams, selected_fit_indices, selected_e_rel, correction, structure),
        "ro",
    )
    pylab.figure()
    pylab.plot(angle_from_poleaxis, selected_e_rel, "bo")

    pylab.show()

    return angle_from_min, selected_fit_indices, angle_from_poleaxis


def make2DGammaPlot(
    params, n=2, index0=[1, -1, 0], poleaxis=[1, 1, 0], number_of_points=50
):
    """
    this is to make the gamma plot cross section using the fitted broken bond
    model
    """

    thetas = np.linspace(0, 2 * pi, number_of_points)
    # angles = []
    # energies = []
    phis = []

    for theta in thetas:
        phi = scipy.optimize.fsolve(dotProduct, 0.8, args=(theta, index0))[0]
        phis.append(phi)
        # print theta, phi
        nvector = [sin(theta) * cos(phi), sin(theta) * sin(phi), cos(theta)]
        [h, k, l] = nvector
        energy = fitFunction(nvector, params)
        # energies.append(energy)
        angle = np.arccos(
            np.dot(poleaxis, [h, k, l])
            / (np.sqrt((h ** 2 + k ** 2 + l ** 2) * np.dot(poleaxis, poleaxis)))
        )
        if np.dot(np.cross([h, k, l], poleaxis), index0) < 0:
            angle = -1.0 * angle
        # angles.append(angle)
        # print angle
        # plot with poleaxis pointing in +y direction
        exp_r = abs(
            0.2200912656713 * sph_harm(0, 0, theta, phi)
            + 0.0032670284794418564 * sph_harm(0, 4, theta, phi)
            + 0.00195264 * (sph_harm(-4, 4, theta, phi) + sph_harm(4, 4, theta, phi))
            - 0.0023674865858444084 * sph_harm(0, 6, theta, phi)
            + 0.00442926 * (sph_harm(4, 6, theta, phi) + sph_harm(-4, 6, theta, phi))
            - 0.00211574 * sph_harm(0, 8, theta, phi)
            - 0.000795321 * (sph_harm(-4, 8, theta, phi) + sph_harm(4, 8, theta, phi))
            - 0.0012122 * (sph_harm(-8, 8, theta, phi) + sph_harm(8, 8, theta, phi))
        )
        pylab.plot(energy * sin(angle), energy * cos(angle), "r.")
        pylab.plot(exp_r * sin(angle), exp_r * cos(angle), "b.")


def dotProduct(phi, theta, nvector):
    return (
        nvector[0] * sin(theta) * cos(phi)
        + nvector[1] * sin(theta) * sin(phi)
        + nvector[2] * cos(theta)
    )


def residual(p, x, y, c, structure):
    return fitFunction(x, p, c, structure) - y


def equilShape(
    element, params, size=(10, 10, 10), distance=25.0, corrections=0, structure="fcc"
):
    """
    this is to use the ratio of energies to calculate the equilibrium crystal shape, cycle through a bunch of (h,k,l) indices
    """
    slab = FaceCenteredCubic(
        element, directions=([[1, 0, 0], [0, 1, 0], [0, 0, 1]]), size=(10, 10, 10)
    )
    energy100 = fitFunction([1, 0, 0], params, corrections, structure)
    h100 = distance
    orig_positions = slab.get_positions()
    kept_positions = list(orig_positions)
    # center = slab.get_center_of_mass()
    for h in range(-12, 12):
        for k in range(0, 9):
            for l in range(0, 9):
                nvector = list([h, k, l] / np.sqrt(h ** 2 + k ** 2 + l ** 2))
                energyhkl = fitFunction(nvector, params, corrections, structure)
                distancehkl = energyhkl / energy100 * h100
                for i in range(0, len(kept_positions)):
                    list_to_pop = []
                    if np.dot(kept_positions[i], nvector) > distancehkl:
                        list_to_pop.append(i)
                for i in list_to_pop:
                    kept_positions.pop(i)

    # set up new slab with new positions
    number_of_atoms = len(kept_positions)
    elstring = element + str(number_of_atoms)
    new_slab = Atoms(elstring, positions=kept_positions)

    return new_slab


def make3Dplot(
    indices, energies, params, sig_am=1 / 1000.0, corrections=0, structure="fcc"
):
    """
    make a 3D plot of theoretical energies, and residuals saying how good the fit is
    """

    dphi, dtheta = pi / 250.0, pi / 250.0
    [phi, theta] = np.mgrid[
        0 : pi + dphi * 1.5 : dphi, 0 : 2 * pi + dtheta * 1.5 : dtheta
    ]

    plottingindices = [cos(phi) * sin(theta), sin(phi) * sin(theta), cos(theta)]
    r = fitFunction(plottingindices, params, corrections, structure)
    x = r * cos(phi) * sin(theta)
    y = r * sin(phi) * sin(theta)
    z = r * cos(theta)

    # sph = mesh(x, y, z, color=(0.8,0.8,0.8), opacity=0.5)
    sph = mesh(x, y, z)

    xs = []
    ys = []
    zs = []
    res = []

    for i in range(0, len(indices)):
        [h, k, l] = indices[i]
        thein, phiin = radianangles(h, k, l)
        energ = energies[i]
        xs.append(energ * cos(phiin) * sin(thein))
        ys.append(energ * sin(phiin) * sin(thein))
        zs.append(energ * cos(thein))
        res.append(
            abs(energ - fitFunction([h, k, l], params, corrections, structure))
            / energ
            * sig_am
        )

    print(xs, ys, zs, res)

    # pts = points3d(xs, ys, zs, res)

    filestring = "SphereplotTest.obj"
    savefig(filestring)

    show()

    return sph


def make_movie(indices, energies, params):
    """
    this is to make a movie
    """
    # sph = make3Dplot(indices, energies, params)
    s = gcf()

    # Make an animation:
    for i in range(72, 144):
        # Rotate the camera by 10 degrees.
        s.scene.camera.azimuth(5)
        # Resets the camera clipping plane so everything fits and then
        # renders.
        s.scene.reset_zoom()
        # Save the scene.
        s.scene.save_png("animation/anim" + str(i).rjust(3, "0") + ".png")
        print(i)
