
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
		int MPI_ERROR;
	} MPI_Status;

typedef int MPI_Datatype;
typedef int MPI_Op;

typedef int MPI_Fint;
typedef int MPI_Errhandler;
typedef int MPI_Info;
typedef int MPI_Group;
typedef unsigned long MPI_Aint;

/* Constants */
#define MPI_UNDEFINED     -0x0BEFBEEF
#define MPI_SUCCESS       0

#define MPI_DATATYPE_NULL (MPI_Datatype) 0xFF00100
#define MPI_PACKED (MPI_Datatype) 0xFF00101
#define MPI_BYTE (MPI_Datatype) 0xFF00102
#define MPI_CHAR (MPI_Datatype) 0xFF00103
#define MPI_UNSIGNED_CHAR (MPI_Datatype) 0xFF00104
#define MPI_SIGNED_CHAR (MPI_Datatype) 0xFF00105
#define MPI_WCHAR (MPI_Datatype) 0xFF00106
#define MPI_SHORT (MPI_Datatype) 0xFF00107
#define MPI_UNSIGNED_SHORT (MPI_Datatype) 0xFF00108
#define MPI_INT (MPI_Datatype) 0xFF00109
#define MPI_UNSIGNED (MPI_Datatype) 0xFF0010A
#define MPI_LONG (MPI_Datatype) 0xFF0010B
#define MPI_UNSIGNED_LONG (MPI_Datatype) 0xFF0010C
#define MPI_LONG_LONG_INT (MPI_Datatype) 0xFF0010D
#define MPI_LONG_LONG (MPI_Datatype) 0xFF0010D // Synonym to MPI_LONG_LONG_INT
#define MPI_UNSIGNED_LONG_LONG (MPI_Datatype) 0xFF0010E
#define MPI_FLOAT (MPI_Datatype) 0xFF0010F
#define MPI_DOUBLE (MPI_Datatype) 0xFF00110
#define MPI_LONG_DOUBLE (MPI_Datatype) 0xFF00111
#define MPI_FLOAT_INT (MPI_Datatype) 0xFF00112
#define MPI_DOUBLE_INT (MPI_Datatype) 0xFF00113
#define MPI_LONG_INT (MPI_Datatype) 0xFF00114
#define MPI_2INT (MPI_Datatype) 0xFF00115
#define MPI_SHORT_INT (MPI_Datatype) 0xFF00116
#define MPI_LONG_DOUBLE_INT (MPI_Datatype) 0xFF00117

static const MPI_Op MPI_OP_NULL = 0xDD00100;
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

#define MPI_ERRORS_ARE_FATAL ((MPI_Errhandler)0x0EE00100)
#define MPI_ERRORS_RETURN    ((MPI_Errhandler)0x0EE00101)

#define MPI_COMM_NULL ((MPI_Comm) 0x0000CC00)
#define MPI_COMM_SELF ((MPI_Comm) 0x0000CC01)
#define MPI_COMM_WORLD ((MPI_Comm) 0x0000CC02)


#define MPI_BOTTOM         ((void*) 0)

#define MPI_ERR_BUFFER    1
#define MPI_ERR_COUNT     2
#define MPI_ERR_TYPE      3
#define MPI_ERR_TAG       4
#define MPI_ERR_COMM      5
#define MPI_ERR_RANK      6
#define MPI_ERR_ROOT      7
#define MPI_ERR_GROUP     8
#define MPI_ERR_OP        9
#define MPI_ERR_REQUEST   19
#define MPI_ERR_IN_STATUS 17
#define MPI_ERR_PENDING   18
#define MPI_ERR_FILE        0x00001001
#define MPI_ERR_ACCESS      0x00001002
#define MPI_ERR_AMODE       0x00001003
#define MPI_ERR_BAD_FILE    0x00001004
#define MPI_ERR_FILE_EXISTS 0x00001005
#define MPI_ERR_FILE_IN_USE 0x00001006
#define MPI_ERR_NO_SPACE    0x00001007
#define MPI_ERR_NO_SUCH_FILE 0x00001008
#define MPI_ERR_IO          0x00001009
#define MPI_ERR_READ_ONLY   0x0000100A
#define MPI_ERR_CONVERSION  0x0000100B
#define MPI_ERR_DUP_DATAREP 0x0000100C
#define MPI_ERR_UNSUPPORTED_DATAREP   0x0000100D

#define MPI_MAX_ERROR_STRING   512

#define MPI_INFO_NULL ((MPI_Info)0x99000000)
#define MPI_INFO_ENV ((MPI_Info)0x99000001)

#define MPI_STATUS_IGNORE ((MPI_Status*) 0)
#define MPI_STATUSES_IGNORE ((MPI_Status*) 0)
#define MPI_ANY_SOURCE -0x0000AA00
#define MPI_ANY_TAG -0x0000BB00
#define MPI_PROC_NULL -0x0000CC00
#define MPI_REQUEST_NULL ((MPI_Request) -0x0000DD00)
#define MPI_GROUP_NULL ((MPI_Group) -0x0000EE00)
#define MPI_KEYVAL_INVALID -0x0000FF00

