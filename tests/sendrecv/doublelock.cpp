#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank;

	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	const int size = 1024 * 780;
	char *mem = (char*) malloc(size);
	memset(mem, 0, size);

	if (rank == 0) {
		MPI_Recv(mem, size, MPI_BYTE, 1, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		MPI_Recv(mem, size, MPI_BYTE, 1, 10, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	} 

	if (rank == 1) {
		MPI_Request r1, r2;
		MPI_Isend(mem, size, MPI_BYTE, 0, 10, MPI_COMM_WORLD, &r1);
		MPI_Isend(mem, size, MPI_BYTE, 0, 10, MPI_COMM_WORLD, &r2);
		MPI_Wait(&r1, MPI_STATUS_IGNORE);
		if (argc > 1 && !strcmp(argv[1], "write")) {
			mem[100 * 1000] = 10;
		}
		MPI_Wait(&r2, MPI_STATUS_IGNORE);
		mem[100 * 1000] = 10;
	}

	MPI_Finalize();
	return 0;
}
