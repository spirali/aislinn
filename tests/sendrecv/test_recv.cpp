#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int return_1, return_2;
	if (argc != 3) {
		return -1;
	}
	return_1 = atoi(argv[1]);
	return_2 = atoi(argv[2]);

	int target = atoi(argv[1]);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r;
	int d;
	if (rank == 1) {
		MPI_Isend(&d, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}
	if (rank == 0) {
		MPI_Irecv(&d, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r);
		int flag;
		MPI_Test(&r, &flag, MPI_STATUS_IGNORE);
		if (flag) {
			return return_1;
		}
		MPI_Wait(&r, MPI_STATUS_IGNORE);
		return return_2;
	}
	MPI_Finalize();
	return 0;
}
