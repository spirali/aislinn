
.PHONY=all
all: userguide.html sspace.html

statespace.png: statespace.svg
	inkscape -e statespace.png -D -d=50.0 statespace.svg

sspace.png: sspace.svg
	inkscape -e sspace.png -D -d=50.0 sspace.svg

userguide.html: userguide.adoc statespace.png
	asciidoctor -a data-uri -a toc2 -a source-highlighter=coderay userguide.adoc

sspace.html: sspace.adoc sspace.png
	asciidoctor -a data-uri -a source-highlighter=coderay sspace.adoc
