#include <aislinn.h>
#include <stdio.h>

int main() {
	aislinn_call_0("First");
	printf("Hello 1!\n");
	fflush(stdout);
	printf("Hello 2!\n");
	fflush(stdout);
	aislinn_call_0("Second");
	return 0;
}
