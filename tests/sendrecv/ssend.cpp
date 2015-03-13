#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	if (argc != 2) {
		fprintf(stderr, "Invalid arguments\n");
		return -1;
	}
	const char *mode = argv[1];

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r;
	int d;
	if (rank == 0) {
		d = 100;
		if (!strcmp(mode, "ssend")) {
			MPI_Ssend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD);
			MPI_Ssend(&d, 1, MPI_INT, 2, 10, MPI_COMM_WORLD);
		} else if (!strcmp(mode, "bsend")) {
			MPI_Bsend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD);
			MPI_Ssend(&d, 1, MPI_INT, 2, 10, MPI_COMM_WORLD);
		} else if (!strcmp(mode, "waitall")) {
			MPI_Request r[2];
			MPI_Issend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r[0]);
			MPI_Issend(&d, 1, MPI_INT, 2, 10, MPI_COMM_WORLD, &r[1]);
			MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
		} else {
			printf("Error\n");
			return 1;
		}
	}
	if (rank == 1) {
		d = 200;
		MPI_Ssend(&d, 1, MPI_INT, 2, 10, MPI_COMM_WORLD);
		MPI_Recv(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}
	if (rank == 2) {
		MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		printf("%i\n", d);
		MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		printf("%i\n", d);
	}
	MPI_Finalize();
	return 0;
}
