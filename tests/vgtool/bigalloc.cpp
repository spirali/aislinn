#include <stdlib.h>
#include <aislinn.h>
#include <string.h>

int main() {
	const size_t size1 = 78 * 1024 * 1024 + 17;
	void *mem_pre = malloc(123);
	void *mem = malloc(size1);
	memset(mem, 'X', size1);
	aislinn_call_1("size", (AislinnArgType) size1);
	aislinn_call_1("mem", (AislinnArgType) mem);
	free(mem_pre);
	free(mem);
	aislinn_call_0("end");
	return 0;
}
