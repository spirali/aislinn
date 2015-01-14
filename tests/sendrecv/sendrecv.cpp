#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank, size;

	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);

	int sbuffer[2] = { rank, rank + 1 };
	int rbuffer[2];
	MPI_Sendrecv(sbuffer, 2, MPI_INT, (rank + 1) % size, 300,
	             rbuffer, 2, MPI_INT, (rank + size - 1) % size, 300, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	printf("%i %i %i\n", rank, rbuffer[0], rbuffer[1]);
	MPI_Finalize();
	return 0;
}
