#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
	MPI_Init(&argc, &argv);

	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	if (rank == 0 || rank == 2) {
		int buffer1;
		int buffer2;
		buffer1 = (rank + 1) * 10;
		buffer2 = (rank + 1) * 10 + 1;
		MPI_Request r[2];
		MPI_Ibsend(&buffer1, 1, MPI_INT, 1, (rank + 1) * 10, MPI_COMM_WORLD, &r[0]);
		MPI_Issend(&buffer2, 1, MPI_INT, 1, (rank + 1) * 10 + 1, MPI_COMM_WORLD, &r[1]);
		MPI_Waitall(2, r, MPI_STATUS_IGNORE);
	}

	if (rank == 1) {
		MPI_Request r[5];
		int data[5];
		int count;
		MPI_Irecv(&data[0], 1, MPI_INT, 0, MPI_ANY_TAG, MPI_COMM_WORLD, &r[0]);
		MPI_Irecv(&data[1], 1, MPI_INT, 2, MPI_ANY_TAG, MPI_COMM_WORLD, &r[1]);
		r[2] = MPI_REQUEST_NULL;
		MPI_Irecv(&data[3], 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &r[3]);
		MPI_Irecv(&data[4], 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &r[4]);
		int indices[5];
		MPI_Status statuses[5];
		MPI_Waitsome(5, r, &count, indices, statuses);
		printf("%i\n", count);
		for (int i = 0; i < count; i++) {
			int index = indices[i];
			fprintf(stdout, "%i %i %i %i\n", index, data[index], statuses[i].MPI_SOURCE, statuses[i].MPI_TAG);
		}

		MPI_Request s[5];
		int remaining = 0;

		for (int i = 0; i < 5; i++) {
			if (r[i] == MPI_REQUEST_NULL) {
				continue;
			}
			s[remaining] = r[i];
			remaining+=1;
		}
		printf("%i\n", remaining);
		MPI_Waitall(remaining, s, MPI_STATUSES_IGNORE);
	}
	MPI_Finalize();
	return 0;
}
