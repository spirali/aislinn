#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	if (rank == 0) {
		MPI_Send(&rank, 1, MPI_INT, 1, 10, MPI_COMM_WORLD);
	}

	if (rank == 1) {
		MPI_Request r[5];
		int data;
		MPI_Irecv(&data, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r[0]);
		int count;
		int indices[1];
		MPI_Waitsome(1, r, &count, indices, MPI_STATUSES_IGNORE);
		if (count != 1 || indices[0] != 0) {
			return 1;
		}
	}
	MPI_Finalize();
	return 0;
}
