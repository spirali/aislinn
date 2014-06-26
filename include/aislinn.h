
#ifndef __AISLINN
#define __AISLINN

#include <valgrind.h>

typedef
   enum {
      VG_USERREQ__AISLINN_CALL_0 = VG_USERREQ_TOOL_BASE('A','N'),
      VG_USERREQ__AISLINN_CALL_1,
      VG_USERREQ__AISLINN_CALL_2,
      VG_USERREQ__AISLINN_CALL_3,
      VG_USERREQ__AISLINN_CALL_4,
      VG_USERREQ__AISLINN_CALL_ARGS,
   } Vg_AislinnClientRequest;

typedef unsigned long AislinnArgType; // Has to be the same type as UWord

#define AISLINN_CALL_0(name) \
   VALGRIND_DO_CLIENT_REQUEST_STMT( \
      VG_USERREQ__AISLINN_CALL_0, (name), 0, 0, 0, 0);

#define AISLINN_CALL_1(name, arg0) \
   VALGRIND_DO_CLIENT_REQUEST_STMT( \
      VG_USERREQ__AISLINN_CALL_1, (name), (arg0), 0, 0, 0);

#define AISLINN_CALL_2(name, arg0, arg1) \
   VALGRIND_DO_CLIENT_REQUEST_STMT( \
      VG_USERREQ__AISLINN_CALL_2, (name), (arg0), (arg1), 0, 0);

#define AISLINN_CALL_3(name, arg0, arg1, arg2) \
   VALGRIND_DO_CLIENT_REQUEST_STMT( \
      VG_USERREQ__AISLINN_CALL_3, (name), (arg0), (arg1), (arg2), 0);

#define AISLINN_CALL_4(name, arg0, arg1, arg2, arg3) \
   VALGRIND_DO_CLIENT_REQUEST_STMT( \
      VG_USERREQ__AISLINN_CALL_4, (name), (arg0), (arg1), (arg2), (arg3));

#define AISLINN_CALL_ARGS(name, args, args_count) \
   VALGRIND_DO_CLIENT_REQUEST_STMT( \
      VG_USERREQ__AISLINN_CALL_ARGS, (name), (args), (args_count), 0, 0);

#endif // __AISLINN
