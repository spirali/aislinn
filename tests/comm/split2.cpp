
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	MPI_Comm c2;
	MPI_Comm_split(MPI_COMM_WORLD, rank / 3, 0, &c2);

	int data = rank * 101;
	int result[3];
	int result2;

	MPI_Request r[2];

	if (rank % 2) {
		MPI_Igather(&data, 1, MPI_INT, &result, 1, MPI_INT, 1, c2, &r[0]);
		MPI_Ireduce(&data, &result2, 1, MPI_INT, MPI_SUM, 1, MPI_COMM_WORLD, &r[1]);
	} else {
		MPI_Ireduce(&data, &result2, 1, MPI_INT, MPI_SUM, 1, MPI_COMM_WORLD, &r[0]);
		MPI_Igather(&data, 1, MPI_INT, &result, 1, MPI_INT, 1, c2, &r[1]);
	}

	MPI_Waitall(2, r, MPI_STATUSES_IGNORE);

	if (rank == 1 || rank == 4) {
		printf("%i %i %i\n", result[0], result[1], result[2]);
	}

	if (rank == 1) {
		printf("%i\n", result2);
	}

	MPI_Finalize();
	return 0;
}
