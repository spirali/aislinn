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

	if (!strcmp(argv[1], "recv-lock")) {
		MPI_Request r;
		MPI_Irecv(buffer, 10, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		MPI_Recv(buffer, 128, MPI_INT, 0, 10, MPI_COMM_WORLD, MPI_STATUSES_IGNORE);
	}

	if (!strcmp(argv[1], "send-lock")) {
		MPI_Request r;
		MPI_Irecv(buffer, 10, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		MPI_Send(buffer, 128, MPI_INT, 0, 10, MPI_COMM_WORLD);
	}

	if (!strcmp(argv[1], "persistent-recv")) {
		MPI_Request r;
		MPI_Recv_init(buffer, 10, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		free(buffer);
		MPI_Start(&r);
	}

	if (!strcmp(argv[1], "persistent-send")) {
		MPI_Request r;
		MPI_Send_init(buffer, 10, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		free(buffer);
		MPI_Start(&r);
	}
	return 0;
}
