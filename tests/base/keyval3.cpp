#include <mpi.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

bool make_error = false;

static int delete_attr(
		MPI_Comm comm,
		int comm_keyval,
		void *attribute_val,
		void *extra_state)
{
	int size;
	if (make_error) {
		MPI_Comm_size(MPI_UNDEFINED, &size);
	} else {
		MPI_Comm_size(comm, &size);
	}
	printf("DELETE %i\n", size);
	return MPI_SUCCESS;
}

int main(int argc, char *argv[])
{
	MPI_Init(&argc, &argv);

	if (argc >= 2 && !strcmp(argv[1], "error")) {
			make_error = true;
	}

	int key;
	void *v;

	MPI_Comm_create_keyval(MPI_NULL_COPY_FN,
			delete_attr,
			&key,
			(void *)0);

	MPI_Comm_set_attr(MPI_COMM_WORLD, key, &v);
	MPI_Comm_delete_attr(MPI_COMM_WORLD, key);
	MPI_Comm_free_keyval(&key);
	return 0;
}
