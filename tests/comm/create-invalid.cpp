#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
	MPI_Init(&argc, &argv);

	MPI_Group gw, gs;
	MPI_Comm_group(MPI_COMM_SELF, &gs);
	MPI_Comm_group(MPI_COMM_WORLD, &gw);

	MPI_Comm cw, cs;
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	if (rank == 0) {
		MPI_Comm_create(MPI_COMM_WORLD, gw, &cw);
	} else {
		MPI_Comm_create(MPI_COMM_WORLD, gs, &cw);
	}

	return 0;
}
