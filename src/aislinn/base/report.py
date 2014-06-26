#
#    Copyright (C) 2014 Stanislav Bohm
#
#    This file is part of Aislinn.
#
#    Aislinn is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License, or
#    (at your option) any later version.
#
#    Aislinn is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Kaira.  If not, see <http://www.gnu.org/licenses/>.
#


from tags import Tag
import xml.etree.ElementTree as xml

class Entry:

    def __init__(self, name, value, description):
        self.name = name
        self.value = value
        self.description = description

    def make_xml_element(self):
        e = xml.Element(self.name)
        e.text = str(self.value)
        return e

    def make_html_text(self):
        if self.description:
            name = self.description
        else:
            name = self.name.capitalize()
        return "{0}: {1}".format(name, self.value)


class EntryList:

    def __init__(self):
        self.entries = []

    def add(self, name, value, description=None):
        self.entries.append(Entry(name, value, description))


class Report:

    def __init__(self, generator):
        self.info = EntryList()
        self.process_count = generator.process_count

        self.info.add(
                "program-args", " ".join(generator.args), "Program arguments")
        self.info.add(
                "send-protocol", generator.send_protocol, "Send protocol")
        if generator.send_protocol == "threshold":
            self.info.add(
                    "send-protocol-thresholds",
                    "{0}:{1}".format(
                        generator.send_protocol_eager_threshold,
                        generator.send_protocol_randezvous_threshold),
                    "Threshold values")
        self.info.add(
                "processes", generator.process_count, "Number of processes")
        self.info.add("nodes",
                      generator.statespace.nodes_count,
                      "Number of nodes in statespace")

        self.error_messages = generator.error_messages

    def entries_to_xml(self, parent_name, entry_list):
        parent = xml.Element(parent_name)
        for entry in entry_list.entries:
            parent.append(entry.make_xml_element())
        return parent

    def entries_to_html(self, tag, entry_list):
        ul = tag.child("ul")
        for entry in entry_list.entries:
            ul.child("li", entry.make_html_text())
        return ul

    def create_xml(self):
        root = xml.Element("report")
        info = self.entries_to_xml("info", self.info)
        root.append(info)
        for error in self.error_messages:
            e = self.entries_to_xml("error", error.get_entries())
            e.set("name", error.name)
            root.append(e)
            ev = xml.Element("events")
            root.append(ev)
            for event in error.events:
                e = self.entries_to_xml("event", event.get_entries())
                e.set("name", event.name)
                e.set("rank", str(event.rank))
                ev.append(e)
        return xml.ElementTree(root)

    def create_html_head(self, html):
        head = html.child("head")
        head.child("title", "Aislinn report")
        head.child("style", REPORT_CSS)

    def _make_row(self, table, data, classes=None, titles=None):
        tr = table.child("tr")
        for i, d in enumerate(data):
            td = tr.child("td", d)
            if classes and classes[i]:
                td.set("class", classes[i])
            if titles and titles[i]:
                td.set("title", titles[i])

    def export_events(self, events, tag):
        table = tag.child("table")
        process_count = self.process_count
        self._make_row(table.child("thead"), range(process_count))
        tbody = table.child("tbody")
        ranks = [ [] for x in xrange(process_count) ]
        for e in events:
            ranks[e.rank].append(e)

        step = 0
        while True:
            data = [""] * process_count
            classes = [None] * process_count
            titles = [None] * process_count
            for r in xrange(process_count):
                if len(ranks[r]) <= step:
                    continue
                e = ranks[r][step]
                name = e.name
                data[r] = name
                if e.stacktrace:
                    titles[r] = e.stacktrace.replace("|", "\n")
                if name.startswith("W"):
                    classes[r] = "Wait"
                if name.endswith("end"):
                    classes[r] = "Send"
                if name.endswith("ecv"):
                    classes[r] = "Recv"
            if not any(data):
                break
            self._make_row(tbody, data, classes, titles)
            step += 1

    def create_html(self):
        html = Tag("html")
        self.create_html_head(html)
        body = html.child("body")
        body.child("h1", "Aislinn report")

        body.child("h2", "Basic information")
        self.entries_to_html(body, self.info)

        body.child("h2", "Errors")

        if self.error_messages:
            body.child("p", "{0} error(s) found" \
                    .format(len(self.error_messages)))
            for error in self.error_messages:
                body.child("h3", "Error: " + error.short_description)
                body.child("p", error.description)
                if error.rank is not None:
                    body.child("p", "Rank: {0}".format(error.rank))
                if error.stacktrace is not None:
                    body.child("p", "{0}" \
                            .format(error.stacktrace.replace("|", "<br>")))
                if error.events:
                    self.export_events(error.events, body)
        else:
            body.child("p", "No errors found")

        return html

    def write_xml(self, filename):
        self.create_xml().write(filename)

    def write_html(self, filename):
        html = self.create_html()
        with open(filename, "w") as f:
            html.write(f)


REPORT_CSS = """

table, tr, td { border: black solid 1px; }
td {
    padding: 0.5em;
    text-align: center;
}

.Wait {
    background-color: orange;
}

.Send {
    background-color: lightgreen;
}

.Recv {
    background-color: lightblue;
}

"""
