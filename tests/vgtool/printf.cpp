#include <stdio.h>

#include <aislinn.h>
#include <stdio.h>

int main() {
	aislinn_call_0("First");
	printf("Hello 1!\n");
	fflush(stdout);
	aislinn_call_0("Second");
	fclose(stdout);
	return 0;
}
