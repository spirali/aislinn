#include <mpi.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
	MPI_Init(&argc, &argv);
	
	if (argc < 2) {
		return -1;
	}

	char *tmp = (char*) malloc(atoi(argv[1]));
	int len;
	MPI_Get_processor_name(tmp, &len);

	if (len != strlen(tmp)) {
		printf("Invalid name\n");
	} else {
		printf("%s\n", tmp);
	}
	free(tmp);
	
	return 0;
}
