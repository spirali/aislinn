#include <stdlib.h>
#include <mpi.h>
#include <stdio.h>


int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);
	int i;
	const int SZ = 12;
	size_t sizes[SZ] = {
		32, 10, 16, 1, 
		1, 1, 1000, 16000, 
		32, 32, 128, 128
	};
	void *m[SZ];
	unsigned long prev = (unsigned long) malloc(sizes[0]);
	for (i = 1; i < SZ; i++) {
		m[i] = malloc(sizes[i]);
		unsigned long a = (unsigned long) m[i];
		printf("%lu\n", a - prev - sizes[i - 1]);
		prev = a;
	}
	MPI_Finalize();
}
