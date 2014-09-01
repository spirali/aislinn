#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	if (argc != 2) {
		fprintf(stderr, "Invalid arg\n");
		return 1;
	}
	MPI_Init(&argc, &argv);
	int rank, size;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	MPI_Request r[2];
	const int root = atoi(argv[1]); 
	const int mysize = 4;

	int d1[mysize], d2[mysize];
        for (int i = 0; i < mysize; i++) {
		d1[i] = (rank + 1) * 100 + i;
		d2[i] = (rank + 1) * 1000 + i;
	}
	MPI_Ibcast(&d1, mysize, MPI_INT, root, MPI_COMM_WORLD, &r[0]);
	MPI_Bcast(&d2, mysize, MPI_INT, root, MPI_COMM_WORLD);
	MPI_Wait(&r[0], MPI_STATUS_IGNORE);
	printf("%i OUT1:", rank);
	for (int i = 0; i < mysize; i++) {
		printf(" %i", d1[i]);
	}
	printf("\n");
	printf("%i OUT2:", rank);
	for (int i = 0; i < mysize; i++) {
		printf(" %i", d2[i]);
	}
	printf("\n");
	MPI_Finalize();
	return 0;
}
