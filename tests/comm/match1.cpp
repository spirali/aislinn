#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r[2];

	if (rank == 0) {
		int d1, d2;
		d1 = 500;
		d2 = 1000;
		MPI_Isend(&d1, 1, MPI_INT, 1, 1, MPI_COMM_WORLD, &r[0]);
		MPI_Isend(&d2, 1, MPI_INT, 1, 1, MPI_COMM_WORLD, &r[1]);
		MPI_Wait(&r[0], MPI_STATUS_IGNORE);
		MPI_Wait(&r[1], MPI_STATUS_IGNORE);
	}

	if (rank == 1) {
		int d1, d2;
		MPI_Irecv(&d1, 1, MPI_INT, MPI_ANY_SOURCE, 1, MPI_COMM_WORLD, &r[0]);
		MPI_Irecv(&d2, 1, MPI_INT, MPI_ANY_SOURCE, 1, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUS_IGNORE);

		if (d1 != 500 || d2 != 1000) {
			return 1;
		}
	}
	MPI_Finalize();
	return 0;
}
