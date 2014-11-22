#include <stdlib.h>
#include <mpi.h>
#include <string.h>
#include <stdio.h>

int main(int argc, char **argv) {
	int rank, touch;

	if (argc != 2) {
		fprintf(stderr, "Invalid arg\n");
		return -1;
	}

	touch = atoi(argv[1]);

	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	int buffer[10];

	MPI_Request r;

	if (rank == 0) {
		MPI_Irecv(buffer, 10, MPI_INT, 1, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		MPI_Send(buffer, 10, MPI_INT, 1, 10, MPI_COMM_WORLD);
	}

	if (rank == 1) {
		MPI_Isend(buffer, 10, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		if (touch == 1) {
			buffer[3] = 10;
		}
		MPI_Wait(&r, MPI_STATUS_IGNORE);

		// This receive is here to make sure that compiler does not get rid of
		// buffer write
		MPI_Recv(buffer, 10, MPI_INT, 0, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}

	return 0;
}
