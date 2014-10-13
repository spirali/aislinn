
#include "mpi.h"

int MPI_Init(int *argc, char ***argv)
{
	aislinn_call_0("MPI_Init");
	return MPI_SUCCESS;
}

int MPI_Initialized(int *flag)
{
	aislinn_call_1("MPI_Initialized", (AislinnArgType) flag);
	return MPI_SUCCESS;
}

int MPI_Finalize()
{
	aislinn_call_0("MPI_Finalize");
	return MPI_SUCCESS;
}

int MPI_Finalized(int *flag)
{
	aislinn_call_1("MPI_Finalized", (AislinnArgType) flag);
	return MPI_SUCCESS;
}

int MPI_Get_address(const void *location, MPI_Aint *address)
{
	*address = (MPI_Aint) location;
	return MPI_SUCCESS;
}

int MPI_Comm_rank(MPI_Comm comm, int *rank)
{
	aislinn_call_2(
		"MPI_Comm_rank",
		(AislinnArgType) comm,
		(AislinnArgType) rank);
	return MPI_SUCCESS;
}

int MPI_Comm_size(MPI_Comm comm, int *size)
{
	aislinn_call_2(
		"MPI_Comm_size",
		(AislinnArgType) comm,
		(AislinnArgType) size);
	return MPI_SUCCESS;
}

int MPI_Get_count(
        const MPI_Status *status, MPI_Datatype datatype, int *count)
{
	aislinn_call_3(
		"MPI_Get_count",
		(AislinnArgType) status,
		(AislinnArgType) datatype,
		(AislinnArgType) count);
	return MPI_SUCCESS;

}

int MPI_Send(const void *buf, int count, MPI_Datatype datatype, int dest,
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
	return MPI_SUCCESS;
}

int MPI_Ssend(const void *buf,int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm)
{
	AislinnArgType args[6];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) dest;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Ssend", args, 6);
	return MPI_SUCCESS;
}

int MPI_Bsend(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm)
{
	AislinnArgType args[6];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) dest;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Bsend", args, 6);
	return MPI_SUCCESS;
}

int MPI_Rsend(const void *buf, int count, MPI_Datatype datatype, int dest, int tag,
              MPI_Comm comm)
{
	AislinnArgType args[6];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) dest;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	aislinn_call_args("MPI_Rsend", args, 6);
	return MPI_SUCCESS;
}

int MPI_Isend(const void *buf, int count, MPI_Datatype datatype, int dest,
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
	return MPI_SUCCESS;
}

int MPI_Issend(const void *buf, int count, MPI_Datatype datatype, int dest,
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
	aislinn_call_args("MPI_Issend", args, 7);
	return MPI_SUCCESS;
}

int MPI_Ibsend(const void *buf, int count, MPI_Datatype datatype, int dest, int tag,
               MPI_Comm comm, MPI_Request *request)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) dest;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	args[6] = (AislinnArgType) request;
	aislinn_call_args("MPI_Ibsend", args, 7);
	return MPI_SUCCESS;
}

int MPI_Irsend(const void *buf, int count, MPI_Datatype datatype, int dest, int tag,
               MPI_Comm comm, MPI_Request *request)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) dest;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	args[6] = (AislinnArgType) request;
	aislinn_call_args("MPI_Irsend", args, 7);
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
}

int MPI_Recv_init(void *buf, int count, MPI_Datatype datatype, int source, 
                 int tag, MPI_Comm comm, MPI_Request *request)
{
	AislinnArgType args[7];
	args[0] = (AislinnArgType) buf;
	args[1] = (AislinnArgType) count;
	args[2] = (AislinnArgType) datatype;
	args[3] = (AislinnArgType) source;
	args[4] = (AislinnArgType) tag;
	args[5] = (AislinnArgType) comm;
	args[6] = (AislinnArgType) request;
	aislinn_call_args("MPI_Recv_init", args, 7);
	return MPI_SUCCESS;
}

int MPI_Send_init(const void *buf, int count, MPI_Datatype datatype, int dest,
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
	aislinn_call_args("MPI_Send_init", args, 7);
	return MPI_SUCCESS;
}

int MPI_Ssend_init(const void *buf, int count, MPI_Datatype datatype, int dest,
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
	aislinn_call_args("MPI_Ssend_init", args, 7);
	return MPI_SUCCESS;
}

