
#ifndef MATRIX_H
#define MATRIX_H

#include <stdlib.h>
#include <fstream>
#include <string.h>

class DoubleMatrix
{
	public:
		DoubleMatrix() {
			this->size_x = 0;
			this->size_y = 0;
			array1 = NULL;
			array2 = NULL;
		}


		DoubleMatrix(int size_x, int size_y)
		{
			this->size_x = size_x;
			this->size_y = size_y;
			array1 = new double[size_y * size_x];
			array2 = new double[size_y * size_x];
			init(0.0);
			swap();
			init(0.0);
		}

		DoubleMatrix(const DoubleMatrix &c)
		{
			this->size_x = c.size_x;
			this->size_y = c.size_y;

			array1 = new double[size_x * size_y];
			memcpy(array1, c.array1, get_data_size());
			array2 = new double[size_x * size_y];
			memcpy(array2, c.array2, get_data_size());
		}

		DoubleMatrix & operator=(const DoubleMatrix & c)
		{
			if(this != &c) {
				if (size_x * size_y != c.size_x * c.size_y) {
					if (array1) {
						delete[] array1;
						delete[] array2;
					}
					array1 = new double[c.size_y * c.size_x];
					array2 = new double[c.size_y * c.size_x];
				}
				size_x = c.size_x;
				size_y = c.size_y;
				memcpy(array1, c.array1, get_data_size());
				memcpy(array2, c.array2, get_data_size());
			}
			return *this;
		}

		void setup(int size_x, int size_y)
		{
			if (array1) {
				delete [] array1;
				delete [] array2;
			}
			this->size_x = size_x;
			this->size_y = size_y;
			array1 = new double[size_y * size_x];
			array2 = new double[size_y * size_x];
			init(0.0);
			swap();
		}

		void init(double value)
		{
			for(int t = 0; t < size_y * size_x; t++) {
				array1[t] = value;
			}
		}

		size_t get_data_size() const {
			return size_y * size_x * sizeof(double);
		}

		double *get_row(int i) const
		{
			return array1 + i * size_x;
		}

		double *get_write_row(int i) const
		{
			return array2 + i * size_x;
		}

		double *get_data() const
		{
			return array1;
		}

		void swap() {
			double *a = array1;
			array1 = array2;
			array2 = a;
		}

		void as_html(std::ofstream &stream)
		{
			stream.precision(2);
			stream.setf(std::ios_base::fixed);
			for(int j = 0; j < size_y; j++) {
				stream << "<tr>" << std::endl;
				for(int i = 0; i < size_x; i++) {
					stream << "<td>" << get(i, j) << "<td/>" << std::endl;
				}
				stream << "</tr>" << std::endl;
			}
		}

		void write_to_file(const char *filename) {
			std::ofstream stream(filename);
			stream << "<html><head><style type='text/css'>table, tr, td { border: 1px solid; }</style>";
			stream << "</head><table>\n";
			as_html(stream);
			stream << "</table></body></html>\n";
			stream.close();
		}

		~DoubleMatrix()
		{
			if (array1) {
				delete[] array1;
				delete[] array2;
			}
		}

		void set_data(double *data)
		{
			set_data(data, 0, get_data_size());
		}

		void set_data(double *data, int offset, int size)
		{
			memcpy(array2 + offset, data, size);
		}

		void set(int i, int j, double value) {
			array2[i + j * size_x] = value;
		}

		double get(int i, int j) {
			return array1[i + j * size_x];
		}

		double * get_write_pointer(int i, int j)
		{
			return &array2[i + j * size_x];
		}

		int get_size_x() const {
			return size_x;
		}

		int get_size_y() const {
			return size_y;
		}

	protected:
		double *array1, *array2;
		int size_x;
		int size_y;
};

#endif // MATRIX_H
