#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
	int rank;
	MPI_Status status;

	MPI_Init(&argc, &argv);

	MPI_Group gw, gs;
	MPI_Comm_group(MPI_COMM_SELF, &gs);
	MPI_Comm_group(MPI_COMM_WORLD, &gw);

	int size;
	MPI_Group_size(gs, &size);
	if (size != 1) {
		return 1;
	}

	MPI_Group_free(&gs);
	if (gs != MPI_GROUP_NULL) {
		return 1;
	}

	MPI_Group_size(gw, &size);
	if (size != 3) {
		return 1;
	}

	MPI_Group_free(&gw);
	MPI_Finalize();
	return 0;
}
