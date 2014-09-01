
#ifndef __AISLINN_MPI_H
#define __AISLINN_MPI_H

#include "aislinn.h"

/** Fake structures */
struct aislinn_request;
struct aislinn_status;

/* Public MPI types */
typedef int MPI_Request;
typedef int MPI_Comm;
typedef
	struct {
		int MPI_SOURCE;
		int MPI_TAG;
		int size;
	} MPI_Status;

typedef int MPI_Datatype;
typedef int MPI_Op;

/* Constants */
const int MPI_UNDEFINED = -0x0BEFBEEF;

const MPI_Comm MPI_COMM_NULL = 0x0000CC00;
const MPI_Comm MPI_COMM_SELF = 0x0000CC01;
const MPI_Comm MPI_COMM_WORLD = 0x0000CC02;

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
const MPI_Datatype MPI_FLOAT_INT = 0xFF00112;
const MPI_Datatype MPI_DOUBLE_INT = 0xFF00113;
const MPI_Datatype MPI_LONG_INT = 0xFF00114;
const MPI_Datatype MPI_2INT = 0xFF00115;
const MPI_Datatype MPI_SHORT_INT = 0xFF00116;
const MPI_Datatype MPI_LONG_DOUBLE_INT = 0xFF00117;

const MPI_Op MPI_MAX = 0xDD00101;
const MPI_Op MPI_MIN = 0xDD00102;
const MPI_Op MPI_SUM = 0xDD00103;
const MPI_Op MPI_PROD = 0xDD00104;
const MPI_Op MPI_LAND = 0xDD00105;
const MPI_Op MPI_BAND = 0xDD00106;
const MPI_Op MPI_LOR = 0xDD00107;
const MPI_Op MPI_BOR = 0xDD00109;
const MPI_Op MPI_LXOR = 0xDD0010A;
const MPI_Op MPI_BXOR = 0xDD0010B;
const MPI_Op MPI_MINLOC = 0xDD0010C;
const MPI_Op MPI_MAXLOC = 0xDD0010D;

#define MPI_STATUS_IGNORE ((MPI_Status*) 0)
#define MPI_STATUSES_IGNORE ((MPI_Status*) 0)
#define MPI_ANY_SOURCE -0x00AA00
#define MPI_ANY_TAG -0x00BB00

inline void MPI_Init(int *argc, char ***argv) {
	aislinn_call_0("MPI_Init");
}

inline int MPI_Finalize() {
	// Currently do nothing
	return 0;
}

inline int MPI_Comm_rank(MPI_Comm comm, int *rank) {
	aislinn_call_2(
		"MPI_Comm_rank",
		(AislinnArgType) comm,
		(AislinnArgType) rank);
	return 0;
}

inline int MPI_Comm_size(MPI_Comm comm, int *size) {
	aislinn_call_2(
		"MPI_Comm_size",
		(AislinnArgType) comm,
		(AislinnArgType) size);
	return 0;
}

inline int MPI_Get_count(
        const MPI_Status *status, MPI_Datatype datatype, int *count) {
	aislinn_call_3(
		"MPI_Get_count",
		(AislinnArgType) status,
		(AislinnArgType) datatype,
		(AislinnArgType) count);
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
	aislinn_call_args("MPI_Send", args, 6);
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
	aislinn_call_args("MPI_Isend", args, 7);
	return 0;
}

int MPI_Recv(void *buf, int count, MPI_Datatype datatype,
        int source, int tag, MPI_Comm comm, MPI_Status *status)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) source;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	args[6] = (AislinnArgType) status;
	aislinn_call_args("MPI_Recv", args, 7);
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
	aislinn_call_args("MPI_Irecv", args, 7);
	return 0;
}

int MPI_Wait(MPI_Request *request, MPI_Status *status)
{
	aislinn_call_2(
		"MPI_Wait",
		(AislinnArgType) request,
		(AislinnArgType) status);
	return 0;
}

int MPI_Waitall(int count, MPI_Request array_of_requests[],
               MPI_Status array_of_statuses[])
{
	aislinn_call_3(
		"MPI_Waitall",
		(AislinnArgType) count,
		(AislinnArgType) array_of_requests,
		(AislinnArgType) array_of_statuses);
	return 0;
}

int MPI_Test(MPI_Request *request, int *flag, MPI_Status *status)
{
	aislinn_call_3(
		"MPI_Test",
		(AislinnArgType) request,
		(AislinnArgType) flag,
		(AislinnArgType) status);
	return 0;
}

int MPI_Barrier(MPI_Comm comm)
{
	aislinn_call_1(
		"MPI_Barrier",
		(AislinnArgType) comm);
	return 0;
}

int MPI_Gather(const void *sendbuf,
                int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf,
                int recvcount,
                MPI_Datatype recvtype,
                int root,
                MPI_Comm comm)
{
	AislinnArgType args[8];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcount;
	args[5] = (AislinnArgType) recvtype;
	args[6] = (AislinnArgType) root;
	args[7] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Gather", args, 8);
	return 0;
}