#define MPI_COMM_NULL_COPY_FN ((MPI_Comm_copy_attr_function*)0)
#define MPI_COMM_NULL_DELETE_FN ((MPI_Comm_delete_attr_function*)0)

#define MPI_Comm_c2f(comm) (MPI_Fint)(comm)
#define MPI_Comm_f2c(comm) (MPI_Comm)(comm)
#define MPI_Type_c2f(datatype) (MPI_Fint)(datatype)
#define MPI_Type_f2c(datatype) (MPI_Datatype)(datatype)
#define MPI_Group_c2f(group) (MPI_Fint)(group)
#define MPI_Group_f2c(group) (MPI_Group)(group)

#define MPI_COMBINER_DUP 0x09000100
#define MPI_COMBINER_CONTIGUOUS 0x09000101

#define MPI_TAG_UB 0x02200101
#define MPI_IN_PLACE ((void *) -1)

/* Constants for MPI_Comm_compare */
#define MPI_UNEQUAL   0
#define MPI_SIMILAR   1
#define MPI_CONGRUENT 2
#define MPI_IDENT     3

#define MPI_MAX_PROCESSOR_NAME 128

/* Functions prototypes */
typedef void (MPI_Comm_errhandler_function)(MPI_Comm *, int *, ...);
typedef void (MPI_Handler_function) (MPI_Comm *, int *, ... );
typedef void (MPI_User_function) (void *, void *, int *, MPI_Datatype * );

typedef int MPI_Comm_copy_attr_function(
	MPI_Comm oldcomm,
	int comm_keyval,
	void *extra_state,
	void *attribute_val_in,
	void *attribute_val_out,
	int *flag);

typedef int MPI_Comm_delete_attr_function(
		MPI_Comm comm,
		int comm_keyval,
		void *attribute_val,
		void *extra_state);

static inline int MPI_Get_address(const void *location, MPI_Aint *address) {
	*address = (MPI_Aint) location;
	return MPI_SUCCESS;
	// the at the end semicolon is necessary for buildhelper.py
}; 

int MPI_Init(int *argc, char ***argv);

int MPI_Initialized(int *flag);

int MPI_Start(MPI_Request *request);

int MPI_Startall(int count, MPI_Request array_of_requests[]);

int MPI_Request_free(MPI_Request *request);

int MPI_Finalize();

int MPI_Finalized(int *flag);

int MPI_Comm_rank(MPI_Comm comm, int *rank);

int MPI_Comm_size(MPI_Comm comm, int *size);

int MPI_Get_count(
	const MPI_Status *status, MPI_Datatype datatype, int *count);

int MPI_Send(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm);

int MPI_Bsend(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm);

int MPI_Ssend(const void *buf,int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm);

int MPI_Rsend(const void *buf, int count, MPI_Datatype datatype, int dest, int tag,
              MPI_Comm comm);

