#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	if (argc != 3) {
		fprintf(stderr, "Invalid args:\n" \
				"%s source deadlock \n", argv[0]);
		return 1;
	}

	const int source_mode = atoi(argv[1]);
	const int deadlock = atoi(argv[2]);
	// source_mode = 1 - any source
	// source_mode = 2 - direct prev

	int rank, size;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	MPI_Request r;
	int prev = (rank + size - 1) % size;
	int next = (rank + 1) % size;
	int d;

	if (deadlock || rank != size -1) {
		MPI_Send(&rank, 1, MPI_INT, next, 20, MPI_COMM_WORLD);
	}

	int source;
	if (source_mode == 1) {
		source = MPI_ANY_SOURCE;
	} if (source_mode == 2) {
		source = prev;
	}

	if (deadlock || rank != 0) {
		MPI_Recv(&d, 1, MPI_INT, source, 20, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}
	MPI_Finalize();
	return 0;
}
