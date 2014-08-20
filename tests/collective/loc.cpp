#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { double x; int y; } DI;
typedef struct { int x; int y; } II;

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
	const int root = 1 % size;
	const int mysize = 3; 

	II d[mysize];
       	DI dd[mysize];

	if (rank == 0) {
		d[0].x = 100; d[0].y = 3;
		d[1].x = 200; d[1].y = 3;
		d[2].x = 1; d[2].y = 3;
	}

	if (rank == 1) {
		d[0].x = 100; d[0].y = 2;
		d[1].x = 100; d[1].y = 3;
		d[2].x = 3; d[2].y = -5;
	}

	if (rank == 2) {
		d[0].x = 100; d[0].y = 1;
		d[1].x = 300; d[1].y = 30;
		d[2].x = 3; d[2].y = 0;
	}

        for (int i = 0; i < mysize; i++) {
		dd[i].x = d[i].x / 1000.0;
		dd[i].y = d[i].y;
	}

	II out1[mysize], out2[mysize];
	DI out1d[mysize], out2d[mysize];

	if (!strcmp(argv[1], "ok")) {
		MPI_Ireduce(d, out1, mysize, MPI_2INT, MPI_MINLOC, root, MPI_COMM_WORLD, &r[0]);
		MPI_Ireduce(d, out2, mysize, MPI_2INT, MPI_MAXLOC, root, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
		MPI_Ireduce(dd, out1d, mysize, MPI_DOUBLE_INT, MPI_MINLOC, root, MPI_COMM_WORLD, &r[0]);
		MPI_Ireduce(dd, out2d, mysize, MPI_DOUBLE_INT, MPI_MAXLOC, root, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
	}

	if (rank == root) {
		for (int i = 0; i < mysize; i++) {
			printf("int: (%i, %i) (%i, %i)\n", out1[i].x, out1[i].y, out2[i].x, out2[i].y);
		}
		for (int i = 0; i < mysize; i++) {
			printf("double: (%g, %i) (%g, %i)\n", out1d[i].x, out1d[i].y, out2d[i].x, out2d[i].y);
		}
	}
	MPI_Finalize();
	return 0;
}
