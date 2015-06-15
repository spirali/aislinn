#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank, size;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);

	/*
	if (rank == 0) {
		MPI_Send(&rank, 1, MPI_INT, 1, 10, MPI_COMM_WORLD);
		MPI_Barrier(MPI_COMM_WORLD);
	} else if (rank == 1) {
		MPI_Barrier(MPI_COMM_WORLD);
		MPI_Recv(&rank, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	} else {
		MPI_Barrier(MPI_COMM_WORLD);
	}*/

	int data[size];
	int r;
	memset(data, 0, sizeof(int) * size);

	if (rank == 0) {
		MPI_Bcast(data, 1, MPI_INT, 2, MPI_COMM_WORLD);
		MPI_Recv(&rank, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	} else if (rank == 1) {
		MPI_Send(&rank, 1, MPI_INT, 0, 10, MPI_COMM_WORLD);
		MPI_Bcast(data, 1, MPI_INT, 2, MPI_COMM_WORLD);
	} else {
		MPI_Bcast(data, 1, MPI_INT, 2, MPI_COMM_WORLD);
	}

	MPI_Finalize();
	return 0;
}
