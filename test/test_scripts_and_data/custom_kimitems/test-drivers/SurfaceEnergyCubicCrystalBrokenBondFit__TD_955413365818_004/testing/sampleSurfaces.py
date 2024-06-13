import numpy
from analysisNEW import *
import pylab

#
# this code is to see what are the minimum number of surfaces needed
# to get a reasonable broken bond parameter fit
#


def fitSampleSurfaces(fileName, sampleSize, p0):

    indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

    e_relaxed_sorted = sorted(e_relaxed)

    N_interval = len(e_relaxed) / sampleSize
    sample_indices = []
    sample_energies = []

    for i in range(0, sampleSize):
        e_rel = e_relaxed_sorted[i * N_interval]
        sample_energies.append(e_rel)
        loc = e_relaxed.index(e_rel)
        sample_indices.append(indices[loc])

    sample_indices = numpy.array(sample_indices)
    sample_energies = numpy.array(sample_energies)

    bfparams, flag = leastsq(residual, p0, args=(sample_indices, sample_energies))

    return bfparams, sample_indices


def plotParamsVsSample(fileName, p0, bfstandard):

    indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

    N_max = len(e_relaxed) - 1

    sizelist = numpy.arange(5, N_max, 10)

    percent_diff_p0 = []
    percent_diff_p1 = []

    for size in sizelist:
        bfparams, sample_indices = fitSampleSurfaces(fileName, size, p0)
        err_p0 = abs(bfparams[0] - bfstandard[0]) / bfstandard[0]
        err_p1 = abs((bfparams[1] - bfstandard[1]) / bfstandard[1])
        percent_diff_p0.append(err_p0)
        percent_diff_p1.append(err_p1)

    pylab.plot(sizelist, percent_diff_p0, "r.")
    pylab.plot(sizelist, percent_diff_p1, "b.")

    pylab.show()


def fitListSurfaces(fileName, sample_indices, p0, corrections=0):

    indices, e_unrelaxed, e_relaxed, sizes = loadFileIntoLists(fileName)

    sample_energies = []

    for ind in sample_indices:
        curr_index = indices.index(ind)
        sample_energies.append(e_relaxed[curr_index])

    bfparams, flag = leastsq(
        residual, p0, args=(numpy.array(sample_indices), sample_energies, corrections)
    )

    return bfparams
