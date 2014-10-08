#include <mpi.h>

int main(int argc, char **argv)
{
	int flag;
	MPI_Initialized(&flag);
	if (flag) {
		return 1;
	}
	MPI_Initialized(&flag);
	if (flag) {
		return 1;
	}
	MPI_Init(&argc, &argv);
	MPI_Initialized(&flag);
	if (!flag) {
		return 1;
	}
	return 0;
}
