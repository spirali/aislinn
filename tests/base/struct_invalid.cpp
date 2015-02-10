#include <mpi.h>
#include <stdio.h>
#include <string.h>

typedef struct {
	char a;
	int b[2];
	char c;
	double d;
} S;

int main(int argc, char *argv[])
{
	if (argc != 2) {
		fprintf(stderr, "Invalid arg");
		return 1;
	}
	int rank;
	MPI_Status status;
	MPI_Datatype type;
	S s;

	MPI_Init(&argc, &argv);
	int types[] = { MPI_INT, MPI_INT };
	int lengths[] = { -1, 1 };
	MPI_Aint displs[] = { 10, 20 };
	if (!strcmp(argv[1], "count")) {
		MPI_Type_struct(-2, lengths, displs, types, &type);
	}
	if (!strcmp(argv[1], "sizes")) {
		MPI_Type_struct(2, lengths, displs, types, &type);
	}
	return 0;
}
