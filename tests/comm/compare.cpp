
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank, size;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);

	MPI_Comm c2, c3;
	MPI_Comm_split(MPI_COMM_WORLD, 0, (rank + 1) % size, &c2);
	MPI_Comm_split(MPI_COMM_WORLD, 0, rank, &c3);
	int r;
	MPI_Comm_compare(MPI_COMM_WORLD, MPI_COMM_WORLD, &r);
	if (r != MPI_IDENT) {
		return 1;
	}
	MPI_Comm_compare(c2, c2, &r);
	if (r != MPI_IDENT) {
		return 2;
	}
	MPI_Comm_compare(MPI_COMM_WORLD, c3, &r);
	if (r != MPI_CONGRUENT) {
		return 3;
	}
	MPI_Comm_compare(MPI_COMM_WORLD, c2, &r);
	if (r != MPI_SIMILAR) {
		return 4;
	}
	MPI_Comm_compare(c3, c2, &r);
	if (r != MPI_SIMILAR) {
		return 5;
	}
	MPI_Comm_compare(c3, MPI_COMM_SELF, &r);
	if (r != MPI_UNEQUAL) {
		return 6;
	}
	MPI_Finalize();
	return 0;
}
