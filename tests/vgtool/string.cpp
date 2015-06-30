#include <aislinn.h>
#include <stdlib.h>
#include <string.h>
int main() {
	const char *s1 = "This is\n my\n string!";
	aislinn_call_1("Hello", (AislinnArgType) s1);

	// vvv HERE is error, too small buffer (missing +1)
	char *s2 = (char*) malloc(strlen(s1));
	memcpy(s2, s1, strlen(s1));
	aislinn_call_1("Hello", (AislinnArgType) s2);
	free(s2);
	return 0;
}
