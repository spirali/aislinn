
#include "compute.h"

#include <time.h>
#include <inttypes.h>

void compute_new_values(DoubleMatrix &matrix, double *top_row, double *bottom_row)
{
	int x = matrix.get_size_x();
	int y = matrix.get_size_y();

	for(int j = 1; j < y - 1; j++) {
		for(int i = 1; i < x - 1; i++) {
			matrix.set(i, j,
					(matrix.get(i, j - 1) +
					matrix.get(i - 1, j) +
					matrix.get(i + 1, j) +
					matrix.get(i, j + 1)) / 4.0);
		}
	}
	// compute left border
	for(int j = 1; j < y - 1; j++) {
		const int i = 0;
		matrix.set(i, j,
				(matrix.get(i, j - 1) +
				matrix.get(i + 1, j) +
				matrix.get(i, j + 1)) / 4.0);
	}
	//tock();
	// compute right border
	for(int j = 1; j < y - 1; j++) {
		const int i = x - 1;
		matrix.set(i, j,
				(matrix.get(i, j - 1) +
				matrix.get(i - 1, j) +
				matrix.get(i, j + 1)) / 4.0);
	}

	// compute upper border
	for(int i = 1; i < x - 1; i++) {
		const int j = 0;
		matrix.set(i, j,
				(top_row[i] +
				matrix.get(i - 1, j) +
				matrix.get(i + 1, j) +
				matrix.get(i, j + 1)) / 4.0);

	}

	// compute bottom border
	for(int i = 1; i < x - 1; i++) {
		const int j = y - 1;
		matrix.set(i, j,
				(bottom_row[i] +
				matrix.get(i, j - 1) +
				matrix.get(i - 1, j) +
				matrix.get(i + 1, j)) / 4.0);

	}

	// compute corners
	matrix.set(0, 0, (top_row[0] + matrix.get(1, 0) + matrix.get(0, 1)) / 4.0);
	matrix.set(x - 1, 0, (top_row[x-1] + matrix.get(x - 2, 0)
		+ matrix.get(x - 1, 1)) / 4.0);
	matrix.set(0, y - 1, (bottom_row[0] + matrix.get(1, y - 1)
		+ matrix.get(0, y - 2)) / 4.0);
	matrix.set(x - 1, y - 1, (bottom_row[x-1] + matrix.get(x - 2, y - 1)
		+ matrix.get(x-1, y-2)) / 4.0);

	memcpy(top_row, matrix.get_write_row(0), sizeof(double) * x);
	memcpy(bottom_row, matrix.get_write_row(y - 1), sizeof(double) * x);
}

void set_fixed_temp(DoubleMatrix &matrix, int full_size_y, int position, double temp)
{
	int source_y = full_size_y / 2;
	if(source_y >= position && source_y < position + matrix.get_size_y()) {
		source_y -= position;
		int source_x = matrix.get_size_x() / 2;
		matrix.set(source_x, source_y, temp);
	}
}

int id_to_position(int full_size_y, int process_count, int process_id)
{
	int rows_per_instance = ((full_size_y - 1) / process_count) + 1;
	return rows_per_instance * process_id;
}

int id_to_size(int full_size_y, int process_count, int process_id)
{
	int rows_per_instance = ((full_size_y - 1) / process_count) + 1;
	int first = rows_per_instance * process_id;
	int end = first + rows_per_instance;
	if(full_size_y < end) {
		end = full_size_y;
	}
	return end - first;
}