int MPI_Isend(const void *buf, int count, MPI_Datatype datatype, int dest,
    int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Issend(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Ibsend(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Irsend(const void *buf, int count, MPI_Datatype datatype, int dest, int tag,
	MPI_Comm comm, MPI_Request *request);

int MPI_Recv(void *buf, int count, MPI_Datatype datatype,
	int source, int tag, MPI_Comm comm, MPI_Status *status);

int MPI_Irecv(void *buf, int count, MPI_Datatype datatype,
	int source, int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Recv_init(void *buf, int count, MPI_Datatype datatype, int source,
	int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Send_init(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Ssend_init(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Bsend_init(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Rsend_init(const void *buf, int count, MPI_Datatype datatype, int dest,
	int tag, MPI_Comm comm, MPI_Request *request);

int MPI_Probe(int source, int tag, MPI_Comm comm, MPI_Status *status);

int MPI_Iprobe(
	int source, int tag, MPI_Comm comm, int *flag, MPI_Status *status);

int MPI_Wait(MPI_Request *request, MPI_Status *status);

int MPI_Waitall(int count, MPI_Request array_of_requests[],
	MPI_Status array_of_statuses[]);

int MPI_Waitany(int count, MPI_Request array_of_requests[], int *index,
	MPI_Status *status);

int MPI_Test(MPI_Request *request, int *flag, MPI_Status *status);

int MPI_Testall(int count, MPI_Request array_of_requests[], int *flag,
               MPI_Status array_of_statuses[]);

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

int MPI_Reduce_scatter(const void *sendbuf,
		       void *recvbuf,
		       const int *recvcnts,
		       MPI_Datatype datatype,
		       MPI_Op op,
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

int MPI_Comm_dup(MPI_Comm comm, MPI_Comm *newcomm);

int MPI_Comm_free(MPI_Comm *comm);

int MPI_Comm_compare(MPI_Comm comm1, MPI_Comm comm2, int *result);

int MPI_Type_size(MPI_Datatype datatype, int *size);

int MPI_Type_commit(MPI_Datatype *datatype);

int MPI_Comm_create_keyval(
  MPI_Comm_copy_attr_function *comm_copy_attr_fn,
  MPI_Comm_delete_attr_function *comm_delete_attr_fn,
  int *comm_keyval,
  void *extra_state
);

int MPI_Comm_get_attr(
  MPI_Comm comm,
  int comm_keyval,
  void *attribute_val,
  int *flag
);

int MPI_Comm_set_attr(
  MPI_Comm comm,
  int comm_keyval,
  void *attribute_val
);

int MPI_Comm_free_keyval(
  int *comm_keyval
);

int MPI_Comm_delete_attr(MPI_Comm comm, int comm_keyval);

int MPI_Type_contiguous(int count, MPI_Datatype oldtype, MPI_Datatype *newtype);

int MPI_Type_indexed(int count,
                    const int *array_of_blocklengths,
                    const int *array_of_displacements,
                    MPI_Datatype oldtype,
                    MPI_Datatype *newtype);

int MPI_Type_create_hindexed(int count,
                    const int *array_of_blocklengths,
                    const MPI_Aint *array_of_displacements,
                    MPI_Datatype oldtype,
                    MPI_Datatype *newtype);

int MPI_Type_vector(
	int count, int blocklength, int stride,
	MPI_Datatype oldtype, MPI_Datatype *newtype);

int MPI_Type_hvector(
	int count, int blocklength, int stride,
	MPI_Datatype oldtype, MPI_Datatype *newtype);

int MPI_Type_create_struct(int count,
	const int *array_of_blocklengths,
	const MPI_Aint *array_of_displacements,
	const MPI_Datatype *array_of_types,
	MPI_Datatype *newtype);

int MPI_Type_free(MPI_Datatype *datatype);

int MPI_Abort(MPI_Comm comm, int errorcode);

int MPI_Dims_create(int nnodes, int ndims, int dims[]);

int MPI_Comm_set_errhandler(MPI_Comm comm, MPI_Errhandler errhandler);

int MPI_Comm_group(MPI_Comm comm, MPI_Group *group);

int MPI_Comm_create(MPI_Comm comm, MPI_Group group, MPI_Comm *newcomm);

int MPI_Group_free(MPI_Group *group);

int MPI_Group_size(MPI_Group group, int *size);

int MPI_Group_incl(MPI_Group group, int n,
	const int ranks[], MPI_Group *newgroup);

int MPI_Group_compare(MPI_Group group1, MPI_Group group2,
	int *result);

int MPI_Op_create(MPI_User_function *user_fn, int commute, MPI_Op *op);

int MPI_Op_free(MPI_Op *op);

int MPI_Comm_create_errhandler(
  MPI_Comm_errhandler_function *function,
  MPI_Errhandler *errhandler
);

int MPI_Errhandler_create(
	MPI_Handler_function *function, MPI_Errhandler *errhandler);
int MPI_Errhandler_set(MPI_Comm comm, MPI_Errhandler errhandler);
int MPI_Errhandler_get(MPI_Comm comm, MPI_Errhandler *errhandler);
int MPI_Errhandler_free(MPI_Errhandler *errhandler);

int MPI_Cancel(MPI_Request *request);

int MPI_Get_processor_name(char *name, int *resultlen);

/* ----------------------------------------------------------------------------
/  DUMMY FUNCTIONS
/  --------------------------------------------------------------------------*/

double MPI_Wtime();

/* ----------------------------------------------------------------------------
/  DEPRECATED INTERFACE
/  --------------------------------------------------------------------------*/

typedef MPI_Comm_errhandler_function MPI_Comm_errhandler_fn;
typedef MPI_Comm_delete_attr_function MPI_Delete_function;
typedef MPI_Comm_copy_attr_function MPI_Copy_function;

#define MPI_NULL_COPY_FN   ((MPI_Copy_function *)0)
#define MPI_NULL_DELETE_FN ((MPI_Delete_function *)0)

int MPI_Keyval_create(
  MPI_Copy_function *comm_copy_attr_fn,
  MPI_Delete_function *comm_delete_attr_fn,
  int *comm_keyval,
  void *extra_state
);

int MPI_Attr_get(
	MPI_Comm comm, int comm_keyval, void *attribute_val, int *flag);

int MPI_Attr_put(MPI_Comm comm, int comm_keyval, void *attribute_val);

int MPI_Attr_delete(MPI_Comm comm, int keyval);

int MPI_Keyval_free(int *comm_keyval);

static inline int MPI_Address(const void *location, MPI_Aint *address) {
	return MPI_Get_address(location, address);
};

int MPI_Type_hindexed(
	int count,
	const int *array_of_blocklengths,
	const MPI_Aint *array_of_displacements,
	MPI_Datatype oldtype,
	MPI_Datatype *newtype);

int MPI_Type_struct(int count,
	const int *array_of_blocklengths,
	const MPI_Aint *array_of_displacements,
	const MPI_Datatype *array_of_types,
	MPI_Datatype *newtype);

int MPI_Error_string(int errorcode, char *string, int *resultlen);

#ifdef __cplusplus
}
#endif // __cplusplus

#endif // __AISLINN_MPI_H
