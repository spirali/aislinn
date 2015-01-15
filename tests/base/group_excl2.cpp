#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
	MPI_Group gw, g2;
	int rank;
	MPI_Status status;

	MPI_Init(&argc, &argv);

	MPI_Comm_group(MPI_COMM_WORLD, &gw);

	int ranks[] = { 2, 1, 1 }; // << Error here, nonunique values
	MPI_Group_excl(gw, 3, ranks, &g2);
	MPI_Finalize();
	return 0;
}
