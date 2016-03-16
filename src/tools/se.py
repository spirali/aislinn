
# Statespace explorer
# (Statespace debugging tool)

import xml.etree.ElementTree as xml

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
        return "<node [{0}] c={1}>".format(
            self.name,
            ";".join("{}".format(a.node.name) for a in self.arcs),
            ";".join("[{}]".format(node.name) for node in self.parents))


class Statespace:

    def __init__(self, filename):
        nodes = {}
        root = xml.parse(filename).getroot()
        for n in root.findall("node"):
            id = n.get("id")
            node = nodes.get(id)
            if node is None:
                node = Node(id)
                nodes[id] = node
            self.nodes = node
            for arc in n.findall("arc"):
                id = arc.get("node-id")
                node2 = nodes.get(id)
                if node2 is None:
                    node2 = Node(id)
                    nodes[id] = node2
                node.arcs.append(Arc(node2, arc.get("label")))
                node2.parents.append(node)
        self.nodes = nodes
        self.initial_node = nodes[root.get("init-node-id")]

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
    queue = [(s1.initial_node, s2.initial_node)]
    found = set(queue)

    while queue:
        node1, node2 = queue.pop()
        if len(node1.arcs) != len(node2.arcs):
            print found
            print "Different child count ", node1, node2
            break
        for i, (a1, a2) in enumerate(zip(node1.arcs, node2.arcs)):
            pair = (a1.node, a2.node)
            print pair, ":",  node1, node2, i
            if pair not in found:
                #queue.append(pair)
                queue.insert(0, pair)
                found.add(pair)

    images1 = {}
    images2 = {}
    for n1, n2 in found:
        a = images1.get(n1)
        if a is None:
            a = []
            images1[n1] = a
        if n1 not in a:
            a.append(n2)

        a = images2.get(n2)
        if a is None:
            a = []
            images2[n2] = a
        if n2 not in a:
            a.append(n2)

    print "1 -> 2 ----------------"
    for key, value in images1.items():
        if len(value) >= 2:
            print key, value
    print "2 -> 1 ----------------"
    for key, value in images2.items():
        if len(value) >= 2:
            print key, value


    """
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
    """


def main():
    import sys
    s1 = Statespace(sys.argv[1])
    s2 = Statespace(sys.argv[2])
    find_differences(s1, s2)


if __name__ == "__main__":
    main()
