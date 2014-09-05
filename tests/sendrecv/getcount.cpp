#include <stdio.h>
#include <mpi.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	int rank;
	MPI_Datatype type;
	MPI_Init(&argc, &argv);
	MPI_Type_contiguous(3, MPI_INT, &type);
	MPI_Type_commit(&type);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	const int size = 123;
	int d[size * 2 * 3];
	MPI_Request r;
	if (rank == 1) {
		MPI_Status s;
		MPI_Irecv(&d, size * 2, type, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, &s);
		int count1, count2;
		MPI_Get_count(&s, MPI_INT, &count1);
		MPI_Get_count(&s, type, &count2);
		printf("%i %i\n", count1, count2);
	} else {
		MPI_Isend(&d, size, type, 1, 10, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}
	MPI_Finalize();
	return 0;
}
