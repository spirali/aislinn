#include <stdlib.h>
#include <mpi.h>
#include <string.h>

int main(int argc, char **argv) {
	int *i = (int*) malloc(sizeof(int));
	if (argc != 2 || strcmp(argv[1], "noinit")) {
		MPI_Init(&argc, &argv);
	}
	MPI_Initialized(i + 1);
	return 0;
}
