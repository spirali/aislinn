
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank1, size1, rank2, size2;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank1);
	MPI_Comm_size(MPI_COMM_WORLD, &size1);
	MPI_Comm_rank(MPI_COMM_SELF, &rank2);
	MPI_Comm_size(MPI_COMM_SELF, &size2);
	printf("%i %i %i %i\n", rank1, size1, rank2, size2);
	MPI_Finalize();
	return 0;
}
