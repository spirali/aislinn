#include <mpi.h>
#include <stdio.h>
#include <string.h>
 
int main(int argc, char *argv[])
{
	int rank;
	MPI_Status status;
	MPI_Datatype type, backup;

	MPI_Init(&argc, &argv);
 
	MPI_Type_contiguous(5, MPI_DOUBLE, &type);
	MPI_Type_commit(&type);

	backup = type;
 
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	MPI_Type_free(&type);
 
	if (rank == 0)
	{
		int buffer[100];
		MPI_Send(buffer, 1, backup, 1, 10, MPI_COMM_WORLD);
	}
	MPI_Finalize();
	return 0;
}
