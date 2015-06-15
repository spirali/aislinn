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

	MPI_Comm c1, c2;
	MPI_Comm_dup(MPI_COMM_WORLD, &c1);
	MPI_Comm_dup(c1, &c2);

	int data[size], data2[size];
	if (rank == 0 || rank == 1) {
		MPI_Bcast(data, 1, MPI_INT, 0, c1);
		MPI_Bcast(data2, 1, MPI_INT, 0, c2);
	}

	if (rank == 2) {
		MPI_Bcast(data, 1, MPI_INT, 0, c2);
		MPI_Bcast(data2, 1, MPI_INT, 0, c1);
	}

	MPI_Finalize();
	return 0;
}
