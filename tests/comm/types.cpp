#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	if (argc != 2) {
		return 4;
	}
	
	int rank, size;
	MPI_Comm_size(MPI_COMM_WORLD, &size);

	if (size != 2) {
		fprintf(stderr, "Invalid number of processes\n");
		return 3;
	}

	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r;
	int d;
	MPI_Datatype type;
	void *mem;
	int i;

	const int COUNT = 1000;
	size_t datasize;

	if (!strcmp(argv[1], "INT")) {
		type = MPI_INT;
		datasize = sizeof(int) * COUNT;
		int *m = (int*) malloc(datasize);
		for (i = 0; i < COUNT; i++) {
			m[i] = i;
		}
		mem = m;
	} else if (!strcmp(argv[1], "LONG")) {
		type = MPI_LONG;
		datasize = sizeof(long) * COUNT;
		long *m = (long*) malloc(datasize);
		for (i = 0; i < COUNT; i++) {
			m[i] = i;
		}
		mem = m;
	} else if (!strcmp(argv[1], "FLOAT")) {
		type = MPI_FLOAT;
		datasize = sizeof(float) * COUNT;
		float *m = (float*) malloc(datasize);
		for (i = 0; i < COUNT; i++) {
			m[i] = i / 1000.0f;
		}
		mem = m;
	} else if (!strcmp(argv[1], "DOUBLE")) {
		type = MPI_DOUBLE;
		datasize = sizeof(double) * COUNT;
		double *m = (double*) malloc(datasize);
		for (i = 0; i < COUNT; i++) {
			m[i] = i / 1000.0;
		}
		mem = m;
	} else {
		fprintf(stderr, "Invalid argument\n");
		return 1;
	}

	if (rank == 0) {
		MPI_Send(mem, COUNT, type, 1, 10, MPI_COMM_WORLD);
	}
	if (rank == 1) {
		void *rbuffer = malloc(datasize);
		MPI_Recv(rbuffer, COUNT, type, 0, 10, MPI_COMM_WORLD);
		char *x = (char*) rbuffer; char *y = (char*) mem;
		if (memcmp(rbuffer, mem, datasize)) {
			return 2;
		}
		free(rbuffer);
	}
	free(mem);
	MPI_Finalize();
	return 0;
}
