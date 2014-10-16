#include "mpi.h"
#include <stdio.h>
#include <stdlib.h>

void int_add_plus_one(int *in, int *out, int *len, MPI_Datatype *dtype)
{
    int i;
    for ( i=0; i<*len; i++ )
        out[i] += in[i] + 1;
    if (*dtype != MPI_INT) {
        exit(1);
    }
}

void int_non_commute(int *in, int *out, int *len, MPI_Datatype *dtype)
{
    printf("NC: %i %i\n", in[0], out[0]);
    if (*dtype != MPI_INT) {
        exit(1);
    }
}

int main( int argc, char **argv )
{
    int rank, size, i;
    int data[2];
    int result[2] = { 0, 0 };
    MPI_Op op, op2;

    MPI_Init( &argc, &argv );
    MPI_Comm_rank( MPI_COMM_WORLD, &rank );

    data[0] = (rank + 1) * 10;
    data[1] = rank;
    MPI_Op_create((MPI_User_function *)int_add_plus_one, 1, &op);
    MPI_Op_create((MPI_User_function *)int_non_commute, 0, &op2);

    MPI_Allreduce(&data, &result, 2, MPI_INT, op, MPI_COMM_WORLD);
    MPI_Op_free(&op);
    if (op != MPI_OP_NULL) {
	return 1;
    }
    printf("%i %i\n", result[0], result[1]);
    MPI_Reduce(&data, &result, 1, MPI_INT, op2, 2, MPI_COMM_WORLD);

    MPI_Op_free(&op2);
    if (op2 != MPI_OP_NULL) {
	return 1;
    }

    MPI_Finalize();
    return 0;
}
