
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	MPI_Comm c = MPI_COMM_WORLD;
	MPI_Comm_free(&c);
	return 0;
}