int MPI_Bsend_init(const void *buf, int count, MPI_Datatype datatype, int dest,
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
	aislinn_call_args("MPI_Bsend_init", args, 7);
	return MPI_SUCCESS;
}

int MPI_Rsend_init(const void *buf, int count, MPI_Datatype datatype, int dest,
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
	aislinn_call_args("MPI_Rsend_init", args, 7);
	return MPI_SUCCESS;
}

int MPI_Start(MPI_Request *request)
{
	aislinn_call_1("MPI_Start",
		       (AislinnArgType) request);
	return MPI_SUCCESS;
}

int MPI_Startall(int count, MPI_Request array_of_requests[])
{
	aislinn_call_2("MPI_Startall",
			(AislinnArgType) count,
			(AislinnArgType) array_of_requests);
	return MPI_SUCCESS;
}

int MPI_Request_free(MPI_Request *request)
{
	aislinn_call_1("MPI_Request_free",
		       (AislinnArgType) request);
	return MPI_SUCCESS;
}

int MPI_Probe(int source, int tag, MPI_Comm comm, MPI_Status *status)
{
	aislinn_call_4("MPI_Probe",
			(AislinnArgType) source,
			(AislinnArgType) tag,
			(AislinnArgType) comm,
			(AislinnArgType) status);
	return MPI_SUCCESS;
}

int MPI_Iprobe(
	int source, int tag, MPI_Comm comm, int *flag, MPI_Status *status)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) source;
	args[1] = (AislinnArgType) tag;
	args[2] = (AislinnArgType) comm;
	args[3] = (AislinnArgType) flag;
	args[4] = (AislinnArgType) status;
	aislinn_call_args("MPI_Iprobe", args, 5);
	return MPI_SUCCESS;
}

int MPI_Wait(MPI_Request *request, MPI_Status *status)
{
	aislinn_call_2(
		"MPI_Wait",
		(AislinnArgType) request,
		(AislinnArgType) status);
	return MPI_SUCCESS;
}

int MPI_Waitall(int count, MPI_Request array_of_requests[],
               MPI_Status array_of_statuses[])
{
	aislinn_call_3(
		"MPI_Waitall",
		(AislinnArgType) count,
		(AislinnArgType) array_of_requests,
		(AislinnArgType) array_of_statuses);
	return MPI_SUCCESS;
}

int MPI_Waitany(int count, MPI_Request array_of_requests[], int *index,
	MPI_Status *status)
{
	aislinn_call_4(
		"MPI_Waitany",
		(AislinnArgType) count,
		(AislinnArgType) array_of_requests,
		(AislinnArgType) index,
		(AislinnArgType) status);
	return MPI_SUCCESS;
}

int MPI_Test(MPI_Request *request, int *flag, MPI_Status *status)
{
	aislinn_call_3(
		"MPI_Test",
		(AislinnArgType) request,
		(AislinnArgType) flag,
		(AislinnArgType) status);
	return MPI_SUCCESS;
}

int MPI_Testall(int count, MPI_Request array_of_requests[], int *flag,
               MPI_Status array_of_statuses[])
{
	aislinn_call_4(
		"MPI_Testall",
		(AislinnArgType) count,
		(AislinnArgType) array_of_requests,
		(AislinnArgType) flag,
		(AislinnArgType) array_of_statuses);
	return MPI_SUCCESS;
}

int MPI_Barrier(MPI_Comm comm)
{
	aislinn_call_1(
		"MPI_Barrier",
		(AislinnArgType) comm);
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
}

int MPI_Ibarrier(MPI_Comm comm, MPI_Request *request)
{
	aislinn_call_2(
		"MPI_Ibarrier",
		(AislinnArgType) comm,
		(AislinnArgType) request);
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
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
	return MPI_SUCCESS;
}

int MPI_Comm_split(MPI_Comm comm, int color, int key, MPI_Comm *newcomm)
{
	aislinn_call_4(
		"MPI_Comm_split",
		(AislinnArgType) comm,
		(AislinnArgType) color,
		(AislinnArgType) key,
		(AislinnArgType) newcomm);
	return MPI_SUCCESS;
}

