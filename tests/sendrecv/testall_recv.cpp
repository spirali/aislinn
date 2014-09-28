#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int return_1, return_2;
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Request r[2];
	int d1 = 101, d2 = 202;
	if (rank == 1) {
		MPI_Isend(&d1, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r[0]);
		MPI_Isend(&d2, 1, MPI_INT, 0, 10, MPI_COMM_WORLD, &r[1]);
		int flag = 0;
		while (!flag) {
			MPI_Testall(2, r, &flag, MPI_STATUS_IGNORE);
		}
	}
	if (rank == 0) {
		MPI_Status s[2];
		int flag = 0;
		MPI_Irecv(&d1, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r[1]);
		MPI_Irecv(&d2, 1, MPI_INT, 1, 10, MPI_COMM_WORLD, &r[0]);
		while (!flag) {
			MPI_Testall(2, r, &flag, s);
		}
		printf("%i %i %i %i\n", d1, d2, s[0].MPI_TAG, s[1].MPI_TAG);
		return return_2;
	}
	MPI_Finalize();
	return 0;
}
