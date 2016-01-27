
# Statespace explorer
# (Statespace debugging tool)


class Arc:

    def __init__(self, node, label):
        self.node = node
        self.label = label


class Node:

    def __init__(self, name):
        self.name = name
        self.arcs = []
        self.parents = []
        self.image = None

    def __repr__(self):
        return "<node [{0}] c={1} p={2}>".format(
            self.name,
            ";".join("{}->{}".format(a.label, a.node.name) for a in self.arcs),
            ";".join("[{}]".format(node.name) for node in self.parents))


class Statespace:

    def __init__(self, filename):
        nodes = {}
        current = None
        with open(filename, "r") as f:
            initial = f.readline().rstrip()
            for line in f:
                line = line.rstrip()
                if line.startswith("\t"):
                    name, label = line[1:].split()
                    node = nodes.get(name)
                    if node is None:
                        node = Node(name)
                        nodes[name] = node
                    current.arcs.append(Arc(node, label))
                    node.parents.append(current)
                else:
                    current = nodes.get(line)
                    if current is None:
                        current = Node(line)
                        nodes[line] = current
        self.nodes = nodes
        self.initial_node = nodes[initial]

    def bf_search(self):
        queue = [self.initial_node]
        visited = set(queue)
        while queue:
            node = queue.pop()
            yield node
            for arc in node.arcs:
                if arc.node not in visited:
                    visited.add(arc.node)
                    queue.append(arc.node)


def find_differences(s1, s2):
    def check_node(node):
        pass

    nodes1 = list(s1.bf_search())
    nodes2 = list(s2.bf_search())

    if len(nodes1) != len(nodes2):
        print "Different size of statespace"

    s1.initial_node.image = s2.initial_node
    s2.initial_node.image = s1.initial_node

    for node1, node2 in zip(nodes1, nodes2):
        if node1.image != node2 or node2.image != node1:
            print "Error found1 ", node1, node2
            return
        if len(node1.arcs) != len(node2.arcs):
            print "Different child count ", node1, node2
            return
        for a1, a2 in zip(node1.arcs, node2.arcs):
            n1 = a1.node
            n2 = a2.node
            if n1.image is None and n2.image is None:
                n1.image = n2
                n2.image = n1
            elif n1.image != n2 or n2.image != n1:
                print "Error found"
                print "arc1.label", a1.label
                print "arc2.label", a2.label
                print "parent1", node1
                print "parent2", node2
                print "n1", n1
                print "n2", n2
                print "n1.image", n1.image,
                print "n2.image", n2.image
                return


def main():
    import sys
    s1 = Statespace(sys.argv[1])
    s2 = Statespace(sys.argv[2])
    find_differences(s1, s2)


if __name__ == "__main__":
    main()
