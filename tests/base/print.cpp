
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>

int main(int argc, char **argv)
{
    printf("Line1\n");
    fprintf(stderr, "Line2\n");
    fflush(stdout);

    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (rank != 1) {
        MPI_Send(&rank, 1, MPI_INT, 1, 100, MPI_COMM_WORLD);
        fprintf(stderr, "Sended\n");
    }

    if (rank == 1) {
        int data, i;
        for (i = 0; i < size - 1; i++) {
            MPI_Recv(&data, 1, MPI_INT, MPI_ANY_SOURCE, 100, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            printf("%i\n", data);
            fflush(stdout);
        }
    }

    printf("End\n");

    MPI_Finalize();
    return 0;
}
