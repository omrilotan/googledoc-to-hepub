#!/usr/bin/env python

import click
import zipfile
import os
from bs4 import BeautifulSoup
import shutil
import re

css = """
* { direction: rtl; -epub-text-align-last: right; letter-spacing: -0.03rem; }
.title, .subtitle, h1, h2, h3 { text-align: center; }
.title, h1 { font-size: 1.8em; page-break-before: always; }
.subtitle, h2 { font-size: 1.4em; }
h3 { font-size: 1.2em; }
h1, h2, h3, p { margin: 0 0 0.2em; }
p { text-align: justify; -epub-hyphens: none; }
img { display: block; max-width: 100%; max-height: 100%; margin: 0 auto; }
hr { page-break-after: always; }
"""


def convert_html_to_rtl(html):
    """Converts HTML to RTL and adds CSS styles.
    Parameters:
    html: The HTML to convert.
    Returns:
    The converted HTML.
    """
    # Remove all the classes, dir, alt, title, style, and empty paragraphs
    html = re.sub(r'(\s(class|dir|alt|title|style)="[^"]*"|<p><\/p>)', "", html)
    # Remove all the spans
    html = re.sub(r"<\/?span\/?>", "", html)
    # Remove empty paragraphs
    html = re.sub(r"<p>[\s\t\r]*<\/p>", "", html, flags=re.MULTILINE)
    # Add the CSS styles
    html = re.sub(r"<style.*<\/style>", f"<style>{css}</style>", html)
    # Set the dir="rtl" attribute to the <html> tag
    html = re.sub(r"(\<html[^>]*)>", rf'\1 dir="rtl">', html)
    return html


@click.command()
@click.argument("input", type=click.Path(exists=True))
@click.option(
    "--output",
    prompt="Output File. Leaving this empty will overwrite the input file",
    help="Path to the output epub file. If not specified, the output file will replace the input file.",
    type=click.Path(),
    default="",
)
@click.option(
    "--clean-before",
    prompt=" Clean existing temp directory",
    help="Clean temp directory before processing, in case a previous run left it there. Default: True",
    type=bool,
    default=True,
)
@click.option(
    "--clean-after",
    prompt=" Delete temporary directory when done?",
    help="Clean temp directory after processing. Default: True",
    type=bool,
    default=True,
)
def convert_epub_to_rtl(input: str, output: str, clean_after: bool, clean_before: bool):
    """Convert an exported GoogleDoc EPUB file to a formatted RTL ebook."""
    if output == "":
        output = input
    if clean_before == True and os.path.exists("temp_epub"):
        shutil.rmtree("temp_epub")
    # Create a temporary directory to work in
    temp_dir = "temp_epub"
    os.makedirs(temp_dir, exist_ok=True)
    # Unzip the input EPUB file
    with zipfile.ZipFile(input, "r") as epub_zip:
        epub_zip.extractall(temp_dir)
    # Modify the content
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if re.search(r"\.(html|xhtml)$", file):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as html_file:
                    content = html_file.read()
                modified_content = convert_html_to_rtl(content)
                with open(file_path, "w", encoding="utf-8") as html_file:
                    html_file.write(modified_content)
    # Set page-progression-direction to "rtl" in the OPF file
    opf_path = os.path.join(temp_dir, "GoogleDoc", "package.opf")
    with open(opf_path, "r", encoding="utf-8") as opf_file:
        opf_content = opf_file.read()
    soup = BeautifulSoup(opf_content, "xml")
    spine_tag = soup.find("spine")
    if spine_tag:
        spine_tag["page-progression-direction"] = "rtl"
    # if there is only one image, make it the cover image
    if len(soup.find_all("item", {"media-type": re.compile("image")})) == 1:
        soup.find("item", {"media-type": re.compile("image")})[
            "properties"
        ] = "cover-image"
    with open(opf_path, "w", encoding="utf-8") as opf_file:
        opf_file.write(str(soup))
    # Create a new EPUB file from the modified content
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as epub_zip:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, temp_dir)
                epub_zip.write(file_path, arcname=rel_path)
    if clean_after:
        shutil.rmtree(temp_dir)
    click.echo(f"Conversion complete. Output saved to {output}")


if __name__ == "__main__":
    convert_epub_to_rtl()
