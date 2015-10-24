#include <stdio.h>

#include <aislinn.h>
#include <stdio.h>
#include <alloca.h>
#include <memory.h>

int main() {
	int size = 1024 * 500;
	char tmp[size];
	for (int i = 0; i < size; i++) {
		tmp[i] = i;
	}
	aislinn_call_0("First");
	return 0;
}
