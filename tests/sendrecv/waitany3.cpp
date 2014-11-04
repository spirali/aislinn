#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	if (rank == 0) {
		int d;
		MPI_Ssend(&d, 1, MPI_INT, 1, 100, MPI_COMM_WORLD);
		MPI_Ssend(&d, 1, MPI_INT, 1, 100, MPI_COMM_WORLD);
	} 

	if (rank == 1) {
		int d, idx;
		MPI_Request r[3];
		r[0] = MPI_REQUEST_NULL;
		r[2] = MPI_REQUEST_NULL;

		// Any source receive
		MPI_Irecv(&d, 1, MPI_INT, MPI_ANY_SOURCE, 100, MPI_COMM_WORLD, &r[1]);
		MPI_Waitany(3, r, &idx, MPI_STATUS_IGNORE);
		
		if (idx != 1) {
			return 1;
		}

		// Deterministic receive
		MPI_Irecv(&d, 1, MPI_INT, 0, 100, MPI_COMM_WORLD, &r[2]);
		MPI_Waitany(3, r, &idx, MPI_STATUS_IGNORE);
		
		if (idx != 2) {
			return 2;
		}

		// Everything is MPI_REQUEST_NULL
		MPI_Waitany(3, r, &idx, MPI_STATUS_IGNORE);
		if (idx != MPI_UNDEFINED) {
			return 3;
		}

		// Everything is MPI_REQUEST_NULL or persistent request
		MPI_Recv_init(&d, 1, MPI_INT, 0, 100, MPI_COMM_WORLD, &r[0]);
		MPI_Waitany(3, r, &idx, MPI_STATUS_IGNORE);
		if (idx != MPI_UNDEFINED) {
			return 3;
		}

	}
	return 0;
}
