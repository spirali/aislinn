#include <mpi.h>
#include <stdio.h>
#include <string.h>

int data[1000];
 
int main(int argc, char *argv[])
{
	int rank;
	MPI_Status status;

	memset(data, 0, sizeof(data));
 
	MPI_Init(&argc, &argv);

	MPI_Datatype type;
	MPI_Type_contiguous(2, MPI_INT, &type);

	int sizes[3] = { 2, 4 };
	MPI_Aint displs[3];

	MPI_Address(&data[1], &displs[0]);
	MPI_Address(&data[14], &displs[1]);

	MPI_Datatype type2;
	MPI_Type_create_hindexed(2, sizes, displs, type, &type2);
	MPI_Type_commit(&type2);

 
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	if (rank == 0)
	{
		for (int i = 0; i < 1000; i++) {
			data[i] = i;
		}
		MPI_Send(MPI_BOTTOM, 1, type2, 1, 123, MPI_COMM_WORLD);
	}
	else if (rank == 1)
	{
		MPI_Recv(MPI_BOTTOM, 1, type2, 0, 123, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		for (int i = 0; i < 30; i++) {
			printf("%i ", data[i]);
		}
		printf("\n");
	}
 
	MPI_Finalize();
	return 0;
}
