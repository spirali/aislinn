
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	MPI_Comm c2, c3;
	MPI_Comm_dup(MPI_COMM_WORLD, &c2);
	MPI_Comm_dup(MPI_COMM_SELF, &c3);
	int rank2, size2, rank3, size3;
	MPI_Comm_rank(c2, &rank2);
	MPI_Comm_size(c2, &size2);
	MPI_Comm_rank(c3, &rank3);
	MPI_Comm_size(c3, &size3);
	printf("%i %i %i %i %i\n", rank, rank2, size2, rank3, size3);
	MPI_Finalize();
	return 0;
}