int MPI_Comm_dup(MPI_Comm comm, MPI_Comm *newcomm)
{
	aislinn_call_2(
		"MPI_Comm_dup",
		(AislinnArgType) comm,
		(AislinnArgType) newcomm);
	return MPI_SUCCESS;

}

int MPI_Comm_free(MPI_Comm *comm)
{
	aislinn_call_1(
		"MPI_Comm_free",
		(AislinnArgType) comm);
	return MPI_SUCCESS;
}

int MPI_Comm_compare(MPI_Comm comm1, MPI_Comm comm2, int *result)
{
	aislinn_call_3(
		"MPI_Comm_compare",
		(AislinnArgType) comm1,
		(AislinnArgType) comm2,
		(AislinnArgType) result);
	return MPI_SUCCESS;
}

int MPI_Type_size(MPI_Datatype datatype, int *size)
{
	aislinn_call_2(
		"MPI_Type_size",
		(AislinnArgType) datatype,
		(AislinnArgType) size);
	return MPI_SUCCESS;

}

int MPI_Comm_create_keyval(
  MPI_Comm_copy_attr_function *comm_copy_attr_fn,
  MPI_Comm_delete_attr_function *comm_delete_attr_fn,
  int *comm_keyval,
  void *extra_state
)
{
	aislinn_call_4(
		"MPI_Comm_create_keyval",
		(AislinnArgType) comm_copy_attr_fn,
		(AislinnArgType) comm_copy_attr_fn,
		(AislinnArgType) comm_keyval,
		(AislinnArgType) extra_state);
	return MPI_SUCCESS;
}

int MPI_Comm_get_attr(
  MPI_Comm comm,
  int comm_keyval,
  void *attribute_val,
  int *flag)
{
	aislinn_call_4(
		"MPI_Comm_get_attr",
		(AislinnArgType) comm,
		(AislinnArgType) comm_keyval,
		(AislinnArgType) attribute_val,
		(AislinnArgType) flag);
	return MPI_SUCCESS;
}

int MPI_Comm_set_attr(
  MPI_Comm comm,
  int comm_keyval,
  void *attribute_val)
{
	aislinn_call_3(
		"MPI_Comm_set_attr",
		(AislinnArgType) comm,
		(AislinnArgType) comm_keyval,
		(AislinnArgType) attribute_val);
	return MPI_SUCCESS;
}

int MPI_Comm_free_keyval(int *comm_keyval)
{
	aislinn_call_1(
		"MPI_Comm_free_keyval",
		(AislinnArgType) comm_keyval);
	return MPI_SUCCESS;
}

int MPI_Comm_set_errhandler(MPI_Comm comm, MPI_Errhandler errhandler)
{
	aislinn_call_2(
		"MPI_Comm_set_errhandler",
		(AislinnArgType) comm,
		(AislinnArgType) errhandler);
	return MPI_SUCCESS;
}

int MPI_Abort(MPI_Comm comm, int errorcode)
{
	aislinn_call_2(
		"MPI_Abort",
		(AislinnArgType) comm,
		(AislinnArgType) errorcode);
	return MPI_SUCCESS;
}

int MPI_Type_contiguous(int count, MPI_Datatype oldtype, MPI_Datatype *newtype)
{
	aislinn_call_3(
		"MPI_Type_contiguous",
		(AislinnArgType) count,
		(AislinnArgType) oldtype,
		(AislinnArgType) newtype);
	return MPI_SUCCESS;
}

int MPI_Type_vector(
	int count, int blocklength, int stride,
	MPI_Datatype oldtype, MPI_Datatype *newtype)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) count;
	args[1] = (AislinnArgType) blocklength;
	args[2] = (AislinnArgType) stride;
	args[3] = (AislinnArgType) oldtype;
	args[4] = (AislinnArgType) newtype;
	aislinn_call_args("MPI_Type_vector", args, 5);
	return MPI_SUCCESS;
}

int MPI_Type_hvector(
	int count, int blocklength, int stride,
	MPI_Datatype oldtype, MPI_Datatype *newtype)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) count;
	args[1] = (AislinnArgType) blocklength;
	args[2] = (AislinnArgType) stride;
	args[3] = (AislinnArgType) oldtype;
	args[4] = (AislinnArgType) newtype;
	aislinn_call_args("MPI_Type_hvector", args, 5);
	return MPI_SUCCESS;
}

