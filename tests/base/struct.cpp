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
	int rank;
	MPI_Status status;
	MPI_Datatype type;
	S s;
 
	MPI_Init(&argc, &argv);
	int types[] = { MPI_CHAR, MPI_INT, MPI_CHAR, MPI_DOUBLE };
	MPI_Aint ss, sa, sb, sc, sd;
	MPI_Get_address(&s, &ss);
	MPI_Get_address(&s.a, &sa);
	MPI_Get_address(&s.b, &sb);
	MPI_Get_address(&s.c, &sc);
	MPI_Get_address(&s.d, &sd);
	MPI_Aint displs[] = {
		sa - ss, sb - ss, sc - ss, sd - ss };

	int lengths[] = { 1, 2, 1, 1 };

	MPI_Type_struct(4, lengths, displs, types, &type);
	int size;
	MPI_Type_size(type, &size);
	MPI_Type_commit(&type);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	if (rank == 0)
	{
		S buffer[500];
		memset(buffer, 0, sizeof(buffer));
		for (int i = 0; i < 200; i++) {
			buffer[i].a = i % 3;
			buffer[i].b[0] = i;
			buffer[i].b[1] = i + 1;
			buffer[i].c = (i + 1) % 7;
			buffer[i].d = 10.0 / (i * 2);
		}

		MPI_Send(buffer, 10, type, 1, 123, MPI_COMM_WORLD);
	}
	else if (rank == 1)
	{
		S buffer[1000];
		memset(buffer, 0, sizeof(S) * 1000);
		MPI_Recv(buffer, 10, type, 0, 123, MPI_COMM_WORLD, &status);
		for (int i = 0; i < 10; i++) {
			printf("%i %i %i %i %g\n", (int) buffer[i].a, 
					      buffer[i].b[0], buffer[i].b[1], 
					      (int) buffer[i].c, 
					      buffer[i].d);
		}
	}
 
	MPI_Finalize();
	return 0;
}
