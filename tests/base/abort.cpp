#include <mpi.h>
#include <string.h>

int main(int argc, char **argv)
{
	if (argc != 2) {
		return -1;
	}
	if (!strcmp(argv[1], "before")) {
		MPI_Abort(MPI_COMM_WORLD, 3);
	}

	MPI_Init(&argc, &argv);

	if (!strcmp(argv[1], "after")) {
		MPI_Abort(MPI_COMM_WORLD, 3);
	}
	return 0;
}
