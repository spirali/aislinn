#include <stdlib.h>
#include <mpi.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);
	if (argc != 2) {
		return 2;
	}
	size_t size = atol(argv[1]);
	void *mem = malloc(size);
	return mem == NULL;
}