int MPI_Gatherv(const void *sendbuf,
                int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf,
                const int recvcounts[],
                const int displs[],
                MPI_Datatype recvtype,
                int root,
                MPI_Comm comm)
{
	AislinnArgType args[9];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcounts;
	args[5] = (AislinnArgType) displs;
	args[6] = (AislinnArgType) recvtype;
	args[7] = (AislinnArgType) root;
	args[8] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Gatherv", args, 9);
	return 0;
}

int MPI_Scatter(const void *sendbuf,
		int sendcount,
		MPI_Datatype sendtype,
		void *recvbuf,
		int recvcount,
		MPI_Datatype recvtype,
		int root,
		MPI_Comm comm)
{
	AislinnArgType args[8];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcount;
	args[5] = (AislinnArgType) recvtype;
	args[6] = (AislinnArgType) root;
	args[7] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Scatter", args, 8);
	return 0;
}

int MPI_Scatterv(const void *sendbuf,
		const int sendcounts[],
		const int displs[],
		MPI_Datatype sendtype,
		void *recvbuf,
		int recvcount,
		MPI_Datatype recvtype,
		int root,
		MPI_Comm comm)
{
	AislinnArgType args[9];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcounts;
	args[2] = (AislinnArgType) displs;
	args[3] = (AislinnArgType) sendtype;
	args[4] = (AislinnArgType) recvbuf;
	args[5] = (AislinnArgType) recvcount;
	args[6] = (AislinnArgType) recvtype;
	args[7] = (AislinnArgType) root;
	args[8] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Scatterv", args, 9);
	return 0;
}

int MPI_Reduce(const void *sendbuf,
		void *recvbuf,
		int count,
		MPI_Datatype datatype,
		MPI_Op op,
		int root,
		MPI_Comm comm)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) recvbuf;
	args[2] = (AislinnArgType) count;
	args[3] = (AislinnArgType) datatype;
	args[4] = (AislinnArgType) op;
	args[5] = (AislinnArgType) root;
	args[6] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Reduce", args, 7);
	return 0;
}

int MPI_Allreduce(void *sendbuf, void *recvbuf, int count,
    MPI_Datatype datatype, MPI_Op op, MPI_Comm comm)
{
	AislinnArgType args[6];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) recvbuf;
	args[2] = (AislinnArgType) count;
	args[3] = (AislinnArgType) datatype;
	args[4] = (AislinnArgType) op;
	args[5] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Allreduce", args, 6);
	return 0;
}

int MPI_Bcast(void *buffer, int count, MPI_Datatype datatype,
		int root, MPI_Comm comm)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) buffer;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) root;
	args[4] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Bcast", args, 5);
	return 0;
}

int MPI_Ibarrier(MPI_Comm comm, MPI_Request *request)
{
	aislinn_call_2(
		"MPI_Ibarrier",
		(AislinnArgType) comm,
		(AislinnArgType) request);
	return 0;
}

int MPI_Scan(const void *sendbuf, void *recvbuf, int count, MPI_Datatype datatype,
             MPI_Op op, MPI_Comm comm)
{
	AislinnArgType args[6];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) recvbuf;
	args[2] = (AislinnArgType) count;
	args[3] = (AislinnArgType) datatype;
	args[4] = (AislinnArgType) op;
	args[5] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Scan", args, 6);
	return 0;
}

int MPI_Allgather(const void *sendbuf, int sendcount, MPI_Datatype sendtype,
                  void *recvbuf, int recvcount, MPI_Datatype recvtype,
                  MPI_Comm comm)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcount;
	args[5] = (AislinnArgType) recvtype;
	args[6] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Allgather", args, 7);
	return 0;
}

int MPI_Alltoall(const void *sendbuf, int sendcount, MPI_Datatype sendtype,
                 void *recvbuf, int recvcount, MPI_Datatype recvtype,
                 MPI_Comm comm)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcount;
	args[5] = (AislinnArgType) recvtype;
	args[6] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Alltoall", args, 7);
	return 0;
}

int MPI_Alltoallv(const void *sendbuf, const int *sendcounts,
                  const int *sdispls, MPI_Datatype sendtype, void *recvbuf,
                  const int *recvcounts, const int *rdispls, MPI_Datatype recvtype,
                  MPI_Comm comm)
{
	AislinnArgType args[9];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcounts;
	args[2] = (AislinnArgType) sdispls;
	args[3] = (AislinnArgType) sendtype;
	args[4] = (AislinnArgType) recvbuf;
	args[5] = (AislinnArgType) recvcounts;
	args[6] = (AislinnArgType) rdispls;
	args[7] = (AislinnArgType) recvtype;
	args[8] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Alltoallv", args, 9);
	return 0;
}

int MPI_Allgatherv(const void *sendbuf, int sendcount, MPI_Datatype sendtype,
                   void *recvbuf, const int *recvcounts, const int *displs,
                   MPI_Datatype recvtype, MPI_Comm comm)
{
	AislinnArgType args[8];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcounts;
	args[5] = (AislinnArgType) displs;
	args[6] = (AislinnArgType) recvtype;
	args[7] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Allgatherv", args, 8);
	return 0;
}

