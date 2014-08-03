#include <mpi.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	volatile char *c = (char*) malloc(1024);
	c[1233] = 'a';
	// Volation - to prevent compliler to remove this statement */
	MPI_Finalize();
	return 0;
}
