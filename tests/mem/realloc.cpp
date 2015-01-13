#include <stdlib.h>
#include <mpi.h>

void check(int *m, int size) 
{
	int i;
	for (i = 0; i < size; i++) {
		if (m[i] != i) {
			break;
		}
	}
	if (i != size) {
		exit(1);
	}
}

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);
	int size = 100;
	int *m = (int*) malloc(sizeof(int) * size);
	for (int i = 0; i < size; i++) {
		m[i] = i;
	}

	m = (int*) realloc(m, sizeof(int) * size);

	check(m, size);
	free(m);

	m = (int*) realloc(NULL, sizeof(int) * size);
	for (int i = 0; i < size; i++) {
		m[i] = i;
	}
	check(m, size);
	
	m = (int*) realloc(m, sizeof(int) * size * 10);
	check(m, size);

	m = (int*) realloc(m, sizeof(int) * size / 10);
	check(m, size / 10);
	free(m);
	MPI_Finalize();
	return 0;
}
