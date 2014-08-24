#include <stdio.h>
#include <aislinn.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>

int main(int argc, char **argv)
{
	int rank;
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	const int size = 123;
	int d[size * 2];
	MPI_Request r;
	if (rank == 1) {
		MPI_Status s;
		MPI_Irecv(&d, size * 2, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, &s);
		int count;
		MPI_Get_count(&s, MPI_INT, &count);
		if (size != count) {
			return 1;
		}
	} else {
		MPI_Isend(&d, size, MPI_INT, 1, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}
	MPI_Finalize();
	return 0;
}
