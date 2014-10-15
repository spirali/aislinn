#include <aislinn.h>

void do_a(int value)
{
	AislinnArgType args[1] = { value };
	aislinn_call_args("A", args, 1);

}

void do_b(int value)
{
	AislinnArgType args[1] = { value };
	aislinn_call_args("B", args, 1);
}

int main() {
	aislinn_call_2("INIT",  (AislinnArgType) &do_a, 
			        (AislinnArgType) &do_b);
	AislinnArgType args[1];
	aislinn_call_args("RUN", args, 0);
	return 0;
}
