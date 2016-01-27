#
#    Copyright (C) 2014 Stanislav Bohm
#
#    This file is part of Aislinn.
#
#    Aislinn is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License, or
#    (at your option) any later version.
#
#    Aislinn is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Aislinn.  If not, see <http://www.gnu.org/licenses/>.
#


def factors(count, dims):
    """ This is naive implementation of algorithm that is needed
        for MPI_Dim_create """
    if dims == 1:
        return [count]

    p = primes(count)

    factors = [1] * dims

    if not p:
        return factors

    for prime in reversed(p):
        mv = factors[0]
        mi = 0
        for i in xrange(1, dims):
            if factors[i] < mv:
                mv = factors[i]
                mi = i
        factors[mi] *= prime

    factors.sort(reverse=True)
    return factors


def primes(n):
    p = []
    d = 2
    while d * d <= n:
        while (n % d) == 0:
            p.append(d)
            n /= d
        d += 1
    if n > 1:
        p.append(n)
    return p
