
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int d;
	MPI_Send(&d, 1, MPI_INT, MPI_PROC_NULL, 10, MPI_COMM_WORLD);
	MPI_Status s;
	memset(&s, 0xC1, sizeof(MPI_Status));
	MPI_Recv(&d, 1, MPI_INT, MPI_PROC_NULL, 10, MPI_COMM_WORLD, &s);

	int count = 123;
	MPI_Get_count(&s, MPI_INT, &count);
	int result = s.MPI_SOURCE == MPI_PROC_NULL && s.MPI_TAG == MPI_ANY_TAG && count == 0;
	memset(&s, 0xC1, sizeof(MPI_Status));
	MPI_Request r;
	MPI_Irecv(&d, 1, MPI_INT, MPI_PROC_NULL, 10, MPI_COMM_WORLD, &r);
	MPI_Wait(&r, &s);
	result |= s.MPI_SOURCE == MPI_PROC_NULL && s.MPI_TAG == MPI_ANY_TAG && count == 0;

	MPI_Finalize();
	return !result;
} 
