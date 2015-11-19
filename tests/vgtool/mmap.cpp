#include <stdio.h>
#include <sys/mman.h>

#include <aislinn.h>
#include <stdio.h>

int main() {
	aislinn_call_0("First");
	const size_t size = 4096 * 2; // 20 pages
	void *x = mmap (NULL, size, PROT_READ | PROT_WRITE, 
                        MAP_PRIVATE | MAP_ANONYMOUS, -1, (off_t)0);
	if (x == MAP_FAILED) {
		perror("mmap");
		aislinn_call_0("Error");
		return 0;
	}

	aislinn_call_0("Second");
	if (munmap(x, size)) {
		perror("munmap");
		aislinn_call_0("Error");
	}
	aislinn_call_0("Third");
	return 0;
}
