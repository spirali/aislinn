
#include <stdio.h>
#include <mpi.h>
int global;

int main(int argc, char **argv)
{
	global = 1001;
	MPI_Init(&argc, &argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	int data;
	if (rank == 0) {
		global = 2002;
		MPI_Recv(&data, 1, MPI_INT, MPI_ANY_SOURCE, 1000, MPI_COMM_WORLD, MPI_STATUSES_IGNORE);
		if (global != 2002) {
			return 2;
		}
	}
	if (rank == 1) {
		MPI_Send(&data, 1, MPI_INT, 0, 1000, MPI_COMM_WORLD);
		if (global != 1001) {
			return 3;
		}
	}
	MPI_Finalize();
	return 0;
}
