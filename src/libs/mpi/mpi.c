
#include "mpi.h"
#include <stdio.h>

#define DEFINE_OP(name, body) \
	static void name(void *input, void *output, int *len, MPI_Datatype *dtype) \
	{ \
		int i, l = *len; \
		switch (*dtype) { \
			case MPI_INT: { \
				int *in = (int*) input; \
				int *out = (int*) output; \
				for (i = 0; i < l; i++) { \
					body; \
				} \
				return; \
			} \
			case MPI_DOUBLE: { \
				double *in = (double*) input; \
				double *out = (double*) output; \
				for (i = 0; i < l; i++) { \
					body; \
				} \
				return; \
			} \
			default: \
				fprintf(stderr, "Invalid type for operation " #name "\n"); \
				MPI_Abort(MPI_COMM_WORLD, 1); \
		} \
	}

DEFINE_OP(op_sum, out[i] += in[i])
DEFINE_OP(op_prod, out[i] *= in[i])

typedef struct { int x; int y; } Type_int_int;
typedef struct { double x; int y; } Type_double_int;

static void op_minloc(void *input, void *output, int *len, MPI_Datatype *dtype)
{
	int i, l = *len;
	if (*dtype == MPI_2INT) {
		Type_int_int *in = (Type_int_int *) input;
		Type_int_int *out = (Type_int_int *) output;
		for (i = 0; i < l; i++) {
			if (out[i].x > in[i].x ||
				(in[i].x == out[i].x && out[i].y > in[i].y)) {
				out[i] = in[i];
			}
		}
		return;
	}

	if (*dtype == MPI_DOUBLE_INT) {
		Type_double_int *in = (Type_double_int *) input;
		Type_double_int *out = (Type_double_int *) output;
		for (i = 0; i < l; i++) {
			if (out[i].x > in[i].x ||
				(in[i].x == out[i].x && out[i].y > in[i].y)) {
				out[i] = in[i];
			}
		}
		return;
	}

	fprintf(stderr, "Invalid type for operation MPI_MINLOC %x\n", *dtype);
//	MPI_Abort(MPI_COMM_WORLD, 1);
}

static void op_maxloc(void *input, void *output, int *len, MPI_Datatype *dtype)
{
	int i, l = *len;

	if (*dtype == MPI_2INT) {
		Type_int_int *in = (Type_int_int *) input;
		Type_int_int *out = (Type_int_int *) output;
		for (i = 0; i < l; i++) {
			if (out[i].x < in[i].x ||
				(in[i].x == out[i].x && out[i].y > in[i].y)) {
				out[i] = in[i];
			}
		}
		return;
	}

	if (*dtype == MPI_DOUBLE_INT) {
		Type_double_int *in = (Type_double_int *) input;
		Type_double_int *out = (Type_double_int *) output;
		for (i = 0; i < l; i++) {
			if (out[i].x < in[i].x ||
				(in[i].x == out[i].x && out[i].y > in[i].y)) {
				out[i] = in[i];
			}
		}
		return;
	}

	fprintf(stderr, "Invalid type for operation MPI_MAXLOC %x\n", *dtype);
	//MPI_Abort(MPI_COMM_WORLD, 1);
}

int MPI_Init(int *argc, char ***argv)
{
	AislinnArgType args[6] = {
		(AislinnArgType) argc,
		(AislinnArgType) argv,
		(AislinnArgType) &op_sum,
		(AislinnArgType) &op_prod,
		(AislinnArgType) &op_minloc,
		(AislinnArgType) &op_maxloc,
	};
	aislinn_call("MPI_Init", args, 6);
	return MPI_SUCCESS;
}
