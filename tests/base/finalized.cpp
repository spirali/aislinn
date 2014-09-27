#include <mpi.h>

int main(int argc, char **argv)
{
	int flag;
	MPI_Init(&argc, &argv);
	MPI_Finalized(&flag);
	if (flag) {
		return 1;
	}
	MPI_Finalize();
	MPI_Finalized(&flag);
	if (!flag) {
		return 1;
	}
	return 0;
}
