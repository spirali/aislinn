#include <mpi.h>
#include <stdlib.h>
#include <stdio.h>

#define INTERVAL 1
#define RESULTS 2
#define FINISH 3

int size;
int limit;

int parse_args(int argc, char **argv)
{
	if (argc != 3) {
		fprintf(stderr, "%s <size> <limit>\n", argv[0]);
		return 0;
	}
	if (sscanf(argv[1], "%i", &size) < 0) {
		fprintf(stderr, "invalid first argument\n");
		return 0;
	}
	if (sscanf(argv[2], "%i", &limit) < 0) {
		fprintf(stderr, "invalid second argument\n");
		return 0;
	}
}

int is_prime(int n) {
	int i;

	if (n < 2 || n % 2 == 0) {
		return 0;
	}
	for (i = 3; i < n; i += 2) {
		if (n % i == 0) {
			return 0;
		}
	}
	return 1;
}

void manager(int workers) {
	MPI_Status status;
	int processed = 0;
	int finished = 0;
	int *result = (int*) malloc(sizeof(int) * size / 2);
	int data[2];
	int i;

	for (i = 0; i < limit / size; i++) {
	}

	for (i = 1; i < workers; i++) {
		data[0] = size * i + 1;
		data[1] = size * (i + 1);
		MPI_Send(data, 2, MPI_INT, i, INTERVAL, MPI_COMM_WORLD);
		processed++;
	}

	while(finished < workers - 1) {
		MPI_Recv(result, size / 2, MPI_INT, MPI_ANY_SOURCE, RESULTS, MPI_COMM_WORLD, &status);
		if (processed >= limit / size) {
			MPI_Send(data, 0, MPI_INT, status.MPI_SOURCE, FINISH, MPI_COMM_WORLD);
			finished++;
		} else {
			data[0] = size * processed + 1;
			data[1] = size * (processed + 1);
			MPI_Send(data, 2, MPI_INT, status.MPI_SOURCE, INTERVAL, MPI_COMM_WORLD);
			processed++;
		}
	}
	free(result);
}

void worker() {
	int interval[2];
	int *primes = (int*)malloc(sizeof(int) * size / 2);
	MPI_Status status;

	while(1) {
		MPI_Recv(interval, 2, MPI_INT, 0, MPI_ANY_TAG, MPI_COMM_WORLD, &status);
		if (status.MPI_TAG == INTERVAL) {
			int j = 0, i;
			for (i = interval[0]; i <= interval[1]; i++) {
				if (is_prime(i)) {
					primes[j++] = i;
				}
			}
			MPI_Send(primes, j, MPI_INT, 0, RESULTS, MPI_COMM_WORLD);
		} else {
			break;
		}
	}
	free(primes);
}


int main(int argc, char **argv)
{
	if (!parse_args(argc, argv)) {
		return 1;
	}
	MPI_Init(&argc, &argv);
	int rank;
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	int workers;
	MPI_Comm_size(MPI_COMM_WORLD, &workers);
	if (rank == 0) {
		manager(workers);
	} else {
		worker();
	}
	MPI_Finalize();
	return 0;
}
