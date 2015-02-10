#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	if (argc != 2) {
		fprintf(stderr, "Invalid arg\n");
		return 1;
	}

	MPI_Init(&argc, &argv);

	int rank;

	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	
	if (rank == 1) {
		int d[3];
		if (!strcmp(argv[1], "scatter")) {
			MPI_Scatter(d, 3, MPI_INT, MPI_IN_PLACE, 3, MPI_INT, 0, MPI_COMM_WORLD);
		}
		if (!strcmp(argv[1], "gather")) {
			MPI_Gather(MPI_IN_PLACE, 3, MPI_INT, d, 3, MPI_INT, 0, MPI_COMM_WORLD);
		}
	}

	MPI_Finalize();
	return 0;
}
