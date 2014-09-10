#include <mpi.h>
#include <stdio.h>
#include <string.h>
 
int main(int argc, char *argv[])
{
	int rank;
	MPI_Status status;
	MPI_Init(&argc, &argv);
	MPI_Datatype t = MPI_INT;
	MPI_Type_free(&t);
	MPI_Finalize();
	return 0;
}
