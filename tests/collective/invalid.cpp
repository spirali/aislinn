#include <mpi.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	if (argc != 2) {
		return 1;
	}

	int data, data2;
	int out[2];
	MPI_Request r;
	int recvs[2] = { 1, 1 };
	int displs[2] = { 0, 1 };

	if (!strcmp(argv[1], "gatherv_root")) {
		MPI_Igatherv(&data, 1, MPI_INT, out, recvs, displs, MPI_INT, 105, MPI_COMM_WORLD, &r);
	} else if(!strcmp(argv[1], "gatherv_sendcount")) {
		MPI_Igatherv(&data, -1, MPI_INT, out, recvs, displs, MPI_INT, 0, MPI_COMM_WORLD, &r);
	} else if(!strcmp(argv[1], "reduce_op")) {
		MPI_Ireduce(&data, &data2, 1, MPI_INT, 123, 0, MPI_COMM_WORLD, &r);
	} else {
		return 1;
	}

	MPI_Finalize();
	return 0;
}