int MPI_Igather(const void *sendbuf,
                int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf,
                int recvcount,
                MPI_Datatype recvtype,
                int root,
                MPI_Comm comm,
                MPI_Request *request)
{
	AislinnArgType args[9];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcount;
	args[5] = (AislinnArgType) recvtype;
	args[6] = (AislinnArgType) root;
	args[7] = (AislinnArgType) comm;
	args[8] = (AislinnArgType) request;
	aislinn_call_args("MPI_Igather", args, 9);
	return 0;
}

int MPI_Igatherv(const void *sendbuf,
                int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf,
                const int recvcounts[],
                const int displs[],
                MPI_Datatype recvtype,
                int root,
                MPI_Comm comm,
                MPI_Request *request)
{
	AislinnArgType args[10];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcounts;
	args[5] = (AislinnArgType) displs;
	args[6] = (AislinnArgType) recvtype;
	args[7] = (AislinnArgType) root;
	args[8] = (AislinnArgType) comm;
	args[9] = (AislinnArgType) request;
	aislinn_call_args("MPI_Igatherv", args, 10);
	return 0;
}

int MPI_Iscatter(const void *sendbuf,
		int sendcount,
		MPI_Datatype sendtype,
		void *recvbuf,
		int recvcount,
		MPI_Datatype recvtype,
		int root,
		MPI_Comm comm,
		MPI_Request *request)
{
	AislinnArgType args[9];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcount;
	args[2] = (AislinnArgType) sendtype;
	args[3] = (AislinnArgType) recvbuf;
	args[4] = (AislinnArgType) recvcount;
	args[5] = (AislinnArgType) recvtype;
	args[6] = (AislinnArgType) root;
	args[7] = (AislinnArgType) comm;
	args[8] = (AislinnArgType) request;
	aislinn_call_args("MPI_Iscatter", args, 9);
	return 0;
}

int MPI_Iscatterv(const void *sendbuf,
		const int sendcounts[],
		const int displs[],
		MPI_Datatype sendtype,
		void *recvbuf,
		int recvcount,
		MPI_Datatype recvtype,
		int root,
		MPI_Comm comm,
		MPI_Request *request)
{
	AislinnArgType args[10];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) sendcounts;
	args[2] = (AislinnArgType) displs;
	args[3] = (AislinnArgType) sendtype;
	args[4] = (AislinnArgType) recvbuf;
	args[5] = (AislinnArgType) recvcount;
	args[6] = (AislinnArgType) recvtype;
	args[7] = (AislinnArgType) root;
	args[8] = (AislinnArgType) comm;
	args[9] = (AislinnArgType) request;
	aislinn_call_args("MPI_Iscatterv", args, 10);
	return 0;
}

int MPI_Ireduce(const void *sendbuf,
		void *recvbuf,
		int count,
		MPI_Datatype datatype,
		MPI_Op op,
		int root,
		MPI_Comm comm,
		MPI_Request *request)
{
	AislinnArgType args[8];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) recvbuf;
	args[2] = (AislinnArgType) count;
	args[3] = (AislinnArgType) datatype;
	args[4] = (AislinnArgType) op;
	args[5] = (AislinnArgType) root;
	args[6] = (AislinnArgType) comm;
	args[7] = (AislinnArgType) request;
	aislinn_call_args("MPI_Ireduce", args, 8);
	return 0;
}

int MPI_Iallreduce(void *sendbuf, void *recvbuf, int count,
    MPI_Datatype datatype, MPI_Op op, MPI_Comm comm, MPI_Request *request)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) sendbuf;
	args[1] = (AislinnArgType) recvbuf;
	args[2] = (AislinnArgType) count;
	args[3] = (AislinnArgType) datatype;
	args[4] = (AislinnArgType) op;
	args[5] = (AislinnArgType) comm;
	args[6] = (AislinnArgType) request;
	aislinn_call_args("MPI_Iallreduce", args, 7);
	return 0;
}

int MPI_Ibcast(void *buffer, int count, MPI_Datatype datatype,
		int root, MPI_Comm comm, MPI_Request *request)
{
	AislinnArgType args[6];
	args[0] = (AislinnArgType) buffer;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) root;
	args[4] = (AislinnArgType) comm;
	args[5] = (AislinnArgType) request;
	aislinn_call_args("MPI_Ibcast", args, 6);
	return 0;
}

int MPI_Comm_split(MPI_Comm comm, int color, int key, MPI_Comm *newcomm)
{
	aislinn_call_4(
		"MPI_Comm_split",
		(AislinnArgType) comm,
		(AislinnArgType) color,
		(AislinnArgType) key,
		(AislinnArgType) newcomm);
	return 0;
}

int MPI_Comm_free(MPI_Comm *comm)
{
	aislinn_call_1(
		"MPI_Comm_free",
		(AislinnArgType) comm);
	return 0;
}

double MPI_Wtime() {
	// Dummy version
	return 0.0;
}

#endif // __AISLINN_MPI_H
