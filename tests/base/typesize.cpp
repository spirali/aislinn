#include <stdlib.h>
#include <stdio.h>
#include <mpi.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);

	MPI_Datatype type1;
	MPI_Type_contiguous(5, MPI_DOUBLE, &type1);
	MPI_Type_commit(&type1);

	int size1, size2, size3, size4;
	MPI_Type_size(MPI_INT, &size1);
	MPI_Type_size(MPI_DOUBLE, &size2);
	MPI_Type_size(MPI_DOUBLE_INT, &size3);
	MPI_Type_size(type1, &size4);

	printf("%i %i %i %i\n", size1, size2, size3, size4);
	MPI_Finalize();
}
