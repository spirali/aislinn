#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r;
	int d;
	int d1, d2;
	if (rank == 0) {
		MPI_Request rr[2];
		MPI_Send_init(&d1, 1, MPI_INT, 1, 20, MPI_COMM_WORLD, &rr[0]);
		MPI_Send_init(&d1, 1, MPI_INT, 2, 20, MPI_COMM_WORLD, &rr[1]);
		int index;
		MPI_Startall(2, rr);
		MPI_Waitany(2, rr, &index, MPI_STATUS_IGNORE);
		rr[index] = MPI_REQUEST_NULL;

		MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);

		MPI_Waitany(2, rr, &index, MPI_STATUS_IGNORE);
	}

	if (rank == 1) {
		MPI_Ssend(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD);
		MPI_Recv(&d, 1, MPI_INT, 0, 20, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	if (rank == 2) {
		MPI_Ssend(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD);
		MPI_Recv(&d, 1, MPI_INT, 0, 20, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	MPI_Finalize();
	return 0;
}
