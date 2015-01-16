/*
 *   Providing invalid memory for Waitsome
 */

#include <mpi.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);

	int in = 1, out;
	MPI_Request r[3];
	MPI_Isend(&in, 1, MPI_INT, 0, 10, MPI_COMM_SELF, &r[0]);
	r[1] = MPI_REQUEST_NULL;
	MPI_Irecv(&out, 1, MPI_INT, 0, 10, MPI_COMM_SELF, &r[2]);

	int *outcount = (int*) malloc(1); // Error here
	int indices[3];

	MPI_Waitsome(3, r, outcount, indices, MPI_STATUSES_IGNORE);

	MPI_Finalize();
	return 0;
}
