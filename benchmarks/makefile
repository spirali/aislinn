AISLINN_ROOT=".."
MPICC=${AISLINN_ROOT}/bin/mpicc
MPICXX=${AISLINN_ROOT}/bin/mpicxx
CFLAGS=-O2 -g

all: heatflow workers testfile

clean:
	rm -r heatflow workers testfile
.PHONY=all clean

heatflow:
	${MPICXX} ${CFLAGS} ${AISLINN_ROOT}/tests/complex/heatflow/*.cpp -o heatflow

workers:
	${MPICC} ${CFLAGS} ${AISLINN_ROOT}/tests/complex/workers/*.c -o workers

testfile: genfile.py
	python genfile.py testfile
