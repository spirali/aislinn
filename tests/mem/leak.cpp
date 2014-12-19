#include <stdlib.h>
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);

	const size_t SIZE = 100;

	int rank, size;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);

	if (size < 2) {
		return -1;
	}

	void *mem = malloc(SIZE);
	if (rank == 0) {
		int *mem = (int*) malloc(SIZE);
		for (int i = 0; i < size - 1; i++) {
			MPI_Recv(mem, 1, MPI_INT, MPI_ANY_SOURCE, 1, 
					  MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		}
		if (mem[0] != 1) {
			free(mem);
		}
	} else {
		MPI_Send(&rank, 1, MPI_INT, 0, 1, MPI_COMM_WORLD);
	}
	return 0;
}
