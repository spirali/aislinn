#include <stdio.h>
#include <aislinn.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>

int main(int argc, char **argv)
{
	int rank;
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	int d, d2;
	if (rank == 1) {
		MPI_Status s;
		MPI_Request r;
		MPI_Irecv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &r);
		MPI_Probe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
		printf("%i\n", s.MPI_TAG);
		MPI_Recv(&d2, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
		printf("%i\n", s.MPI_TAG);
		MPI_Wait(&r, &s);
		printf("%i\n", s.MPI_TAG);

		// Once again but not for deterministic probe
		MPI_Irecv(&d, 1, MPI_INT, 0, MPI_ANY_TAG, MPI_COMM_WORLD, &r);
		MPI_Probe(0, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
		printf("%i\n", s.MPI_TAG);
		MPI_Recv(&d2, 1, MPI_INT, 0, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
		printf("%i\n", s.MPI_TAG);
		MPI_Wait(&r, &s);
		printf("%i\n", s.MPI_TAG);

	} else {
		MPI_Bsend(&d, 1, MPI_INT, 1, 11, MPI_COMM_WORLD);
		MPI_Bsend(&d, 1, MPI_INT, 1, 12, MPI_COMM_WORLD);
		MPI_Bsend(&d, 1, MPI_INT, 1, 13, MPI_COMM_WORLD);
		MPI_Bsend(&d, 1, MPI_INT, 1, 14, MPI_COMM_WORLD);
	}
	MPI_Finalize();
	return 0;
}
