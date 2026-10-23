Rasd v0.39
==========

Rasd.exe is the application. On first launch it creates Log beside itself;
put each project in its own subfolder inside Log. Rasd only opens projects
stored there, and its embedded Everything search is restricted to the
currently open project folder.

The Python runtime, app libraries, and Everything are bundled in Rasd.exe.
Installing or running Rasd does not require Python, command-line steps,
downloads, or an Internet connection.

Rasd checks the public GitHub Releases page for updates in the background
when it starts. Update checks and downloads require an Internet connection.
The user can install now, prepare the update for the next launch, or snooze
the reminder for one day. The first update from v0.38 to v0.39 must be
installed manually; in-app updates are available from v0.39 onward.
The installer is downloaded over HTTPS and verified against its published
SHA-256 digest before it is queued.

Python Source contains the editable modules and Python Source\full code\app.py,
which is the complete merged application in one file.

Download `RasdSetup_v0.39.exe` (standard) or
`RasdPortableSetup_v0.39.exe` (portable) from the GitHub Releases page.
The standard installer lets you choose the install folder. Its `Log` folder
is created beside Rasd.exe and is kept when Rasd is uninstalled.

The portable installer creates a separate `Rasd_v0.39_Portable` folder beside
the installer. Close the app before moving the complete portable folder; keep
`Rasd.exe` and `Log` together.

