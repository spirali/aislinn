#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank, size;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	int *nsizes = (int*) malloc(size * size);
	int total = 0;
	for (int i = 0; i < size; i++) {
		nsizes[i] = (i % 3 + 1);
		total += nsizes[i];
	}
	int *data = (int*) malloc(sizeof(int) * total);

	int *out = (int*) malloc(sizeof(int) * nsizes[rank]);
	for (int i = 0; i < total; i++) {
		data[i] = (rank + 1) * 100 + i;
	}
	MPI_Reduce_scatter(data, out, nsizes, MPI_INT, MPI_SUM, MPI_COMM_WORLD);
	free(data);
	for (int i = 0; i < nsizes[rank]; i++) {
		printf("%i %i\n", rank, out[i]);
	}
	free(out);
	MPI_Finalize();
	return 0;
}
