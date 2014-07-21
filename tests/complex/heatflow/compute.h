
#ifndef COMPUTE_H
#define COMPUTE_H

#include "matrix.h"

void compute_new_values(DoubleMatrix &matrix, double *top_row, double *bottom_row);
void set_fixed_temp(DoubleMatrix &matrix, int full_size_y, int position, double temp);
int id_to_position(int full_size_y, int process_count, int process_id);
int id_to_size(int full_size_y, int process_count, int process_id);

#endif // COMPUTE_H
