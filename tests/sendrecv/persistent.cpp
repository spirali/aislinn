#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	if (argc != 3) {
		fprintf(stderr, "Invalid arguments\n");
		return -1;
	}

	int target = atoi(argv[1]);
	const char *mode = argv[2];

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r[2];
	if (rank == 0) {
		int d[4] = { 101, 202, 303, 404 };

		if (!strcmp(mode, "send")) {
			MPI_Send(&d[0], 1, MPI_INT, target, 10, MPI_COMM_WORLD);
			MPI_Send(&d[1], 1, MPI_INT, target, 10, MPI_COMM_WORLD);
			MPI_Send(&d[2], 1, MPI_INT, target, 10, MPI_COMM_WORLD);
			MPI_Send(&d[3], 1, MPI_INT, target, 10, MPI_COMM_WORLD);
		}

		if (!strcmp(mode, "psend")) {
			MPI_Send_init(&d[0], 1, MPI_INT, MPI_PROC_NULL, 10, MPI_COMM_WORLD, &r[0]);
			MPI_Start(&r[0]);
			MPI_Wait(&r[0], MPI_STATUS_IGNORE);
			MPI_Start(&r[0]);
			MPI_Wait(&r[0], MPI_STATUS_IGNORE);
			MPI_Request_free(&r[0]);

			MPI_Send_init(&d[0], 1, MPI_INT, target, 10, MPI_COMM_WORLD, &r[0]);
			MPI_Send_init(&d[1], 1, MPI_INT, target, 10, MPI_COMM_WORLD, &r[1]);
			MPI_Start(&r[0]);
			MPI_Start(&r[1]);
			MPI_Waitall(2, r, MPI_STATUS_IGNORE);
			d[0] = d[3];
			d[1] = d[2];
			MPI_Start(&r[1]);
			MPI_Start(&r[0]);
			MPI_Waitall(2, r, MPI_STATUS_IGNORE);
			MPI_Request_free(&r[0]);
			MPI_Request_free(&r[1]);
		}
	}
	if (rank == 1) {
		int d[2];
		MPI_Recv_init(&d[0], 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r[0]);
		MPI_Recv_init(&d[1], 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r[1]);
		MPI_Start(&r[0]);
		MPI_Start(&r[1]);
		MPI_Waitall(2, r, MPI_STATUS_IGNORE);
		printf("%i %i\n", d[0], d[1]);
		MPI_Start(&r[1]);
		MPI_Start(&r[0]);
		MPI_Waitall(2, r, MPI_STATUS_IGNORE);
		printf("%i %i\n", d[0], d[1]);
		MPI_Request_free(&r[1]);
		MPI_Request_free(&r[0]);
		if (r[0] != MPI_REQUEST_NULL || r[1] != MPI_REQUEST_NULL) {
			return 1;
		}
	}
	MPI_Finalize();
	return 0;
}
