#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
 
int main(int argc, char *argv[])
{
	MPI_Init(&argc, &argv);

	int *data = (int*) malloc(sizeof(int));
	MPI_Request r;
	MPI_Ibsend(data, 1, MPI_INT, 1, 2, MPI_COMM_WORLD, &r);
	MPI_Wait(&r, MPI_STATUS_IGNORE);
	MPI_Finalize();
	return 0;
}
