
#include <stdlib.h>
#include <mpi.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
	void *mem;
	for (int i = 0; i < 10000; ++i) {
		mem = malloc(i * 100);
		if (mem == NULL) {
			return 1;
		}
		free(mem);
	}

	for (int i = 0; i < 10000; ++i) {
		mem = malloc(480000);
		if (mem == NULL) {
			return 1;
		}
		free(mem);
	}
	return 0;
}
