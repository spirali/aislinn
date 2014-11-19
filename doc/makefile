
.PHONY=all
all: userguide.html

statespace.png: statespace.svg
	inkscape -e statespace.png -D -d=50.0 statespace.svg

userguide.html: userguide.adoc statespace.png
	asciidoctor -a data-uri -a toc2 -a source-highlighter=coderay userguide.adoc
