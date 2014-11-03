#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void my_mul(int *in, int *out, int *len, MPI_Datatype *dtype)
{
	if (*dtype != MPI_INT) {
		exit(1);
	}
	int i;
	for (int i = 0; i < *len; i++) {
		out[i] = (in[i] * out[i]);
	}
}

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank, size;
	MPI_Op myop;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	MPI_Op_create((MPI_User_function *)my_mul, 1, &myop);
	int d, out1 = -1, out2 = -1, out3 = -1;

	switch(rank) {
		case 0: d = 10; break;
		case 1: d = 5; break;
		case 2: d = 12; break;
		case 3: d = 13; break;
		case 4: d = 0; break;
		default: d = 1; break;
	}

	MPI_Scan(&d, &out1, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);
	MPI_Scan(&d, &out2, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
	MPI_Scan(&d, &out3, 1, MPI_INT, myop, MPI_COMM_WORLD);

	printf("OUT[%i]: %i %i %i\n", rank, out1, out2, out3);
	MPI_Finalize();
	return 0;
}
