#include <mpi.h>
#include <stdio.h>
#include <string.h>
 
int main(int argc, char *argv[])
{
    int rank;
    MPI_Status status;
    MPI_Datatype type;
    double buffer[10] = {
	1.11, 2.22, 3.33, 4.44, 5.55, 6.66, 7.77, 8.88, 9.99, 10.1010
    };
 
    MPI_Init(&argc, &argv);
 
    MPI_Type_contiguous(5, MPI_DOUBLE, &type);
    MPI_Type_commit(&type);
 
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
 
    if (rank == 0)
    {
        MPI_Send(buffer, 2, type, 1, 123, MPI_COMM_WORLD);
    }
    else if (rank == 1)
    {
	double b[10];
	int i;
	memset(b, 0, sizeof(double) * 10);
        MPI_Recv(b, 2, type, 0, 123, MPI_COMM_WORLD, &status);
	for (i = 0; i < 10; i++) {
		printf("%g\n", b[i]);
	}
    }
 
    MPI_Finalize();
    return 0;
}
