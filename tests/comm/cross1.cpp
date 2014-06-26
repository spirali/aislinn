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
	if (rank == 1) {
		MPI_Isend(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		MPI_Irecv(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);

	}
	if (rank == 0) {
		MPI_Isend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		MPI_Irecv(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}
	MPI_Finalize();
	return 0;
}
