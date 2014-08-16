#include <stdio.h>
#include <aislinn.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>

int main(int argc, char **argv)
{
	if (argc != 2) {
		fprintf(stderr, "Invalid args\n");
		return 1;
	}
	int rank, size;
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	int d = rank * 100;
	int out[size];
	int root = 1;
	MPI_Request r[3];
	if (rank == 0) {
		MPI_Isend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r[0]);
		MPI_Ibarrier(MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
	} else if (rank == 2) {
		if (!strcmp(argv[1], "a")) {
			MPI_Ibarrier(MPI_COMM_WORLD, &r[1]);
			MPI_Isend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r[0]);
			MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
		} 

		if (!strcmp(argv[1], "b")) {
			MPI_Ibarrier(MPI_COMM_WORLD, &r[1]);
			MPI_Wait(&r[1], MPI_STATUSES_IGNORE);
			MPI_Isend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r[0]);
			MPI_Wait(&r[0], MPI_STATUSES_IGNORE);
		}
	} else if (rank == 1) {
		int a, b;
		MPI_Irecv(&a, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, &r[0]);
		MPI_Wait(&r[0], MPI_STATUSES_IGNORE);
		MPI_Ibarrier(MPI_COMM_WORLD, &r[0]);
		MPI_Irecv(&b, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
		printf("a = %i; b = %i\n", a, b);
	}

	MPI_Finalize();
	return 0;
}
