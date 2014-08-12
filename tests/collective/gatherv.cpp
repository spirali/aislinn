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

	int total = 0;
	for (int i = 0; i < size; i++) {
		total += per_rank_size(i, size);
	}


	int d[mysize];
        for (int i = 0; i < mysize; i++) {
		d[i] = (rank + 1) * 100 + i;
	}
	int out1[total], out2[total];

	int displs[size], recvs[size];
	int ds = 0;
	for (int i = 0; i < size; i++) {
		recvs[i] = per_rank_size(i, size);
		displs[i] = ds;
		ds += recvs[i];
	}

	if (!strcmp(argv[1], "waitall")) {
		MPI_Igatherv(&d, mysize, MPI_INT, out1, recvs, displs, MPI_INT, root, MPI_COMM_WORLD, &r[0]);
		MPI_Igatherv(&d, mysize, MPI_INT, out2, recvs, displs, MPI_INT, root, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
	}

	if (!strcmp(argv[1], "wait")) {
		MPI_Igatherv(&d, mysize, MPI_INT, out1, recvs, displs, MPI_INT, root, MPI_COMM_WORLD, &r[0]);
		MPI_Wait(&r[0], MPI_STATUS_IGNORE);
		MPI_Igatherv(&d, mysize, MPI_INT, out2, recvs, displs, MPI_INT, root, MPI_COMM_WORLD, &r[1]);
		MPI_Wait(&r[1], MPI_STATUS_IGNORE);
	}

	if (!strcmp(argv[1], "mismatch")) {
		MPI_Igatherv(&d, mysize, MPI_INT, out1, recvs, displs, MPI_INT, rank, MPI_COMM_WORLD, &r[0]);
		MPI_Wait(&r[0], MPI_STATUS_IGNORE);
		MPI_Igatherv(&d, mysize, MPI_INT, out2, recvs, displs, MPI_INT, rank, MPI_COMM_WORLD, &r[1]);
		MPI_Wait(&r[1], MPI_STATUS_IGNORE);
	}

	if (rank == root) {
		printf("OUT1:");
		for (int i = 0; i < total; i++) {
			printf(" %i", out1[i]);
		}
		printf("\n");
		printf("OUT2:");
		for (int i = 0; i < total; i++) {
			printf(" %i", out2[i]);
		}
		printf("\n");
	}
	MPI_Finalize();
	return 0;
}
