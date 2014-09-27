#include <stdio.h>
#include <aislinn.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>

int main(int argc, char **argv)
{
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
		MPI_Barrier(MPI_COMM_WORLD);
		MPI_Waitall(1, r, MPI_STATUSES_IGNORE);
	} else if (rank == 2) {
		MPI_Barrier(MPI_COMM_WORLD);
		MPI_Send(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD);
	} else if (rank == 1) {
		int a, b;
		MPI_Recv(&a, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		MPI_Barrier(MPI_COMM_WORLD);
		MPI_Recv(&b, 1, MPI_INT, MPI_ANY_SOURCE, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		printf("a = %i; b = %i\n", a, b);
	}

	MPI_Finalize();
	return 0;
}
