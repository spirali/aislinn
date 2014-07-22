#include <aislinn.h>
#include <stdio.h>

int global = 210;
int main() {
	aislinn_call_1("Hello", (AislinnArgType) &global);
	aislinn_call_1("Hello", (AislinnArgType) &global);
	return 0;
}
