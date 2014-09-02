
#include "mpi.h"

void MPI_Init(int *argc, char ***argv) 
{
	aislinn_call_0("MPI_Init");
}

int MPI_Finalize() 
{
	// Currently do nothing
	return 0;
}

int MPI_Comm_rank(MPI_Comm comm, int *rank) 
{
	aislinn_call_2(
		"MPI_Comm_rank",
		(AislinnArgType) comm,
		(AislinnArgType) rank);
	return 0;
}

int MPI_Comm_size(MPI_Comm comm, int *size) 
{
	aislinn_call_2(
		"MPI_Comm_size",
		(AislinnArgType) comm,
		(AislinnArgType) size);
	return 0;
}

int MPI_Get_count(
        const MPI_Status *status, MPI_Datatype datatype, int *count) 
{
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

int MPI_Comm_dup(MPI_Comm comm, MPI_Comm *newcomm)
{
	aislinn_call_2(
		"MPI_Comm_dup",
		(AislinnArgType) comm,
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

double MPI_Wtime()
{
	// Dummy version
	return 0.0;
}
