#!/usr/bin/env python3

import hashlib
import html
import mimetypes
import os
import sys

import oletools.olevba3 as vba3  # pip install oletools

__author__ = "Robert Harder"


def main():
    sys.argv += [r"c:\temp\vba\out.html",
                 r"c:\temp\vba\Lab05 - Solutions.xlsm",
                 r"c:\temp\vba\Lab25-Solution.xlsm"]
    if len(sys.argv) <= 2:
        print("Usage: {} outfile.html file1.xlsm file2.xlsm ...".format(os.path.basename(__file__)))
        sys.exit(1)
    else:
        extract_vba_from_office_files(sys.argv[1], sys.argv[2:])


def extract_vba_from_office_files(outfilename: str, infiles: []):
    with open(outfilename, "w") as f:
        print("<html>", file=f)
        print("<head>", file=f)
        print("""<script src="https://cdn.rawgit.com/google/code-prettify/master/loader/run_prettify.js"></script>""",
              file=f)
        print("</head>", file=f)
        print("<body>", file=f)

        # File links
        print("<h1>Table of Contents</h1>", file=f)
        print("<ul>", file=f)
        for infile in infiles:
            mime, b = mimetypes.guess_type(infile)
            print(infile, mime, b)

            a = hashlib.sha256(infile.encode()).hexdigest()
            print("""<li><a href="#{}">{}</a></li>""".format(a, html.escape(infile)), file=f)
        print("</ul>", file=f)

        # File contents
        print("<h1>Files</h1>", file=f)
        for infile in infiles:
            a = hashlib.sha256(infile.encode()).hexdigest()
            print("""<h2><a name="{}" />{}</h2>""".format(a, html.escape(infile)), file=f)
            html_vba_dump(infile, outfile=f)

        print("</body></html>", file=f)


def html_vba_dump(office_filename, outfile=None):
    if outfile is None:
        outfile = sys.stdout
    vp = vba3.VBA_Parser(office_filename)
    for (filename, stream_path, vba_filename, vba_code) in vp.extract_macros():
        print("""<h3>{}: {}</h3>""".format(
            html.escape(office_filename), html.escape(stream_path)),
            file=outfile)
        code = vba_code.decode("utf-8").replace("\r", "")
        print("""<pre class="prettyprint">{}</pre>""".format(code), file=outfile)


if __name__ == "__main__":
    main()
