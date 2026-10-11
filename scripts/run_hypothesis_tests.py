"""Run every Hypothesis test with its entry-point example isolated.

The auxiliary installed example registers a type eagerly and imports NumPy.
It must not leak that startup hook into the main suite's subprocess tests.
Both suites run on every invocation; their JUnit suites are combined unchanged.
"""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


EXAMPLE = "hypothesis-python/examples/example_hypothesis_entrypoint"


def run(args):
    xml_args = [arg for arg in args if arg.startswith("--junitxml=")]
    if len(xml_args) != 1:
        raise ValueError("Exactly one JUnit evidence path is required")
    output = Path(xml_args[0].split("=", 1)[1])
    main_xml = output.with_name(output.stem + "-main.xml")
    example_xml = output.with_name(output.stem + "-entrypoint.xml")
    common = [arg for arg in args if not arg.startswith("--junitxml=")]
    main = common + ["--ignore=" + EXAMPLE, "--junitxml=" + str(main_xml)]
    example = [EXAMPLE if arg == "hypothesis-python" else arg for arg in common]
    example += ["--junitxml=" + str(example_xml)]
    codes = []
    for python, arguments in [(sys.executable, main),
                              (str(Path.cwd() / ".entrypoint-venv/bin/python"), example)]:
        codes.append(subprocess.call([python, "-u", "-m", "pytest"] + arguments))
    # Never publish a partial combined round as complete evidence.
    if any(code not in (0, 1) for code in codes):
        return next(code for code in codes if code not in (0, 1))
    root = ET.Element("testsuites")
    for path in (main_xml, example_xml):
        source = ET.parse(path).getroot()
        root.extend(list(source) if source.tag == "testsuites" else [source])
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    main_xml.unlink()
    example_xml.unlink()
    return max(codes)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