int MPI_Type_indexed(int count,
                    const int *array_of_blocklengths,
                    const int *array_of_displacements,
                    MPI_Datatype oldtype,
                    MPI_Datatype *newtype)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) count;
	args[1] = (AislinnArgType) array_of_blocklengths;
	args[2] = (AislinnArgType) array_of_displacements;
	args[3] = (AislinnArgType) oldtype;
	args[4] = (AislinnArgType) newtype;
	aislinn_call_args("MPI_Type_indexed", args, 5);
	return MPI_SUCCESS;
}

int MPI_Type_create_hindexed(

			  int count,
			  const int *array_of_blocklengths,
			  const MPI_Aint *array_of_displacements,
			  MPI_Datatype oldtype,
			  MPI_Datatype *newtype
)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) count;
	args[1] = (AislinnArgType) array_of_blocklengths;
	args[2] = (AislinnArgType) array_of_displacements;
	args[3] = (AislinnArgType) oldtype;
	args[4] = (AislinnArgType) newtype;
	aislinn_call_args("MPI_Type_create_hindexed", args, 5);
	return MPI_SUCCESS;
}


int MPI_Type_create_struct(int count,
    const int *array_of_blocklengths,
    const MPI_Aint *array_of_displacements,
    const MPI_Datatype *array_of_types,
    MPI_Datatype *newtype)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) count;
	args[1] = (AislinnArgType) array_of_blocklengths;
	args[2] = (AislinnArgType) array_of_displacements;
	args[3] = (AislinnArgType) array_of_types;
	args[4] = (AislinnArgType) newtype;
	aislinn_call_args("MPI_Type_create_struct", args, 5);
	return MPI_SUCCESS;
}

int MPI_Type_commit(MPI_Datatype *datatype)
{
	aislinn_call_1("MPI_Type_commit", (AislinnArgType) datatype);
	return MPI_SUCCESS;
}

int MPI_Type_free(MPI_Datatype *datatype)
{
	aislinn_call_1("MPI_Type_free", (AislinnArgType) datatype);
	return MPI_SUCCESS;
}

int MPI_Dims_create(int nnodes, int ndims, int dims[])
{
	aislinn_call_3("MPI_Dims_create",
		(AislinnArgType) nnodes,
		(AislinnArgType) ndims,
		(AislinnArgType) dims);
	return MPI_SUCCESS;
}

int MPI_Comm_group(MPI_Comm comm, MPI_Group *group)
{
	aislinn_call_2(
		"MPI_Comm_group", (AislinnArgType) comm, (AislinnArgType) group);
	return MPI_SUCCESS;
}

int MPI_Comm_create(MPI_Comm comm, MPI_Group group, MPI_Comm *newcomm)
{
	aislinn_call_3(
		"MPI_Comm_create",
		(AislinnArgType) comm,
		(AislinnArgType) group,
		(AislinnArgType) newcomm);
	return MPI_SUCCESS;
}

int MPI_Comm_create_errhandler(
  MPI_Comm_errhandler_function *function,
  MPI_Errhandler *errhandler
)
{
	aislinn_call_2(
		"MPI_Comm_create_errhandler",
		(AislinnArgType) function,
		(AislinnArgType) errhandler);
	return MPI_SUCCESS;
}

int MPI_Errhandler_create(
	MPI_Handler_function *function, MPI_Errhandler *errhandler)
{
	aislinn_call_2(
		"MPI_Errhandler_create",
		(AislinnArgType) function,
		(AislinnArgType) errhandler);
	return MPI_SUCCESS;

}

int MPI_Errhandler_set(MPI_Comm comm, MPI_Errhandler errhandler)
{
	aislinn_call_2(
		"MPI_Errhandler_set",
		(AislinnArgType) comm,
		(AislinnArgType) errhandler);
	return MPI_SUCCESS;
}

int MPI_Errhandler_get(MPI_Comm comm, MPI_Errhandler *errhandler)
{
	aislinn_call_2(
		"MPI_Errhandler_get",
		(AislinnArgType) comm,
		(AislinnArgType) errhandler);
	return MPI_SUCCESS;
}

