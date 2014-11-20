#include <aislinn.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	if (argc != 3) {
		return 1;
	}
	int *mem = (int*) malloc(atoi(argv[1]) * sizeof(int));
	aislinn_call_1("init", (AislinnArgType) mem);
	mem[atoi(argv[2])] = 0xBBBB;
	return 0;
}
