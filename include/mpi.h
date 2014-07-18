
#ifndef __AISLINN_MPI_H
#define __AISLINN_MPI_H

#include "aislinn.h"

/** Fake structures */
struct aislinn_request;
struct aislinn_status;

/* Public MPI types */
typedef int MPI_Request;
typedef int MPI_Comm;
typedef aislinn_status *MPI_Status;
typedef int MPI_Datatype;

/* Constants */
const MPI_Comm MPI_COMM_WORLD = 0;

const MPI_Datatype MPI_PACKED = 0xFF00101;
const MPI_Datatype MPI_BYTE = 0xFF00102;
const MPI_Datatype MPI_CHAR = 0xFF00103;
const MPI_Datatype MPI_UNSIGNED_CHAR = 0xFF00104;
const MPI_Datatype MPI_SIGNED_CHAR = 0xFF00105;
const MPI_Datatype MPI_WCHAR = 0xFF00106;
const MPI_Datatype MPI_SHORT = 0xFF00107;
const MPI_Datatype MPI_UNSIGNED_SHORT = 0xFF00108;
const MPI_Datatype MPI_INT = 0xFF00109;
const MPI_Datatype MPI_UNSIGNED = 0xFF0010A;
const MPI_Datatype MPI_LONG = 0xFF0010B;
const MPI_Datatype MPI_UNSIGNED_LONG = 0xFF0010C;
const MPI_Datatype MPI_LONG_LONG_INT = 0xFF0010D;
const MPI_Datatype MPI_UNSIGNED_LONG_LONG = 0xFF0010E;
const MPI_Datatype MPI_FLOAT = 0xFF0010F;
const MPI_Datatype MPI_DOUBLE = 0xFF00110;
const MPI_Datatype MPI_LONG_DOUBLE = 0xFF00111;

#define MPI_STATUS_IGNORE ((MPI_Status*) 0)
#define MPI_STATUSES_IGNORE ((MPI_Status*) 0)
#define MPI_ANY_SOURCE 0xFFFF

inline void MPI_Init(int *argc, char ***argv) {
	AISLINN_CALL_0("MPI_Init");
}

inline int MPI_Finalize() {
	// Currently do nothing
	return 0;
}

inline int MPI_Comm_rank(MPI_Comm comm, int *rank) {
	AISLINN_CALL_2("MPI_Comm_rank", comm, rank);
	return 0;
}

inline int MPI_Comm_size(MPI_Comm comm, int *size) {
	AISLINN_CALL_2("MPI_Comm_size", comm, size);
	return 0;
}

int MPI_Send(void *buf, int count, MPI_Datatype datatype, int dest,
    int tag, MPI_Comm comm)
{
	AislinnArgType args[6];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) dest;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	AISLINN_CALL_ARGS("MPI_Send", args, 6);
	return 0;
}

int MPI_Isend(void *buf, int count, MPI_Datatype datatype, int dest,
    int tag, MPI_Comm comm, MPI_Request *request)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) dest;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	args[6] = (AislinnArgType) request;
	AISLINN_CALL_ARGS("MPI_Isend", args, 7);
	return 0;
}

int MPI_Recv(void *buf, int count, MPI_Datatype datatype,
        int source, int tag, MPI_Comm comm)
{
	AislinnArgType args[6];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) source;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	AISLINN_CALL_ARGS("MPI_Recv", args, 6);
	return 0;
}

int MPI_Irecv(void *buf, int count, MPI_Datatype datatype,
        int source, int tag, MPI_Comm comm, MPI_Request *request)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) source;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	args[6] = (AislinnArgType) request;
	AISLINN_CALL_ARGS("MPI_Irecv", args, 7);
	return 0;
}

int MPI_Wait(MPI_Request *request, MPI_Status *status)
{
	AISLINN_CALL_2("MPI_Wait", request, status);
	return 0;
}

int MPI_Waitall(int count, MPI_Request array_of_requests[],
               MPI_Status array_of_statuses[])
{
	AISLINN_CALL_3("MPI_Waitall",
			count,
			array_of_requests,
			array_of_statuses);
	return 0;
}

int MPI_Test(MPI_Request *request, int *flag, MPI_Status *status)
{
	AISLINN_CALL_3("MPI_Test", request, flag, status);
	return 0;
}

#endif // __AISLINN_MPI_H
