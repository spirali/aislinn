#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank, size;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	int data1[4];
	int out1[4], out2[4], out3[4], out4[4];
	if (rank == 0) {
		data1[0] = 1; data1[1] = 0; data1[2] = 0xFF; data1[3] = 0;
	}

	if (rank == 1) {
		data1[0] = 0; data1[1] = 0xF0; data1[2] = 0xFFF; data1[3] = 0;
	}

	if (rank == 2) {
		data1[0] = 1; data1[1] = 0x0F; data1[2] = 0xFFFF; data1[3] = 0;
	}

	MPI_Reduce(data1, out1, 4, MPI_INT, MPI_LAND, 1, MPI_COMM_WORLD);
	MPI_Reduce(data1, out2, 4, MPI_INT, MPI_LOR, 1, MPI_COMM_WORLD);
	MPI_Reduce(data1, out3, 4, MPI_INT, MPI_BAND, 1, MPI_COMM_WORLD);
	MPI_Reduce(data1, out4, 4, MPI_INT, MPI_BOR, 1, MPI_COMM_WORLD);

	if (rank == 1) {
		printf("%x %x %x %x\n", out1[0], out1[1], out1[2], out1[3]);
		printf("%x %x %x %x\n", out2[0], out2[1], out2[2], out2[3]);
		printf("%x %x %x %x\n", out3[0], out3[1], out3[2], out3[3]);
		printf("%x %x %x %x\n", out4[0], out4[1], out4[2], out4[3]);
	}

	MPI_Finalize();
	return 0;
}
