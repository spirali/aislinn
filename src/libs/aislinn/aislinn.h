
#ifndef __AISLINN
#define __AISLINN

#ifdef __cplusplus
extern "C" {
#endif // __cplusplus

#include <valgrind.h>

typedef unsigned long AislinnArgType; // Has to be the same type as UWord

typedef
	enum {
		VG_USERREQ__AISLINN_CALL = VG_USERREQ_TOOL_BASE('A','N'),
		VG_USERREQ__AISLINN_FUNCTION_RETURN,
	} Vg_AislinnClientRequest;

typedef
	enum {
		VG_AISLINN_FN_INT,
	} Vg_AislinnFnType;

typedef void (Vg_AislinnFnInt) (int);

typedef
	struct {
		void *function;
		Vg_AislinnFnType function_type;
		AislinnArgType args[4];
	} Vg_AislinnCallAnswer;

void aislinn_call_0(const char *name);
void aislinn_call_1(const char *name, AislinnArgType arg0);

void aislinn_call(
    const char *name,
    AislinnArgType *args,
    AislinnArgType count);

#ifdef __cplusplus
}
#endif // __cplusplus

#endif // __AISLINN
