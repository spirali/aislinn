
import sys
import random

def main():
    argv = sys.argv
    if len(argv) != 2:
        print "Invalid args"
        return

    random.seed(1001)

    with open(argv[1], "w") as f:
        f.write("BEGIN\n")
        for i in xrange(100000):
            if i % 100 == 0:
                f.write("--" * 40)
            f.write(str(i) + " {")
            size = random.randint(2, 16)
            for j in xrange(size):
                f.write(" " + hex(random.randint(0, 65535)))
            f.write(" }\n")
        f.write("END\n")

if __name__ == "__main__":
    main()
