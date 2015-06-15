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

	int data[size];
	int r;
	memset(data, 0, sizeof(int) * size);

	switch(rank) {
		case 1: 
			MPI_Bcast(data, 1, MPI_INT, 0, MPI_COMM_WORLD);
			MPI_Send(&rank, 1, MPI_INT, 3, 10, MPI_COMM_WORLD);
			break;
		case 2: 
			MPI_Bsend(data, 1, MPI_INT, 3, 10, MPI_COMM_WORLD);
			MPI_Bcast(&rank, 1, MPI_INT, 0, MPI_COMM_WORLD);
			break;
		case 3: 
			MPI_Recv(&r, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
			MPI_Send(&r, 1, MPI_INT, 4, 10, MPI_COMM_WORLD);
			MPI_Send(&r, 1, MPI_INT, 5, 10, MPI_COMM_WORLD);
			MPI_Bcast(data, 1, MPI_INT, 0, MPI_COMM_WORLD);
			MPI_Recv(&r, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
			break;
		case 4:
			MPI_Recv(&r, 1, MPI_INT, 3, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
			if (r == 1) {
				MPI_Bcast(data, 1, MPI_INT, 0, MPI_COMM_WORLD);
				MPI_Recv(&rank, 1, MPI_INT, 5, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
			} else {
				MPI_Bcast(data, 1, MPI_INT, 0, MPI_COMM_WORLD);
			}
			break;
		case 5:
			MPI_Recv(&r, 1, MPI_INT, 3, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
			if (r == 1) {
				MPI_Send(&rank, 1, MPI_INT, 4, 10, MPI_COMM_WORLD);
				MPI_Bcast(data, 1, MPI_INT, 0, MPI_COMM_WORLD);
			} else {
				MPI_Bcast(data, 1, MPI_INT, 0, MPI_COMM_WORLD);
			}
			break;
		default: /* including rank 0 */
			MPI_Bcast(data, 1, MPI_INT, 0, MPI_COMM_WORLD);
			break;
	}
	MPI_Finalize();
	return 0;
}
