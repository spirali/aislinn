
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	MPI_Comm c2;
	MPI_Comm_split(MPI_COMM_WORLD, rank / 2, 0, &c2);
	MPI_Comm c3;
	MPI_Comm_split(c2, 0, 0, &c3);
	MPI_Comm_free(&c2);

	int rank1, size1, rank2, size2;
	// Check that the rest is working
	MPI_Comm_rank(MPI_COMM_WORLD, &rank1);
	MPI_Comm_size(MPI_COMM_WORLD, &size1);
	MPI_Comm_rank(c3, &rank2);
	MPI_Comm_size(c3, &size2);
	printf("%i %i %i %i\n", rank1, size1, rank2, size2);

	MPI_Finalize();

	if (c2 != MPI_COMM_NULL) {
		return 1;
	}

	return 0;
}
