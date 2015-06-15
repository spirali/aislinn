#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

/* This does not contain a deadlock,
   it is a check for false alarms */

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r;
	int d;
	int d2[2];
	if (rank == 0) {
		d = 100;
		MPI_Send(&d, 1, MPI_INT, 1, 20, MPI_COMM_WORLD);
		MPI_Ssend(&d, 1, MPI_INT, 2, 10, MPI_COMM_WORLD);
	}

	if (rank == 1) {
		MPI_Ssend(&d, 1, MPI_INT, 2, 10, MPI_COMM_WORLD);
		MPI_Recv(&d, 1, MPI_INT, 0, 20, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	if (rank == 2) {
		MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	MPI_Finalize();
	return 0;
}
