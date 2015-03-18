#include <stdio.h>
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
		MPI_Probe(0, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
		MPI_Probe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
		printf("%i\n", s.MPI_SOURCE);

		MPI_Recv(&d, 1, MPI_INT, s.MPI_SOURCE, s.MPI_TAG, MPI_COMM_WORLD, &s);
		printf("%i\n", s.MPI_SOURCE);

		MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
		printf("%i\n", s.MPI_SOURCE);
	} else if (rank == 0 || rank == 2) {
		MPI_Ssend(&d, 1, MPI_INT, 1, 11, MPI_COMM_WORLD);
	}
	MPI_Finalize();
	return 0;
}
