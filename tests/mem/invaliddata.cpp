#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
	int rank, touch;

	if (argc != 2) {
		fprintf(stderr, "Invalid arg\n");
		return -1;
	}

	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	int *buffer = (int*) malloc(127 * sizeof(int));

	MPI_Request r;

	if (!strcmp(argv[1], "recv")) {
		MPI_Recv(buffer, 128, MPI_INT, 0, 10, MPI_COMM_WORLD, MPI_STATUSES_IGNORE);
	}

	if (!strcmp(argv[1], "send")) {
		MPI_Send(buffer, 128, MPI_INT, 0, 10, MPI_COMM_WORLD);
	}
	return 0;
}
