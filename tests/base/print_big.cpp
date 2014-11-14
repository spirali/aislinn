
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    const size_t size = 1024 * 1024 * 10;
    char *data = (char*) malloc(size + 1);
    int i;
    char c[4] = { 'a', 'b', 'c', 'd' };
    for (i = 0; i < size; i++) {
	data[i] = c[i % 4];
    }
    data[size] = 0;
    printf("%s\n", data);
    MPI_Finalize();
    free(data);
    return 0;
}
