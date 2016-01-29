
#include <stdio.h>

int main()
{
	FILE *f = fopen("data", "w");
	fprintf(f, "Test\n");
	fclose(f);
}
