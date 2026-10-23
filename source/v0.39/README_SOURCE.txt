Rasd v0.39 source
=================

The editable application is split into these modules:
  core.py       shared imports, paths, data model, and helpers
  main_ui.py    application shell and project screens
  files.py      project file listing and file actions
  search.py     Everything integration and search screens
  previews.py   file preview implementations

The complete merged application code is in: full code\app.py

To regenerate the merged file after editing the modules:
  python build_single.py

To build a Windows executable for development, use Python 3.11 and install
the packages in requirements-build.txt, then run:
  python -m PyInstaller --noconfirm --clean Rasd_v0.39.spec

The distributed Rasd.exe already bundles its Python runtime, application
libraries, and the Everything search engine. End users do not need Python,
pip, a command prompt, or an Internet connection to install and run Rasd.
The bundled Everything engine only indexes the opened project folder, which
must be located inside the Log folder beside Rasd.exe.

