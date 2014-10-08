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
	MPI_Request r;
	int d;
	if (rank == 0) {
		if (!strcmp(mode, "send")) {
			MPI_Isend(&d, 1, MPI_INT, target, 10, MPI_COMM_WORLD, &r);
		}

		if (!strcmp(mode,"bsend")) {
			MPI_Ibsend(&d, 1, MPI_INT, target, 10, MPI_COMM_WORLD, &r);
		}

		if (!strcmp(mode, "ssend")) {
			MPI_Issend(&d, 1, MPI_INT, target, 10, MPI_COMM_WORLD, &r);
		}
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		printf("Send\n");
	}
	if (rank == 1) {
		MPI_Irecv(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		printf("Receive\n");
	}
	MPI_Finalize();
	return 0;
}
