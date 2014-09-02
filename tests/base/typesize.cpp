#include <stdlib.h>
#include <stdio.h>
#include <mpi.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);
	int size1, size2, size3;
	MPI_Type_size(MPI_INT, &size1);
	MPI_Type_size(MPI_DOUBLE, &size2);
	MPI_Type_size(MPI_DOUBLE_INT, &size3);
	printf("%i %i %i\n", size1, size2, size3);
	MPI_Finalize();
}
