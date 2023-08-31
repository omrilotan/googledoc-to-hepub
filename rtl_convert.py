import click
import zipfile
import os
from bs4 import BeautifulSoup
import shutil
import re

css = '''
* { direction: rtl; letter-spacing: -0.03rem; }
.title, .subtitle, h1, h2 { text-align: center; }
.title, h1 { font-size: 1.8em; page-break-before: always; }
.subtitle, h2 { font-size: 1.4em; }
h1, h2, p { margin: 0 0 0.2em; }
p { text-align: justify; }
img { display: block; max-width: 100%; margin: 0 auto; }
hr { page-break-after: always; }
'''

def convert_html_to_rtl(html):
	html = re.sub(r'(\s(class|dir|alt|title|style)="[^"]*"|<p><\/p>)', '', html)
	html = re.sub(r'<\/?span>', '', html)
	html = re.sub(r'<style.*<\/style>', f'<style>\n{css}</style>', html)
	html = re.sub(r'(\<html[^>]*)>', rf'\1 dir="rtl">', html)
	return html

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path(), default='')
def convert_epub_to_rtl(input_file, output_file):
    if (output_file == ''):
        output_file = input_file

    # Create a temporary directory to work in
    temp_dir = 'temp_epub'
    os.makedirs(temp_dir, exist_ok=True)

    # Unzip the input EPUB file
    with zipfile.ZipFile(input_file, 'r') as epub_zip:
        epub_zip.extractall(temp_dir)

    # Modify the content
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if re.search(r"\.(html|xhtml)$", file):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as html_file:
                    content = html_file.read()
                modified_content = convert_html_to_rtl(content)
                with open(file_path, 'w', encoding='utf-8') as html_file:
                    html_file.write(modified_content)

    # Set page-progression-direction to "rtl" in the OPF file
    opf_path = os.path.join(temp_dir, 'GoogleDoc','package.opf')
    with open(opf_path, 'r', encoding='utf-8') as opf_file:
        opf_content = opf_file.read()
    soup = BeautifulSoup(opf_content, 'xml')
    spine_tag = soup.find('spine')
    if spine_tag:
        spine_tag['page-progression-direction'] = 'rtl'
    with open(opf_path, 'w', encoding='utf-8') as opf_file:
        opf_file.write(str(soup))


    # Create a new EPUB file from the modified content
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, temp_dir)
                epub_zip.write(file_path, arcname=rel_path)

    # Clean up the temporary directory
    shutil.rmtree(temp_dir)

    click.echo(f"Conversion complete. Output saved to {output_file}")

if __name__ == "__main__":
    convert_epub_to_rtl()
