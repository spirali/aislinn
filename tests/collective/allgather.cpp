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
	MPI_Request r[2];
	const int mysize = 4;

	int d[mysize * size];
	for (int i = 0; i < size * mysize; i++) {
		d[i] = (i + 1) * (100 + rank);
	}
	int out2[mysize * size];

	MPI_Allgather(d, mysize, MPI_INT, out2, mysize, MPI_INT, MPI_COMM_WORLD);

	printf("OUT:");
	for (int i = 0; i < mysize * size; i++) {
		printf(" %i", out2[i]);
	}
	printf("\n");
	MPI_Finalize();
	return 0;
}
