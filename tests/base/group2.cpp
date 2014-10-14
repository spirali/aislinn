#include <mpi.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
	int rank;
	MPI_Status status;

	MPI_Init(&argc, &argv);

	MPI_Group gw, g1, g2, g3;
	MPI_Comm_group(MPI_COMM_WORLD, &gw);

	int new_ranks[] = {0, 2, 3};
	MPI_Group_incl(gw, 3, new_ranks, &g1);

	int new_ranks2[] = {2, 3, 0};
	MPI_Group_incl(gw, 3, new_ranks2, &g2);

	MPI_Group_incl(gw, 3, new_ranks2, &g3);


	int size1, size2, size3;
	MPI_Group_size(g1, &size1);
	MPI_Group_size(g1, &size2);
	MPI_Group_size(g1, &size3);

	if (size1 != size2 || size2 != size3 || size1 != 3) {
		return 1;
	}

	int r1, r2;
	MPI_Group_compare(g1, g2, &r1);
	MPI_Group_compare(g2, g3, &r2);
	if (r1 != MPI_SIMILAR || r2 != MPI_IDENT) {
		return 1;
	}

	MPI_Group_free(&g1);
	MPI_Group_free(&g3);
	MPI_Group_free(&g2);

	return 0;
}
