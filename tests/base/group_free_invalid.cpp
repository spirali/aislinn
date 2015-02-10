#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
	int rank;
	MPI_Init(&argc, &argv);
	MPI_Group g = 123;
	MPI_Group_free(&g);
	MPI_Finalize();
	return 0;
}
