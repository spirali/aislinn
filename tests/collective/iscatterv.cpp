#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int per_rank_size(int rank, int size)
{
	return size * 2 - rank;
}

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
	const int mysize = per_rank_size(rank, size);

	int total = 100;

	int out1[mysize], out2[mysize];
	int d[total];
	int displs[size], sends[size];
	if (rank == root) {
		for (int i = 0; i < total; i++) {
			d[i] = i * 100;
		}
		for (int i = 0; i < size; i++) {
			sends[i] = per_rank_size(i, size);
			displs[i] = i + 1;
		}
	}

	if (!strcmp(argv[1], "waitall")) {
		MPI_Iscatterv(d, sends, displs, MPI_INT, out1, mysize, MPI_INT, root, MPI_COMM_WORLD, &r[0]);
		MPI_Iscatterv(d, sends, displs, MPI_INT, out2, mysize, MPI_INT, root, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
	}

	if (!strcmp(argv[1], "wait")) {
		MPI_Iscatterv(d, sends, displs, MPI_INT, out1, mysize, MPI_INT, root, MPI_COMM_WORLD, &r[0]);
		MPI_Wait(&r[0], MPI_STATUS_IGNORE);
		MPI_Iscatterv(d, sends, displs, MPI_INT, out2, mysize, MPI_INT, root, MPI_COMM_WORLD, &r[1]);
		MPI_Wait(&r[1], MPI_STATUS_IGNORE);
	}

	printf("%d/%d:OUT1:", rank, mysize);
	for (int i = 0; i < mysize; i++) {
		printf(" %i", out1[i]);
	}
	printf("\n");
	printf("%d/%d:OUT2:", rank, mysize);
	for (int i = 0; i < mysize; i++) {
		printf(" %i", out2[i]);
	}
	printf("\n");
	MPI_Finalize();
	return 0;
}