int MPI_Errhandler_free(MPI_Errhandler *errhandler)
{
	aislinn_call_1(
		"MPI_Errhandler_free",
		(AislinnArgType) errhandler);
	return MPI_SUCCESS;
}

int MPI_Group_free(MPI_Group *group)
{
	aislinn_call_1(
		"MPI_Group_free", (AislinnArgType) group);
	return MPI_SUCCESS;
}

int MPI_Group_size(MPI_Group group, int *size)
{
	aislinn_call_2(
		"MPI_Group_size",
		(AislinnArgType) group,
		(AislinnArgType) size);
	return MPI_SUCCESS;
}

/* ----------------------------------------------------------------------------
/  DEPRECATED INTERFACE
/  --------------------------------------------------------------------------*/

int MPI_Keyval_create(
  MPI_Copy_function *comm_copy_attr_fn,
  MPI_Delete_function *comm_delete_attr_fn,
  int *comm_keyval,
  void *extra_state
)
{
	aislinn_call_4(
		"MPI_Keyval_create",
		(AislinnArgType) comm_copy_attr_fn,
		(AislinnArgType) comm_copy_attr_fn,
		(AislinnArgType) comm_keyval,
		(AislinnArgType) extra_state);
	return MPI_SUCCESS;
}

int MPI_Attr_get(
	MPI_Comm comm, int comm_keyval, void *attribute_val, int *flag)
{
	aislinn_call_4(
		"MPI_Attr_get",
		(AislinnArgType) comm,
		(AislinnArgType) comm_keyval,
		(AislinnArgType) attribute_val,
		(AislinnArgType) flag);
	return MPI_SUCCESS;
}

int MPI_Attr_put(
  MPI_Comm comm,
  int comm_keyval,
  void *attribute_val)
{
	aislinn_call_3(
		"MPI_Attr_put",
		(AislinnArgType) comm,
		(AislinnArgType) comm_keyval,
		(AislinnArgType) attribute_val);
	return MPI_SUCCESS;
}

int MPI_Attr_set(
  MPI_Comm comm,
  int comm_keyval,
  void *attribute_val)
{
	aislinn_call_3(
		"MPI_Attr_set",
		(AislinnArgType) comm,
		(AislinnArgType) comm_keyval,
		(AislinnArgType) attribute_val);
	return MPI_SUCCESS;
}


int MPI_Attr_delete(MPI_Comm comm, int comm_keyval)
{
	aislinn_call_2(
		"MPI_Attr_delete",
		(AislinnArgType) comm,
		(AislinnArgType) comm_keyval);
	return MPI_SUCCESS;
}

int MPI_Keyval_free(int *comm_keyval)
{
	aislinn_call_1(
		"MPI_Keyval_free",
		(AislinnArgType) comm_keyval);
	return MPI_SUCCESS;
}

int MPI_Type_hindexed(int count,
                    const int *array_of_blocklengths,
                    const MPI_Aint *array_of_displacements,
                    MPI_Datatype oldtype,
                    MPI_Datatype *newtype)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) count;
	args[1] = (AislinnArgType) array_of_blocklengths;
	args[2] = (AislinnArgType) array_of_displacements;
	args[3] = (AislinnArgType) oldtype;
	args[4] = (AislinnArgType) newtype;
	aislinn_call_args("MPI_Type_hindexed", args, 5);
	return MPI_SUCCESS;
}

int MPI_Type_struct(int count,
    const int *array_of_blocklengths,
    const MPI_Aint *array_of_displacements,
    const MPI_Datatype *array_of_types,
    MPI_Datatype *newtype)
{
	AislinnArgType args[5];
	args[0] = (AislinnArgType) count;
	args[1] = (AislinnArgType) array_of_blocklengths;
	args[2] = (AislinnArgType) array_of_displacements;
	args[3] = (AislinnArgType) array_of_types;
	args[4] = (AislinnArgType) newtype;
	aislinn_call_args("MPI_Type_struct", args, 5);
	return MPI_SUCCESS;
}

int MPI_Address(const void *location, MPI_Aint *address)
{
	return MPI_Get_address(location, address);
}

/* ----------------------------------------------------------------------------
/  Dummy functions
/  --------------------------------------------------------------------------*/

double MPI_Wtime()
{
	// Dummy version
	return 0.0;
}
