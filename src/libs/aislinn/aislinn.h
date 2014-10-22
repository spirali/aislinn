
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
		VG_AISLINN_FN_4_POINTER,
		VG_AISLINN_FN_2_INT_2_POINTER,
		VG_AISLINN_FN_2_INT_4_POINTER,
	} Vg_AislinnFnType;

typedef void (Vg_AislinnFnInt) (int);
typedef void (Vg_AislinnFn4Pointer) (void*, void*, void*, void*);
typedef void (Vg_AislinnFn2Int2Pointer) (int, int, void*, void*);
typedef void (Vg_AislinnFn2Int4Pointer) (int, int, void*, void*, void*, void*);

typedef
	struct {
		void *function;
		Vg_AislinnFnType function_type;
		AislinnArgType args[6];
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
