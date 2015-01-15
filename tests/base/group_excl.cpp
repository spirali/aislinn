#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
	int rank;
	MPI_Status status;

	MPI_Init(&argc, &argv);

	MPI_Group gw, g2;
	int size;
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	MPI_Comm_group(MPI_COMM_WORLD, &gw);

	int ranks[] = { 0, 3 };
	int group_size;
	MPI_Group_excl(gw, 2, ranks, &g2);
	MPI_Group_size(g2, &group_size);

	if (group_size + 2 != size) {
		return 2;
	}

	MPI_Group_free(&gw);
	MPI_Group_free(&g2);
	MPI_Finalize();
	return 0;
}
