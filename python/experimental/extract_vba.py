#!/usr/bin/env python3

#
# Command-line tool to extract VBA code from Office files.
#

# Modded by Randy Bower

import argparse
import glob
import hashlib
import html
import sys

import oletools.olevba3 as vba3  # pip install oletools

EPILOG = """
==============================================================================
The -o option specifies the output file; required.

The -m option allows specification of specific modules to be extracted;
optional, all modules extracted if not specified; can be repeated to specify
multiple modules.

The -c option collapses the individual modules.

The -s option sorts files based on last name, assuming the file name contians
an email address in the format c85marty.mcfly@usafa.edu.

The -v option shows verbose output in the command window.

Example Usage:
c:\> python extract_vba.py -o Results.html -m Examples -m Exercises -c -s -v Labs\*.xlsm
"""

FUNCTIONS = """<script>
function collapse_all() {
  for(var i=0; i<document.getElementsByTagName("details").length; i++) {
    document.getElementsByTagName("details")[i].removeAttribute("open");
  }
}

function expand_all() {
  for(var i=0; i<document.getElementsByTagName("details").length; i++) {
    document.getElementsByTagName("details")[i].setAttribute("open", "open");
  }
}
</script>"""


def main(argv):
    """Main function to run the extraction.

    :param list[str] argv: List of command line arguments.
    """
    extract_vba_from_office_files(parse_args(argv))


def extract_vba_from_office_files(args):
    # Glob the filenames and put them in a dictionary, extracting
    # "Lastname, Firstname" if the sort option is specified.
    filenames = {}
    for infilename in args.files:
        for filename in glob.glob(infilename):
            if args.sort:
                # The file name must include an email address and be in the format produced by Blackboard:
                # Assignment_c85marty.mcfly@usafa.edu_attempt_1900-01-01-00-00-00_Filename.xlsm
                lastname = filename[filename.rfind(".", 0, filename.find("@")) + 1: filename.find("@")].title()
                firstname = filename[filename.rfind("_", 0, filename.find("@")) + 4: filename.rfind(".", 0,
                                                                                                    filename.find(
                                                                                                        "@"))].title()
                key = lastname + ", " + firstname
            else:
                # Use the full file name itself as the key; redundant, I know.
                key = filename
            filenames[key] = filename

    # Build the html file.
    with open(args.outfile, "w") as outfile:
        # html header
        print("""<html>""", file=outfile)
        print("""<head>""", file=outfile)
        print(
            """<script src="https://cdn.rawgit.com/google/code-prettify/master/loader/run_prettify.js?lang=vb"></script>""",
            file=outfile)
        print(FUNCTIONS, file=outfile)
        print("""</head>""", file=outfile)
        print("""<body>""", file=outfile)

        # Links to each file
        print("""<h1>Table of Contents &ndash; {}</h1>""".format(args.outfile), file=outfile)
        print(
            """<div style="width: 67%; -webkit-column-count: {0}; -moz-column-count: {0}; column-count: {0};">""".format(
                3 if args.sort else 1), file=outfile)
        for key in sorted(filenames):
            filename = filenames[key]
            a = hashlib.sha256(filename.encode()).hexdigest()
            print("""&bullet; <a href="#{}">{}</a><br />""".format(a, html.escape(key)), file=outfile)
        print("""</div>""", file=outfile)

        # File contents
        print("""<h1>Files</h1>""", file=outfile)
        print(
            """<h3><a href="javascript:collapse_all()">Collapse All</a> &ndash; <a href="javascript:expand_all()">Expand All</a></h3>""",
            file=outfile)
        for key in sorted(filenames):
            filename = filenames[key]
            a = hashlib.sha256(filename.encode()).hexdigest()

            # Don't print this <h2> as it's now in the <summary> tag.
            # print("""<h2><a name="{}" />{}</h2>""".format(a, html.escape(filename)), file=outfile)

            if args.collapse:
                print("""<details>""", file=outfile)
            else:
                print("""<details open>""", file=outfile)

            print("""<summary><strong><a name="{}" />{}</strong></summary>""".format(a, html.escape(key)), file=outfile)
            html_vba_dump(args, filename, outfile=outfile)
            print("""</details>""", file=outfile)

        # End of HTML
        print("""</body>""", file=outfile)
        print("""</html>""", file=outfile)


def html_vba_dump(args, office_filename, outfile):
    vba_parser = vba3.VBA_Parser(office_filename)
    for (filename, stream_path, vba_filename, vba_code) in vba_parser.extract_macros():
        # The stream_path should be the module name with a "VBA/" prefix; e.g., "VBA/Exercises"
        stream_path = html.escape(stream_path)
        if args.modules is None or stream_path[stream_path.find("/") + 1:] in args.modules:
            if args.sort:
                # If the user specified the sort option, the summary tag will only
                # show Lastname, Firstname, show the full file name in the output.
                print("""<h3 style="margin-left: 20px">{}: {}</h3>""".format(html.escape(office_filename),
                                                                             html.escape(stream_path)), file=outfile)

            # Pre-format and pretty-print the code.
            print("""<pre style="margin-left: 20px" class="prettyprint lang-vb">""", file=outfile)
            print(vba_code.decode("utf-8").replace("\r", ""), file=outfile)
            print("""</pre>""", file=outfile)

            # Show progress if the user has asked for it.
            if args.verbose:
                print("""{}: {}""".format(html.escape(office_filename), html.escape(stream_path)))


def parse_args(argv):
    """Function to use an ArgumentParser to parse the command line arguments.

    :param list[str] argv: List of command line arguments.
    :return: The Namespace created by the ArgumentParser.
    :rtype: Namespace
    """
    # Create an argument parser object and setup the arguments.
    parser = argparse.ArgumentParser(description="Command line VBA code extractor.", epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    # The outfile file is an optional argument; default is stdout.
    parser.add_argument("-o", "--outfile", required=True, help="Output file name; required.")

    # Specific module names to include in output; may be specified multiple times.
    parser.add_argument("-m", "--modules", action="append",
                        help="Specific modules to include in output; default is all modules.")

    # Flag to output collapse elements instead of table of contents.
    parser.add_argument("-c", "--collapse", action="store_true", default=False,
                        help="Collapse individual modules.")

    # Flag to sort files based on last name, assuming the file name contians
    # an email address in the format c85marty.mcfly@usafa.edu
    parser.add_argument("-s", "--sort", action="store_true", default=False,
                        help="Sort files based on last name.")

    # Flag to show verbose output in command window.
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="Produce verbose output in command window.")

    # The remaining arguments are the files to be extracted.
    parser.add_argument("files", metavar="FILE", nargs="+",
                        help="Names of files to be extracted.")

    # Once all arguments are added to the ArgumentParser object, the parse_args method
    # creates a Namespace (basically a dictionary) with attributes set for each option.
    return parser.parse_args(argv)


# Execute main, passing the list of arguments without the program name.
if __name__ == "__main__":
    main(sys.argv[1:])
