#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	if (argc != 3) {
		return -1;
	}

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r1, r2;
	int d, e;
	if (rank == 0) {
		d = 100;
		MPI_Isend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r1);
		e = 200;
		MPI_Isend(&e, 1, MPI_INT, 1, 20, MPI_COMM_WORLD, &r2);
		MPI_Wait(&r1, MPI_STATUS_IGNORE);
		MPI_Wait(&r2, MPI_STATUS_IGNORE);
	}
	if (rank == 1) {
		int tag;
		if (!strcmp("MPI_ANY_TAG", argv[1])) {
			tag = MPI_ANY_TAG;
		} else {
			tag = atoi(argv[1]);
		}
		MPI_Recv(&d, 1, MPI_INT, 0, tag, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		if (!strcmp("MPI_ANY_TAG", argv[2])) {
			tag = MPI_ANY_TAG;
		} else {
			tag = atoi(argv[2]);
		}
		MPI_Recv(&e, 1, MPI_INT, 0, tag, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		printf("%i %i\n", d, e);
	}
	MPI_Finalize();
	return 0;
}
