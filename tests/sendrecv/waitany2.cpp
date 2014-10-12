#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);

	if (argc != 2) {
		return 1;
	}

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	if (rank == 0 || rank == 2) {
		int buffer1[2];
		int buffer2[2];
		buffer1[0] = 101 + rank;
		buffer1[1] = 105 + rank;
		buffer2[0] = 201 + rank;
		buffer2[1] = 205 + rank;
		MPI_Request r[2];
		MPI_Isend(&buffer1, 2, MPI_INT, 1, 5, MPI_COMM_WORLD, &r[0]);
		MPI_Isend(&buffer2, 2, MPI_INT, 1, 5, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUS_IGNORE);

		if (r[0] != MPI_REQUEST_NULL || r[1] != MPI_REQUEST_NULL) {
			return 1;
		}
	}

	if (rank == 1) {
		MPI_Request r[4];
		int x, y;
		int index;
		MPI_Status status;
		int b1[2], b2[2], b3[2], b4[4];
		MPI_Irecv(&b1, 2, MPI_INT, 0, 5, MPI_COMM_WORLD, &r[0]);
		MPI_Irecv(&b2, 2, MPI_INT, 0, 5, MPI_COMM_WORLD, &r[1]);
		MPI_Irecv(&b3, 2, MPI_INT, 2, 5, MPI_COMM_WORLD, &r[2]);
		MPI_Irecv(&b4, 2, MPI_INT, 2, 5, MPI_COMM_WORLD, &r[3]);

		if (!strcmp(argv[1], "a")) {
			MPI_Waitany(4, r, &index, MPI_STATUS_IGNORE);
			if (r[index] != MPI_REQUEST_NULL) {
				return 11;
			}
			r[index] = r[3];
			MPI_Waitany(3, r, &index, &status);
			if (r[index] != MPI_REQUEST_NULL) {
				return 11;
			}
			r[index] = r[2];
			MPI_Waitany(2, r, &index, MPI_STATUS_IGNORE);
			if (r[index] != MPI_REQUEST_NULL) {
				return 11;
			}
			r[index] = r[1];
			MPI_Waitany(1, r, &index, MPI_STATUS_IGNORE);
			if (r[index] != MPI_REQUEST_NULL) {
				return 11;
			}
		}

		if (!strcmp(argv[1], "b")) {
			MPI_Waitany(4, r, &index, MPI_STATUS_IGNORE);
			if (r[index] != MPI_REQUEST_NULL) {
				return 11;
			}
			r[index] = r[3];
			MPI_Waitany(3, r, &index, &status);
			if (r[index] != MPI_REQUEST_NULL) {
				return 11;
			}
			r[index] = r[2];
			MPI_Waitall(2, r, MPI_STATUS_IGNORE);
			if (r[0] != MPI_REQUEST_NULL) {
				return 11;
			}
			if (r[1] != MPI_REQUEST_NULL) {
				return 11;
			}
		}

		fprintf(stdout, "%i %i %i %i\n", b1[0], b2[0], b3[0], b4[0]);
		fprintf(stdout, "STATUS %i %i\n", status.MPI_SOURCE, status.MPI_TAG);
	}
	MPI_Finalize();
	return 0;
}
