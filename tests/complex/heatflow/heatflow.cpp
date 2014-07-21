
#include <mpi.h>
#include <time.h>
#include "compute.h"
#include <time.h>
#include <inttypes.h>

#define TAG_ROW1 1
#define TAG_ROW2 2
#define TAG_MATRIX 3

int size_x;
int size_y;
int iterations;
double temp;

void parse_args(int argc, char **argv)
{
	if (argc < 5) {
		fprintf(stderr, "%s <size_x> <size_y> <iterations> <temp>\n", argv[0]);
		exit(-1);
	}
	sscanf(argv[1], "%i", &size_x);
	sscanf(argv[2], "%i", &size_y);
	sscanf(argv[3], "%i", &iterations);
	sscanf(argv[4], "%lg", &temp);
}

void compute(int rank, int size)
{
	double *row1a = (double *) malloc(sizeof(double) * size_x);
	double *row1b = (double *) malloc(sizeof(double) * size_x);
	memset(row1a, 0, sizeof(double *) * size_x);
	double *row2a = (double *) malloc(sizeof(double) * size_x);
	double *row2b = (double *) malloc(sizeof(double) * size_x);
	memset(row2a, 0, sizeof(double *) * size_x);
	int position = id_to_position(size_y, size, rank);
	int height = id_to_size(size_y, size, rank);
	MPI_Request req[2];
	MPI_Request req2[2];
	DoubleMatrix matrix(size_x, height);

	set_fixed_temp(matrix, size_y, position, temp);
	matrix.swap();
	compute_new_values(matrix, row1a, row2a);
	set_fixed_temp(matrix, size_y, position, temp);
	matrix.swap();
	for (int i = 1; i < iterations; i++) {
		MPI_Isend(row1a, size_x, MPI_DOUBLE, (rank + size - 1) % size, TAG_ROW1,
			MPI_COMM_WORLD, &req[0]);
		MPI_Isend(row2a, size_x, MPI_DOUBLE, (rank + 1) % size, TAG_ROW2,
			MPI_COMM_WORLD, &req[1]);
		MPI_Irecv(row1b, size_x, MPI_DOUBLE, (rank + size - 1) % size, TAG_ROW2,
			MPI_COMM_WORLD, &req2[0]);
		MPI_Irecv(row2b, size_x, MPI_DOUBLE, (rank + 1) % size, TAG_ROW1,
			MPI_COMM_WORLD, &req2[1]);

		MPI_Waitall(2, req2, MPI_STATUSES_IGNORE);
		double *tmp;
		tmp = row1a; // swap row1a <-> row1b
		row1a = row1b;
		row1b = tmp;
		tmp = row2a; // swap row2a <-> row2b
		row2a = row2b;
		row2b = tmp;

		compute_new_values(matrix, row1a, row2a);
		set_fixed_temp(matrix, size_y, position, temp);
		matrix.swap();
		MPI_Waitall(2, req, MPI_STATUSES_IGNORE);
	}
	free(row1a);
	free(row1b);
	free(row2a);
	free(row2b);
	if (rank == 0) {
		DoubleMatrix out(size_x, size_y);
		out.set_data(matrix.get_data(), size_x * position, matrix.get_data_size());

		for (int rank = 1; rank < size; rank++) {
			int position = id_to_position(size_y, size, rank);
			int height = id_to_size(size_y, size, rank);
			MPI_Recv(out.get_write_pointer(0, position),
						size_x * height, MPI_DOUBLE, rank, TAG_MATRIX,
						MPI_COMM_WORLD, MPI_STATUS_IGNORE);
		}
		out.swap();
		out.write_to_file("result2.html");
	} else {
		MPI_Send(matrix.get_data(),
				 matrix.get_size_x() * matrix.get_size_y(),
				 MPI_DOUBLE, 0, TAG_MATRIX, MPI_COMM_WORLD);
	}
}

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	parse_args(argc, argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	int size;
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	compute(rank, size);
	MPI_Finalize();
	return 0;
}
