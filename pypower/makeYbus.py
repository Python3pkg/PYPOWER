# Copyright (C) 1996-2011 Power System Engineering Research Center
# Copyright (C) 2010-2011 Richard Lincoln
#
# PYPOWER is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# PYPOWER is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PYPOWER. If not, see <http://www.gnu.org/licenses/>.

"""Builds the bus admittance matrix and branch admittance matrices.
"""

from sys import stderr

from numpy import ones, conj, nonzero, any, exp, pi, r_
from scipy.sparse import csr_matrix

from idx_bus import BUS_I, GS, BS
from idx_brch import F_BUS, T_BUS, BR_R, BR_X, BR_B, BR_STATUS, SHIFT, TAP


def makeYbus(baseMVA, bus, branch):
    """Builds the bus admittance matrix and branch admittance matrices.

    Returns the full bus admittance matrix (i.e. for all buses) and the
    matrices C{Yf} and C{Yt} which, when multiplied by a complex voltage
    vector, yield the vector currents injected into each line from the
    "from" and "to" buses respectively of each line. Does appropriate
    conversions to p.u.

    @see: L{makeSbus}
    """
    ## constants
    nb = bus.shape[0]          ## number of buses
    nl = branch.shape[0]       ## number of lines

    ## check that bus numbers are equal to indices to bus (one set of bus nums)
    if any(bus[:, BUS_I] != range(nb)):
        stderr.write('buses must appear in order by bus number\n')

    ## for each branch, compute the elements of the branch admittance matrix where
    ##
    ##      | If |   | Yff  Yft |   | Vf |
    ##      |    | = |          | * |    |
    ##      | It |   | Ytf  Ytt |   | Vt |
    ##
    stat = branch[:, BR_STATUS]              ## ones at in-service branches
    Ys = stat / (branch[:, BR_R] + 1j * branch[:, BR_X])  ## series admittance
    Bc = stat * branch[:, BR_B]              ## line charging susceptance
    tap = ones(nl)                           ## default tap ratio = 1
    i = nonzero(branch[:, TAP])              ## indices of non-zero tap ratios
    tap[i] = branch[i, TAP]                  ## assign non-zero tap ratios
    tap = tap * exp(1j * pi / 180 * branch[:, SHIFT]) ## add phase shifters

    Ytt = Ys + 1j * Bc / 2
    Yff = Ytt / (tap * conj(tap))
    Yft = - Ys / conj(tap)
    Ytf = - Ys / tap

    ## compute shunt admittance
    ## if Psh is the real power consumed by the shunt at V = 1.0 p.u.
    ## and Qsh is the reactive power injected by the shunt at V = 1.0 p.u.
    ## then Psh - j Qsh = V * conj(Ysh * V) = conj(Ysh) = Gs - j Bs,
    ## i.e. Ysh = Psh + j Qsh, so ...
    ## vector of shunt admittances
    Ysh = (bus[:, GS] + 1j * bus[:, BS]) / baseMVA

    ## build connection matrices
    f = branch[:, F_BUS]                           ## list of "from" buses
    t = branch[:, T_BUS]                           ## list of "to" buses
    ## connection matrix for line & from buses
    Cf = csr_matrix((ones(nl), (range(nl), f)), (nl, nb))
    ## connection matrix for line & to buses
    Ct = csr_matrix((ones(nl), (range(nl), t)), (nl, nb))

    ## build Yf and Yt such that Yf * V is the vector of complex branch currents injected
    ## at each branch's "from" bus, and Yt is the same for the "to" bus end
    i = r_[range(nl), range(nl)]                   ## double set of row indices

    Yf = csr_matrix((r_[Yff, Yft], (i, r_[f, t])), (nl, nb))
    Yt = csr_matrix((r_[Ytf, Ytt], (i, r_[f, t])), (nl, nb))
    # Yf = spdiags(Yff, 0, nl, nl) * Cf + spdiags(Yft, 0, nl, nl) * Ct
    # Yt = spdiags(Ytf, 0, nl, nl) * Cf + spdiags(Ytt, 0, nl, nl) * Ct

    ## build Ybus
    Ybus = Cf.T * Yf + Ct.T * Yt + \
        csr_matrix((Ysh, (range(nb), range(nb))), (nb, nb))

    return Ybus, Yf, Yt