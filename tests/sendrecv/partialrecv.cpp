#include <mpi.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
 
int main(int argc, char *argv[])
{
	if (argc != 2) {
		fprintf(stderr, "Invalid args\n");
		return 1;
	}
	int rank;
	MPI_Status status;
	MPI_Datatype type;
 
	MPI_Init(&argc, &argv);
 
	MPI_Type_contiguous(2, MPI_INT, &type);
	MPI_Type_commit(&type);
 
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
 
	if (rank == 0)
	{
		int buffer[6] = { 12, 13, 15, 21, 22, 30 };
		MPI_Send(buffer, atoi(argv[1]), MPI_INT, 1, 123, MPI_COMM_WORLD);
	}

	else if (rank == 1)
	{
		int b[10];
		int i, count1, count2;
		memset(b, -1, sizeof(int) * 10);
		MPI_Recv(b, 2, type, 0, 123, MPI_COMM_WORLD, &status);
		MPI_Get_count(&status, MPI_INT, &count1);
		MPI_Get_count(&status, type, &count2);
		printf("%i %i\n", count1, count2 == MPI_UNDEFINED);
		for (i = 0; i < 5; i++) {
			printf("%i\n", b[i]);
		}
	}
 
	MPI_Finalize();
	return 0;
}
