
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Comm c2;
	int rank;
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	if (rank == 1) {
		MPI_Comm_split(MPI_COMM_WORLD, -10, 0, &c2);
	} else {
		MPI_Comm_split(MPI_COMM_WORLD, 10, 0, &c2);
	}
	MPI_Finalize();
	return 0;
}
