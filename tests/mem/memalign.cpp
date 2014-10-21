#include <mpi.h>
#include <stdlib.h>
#include <malloc.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	void *mem1 = memalign(4, 10);
	void *mem2 = memalign(4, 10);
	void *mem3 = memalign(1024, 100);
	void *mem4 = memalign(4096, 100);

	if (((unsigned long) mem1) % 4 != 0) {
		return 1;
	}

	if (((unsigned long) mem2) % 4 != 0) {
		return 2;
	}

	if (((unsigned long) mem3) % 1024 != 0) {
		return 3;
	}

	if (((unsigned long) mem4) % 4096 != 0) {
		return 4;
	}

	void *memx = malloc(100);
	void *memy = malloc(100000);

	free(mem2);
	free(mem1);
	free(mem3);

	mem1 = memalign(64, 10);
	mem2 = memalign(128, 10);
	mem3 = memalign(64, 10);

	if (((unsigned long) mem1) % 64 != 0) {
		return 5;
	}

	if (((unsigned long) mem2) % 128 != 0) {
		return 6;
	}

	if (((unsigned long) mem3) % 64 != 0) {
		return 5;
	}

	free(mem4);
	free(mem1);
	free(mem3);
	free(mem2);
	free(memx);
	free(memy);

	return 0;
}
