#include <aislinn.h>
#include <stdio.h>

int main() {
	int local = 210;
	// Call1
	aislinn_call_1("Hello", (AislinnArgType) &local);
	return 0;
}
