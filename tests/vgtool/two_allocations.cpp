#include <stdlib.h>
#include <aislinn.h>
#include <string.h>

int main() {
	const size_t size1 = 10;
	const size_t size2 = 100000;
	void *mem1 = malloc(size1);
	void *mem2 = malloc(size2);
	memset(mem1, 'X', size1);
	memset(mem2, 'Y', size2);
	aislinn_call_1("first", (AislinnArgType) mem1);
	aislinn_call_1("second", (AislinnArgType) mem2);
	free(mem1);
	free(mem2);
	return 0;
}
