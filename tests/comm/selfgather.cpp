
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	if (rank == 1) {
		const int mysize = 5;
		int a[mysize];
		int b[mysize];
		for (int i = 0; i < mysize; i++) {
			a[i] = i * 101;
		}
		MPI_Gather(a, mysize, MPI_INT, b, mysize, MPI_INT, 0, MPI_COMM_SELF);

		for (int i = 0; i < mysize; i++) {
			printf("%i\n", b[i]);
		}
	}
	MPI_Finalize();
	return 0;
}
