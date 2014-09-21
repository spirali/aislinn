#include <stdio.h>
#include <aislinn.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>

int main(int argc, char **argv)
{
	if (argc != 2) {
		return -1;
	}

	int rank;
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	int d;
	MPI_Request r;
	if (rank == 1) {
		if (!strcmp(argv[1], "wait")) {
			MPI_Status s;
			MPI_Irecv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &r);
			MPI_Wait(&r, &s);
			printf("%i %i\n", s.MPI_SOURCE, s.MPI_TAG);
			MPI_Irecv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &r);
			MPI_Wait(&r, &s);
			printf("%i %i\n", s.MPI_SOURCE, s.MPI_TAG);
		} else if (!strcmp(argv[1], "waitall")) {
			MPI_Status s[2];
			MPI_Request rs[2];
			MPI_Irecv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &rs[0]);
			MPI_Irecv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &rs[1]);
			MPI_Waitall(2, rs, s);
			printf("%i %i\n", s[0].MPI_SOURCE, s[0].MPI_TAG);
			printf("%i %i\n", s[1].MPI_SOURCE, s[1].MPI_TAG);
		} else if (!strcmp(argv[1], "recv")) {
			MPI_Status s;
			MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			printf("%i %i\n", s.MPI_SOURCE, s.MPI_TAG);
			MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			printf("%i %i\n", s.MPI_SOURCE, s.MPI_TAG);
		} else if (!strcmp(argv[1], "probe")) {
			MPI_Status s;
			MPI_Probe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			printf("First1 %i %i\n", s.MPI_SOURCE, s.MPI_TAG);
			MPI_Probe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			printf("First2 %i %i 1\n", s.MPI_SOURCE, s.MPI_TAG);
			MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			printf("First3 %i %i\n", s.MPI_SOURCE, s.MPI_TAG);
			MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			printf("Second %i %i\n", s.MPI_SOURCE, s.MPI_TAG);
		} else if (!strcmp(argv[1], "iprobe")) {
			MPI_Status s;
			int flag = 0;
			while (!flag) {
				MPI_Iprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &s);
			}
			printf("First1 %i %i\n", s.MPI_SOURCE, s.MPI_TAG);

			MPI_Iprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &s);
			printf("First2 %i %i %i\n", s.MPI_SOURCE, s.MPI_TAG, flag);

			MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);

			printf("First3 %i %i\n", s.MPI_SOURCE, s.MPI_TAG);
			MPI_Recv(&d, 1, MPI_INT, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &s);
			printf("Second %i %i\n", s.MPI_SOURCE, s.MPI_TAG);
		} else {
			return 1;
		}
	} else {
		MPI_Isend(&d, 1, MPI_INT, 1, (rank + 1) * 111, MPI_COMM_WORLD, &r);
		MPI_Wait(&r, MPI_STATUS_IGNORE);
	}
	MPI_Finalize();
	return 0;
}
