
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv) 
{
	MPI_Init(&argc, &argv);
	int dims[10];

	dims[0] = 0; dims[1] = 0;
	MPI_Dims_create(6, 2, dims);
	printf("%i %i\n", dims[0], dims[1]);

	dims[0] = 0; dims[1] = 10;
	MPI_Dims_create(30, 2, dims);
	printf("%i %i\n", dims[0], dims[1]);

	dims[0] = 2; dims[1] = 0;
	MPI_Dims_create(1024, 2, dims);
	printf("%i %i\n", dims[0], dims[1]);

	dims[0] = 0; dims[1] = 0;
	MPI_Dims_create(7, 2, dims);
	printf("%i %i\n", dims[0], dims[1]);

	dims[0] = 10; dims[1] = 20;
	MPI_Dims_create(200, 2, dims);
	printf("%i %i\n", dims[0], dims[1]);

	dims[0] = 0; dims[1] = 0;
	MPI_Dims_create(1, 2, dims);
	printf("%i %i\n", dims[0], dims[1]);

	dims[0] = 0; dims[1] = 0; dims[2] = 0;
	MPI_Dims_create(792, 3, dims);
	printf("%i %i %i\n", dims[0], dims[1], dims[2]);

	MPI_Finalize();
	return 0;
}
