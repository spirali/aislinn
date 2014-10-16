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
	const int root = 1 % size;
	const int mysize = 4;

	int d[mysize];
	double dd[mysize];
	for (int i = 0; i < mysize; i++) {
		d[i] = (rank + 1) * 100 + i;
		dd[i] = ((rank + 1) * 100 + i) / 1000.0;
	}
	int out1[mysize], out2[mysize];
	double out1d[mysize], out2d[mysize];

	if (!strcmp(argv[1], "ok")) {
		MPI_Reduce(d, out1, mysize, MPI_INT, MPI_SUM, root, MPI_COMM_WORLD);
		MPI_Reduce(d, out2, mysize, MPI_INT, MPI_PROD, root, MPI_COMM_WORLD);
		MPI_Reduce(dd, out1d, mysize, MPI_DOUBLE, MPI_SUM, root, MPI_COMM_WORLD);
		MPI_Reduce(dd, out2d, mysize, MPI_DOUBLE, MPI_PROD, root, MPI_COMM_WORLD);
	}

	/*
	if (!strcmp(argv[1], "mismatch")) {
		MPI_Igatherv(&d, mysize, MPI_INT, out1, recvs, displs, MPI_INT, rank, MPI_COMM_WORLD, &r[0]);
		MPI_Wait(&r[0], MPI_STATUS_IGNORE);
		MPI_Igatherv(&d, mysize, MPI_INT, out2, recvs, displs, MPI_INT, rank, MPI_COMM_WORLD, &r[1]);
		MPI_Wait(&r[1], MPI_STATUS_IGNORE);
	}*/

	if (rank == root) {
		printf("OUT1:");
		for (int i = 0; i < mysize; i++) {
			printf(" %i", out1[i]);
		}
		printf("\n");
		printf("OUT2:");
		for (int i = 0; i < mysize; i++) {
			printf(" %i", out2[i]);
		}
		printf("\n");

		printf("OUT1d:");
		for (int i = 0; i < mysize; i++) {
			printf(" %g", out1d[i]);
		}
		printf("\n");
		printf("OUT2d:");
		for (int i = 0; i < mysize; i++) {
			printf(" %g", out2d[i]);
		}
		printf("\n");

	}
	MPI_Finalize();
	return 0;
}
