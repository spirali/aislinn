#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	/*if (argc != 2) {
		return -1;
	}*/

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r;
	int c, d;
	int d2[2];
	if (rank == 0) {
		d = 10;
		MPI_Isend(&d, 1, MPI_INT, 2, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		d = 20;
		MPI_Isend(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);

		MPI_Isend(d2, 2, MPI_INT, 2, 11, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		MPI_Irecv(d2, 2, MPI_INT, 2, 11, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}

	if (rank == 1) {
		MPI_Irecv(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		MPI_Isend(&d, 1, MPI_INT, 2, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}

	if (rank == 2) {
		MPI_Irecv(&d, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);

		MPI_Irecv(&c, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		if (d == 20) {
			MPI_Isend(d2, 2, MPI_INT, 0, 11, MPI_COMM_WORLD, &r);
			MPI_Wait(&r, MPI_STATUS_IGNORE);
			MPI_Irecv(d2, 2, MPI_INT, 0, 11, MPI_COMM_WORLD, &r);
			MPI_Wait(&r, MPI_STATUS_IGNORE);
		} else {
			MPI_Irecv(d2, 2, MPI_INT, 0, 11, MPI_COMM_WORLD, &r);
			MPI_Wait(&r, MPI_STATUS_IGNORE);
			MPI_Isend(d2, 2, MPI_INT, 0, 11, MPI_COMM_WORLD, &r);
			MPI_Wait(&r, MPI_STATUS_IGNORE);
		}
	}
	MPI_Finalize();
	return 0;
}
