#include <stdlib.h>
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv) {
	int *a = (int*) 123;
	printf("%i\n", *a);
	return 0;
}
