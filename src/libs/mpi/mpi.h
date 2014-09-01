
#ifndef __AISLINN_MPI_H
#define __AISLINN_MPI_H

#include "aislinn.h"

#ifdef __cplusplus
extern "C" {
#endif // __cplusplus

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

typedef int MPI_Fint;

/* Constants */
static const int MPI_UNDEFINED = -0x0BEFBEEF;

static const MPI_Comm MPI_COMM_NULL = 0x0000CC00;
static const MPI_Comm MPI_COMM_SELF = 0x0000CC01;
static const MPI_Comm MPI_COMM_WORLD = 0x0000CC02;

static const MPI_Datatype MPI_PACKED = 0xFF00101;
static const MPI_Datatype MPI_BYTE = 0xFF00102;
static const MPI_Datatype MPI_CHAR = 0xFF00103;
static const MPI_Datatype MPI_UNSIGNED_CHAR = 0xFF00104;
static const MPI_Datatype MPI_SIGNED_CHAR = 0xFF00105;
static const MPI_Datatype MPI_WCHAR = 0xFF00106;
static const MPI_Datatype MPI_SHORT = 0xFF00107;
static const MPI_Datatype MPI_UNSIGNED_SHORT = 0xFF00108;
static const MPI_Datatype MPI_INT = 0xFF00109;
static const MPI_Datatype MPI_UNSIGNED = 0xFF0010A;
static const MPI_Datatype MPI_LONG = 0xFF0010B;
static const MPI_Datatype MPI_UNSIGNED_LONG = 0xFF0010C;
static const MPI_Datatype MPI_LONG_LONG_INT = 0xFF0010D;
static const MPI_Datatype MPI_UNSIGNED_LONG_LONG = 0xFF0010E;
static const MPI_Datatype MPI_FLOAT = 0xFF0010F;
static const MPI_Datatype MPI_DOUBLE = 0xFF00110;
static const MPI_Datatype MPI_LONG_DOUBLE = 0xFF00111;
static const MPI_Datatype MPI_FLOAT_INT = 0xFF00112;
static const MPI_Datatype MPI_DOUBLE_INT = 0xFF00113;
static const MPI_Datatype MPI_LONG_INT = 0xFF00114;
static const MPI_Datatype MPI_2INT = 0xFF00115;
static const MPI_Datatype MPI_SHORT_INT = 0xFF00116;
static const MPI_Datatype MPI_LONG_DOUBLE_INT = 0xFF00117;

static const MPI_Op MPI_MAX = 0xDD00101;
static const MPI_Op MPI_MIN = 0xDD00102;
static const MPI_Op MPI_SUM = 0xDD00103;
static const MPI_Op MPI_PROD = 0xDD00104;
static const MPI_Op MPI_LAND = 0xDD00105;
static const MPI_Op MPI_BAND = 0xDD00106;
static const MPI_Op MPI_LOR = 0xDD00107;
static const MPI_Op MPI_BOR = 0xDD00109;
static const MPI_Op MPI_LXOR = 0xDD0010A;
static const MPI_Op MPI_BXOR = 0xDD0010B;
static const MPI_Op MPI_MINLOC = 0xDD0010C;
static const MPI_Op MPI_MAXLOC = 0xDD0010D;

#define MPI_STATUS_IGNORE ((MPI_Status*) 0)
#define MPI_STATUSES_IGNORE ((MPI_Status*) 0)
#define MPI_ANY_SOURCE -0x00AA00
#define MPI_ANY_TAG -0x00BB00

void MPI_Init(int *argc, char ***argv);

int MPI_Finalize();

int MPI_Comm_rank(MPI_Comm comm, int *rank);

int MPI_Comm_size(MPI_Comm comm, int *size);

int MPI_Get_count(
	const MPI_Status *status, MPI_Datatype datatype, int *count);

int MPI_Send(void *buf, int count, MPI_Datatype datatype, int dest,
    int tag, MPI_Comm comm);

int MPI_Isend(void *buf, int count, MPI_Datatype datatype, int dest,
    int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Recv(void *buf, int count, MPI_Datatype datatype,
        int source, int tag, MPI_Comm comm, MPI_Status *status);

int MPI_Irecv(void *buf, int count, MPI_Datatype datatype,
        int source, int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Wait(MPI_Request *request, MPI_Status *status);

int MPI_Waitall(int count, MPI_Request array_of_requests[],
               MPI_Status array_of_statuses[]);

int MPI_Test(MPI_Request *request, int *flag, MPI_Status *status);

int MPI_Barrier(MPI_Comm comm);

int MPI_Gather(const void *sendbuf,
                int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf,
                int recvcount,
                MPI_Datatype recvtype,
                int root,
                MPI_Comm comm);

int MPI_Gatherv(const void *sendbuf,
                int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf,
                const int recvcounts[],
                const int displs[],
                MPI_Datatype recvtype,
                int root,
                MPI_Comm comm);

int MPI_Scatter(const void *sendbuf,
		int sendcount,
		MPI_Datatype sendtype,
		void *recvbuf,
		int recvcount,
		MPI_Datatype recvtype,
		int root,
		MPI_Comm comm);

int MPI_Scatterv(const void *sendbuf,
		const int sendcounts[],
		const int displs[],
		MPI_Datatype sendtype,
		void *recvbuf,
		int recvcount,
		MPI_Datatype recvtype,
		int root,
		MPI_Comm comm);

int MPI_Reduce(const void *sendbuf,
		void *recvbuf,
		int count,
		MPI_Datatype datatype,
		MPI_Op op,
		int root,
		MPI_Comm comm);

int MPI_Allreduce(void *sendbuf, void *recvbuf, int count,
    MPI_Datatype datatype, MPI_Op op, MPI_Comm comm);

int MPI_Bcast(void *buffer, int count, MPI_Datatype datatype,
		int root, MPI_Comm comm);

int MPI_Ibarrier(MPI_Comm comm, MPI_Request *request);

int MPI_Scan(const void *sendbuf, void *recvbuf, int count, MPI_Datatype datatype,
             MPI_Op op, MPI_Comm comm);

int MPI_Allgather(const void *sendbuf, int sendcount, MPI_Datatype sendtype,
                  void *recvbuf, int recvcount, MPI_Datatype recvtype,
                  MPI_Comm comm);

int MPI_Alltoall(const void *sendbuf, int sendcount, MPI_Datatype sendtype,
                 void *recvbuf, int recvcount, MPI_Datatype recvtype,
                 MPI_Comm comm);

int MPI_Alltoallv(const void *sendbuf, const int *sendcounts,
                  const int *sdispls, MPI_Datatype sendtype, void *recvbuf,
                  const int *recvcounts, const int *rdispls, MPI_Datatype recvtype,
                  MPI_Comm comm);

int MPI_Allgatherv(const void *sendbuf, int sendcount, MPI_Datatype sendtype,
                   void *recvbuf, const int *recvcounts, const int *displs,
                   MPI_Datatype recvtype, MPI_Comm comm);

int MPI_Igather(const void *sendbuf,
                int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf,
                int recvcount,
                MPI_Datatype recvtype,
                int root,
                MPI_Comm comm,
                MPI_Request *request);

int MPI_Igatherv(const void *sendbuf,
                int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf,
                const int recvcounts[],
                const int displs[],
                MPI_Datatype recvtype,
                int root,
                MPI_Comm comm,
                MPI_Request *request);

int MPI_Iscatter(const void *sendbuf,
		int sendcount,
		MPI_Datatype sendtype,
		void *recvbuf,
		int recvcount,
		MPI_Datatype recvtype,
		int root,
		MPI_Comm comm,
		MPI_Request *request);

int MPI_Iscatterv(const void *sendbuf,
		const int sendcounts[],
		const int displs[],
		MPI_Datatype sendtype,
		void *recvbuf,
		int recvcount,
		MPI_Datatype recvtype,
		int root,
		MPI_Comm comm,
		MPI_Request *request);

int MPI_Ireduce(const void *sendbuf,
		void *recvbuf,
		int count,
		MPI_Datatype datatype,
		MPI_Op op,
		int root,
		MPI_Comm comm,
		MPI_Request *request);

int MPI_Iallreduce(void *sendbuf, void *recvbuf, int count,
    MPI_Datatype datatype, MPI_Op op, MPI_Comm comm, MPI_Request *request);

int MPI_Ibcast(void *buffer, int count, MPI_Datatype datatype,
		int root, MPI_Comm comm, MPI_Request *request);

int MPI_Comm_split(MPI_Comm comm, int color, int key, MPI_Comm *newcomm);

int MPI_Comm_free(MPI_Comm *comm);

double MPI_Wtime();

#ifdef __cplusplus
}
#endif // __cplusplus

#endif // __AISLINN_MPI_H
