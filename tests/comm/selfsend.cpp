
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	if (rank == 1) {
		int a = 100, b, c;
		MPI_Request r[3];
		MPI_Isend(&a, 1, MPI_INT, 0, 100, MPI_COMM_SELF, &r[0]);
		MPI_Irecv(&b, 1, MPI_INT, MPI_ANY_SOURCE, 100, MPI_COMM_SELF, &r[1]);
		MPI_Irecv(&c, 1, MPI_INT, MPI_ANY_SOURCE, 100, MPI_COMM_WORLD, &r[2]);
		MPI_Waitall(3, r, MPI_STATUSES_IGNORE);
		printf("%i %i %i\n", a, b, c);
	} else {
		int a = 123;
		MPI_Request r;
		MPI_Isend(&a, 1, MPI_INT, 1, 100, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}
	MPI_Finalize();
	return 0;
}
