/*
 This example tests memory locking mechanism on a sparse type 
 */

#include <mpi.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int data[1000];
 
int main(int argc, char *argv[])
{
	int shift;

	if (argc != 2) {
		fprintf(stderr, "Invalid args\n");
		exit(1);
	}
	
	shift = atoi(argv[1]);

	int rank;
	MPI_Status status;

	memset(data, 0, sizeof(data));
 
	MPI_Init(&argc, &argv);

	MPI_Datatype type;
	MPI_Type_contiguous(2, MPI_INT, &type);

	int sizes[3] = { 2, 1 };
	MPI_Aint displs[3];

	displs[0] = sizeof(int);
	displs[1] = sizeof(int) * 12;

	MPI_Datatype type2;
	MPI_Type_create_hindexed(2, sizes, displs, type, &type2);
	MPI_Type_commit(&type2);

 
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	if (rank == 0)
	{
		for (int i = 0; i < 1000; i++) {
			data[i] = i;
		}
		MPI_Request r[2];
		MPI_Isend(data, 1, type2, 1, 123, MPI_COMM_WORLD, &r[0]);
		MPI_Isend(data + shift, 1, type2, 1, 123, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
	}
	else if (rank == 1)
	{
		MPI_Request r[2];
		MPI_Irecv(data, 1, type2, 0, 123, MPI_COMM_WORLD, &r[0]);
		MPI_Irecv(data + shift, 1, type2, 0, 123, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUSES_IGNORE);
		for (int i = 0; i < 30; i++) {
			printf("%i ", data[i]);
		}
		printf("\n");
	}
 
	MPI_Finalize();
	return 0;
}
