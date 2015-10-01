#
#    Copyright (C) 2014, 2015 Stanislav Bohm
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
#    along with Aislinn.  If not, see <http://www.gnu.org/licenses/>.
#


from arc import STREAM_STDOUT, STREAM_STDERR, COUNTER_INSTRUCTIONS
from arc import COUNTER_ALLOCATIONS, COUNTER_SIZE_ALLOCATIONS
from arc import COUNTER_MPICALLS
import xml.etree.ElementTree as xml
import os
import paths
import base64
import jinja2

plt = None
try:
    import matplotlib.pyplot as plt
    import StringIO
except ImportError:
    pass # User of plt has to make sure that plt is not None

def serialize_fig(fig):
    stringfile = StringIO.StringIO()
    fig.savefig(stringfile, format="png", transparent=True)
    stringfile.seek(0)
    return stringfile.buf

def make_chart(data, ydata, units):
    fig = plt.figure(figsize=(8, 2))
    plt.plot(ydata, data, "-")
    plt.ylabel(units)
    return serialize_fig(fig)

def make_chart_1d(data, yticks, xlabel, ylabel):
    fig = plt.figure(figsize=(8, 0.5 + 0.5 * len(data)))
    plt.yticks(yticks)
    plt.gca().invert_yaxis()
    plt.margins(0.2)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    for i, d in enumerate(data):
            plt.plot(d, len(d) * [i], "1")
    plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
    return serialize_fig(fig)

def html_embed_img(data):
    return "data:image/png;base64," + base64.b64encode(data)


class Entry:

    def __init__(self, name, value, description, help=None):
        self.name = name
        self.value = value
        self.description = description
        self.help = help

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

OUTPUTS_LIMIT = 10


