
#include <mpi.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);

	if (argc != 2) {
		return 1;
	}

	int data;
	MPI_Request r;
	if (!strcmp(argv[1], "isend_rank_1")) {
		MPI_Isend(&data, 1, MPI_INT, -1, 1, MPI_COMM_WORLD, &r);
	} else if(!strcmp(argv[1], "isend_rank_2")) {
		MPI_Isend(&data, 1, MPI_INT, 1000, 1, MPI_COMM_WORLD, &r);
	} else if(!strcmp(argv[1], "isend_rank_3")) {
		MPI_Isend(&data, 1, MPI_INT, MPI_ANY_SOURCE, 1, MPI_COMM_WORLD, &r);
	} else if(!strcmp(argv[1], "irecv_rank")) {
		MPI_Irecv(&data, 1, MPI_INT, 1000, 1, MPI_COMM_WORLD, &r);
	} else if(!strcmp(argv[1], "isend_count")) {
		MPI_Isend(&data, -500, MPI_INT, 1, 1, MPI_COMM_WORLD, &r);
	} else if(!strcmp(argv[1], "irecv_count")) {
		MPI_Irecv(&data, -1, MPI_INT, 1, 1, MPI_COMM_WORLD, &r);
    } else if(!strcmp(argv[1], "irecv_datatype")) {
		MPI_Irecv(&data, 100, 0, 1, 1, MPI_COMM_WORLD, &r);
	} else {
		return 1;
	}

	MPI_Finalize();
	return 0;
}
