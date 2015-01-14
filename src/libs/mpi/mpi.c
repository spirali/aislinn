
#include "mpi.h"
#include <stdio.h>

#define CASE(mpi_type, c_type, body) \
	case mpi_type: { \
		c_type *in = (c_type*) input; \
		c_type *out = (c_type*) output; \
		for (i = 0; i < l; i++) { \
			body; \
		} \
		return; \
	}

#define INT_TYPES(body) \
	CASE(MPI_INT, int, body) \
	CASE(MPI_UNSIGNED, unsigned, body) \
	CASE(MPI_LONG, long, body) \
	CASE(MPI_UNSIGNED_LONG, unsigned long, body) \
	CASE(MPI_LONG_LONG_INT, long long int, body) \
	CASE(MPI_UNSIGNED_LONG_LONG, unsigned long long, body) \
	CASE(MPI_CHAR, char, body)

#define FLOAT_TYPES(body) \
	CASE(MPI_FLOAT, float, body) \
	CASE(MPI_DOUBLE, double, body) \
	CASE(MPI_LONG_DOUBLE, long double, body)

#define NUM_TYPES(body) \
	INT_TYPES(body) \
	FLOAT_TYPES(body)

#define DEFINE_OP(name) \
	static void name(void *input, void *output, int *len, MPI_Datatype *dtype) \
	{ \
		int i, l = *len; \
		switch (*dtype) {

#define END_OP(name) \
		default: \
			fprintf(stderr, "Invalid type for operation " #name " datatype=%i\n", *dtype); \
			MPI_Abort(MPI_COMM_WORLD, 1); \
		} \
	}

DEFINE_OP(op_sum)
NUM_TYPES(out[i] += in[i])
END_OP(op_sum)

DEFINE_OP(op_prod)
NUM_TYPES(out[i] *= in[i])
END_OP(op_prod)

DEFINE_OP(op_min)
NUM_TYPES(out[i] = (out[i] <= in[i]) ? out[i] : in[i])
END_OP(op_min)

DEFINE_OP(op_max)
NUM_TYPES(out[i] = (out[i] >= in[i]) ? out[i] : in[i])
END_OP(op_max)

DEFINE_OP(op_land)
INT_TYPES(out[i] = out[i] && in[i])
END_OP(op_land)

DEFINE_OP(op_lor)
INT_TYPES(out[i] = out[i] || in[i])
END_OP(op_lor)

DEFINE_OP(op_band)
INT_TYPES(out[i] &= in[i])
END_OP(op_band)

DEFINE_OP(op_bor)
INT_TYPES(out[i] |= in[i])
END_OP(op_bor)


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
	MPI_Abort(MPI_COMM_WORLD, 1);
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
	MPI_Abort(MPI_COMM_WORLD, 1);
}

static int consts_pool[1];

int MPI_Init(int *argc, char ***argv)
{
	AislinnArgType args[13] = {
		(AislinnArgType) argc,
		(AislinnArgType) argv,
		(AislinnArgType) &consts_pool,
		(AislinnArgType) &op_sum,
		(AislinnArgType) &op_prod,
		(AislinnArgType) &op_min,
		(AislinnArgType) &op_max,
		(AislinnArgType) &op_land,
		(AislinnArgType) &op_lor,
		(AislinnArgType) &op_band,
		(AislinnArgType) &op_bor,
		(AislinnArgType) &op_minloc,
		(AislinnArgType) &op_maxloc,
	};
	aislinn_call("MPI_Init", args, 13);
	return MPI_SUCCESS;
}

double MPI_Wtime()
{
	return 0.0;
}

double MPI_Wtick()
{
	return 10e-3;
}
