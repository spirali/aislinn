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
	int d2[2];
	if (rank == 0) {
		d = 101;
		MPI_Isend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		MPI_Recv(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	if (rank == 1) {
		d = 202;
		MPI_Send(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD);
		MPI_Recv(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	MPI_Finalize();
	return 0;
}
