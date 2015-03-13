#include <stdio.h>
#include <aislinn.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>

int main(int argc, char **argv)
{
	int rank;
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	int d, d2;
	if (rank == 1) {
		MPI_Status s;
		int flag = 0;

		MPI_Iprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &s);
		if (flag) {
			printf("Found1\n");
			MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			return 0;
		}
		printf("Not found1\n");

		MPI_Iprobe(0, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &s);
		if (flag) {
			printf("Found2\n");
			MPI_Recv(&d, 1, MPI_INT, 0, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			return 0;
		}
		printf("Not found2\n");

		flag = 1;
		MPI_Iprobe(1, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &s);
		if (flag) { // This should not happen
			return 1;
		}

		MPI_Iprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &s);
		if (flag) {
			printf("Found3\n");
			MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			return 0;
		}
		printf("Not found3\n");
		MPI_Probe(0, 111, MPI_COMM_WORLD, &s);
		MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
	} else {
		MPI_Send(&d, 1, MPI_INT, 1, (rank + 1) * 111, MPI_COMM_WORLD);
	}
	MPI_Finalize();
	return 0;
}
