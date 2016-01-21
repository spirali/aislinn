#include <stdio.h>

#include <aislinn.h>
#include <stdio.h>
#include <alloca.h>
#include <memory.h>

__attribute__ ((noinline)) void g() {
	int b;
	aislinn_call_1("Second", (AislinnArgType) &b);
}

int main() {
	aislinn_call_0("First");
	g();
}
