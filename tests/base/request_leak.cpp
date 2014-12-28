#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
 
int main(int argc, char *argv[])
{
	MPI_Init(&argc, &argv);

	if (argc != 2) {
		return -1;
	}

	int *data = (int*) malloc(sizeof(int));
	MPI_Request r;

	if (!strcmp(argv[1], "send")) {
		MPI_Isend(data, 1, MPI_INT, 0, 1, MPI_COMM_WORLD, &r);
	}

	if (!strcmp(argv[1], "recv")) {
		MPI_Irecv(data, 1, MPI_INT, 0, 1, MPI_COMM_WORLD, &r);
	}

	MPI_Finalize();
	return 0;
}