class Report:

    def __init__(self, generator, args, version):
        self.process_count = generator.process_count
        self.statistics = generator.get_statistics()
        if self.statistics and self.statistics[1]:
            self.statistics_max = [ max((v[i] for v in self.statistics[1]))
                                    for i in xrange(len(self.statistics[0])) ]
        else:
            self.statistics_max = None

        self.stdout_counts = None
        self.stderr_counts = None

        self.version = version

        self.outputs = {}

        def count_of_outputs(count):
            if count == None:
                return ">" + str(OUTPUTS_LIMIT)
            else:
                return str(count)

        if generator.stdout_mode == "capture" \
                and generator.statespace.initial_node:
            self.stdout_counts = \
                    [ count_of_outputs(
                        generator.statespace.get_outputs_count(
                        STREAM_STDOUT, pid, OUTPUTS_LIMIT))
                      for pid in xrange(generator.process_count) ]

        if generator.stderr_mode == "capture" \
                and generator.statespace.initial_node:
            self.stderr_counts = \
                    [ count_of_outputs(
                        generator.statespace.get_outputs_count(
                        STREAM_STDERR, pid, OUTPUTS_LIMIT))
                      for pid in xrange(generator.process_count) ]

        if args.stderr_write \
                and generator.stderr_mode == "generator" \
                and generator.statespace.initial_node:
            if args.stderr_write == "all":
                limit = None
            else:
                limit = args.stderr_write
            self.outputs[STREAM_STDERR.name] = [
                    generator.statespace.get_all_outputs(STREAM_STDERR, pid, limit)
                    for pid in xrange(generator.process_count)]

        if args.stdout_write \
                and generator.stdout_mode == "capture" \
                and generator.statespace.initial_node:
            if args.stderr_write == "all":
                limit = None
            else:
                limit = args.stderr_write
            self.outputs[STREAM_STDOUT.name] = [
                    generator.statespace.get_all_outputs(STREAM_STDOUT, pid, limit)
                    for pid in xrange(generator.process_count)]

        if args.profile:
            self.profile = {}
            for name, counter in (("instructions", COUNTER_INSTRUCTIONS),
                                  ("allocations", COUNTER_ALLOCATIONS),
                                  ("size_allocations",
                                      COUNTER_SIZE_ALLOCATIONS),
                                  ("mpi_calls", COUNTER_MPICALLS)):
                self.profile[name] = []
                for pid in xrange(generator.process_count):
                    lst = list(generator.statespace \
                            .get_all_outputs(counter, pid, init=0))
                    self.profile[name].append(lst)
                self.profile[name + "_global"] = \
                        list(generator.statespace.get_all_outputs(
                            counter, range(generator.process_count), init=0))
        else:
            self.profile = None

        self.program_info = [
            Entry("program-args", " ".join(generator.args), "Program arguments"),
            Entry("processes", generator.process_count, "Number of processes"),
        ]

        self.analysis_configuration = [
            Entry("stdout-mode", generator.stdout_mode, "Stdout mode"),
            Entry("stderr-mode", generator.stderr_mode, "Stderr mode"),
            Entry("send-protocol", generator.send_protocol, "Send protocol"),
            Entry("search", generator.search, "Search strategy"),
        ]

        if args.heap_size:
            self.analysis_configuration.append(
                    Entry("heap-size", args.heap_size, "Heap size"))

        if args.redzone_size:
            self.analysis_configuration.append(
                Entry("redzone-size", args.redzone_size, "Redzone size"))

        sizes = list(generator.message_sizes)
        sizes.sort()

        self.analysis_output = [
            Entry("stdout-outputs",
                  ",".join(self.stdout_counts) if self.stdout_counts else "N/A",
                 "# of possible outputs on stdout (per rank)"),
            Entry("stderr-outputs",
                  ",".join(self.stderr_counts) if self.stderr_counts else "N/A",
                 "# of possible outputs on stderr (per rank)"),
            Entry("deterministic-non-freed-memory",
                  generator.deterministic_unallocated_memory,
                 "Deterministic unallocated memory (bytes)"),
            Entry("message-sizes",
                  sizes,
                 "Sizes of unicast messages (bytes)")
        ]

        execution_time = generator.end_time - generator.init_time
        self.analysis_details = [
            Entry("init-time",
                  generator.init_time,
                  "Start of verification"),
            Entry("execution-time",
                  execution_time,
                  "Execution time"),
            Entry("nodes",
                  generator.statespace.nodes_count,
                  "Number of nodes in statespace"),
            Entry("full-statespace",
                  generator.is_full_statespace,
                  "Statespace fully explored"),
            Entry("speed",
                  generator.statespace.nodes_count
                    / execution_time.total_seconds(),
                  "Nodes per seconds"),
        ]
        self.error_messages = generator.error_messages

    @property
    def error_message_keys(self):
        return [ m.key for m in self.error_messages ]

    @property
    def pids(self):
        return range(self.process_count)

    def entries_to_xml(self, parent_name, entry_list):
        parent = xml.Element(parent_name)
        for entry in entry_list:
            parent.append(entry.make_xml_element())
        return parent

    def create_xml(self):
        root = xml.Element("report")
        info = self.entries_to_xml("program", self.program_info)
        root.append(info)
        info = self.entries_to_xml(
                "analysis", self.analysis_output + self.analysis_details)
        root.append(info)

        if self.statistics:
            stats = xml.Element("statistics")
            root.append(stats)
            mx = xml.Element("max")
            stats.append(mx)
            for name, value in zip(self.statistics[0], self.statistics_max):
                e = xml.Element("value")
                e.set("name", name[0])
                e.set("units", name[1])
                e.text = str(value)
                mx.append(e)

        for error in self.error_messages:
            e = xml.Element("error")
            e.set("key", error.key)
            e.set("name", error.name)
            e.set("description", error.description)
            for name, value in error.args.items():
                if value is not None:
                    e.set(name, str(value))
            if error.pid is not None:
                e.set("pid", str(error.pid))
            root.append(e)
            ev = xml.Element("events")
            root.append(ev)
            if error.events is not None:
                for event in error.events:
                    e = xml.Element("event")
                    e.set("name", event.name)
                    if hasattr(e, "pid"):
                        e.set("pid", str(event.pid))
                    ev.append(e)

        if self.outputs:
            streams = xml.Element("streams")
            root.append(streams)
            for name, s in self.outputs.items():
                stream = xml.Element("stream")
                stream.set("name", name)
                streams.append(stream)
                for i, outputs in enumerate(s):
                    process = xml.Element("process")
                    process.set("pid", str(i))
                    stream.append(process)
                    for text in outputs:
                        e = xml.Element("output")
                        e.text = text
                        process.append(e)

        if self.profile:
            profile = xml.Element("profile")
            root.append(profile)
            self.write_xml_profile(profile)
        return xml.ElementTree(root)

    def events_table(self, events):
        process_count = self.process_count
        pids = [ [] for x in xrange(process_count) ]
        for e in events:
            if hasattr(e, "pid"):
                pids[e.pid].append(e)
        table = []
        for step in xrange(max(len(p) for p in pids)):
            row = [ pids[p][step] if step < len(pids[p]) else None
                    for p in xrange(process_count) ]
            table.append(row)
        return table

    def write_xml_profile(self, parent):
        e = xml.Element("instructions")
        parent.append(e)
        for i, d in enumerate(self.profile["instructions"]):
            f = xml.Element("process" + str(i))
            f.text = " ".join(map(str, d))
            e.append(f)
        f = xml.Element("global")
        f.text = " ".join(map(str, self.profile["instructions_global"]))
        e.append(f)

    @property
    def statistics_text(self):
        if plt is None:
            return "Error: Module 'matplotlib' not installed"
        return ""

    @property
    def statistics_charts(self):
        if plt is None:
            return
        metadata, data, tick = self.statistics
        ydata = range(0, len(data) * tick, tick)

        for i, (name, units) in enumerate(metadata):
            img = make_chart([s[i] for s in data], ydata, units)
            yield name, html_embed_img(img)

    @property
    def profile_text(self):
        if plt is None:
            return "Error: Module 'matplotlib' not installed"
        return ""

    @property
    def profile_charts(self):
        if plt is None:
            return
        for label, name in (("# of instructions", "instructions"),
                            ("# of MPI calls", "mpi_calls"),
                            ("# of allocations", "allocations"),
                            ("size of allocations", "size_allocations")):
            img1 = make_chart_1d(self.profile[name],
                                range(len(self.profile[name])),
                                label, "Process")

            global_data = self.profile[name + "_global"]
            img2 = make_chart_1d([global_data],
                                 (),
                                label, "")
            yield (name,
                   html_embed_img(img1),
                   html_embed_img(img2),
                   map(len, self.profile[name]),
                   len(global_data), max(global_data))

    def write_xml(self, filename):
        self.create_xml().write(filename)

def write_as_html(report, filename):
    with open(os.path.join(paths.AISLINN_TEMPLATE, "report.html"), "r") as f:
        template = jinja2.Template(f.read())
    with open(filename, "w") as f:
        for s in template.generate(report=report):
            f.write(s)
