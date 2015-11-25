#include <stdio.h>

#include <aislinn.h>
#include <stdio.h>
#include <alloca.h>
#include <memory.h>

void f()
{
	size_t size = 500 * 1024;
	void *data = alloca(size);
	memset(data, 0xaa, size);
	aislinn_call_1("Second-a", (AislinnArgType) data);
	memset(data, 0xbb, size);
	aislinn_call_1("Second-b", (AislinnArgType) data);
}

int main() {
	aislinn_call_0("First");
	f();
	aislinn_call_0("Third");
	return 0;
}
