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
	MPI_Comm_create(MPI_COMM_WORLD, gw, &cw);
	MPI_Comm_create(MPI_COMM_SELF, gs, &cs);

	MPI_Group_free(&gs);
	MPI_Group_free(&gw);

	int world_size;
	MPI_Comm_size(MPI_COMM_WORLD, &world_size);

	int size;
	MPI_Comm_size(cw, &size);
	if (size != world_size) {
		return 1;
	}

	MPI_Comm_size(cs, &size);
	if (size != 1) {
		return 2;
	}

	int world_rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

	int rank;
	MPI_Comm_rank(cw, &rank);
	if (rank != world_rank) {
		return 3;
	}

	MPI_Comm_rank(cs, &rank);
	if (rank != 0) {
		return 4;
	}
	MPI_Finalize();
	return 0;

}
