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

	int d[mysize * size];
        for (int i = 0; i < size * mysize; i++) {
		d[i] = (i + 1) * 100;
	}
	int out1[mysize], out2[mysize];

	MPI_Iscatter(&d, mysize, MPI_INT, out1, mysize, MPI_INT, root, MPI_COMM_WORLD, &r[0]);
	MPI_Wait(&r[0], MPI_STATUS_IGNORE);

        for (int i = 0; i < size * mysize; i++) {
		d[i] = (i + 1) * 1000;
	}

	MPI_Iscatter(&d, mysize, MPI_INT, out2, mysize, MPI_INT, root, MPI_COMM_WORLD, &r[1]);
	MPI_Wait(&r[1], MPI_STATUS_IGNORE);

	printf("%i: OUT1:", rank);
	for (int i = 0; i < mysize; i++) {
		printf(" %i", out1[i]);
	}
	printf("\n");
	printf("%i OUT2:", rank);
	for (int i = 0; i < mysize; i++) {
		printf(" %i", out2[i]);
	}
	printf("\n");
	MPI_Finalize();
	return 0;
}
