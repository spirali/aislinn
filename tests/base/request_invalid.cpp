#include <mpi.h>
#include <stdio.h>
#include <string.h>
 
int main(int argc, char *argv[])
{
	if (argc != 2) {
		return 1;
	}
	int rank;
	MPI_Init(&argc, &argv);
	if (!strcmp(argv[1], "wait")) {
		MPI_Request r = 1234;
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}
	if (!strcmp(argv[1], "waitall")) {
		MPI_Request r[2] = { MPI_REQUEST_NULL, 123 };
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
	}
	if (!strcmp(argv[1], "start")) {
		MPI_Request r = 1234;
		MPI_Start(&r);
	}
	if (!strcmp(argv[1], "start-active")) {
		int d;
		MPI_Request r;
		MPI_Send_init(&d, 1, MPI_INT, 0, 101, MPI_COMM_WORLD, &r);
		MPI_Start(&r);
		MPI_Start(&r);
	}

	MPI_Finalize();
	return 0;
}
