# Third-party software notices

Rasd is licensed under the GNU Affero General Public License v3.0. The complete license is in `LICENSE`.

## Components included with Rasd v0.39

- **Everything and ES** by David Carpenter are distributed with Rasd. Preserve the MIT notice in `source/v0.39/Everything/License.txt`. Official notice: https://www.voidtools.com/License.txt
- **PyMuPDF / MuPDF 2.0** provides PDF preview support. It is available under GNU AGPL-3.0 or a commercial license from Artifex. Rasd selects the AGPL-3.0 option. Read the full license terms and comply with the AGPL when redistributing this combined application. See https://pymupdf.readthedocs.io/en/latest/about.html and https://github.com/pymupdf/PyMuPDF.
- **PyInstaller 6.22.3** is used to build the Windows executable. Its license includes an exception for distributing applications built with it. See https://pyinstaller.org/en/v6.22.3/license.html.
- Other build dependencies are listed in `source/v0.39/requirements-build.txt`. That file uses unpinned package names; the exact versions used for a particular build can be recorded with `pip freeze`.

These notices are a release aid, not a substitute for reviewing the exact dependency versions and license texts included in a particular binary build.
