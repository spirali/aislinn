#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank;

	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	
	int in[3], out[3];

	if (rank == 0) {
        MPI_Request r;
		MPI_Igather(in, 3, MPI_INT, out, 3, MPI_INT, 0, MPI_COMM_WORLD, &r);
	}
	if (rank == 1) {
		MPI_Gather(in, 3, MPI_INT, out, 3, MPI_INT, 0, MPI_COMM_WORLD);
	}

	MPI_Finalize();
	return 0;
}
