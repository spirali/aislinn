
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	MPI_Comm c2;
	 if (rank < 5) {
		MPI_Comm_split(MPI_COMM_WORLD, rank / 2, 1 - rank % 2, &c2);
		int rank2, size2;
		MPI_Comm_rank(c2, &rank2);
		MPI_Comm_size(c2, &size2);
		printf("%i %i %i\n", rank, rank2, size2);

	} else {
		MPI_Comm_split(MPI_COMM_WORLD, MPI_UNDEFINED, 0, &c2);
		if (c2 == MPI_COMM_NULL) {
			printf("Ok\n");
		}
	}
	MPI_Finalize();
	return 0;
}
