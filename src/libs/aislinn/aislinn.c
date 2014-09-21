
#include "aislinn.h"
#include <stdlib.h>
#include <stdio.h>

static void report_invalid_usage()
{
	fprintf(stderr, "This application was compiled with Aislinn.\n"
			"It cannot be directly run.\n");
	exit(1);
}

void aislinn_call_0(const char *name) {
	if (VALGRIND_DO_CLIENT_REQUEST_EXPR( \
		1, VG_USERREQ__AISLINN_CALL_0, name, 0, 0, 0, 0)) {
		report_invalid_usage();
	}
}

void aislinn_call_1(const char *name, AislinnArgType arg0) {
	if (VALGRIND_DO_CLIENT_REQUEST_EXPR( \
		1, VG_USERREQ__AISLINN_CALL_1, name, arg0, 0, 0, 0)) {
		report_invalid_usage();
	}
}

void aislinn_call_2(const char *name,
			AislinnArgType arg0,
			AislinnArgType arg1) {
	if (VALGRIND_DO_CLIENT_REQUEST_EXPR( \
		1, VG_USERREQ__AISLINN_CALL_2, name, arg0, arg1, 0, 0)) {
		report_invalid_usage();
	}
}

void aislinn_call_3(const char *name,
			AislinnArgType arg0,
			AislinnArgType arg1,
			AislinnArgType arg2) {
	if (VALGRIND_DO_CLIENT_REQUEST_EXPR( \
		1, VG_USERREQ__AISLINN_CALL_3, name, arg0, arg1, arg2, 0)) {
		report_invalid_usage();
	}
}

void aislinn_call_4(const char *name,
			AislinnArgType arg0,
			AislinnArgType arg1,
			AislinnArgType arg2,
			AislinnArgType arg3) {
	if (VALGRIND_DO_CLIENT_REQUEST_EXPR( \
		1, VG_USERREQ__AISLINN_CALL_4, name, arg0, arg1, arg2, arg3)) {
		report_invalid_usage();
	}
}

void aislinn_call_args(const char *name,
			AislinnArgType *args,
			AislinnArgType args_count) {
	if (VALGRIND_DO_CLIENT_REQUEST_EXPR( \
		1, VG_USERREQ__AISLINN_CALL_ARGS, name, args, args_count, 0, 0)) {
		report_invalid_usage();
	}
}
