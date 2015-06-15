#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* This does not contain a deadlock,
   it is a check for false alarms */

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	int rank, size;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);

	int data[size];
	int data2[size];
	int r;
	memset(data, 0, sizeof(int) * size);
	MPI_Bcast(data, 1, MPI_INT, 0, MPI_COMM_WORLD);
	MPI_Bcast(data2, 1, MPI_INT, 0, MPI_COMM_WORLD);
	MPI_Finalize();
	return 0;
}
