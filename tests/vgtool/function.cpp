#include <aislinn.h>

void do_a(int value)
{
	AislinnArgType args[1] = { value };
	aislinn_call("A", args, 1);

}

void do_b(int value)
{
	AislinnArgType args[1] = { value };
	aislinn_call("B", args, 1);
}

int main() {
	AislinnArgType args[2] = {
		(AislinnArgType) &do_a,
		(AislinnArgType) &do_b
	};
	aislinn_call("INIT", args, 2);
	aislinn_call_0("RUN");
	return 0;
}
