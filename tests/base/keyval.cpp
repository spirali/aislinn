#include <mpi.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int delete_attr(
		MPI_Comm comm,
		int comm_keyval,
		void *attribute_val,
		void *extra_state)
{
	printf("DELETE %i\n", *((int*) attribute_val));
	return MPI_SUCCESS;
}

static int delete2_attr(
		MPI_Comm comm,
		int comm_keyval,
		void *attribute_val,
		void *extra_state)
{
	printf("DELETE %i\n", *((int*) attribute_val));
	free(attribute_val);
	return MPI_SUCCESS;
}


static int copy_fn(
	MPI_Comm oldcomm,
	int comm_keyval,
	void *extra_state,
	void *attribute_val_in,
	void *attribute_val_out,
	int *flag)
{
	int *out = (int*) malloc(sizeof(int));
	int *in = (int*) attribute_val_in;
	*out = *in;
	printf("COPY %i\n", *in);
	memcpy(attribute_val_out, &out, sizeof(int*));
	*flag = 1;
	return MPI_SUCCESS;
}

int main(int argc, char *argv[])
{
	int key[3];
	int val[3] = { 1, 2, 3 };
	int *val2 = (int*) malloc(sizeof(int));
	int flag;
	int *out;
	int *out2;
	*val2 = 4;

	MPI_Init(&argc, &argv);

	MPI_Comm_create_keyval(MPI_NULL_COPY_FN,
			MPI_NULL_DELETE_FN,
			&key[0],
			(void *)0);

	MPI_Comm_create_keyval(MPI_NULL_COPY_FN,
			delete_attr,
			&key[1],
			(void *)0);

	MPI_Comm_create_keyval(copy_fn,
			delete2_attr,
			&key[2],
			(void *)0);
	MPI_Comm_get_attr(MPI_COMM_WORLD, key[0], &out2, &flag);
	if (flag) {
		return 1;
	}
	MPI_Comm_get_attr(MPI_COMM_WORLD, key[1], &out2, &flag);
	if (flag) {
		return 1;
	}

	MPI_Comm_set_attr(MPI_COMM_WORLD, key[0], &val[0]);
	MPI_Comm_set_attr(MPI_COMM_WORLD, key[1], &val[1]);
	MPI_Comm_set_attr(MPI_COMM_WORLD, key[2], val2);

	MPI_Comm_get_attr(MPI_COMM_SELF, key[1], &out2, &flag);
	if (flag) {
		return 1;
	}

		MPI_Comm_set_attr(MPI_COMM_SELF, key[1], &val[2]);

	MPI_Comm_get_attr(MPI_COMM_SELF, key[1], &out, &flag);
	if (!flag || *out != 3) {
		return 1;
	}

	MPI_Comm_get_attr(MPI_COMM_WORLD, key[1], &out, &flag);
	if (!flag || *out != 2) {
		return 1;
	}

	MPI_Comm_get_attr(MPI_COMM_WORLD, key[0], &out, &flag);
	if (!flag || *out != 1) {
		return 1;
	}

	MPI_Comm_set_attr(MPI_COMM_WORLD, key[1], &val[0]);

	MPI_Comm_get_attr(MPI_COMM_WORLD, key[1], &out, &flag);
	if (!flag || *out != 1) {
		return 1;
	}

	MPI_Comm_get_attr(MPI_COMM_WORLD, key[2], &out, &flag);
	if (!flag || *out != 4) {
		return 1;
	}

	MPI_Comm_get_attr(MPI_COMM_SELF, key[1], &out, &flag);
	if (!flag || *out != 3) {
		return 1;
	}

	MPI_Comm new_comm;
	MPI_Comm_dup(MPI_COMM_WORLD, &new_comm);

	MPI_Comm_get_attr(MPI_COMM_WORLD, key[2], &out, &flag);
	if (!flag || *out != 4) {
		return 1;
	}

	MPI_Comm_get_attr(new_comm, key[2], &out, &flag);
	if (!flag || *out != 4) {
		return 1;
	}

	MPI_Comm_get_attr(new_comm, key[0], &out2, &flag);
	if (flag) {
		return 1;
	}

	MPI_Comm_get_attr(new_comm, key[1], &out2, &flag);
	if (flag) {
		return 1;
	}

	MPI_Comm_get_attr(new_comm, MPI_TAG_UB, &out2, &flag);
	if (!flag) {
		return 100;
	}

	MPI_Comm_delete_attr(MPI_COMM_WORLD, key[0]);
	MPI_Comm_delete_attr(MPI_COMM_WORLD, key[1]);
	MPI_Comm_delete_attr(MPI_COMM_SELF, key[1]);
	MPI_Comm_free_keyval(&key[0]);
	MPI_Comm_free_keyval(&key[1]);
	if (key[0] != MPI_KEYVAL_INVALID || key[1] != MPI_KEYVAL_INVALID) {
		return 2;
	}
	MPI_Comm_free(&new_comm);
	return 0;
}
