
#ifndef __AISLINN
#define __AISLINN

#ifdef __cplusplus
extern "C" {
#endif // __cplusplus

#include <valgrind.h>

typedef unsigned long AislinnArgType; // Has to be the same type as UWord

typedef
   enum {
      VG_USERREQ__AISLINN_CALL_0 = VG_USERREQ_TOOL_BASE('A','N'),
      VG_USERREQ__AISLINN_CALL_1,
      VG_USERREQ__AISLINN_CALL_2,
      VG_USERREQ__AISLINN_CALL_3,
      VG_USERREQ__AISLINN_CALL_4,
      VG_USERREQ__AISLINN_CALL_ARGS,
   } Vg_AislinnClientRequest;


void aislinn_call_0(const char *name);

void aislinn_call_1(const char *name, AislinnArgType arg0);

void aislinn_call_2(const char *name, 
		             AislinnArgType arg0, 
			     AislinnArgType arg1);

void aislinn_call_3(const char *name, 
		             AislinnArgType arg0, 
		             AislinnArgType arg1, 
			     AislinnArgType arg2);

void aislinn_call_4(const char *name, 
		             AislinnArgType arg0, 
		             AislinnArgType arg1, 
		             AislinnArgType arg2, 
			     AislinnArgType arg3);

void aislinn_call_args(const char *name, 
		                AislinnArgType *args, 
		                AislinnArgType count);

#ifdef __cplusplus
}
#endif // __cplusplus

#endif // __AISLINN
