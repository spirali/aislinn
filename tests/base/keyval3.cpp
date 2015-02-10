#include <mpi.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

bool make_error = false;
bool make_free_error = false;
bool make_delete_attr_error = false;
bool make_exit_error = false;
bool make_comm_error = false;

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

	if (make_exit_error) {
		exit(50);
	}

	if (make_comm_error) {
		MPI_Barrier(MPI_COMM_WORLD);
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

	if (argc >= 2 && !strcmp(argv[1], "free_error")) {
			make_free_error = true;
	}

	if (argc >= 2 && !strcmp(argv[1], "delete_attr_error")) {
			make_delete_attr_error = true;
	}

	if (argc >= 2 && !strcmp(argv[1], "exit_error")) {
			make_exit_error = true;
	}

	if (argc >= 2 && !strcmp(argv[1], "comm_error")) {
			make_comm_error = true;
	}

	int key;
	void *v;

	MPI_Comm_create_keyval(MPI_NULL_COPY_FN,
			delete_attr,
			&key,
			(void *)0);

	MPI_Comm_set_attr(MPI_COMM_WORLD, key, &v);
	MPI_Comm_delete_attr(MPI_COMM_WORLD, key);
	if (make_delete_attr_error) {
		MPI_Comm_delete_attr(MPI_COMM_WORLD, key);
	}
	MPI_Comm_free_keyval(&key);
	if (make_free_error) {
        MPI_Comm_free_keyval(&key);
	}

	return 0;
}
