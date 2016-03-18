#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r[2];
	int d;
	int d2[2];
	if (rank == 0) {
		MPI_Isend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r[0]);
		MPI_Isend(&d, 1, MPI_INT, 3, 10, MPI_COMM_WORLD, &r[1]);
		int i;
		MPI_Waitany(2, r, &i, MPI_STATUS_IGNORE);
		//MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
		int d3;
		MPI_Recv(&d3, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		MPI_Recv(&d2, 1, MPI_INT, 3, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		MPI_Waitany(2, r, &i, MPI_STATUS_IGNORE);
	}

	if (rank == 1) {
		MPI_Ssend(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD);
		MPI_Recv(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	if (rank == 2) {
		MPI_Ssend(&d, 1, MPI_INT, 3, 20, MPI_COMM_WORLD);
	}

	if (rank == 3) {
		MPI_Recv(&d, 1, MPI_INT, 2, 20, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		MPI_Send(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD);
		MPI_Recv(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	MPI_Finalize();
	return 0;
}
