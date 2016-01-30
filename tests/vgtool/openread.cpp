#include <aislinn.h>
#include <stdio.h>

int main()
{
	FILE *f = fopen("data", "r");
	int x, y;
	char tmp[100];
	if (2 != fscanf(f, "%i %i\n", &x, &y)) {
		return 1;
	}
	if (1 != fscanf(f, "%s\n", tmp)) {
		return 1;
	}

	fclose(f);

	AislinnArgType args[3];
	args[0] = x;
	args[1] = y;
	args[2] = (AislinnArgType) tmp;
	aislinn_call("first", args, 3);
	return 0;
}
