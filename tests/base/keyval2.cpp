/* Same as keyval.cpp, but with deprecated functions */

#include <mpi.h>
#include <stdio.h>
#include <string.h>

static int delete_attr(
		MPI_Comm comm,
		int comm_keyval,
		void *attribute_val,
		void *extra_state)
{
	printf("DELETE %i\n", *((int*) attribute_val));
	return MPI_SUCCESS;
}


int main(int argc, char *argv[])
{
	int key[3];
	int val[3] = { 1, 2, 3 };
	int flag;
	int *out;

	MPI_Init(&argc, &argv);

	MPI_Keyval_create(MPI_NULL_COPY_FN,
			       MPI_NULL_DELETE_FN,
			       &key[0],
			       (void *)0);

	MPI_Keyval_create(MPI_NULL_COPY_FN,
			       delete_attr,
			       &key[1],
			       (void *)0);

	/* TODO: nonempty COPY_FN
	MPI_Comm_create_keyval(MPI_NULL_COPY_FN,
			       delete_attr,
			       &key[2],
			       (void *)0); */

	MPI_Attr_get(MPI_COMM_WORLD, key[0], NULL, &flag);
	if (flag) {
		return 1;
	}
	MPI_Attr_get(MPI_COMM_WORLD, key[1], NULL, &flag);
	if (flag) {
		return 1;
	}

    	MPI_Attr_put(MPI_COMM_WORLD, key[0], &val[0]);
    	MPI_Attr_put(MPI_COMM_WORLD, key[1], &val[1]);

	MPI_Attr_get(MPI_COMM_SELF, key[1], NULL, &flag);
	if (flag) {
		return 1;
	}

    	MPI_Attr_put(MPI_COMM_SELF, key[1], &val[2]);

	MPI_Attr_get(MPI_COMM_SELF, key[1], &out, &flag);
	if (!flag || *out != 3) {
		return 1;
	}

	MPI_Attr_get(MPI_COMM_WORLD, key[1], &out, &flag);
	if (!flag || *out != 2) {
		return 1;
	}

	MPI_Attr_get(MPI_COMM_WORLD, key[0], &out, &flag);
	if (!flag || *out != 1) {
		return 1;
	}

    	MPI_Attr_put(MPI_COMM_WORLD, key[1], &val[0]);

	MPI_Attr_get(MPI_COMM_WORLD, key[1], &out, &flag);
	if (!flag || *out != 1) {
		return 1;
	}

	MPI_Attr_get(MPI_COMM_SELF, key[1], &out, &flag);
	if (!flag || *out != 3) {
		return 1;
	}

	MPI_Attr_delete(MPI_COMM_WORLD, key[0]);
	MPI_Attr_delete(MPI_COMM_WORLD, key[1]);
	MPI_Attr_delete(MPI_COMM_SELF, key[1]);
	MPI_Keyval_free(&key[0]);
	MPI_Keyval_free(&key[1]);
	if (key[0] != MPI_KEYVAL_INVALID || key[1] != MPI_KEYVAL_INVALID) {
		return 2;
	}
	return 0;
}
