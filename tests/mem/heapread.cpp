#include <mpi.h>
#include <stdlib.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	char *c = (char*) malloc(1024);
	printf("%c\n", c[1233]);
	MPI_Finalize();
	return 0;
}
