
#include "aislinn.h"
#include <stdlib.h>
#include <stdio.h>

void aislinn_call_0(const char *name) {
	aislinn_call(name, NULL, 0);
}

void aislinn_call_1(const char *name, AislinnArgType arg0) {
	AislinnArgType args[1] = { arg0 };
	aislinn_call(name, args, 1);
}

static void aislinn_function_call(Vg_AislinnCallAnswer *answer)
{
	switch(answer->function_type) {
		case VG_AISLINN_FN_INT: {
			Vg_AislinnFnInt *fn = (Vg_AislinnFnInt*) answer->function;
			fn(answer->args[0]);
			return;
		}
		case VG_AISLINN_FN_4_POINTER: {
			Vg_AislinnFn4Pointer *fn = (Vg_AislinnFn4Pointer*) answer->function;
			fn((void*)answer->args[0], (void*)answer->args[1],
				(void*)answer->args[2], (void*)answer->args[3]);
			return;
		}
		case VG_AISLINN_FN_2_INT_2_POINTER: {
			Vg_AislinnFn2Int2Pointer *fn = (Vg_AislinnFn2Int2Pointer*) answer->function;
			fn((int)answer->args[0], (int)answer->args[1],
				(void*)answer->args[2], (void*)answer->args[3]);
			return;
		}
		default:
			fprintf(stderr, "Invalid function type\n");
			exit(1);
	}
}

void aislinn_call(const char *name,
		AislinnArgType *args,
		AislinnArgType args_count) {
	Vg_AislinnCallAnswer answer;
	if (VALGRIND_DO_CLIENT_REQUEST_EXPR( \
		1, VG_USERREQ__AISLINN_CALL, name, args, args_count, &answer, 0)) {
		fprintf(stderr, "This application was compiled with Aislinn.\n"
			"It cannot be directly run.\n");
	}
	while (answer.function) {
		aislinn_function_call(&answer);
		VALGRIND_DO_CLIENT_REQUEST_STMT(
			VG_USERREQ__AISLINN_FUNCTION_RETURN, &answer, 0, 0, 0, 0);
	}
}
