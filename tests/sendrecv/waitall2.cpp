/*
 *  MPI_Waitall with empty lits of requests or containing MPI_REQUEST_NULL
 */

#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);

	MPI_Waitall(0, NULL, MPI_STATUSES_IGNORE);

	MPI_Request r[3];
	r[0] = MPI_REQUEST_NULL;
	MPI_Waitall(1, r, MPI_STATUSES_IGNORE);

	int in = 1, out;
	MPI_Isend(&in, 1, MPI_INT, 0, 10, MPI_COMM_SELF, &r[0]);
	r[1] = MPI_REQUEST_NULL;
	MPI_Irecv(&out, 1, MPI_INT, 0, 10, MPI_COMM_SELF, &r[2]);
	MPI_Waitall(3, r, MPI_STATUSES_IGNORE);

	MPI_Finalize();
	return 0;
}
