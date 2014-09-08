#include <mpi.h>
#include <stdio.h>
#include <string.h>
 
int main(int argc, char *argv[])
{
	if (argc != 2) {
		fprintf(stderr, "Invalid argument\n");
		return 1;
	}

	int rank;
	MPI_Status status;
 
	MPI_Init(&argc, &argv);

	MPI_Datatype type;
	MPI_Type_contiguous(2, MPI_INT, &type);

 
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	if (rank == 0)
	{
		int buffer[1000];
		for (int i = 0; i < 1000; i++) {
			buffer[i] = i;
		}
		// 2 * (6x int + 5x space)
		MPI_Datatype vtype;
		int sizes[3] = { 1, 2, 3 };
		int displs[3] = { 0, 10, 20 };
		MPI_Type_indexed(3, sizes, displs, type, &vtype);
		MPI_Type_commit(&vtype);

		MPI_Send(buffer, 2, vtype, 1, 123, MPI_COMM_WORLD);
		MPI_Send(buffer, 2, vtype, 1, 123, MPI_COMM_WORLD);
	}
	else if (rank == 1)
	{
		int buffer1[1000], buffer2[1000];
		for (int i = 0; i < 1000; i++) {
			buffer1[i] = -1;
			buffer2[i] = -1;
		}
		MPI_Recv(buffer1, 24, MPI_INT, 0, 123, MPI_COMM_WORLD, &status);
		for (int i = 0; i < 30; i++) {
			printf("%i ", buffer1[i]);
		}
		printf("\n");

		MPI_Datatype vtype;
		int sizes[3] = { 2, 4 };
		MPI_Aint displs[3] = { 5 * sizeof(int), 0 };

		if (!strcmp("old", argv[1])) {
			MPI_Type_hindexed(2, sizes, displs, MPI_INT, &vtype);
		} else {
			MPI_Type_create_hindexed(2, sizes, displs, MPI_INT, &vtype);
		}

		MPI_Type_commit(&vtype);

		MPI_Recv(buffer2, 4, vtype, 0, 123, MPI_COMM_WORLD, &status);
		for (int i = 0; i < 30; i++) {
			printf("%i ", buffer2[i]);
		}
		printf("\n");
	}
 
	MPI_Finalize();
	return 0;
}
