# Windows installer validation: GETEdit 1.0.6

Build commit: 63e45ab
Windows CI: https://github.com/n0ngXarm/GETEdit/actions/runs/42185684283
Result: SUCCESS

Verified: regression suite; per-user installer; install path with Thai characters and spaces; installed GUI launch; reinstall/update; Start Menu shortcut; HKCU uninstall registration; uninstallation; separate user fixture retained.

Installed runtime test uses the native Windows Qt backend, imports a generated PDF through GETEditWorker.exe, exports and reopens it. 38 regression tests (one POSIX-only check skips on Windows). LibreOffice is optional and not bundled; Office conversion from the frozen Windows build is not acceptance-tested.

Microsoft Defender custom scan completed on the CI runner (see SECURITY-REPORT.txt). Binaries are unsigned; SmartScreen reputation and every antivirus cannot be guaranteed. CI uses windows-latest, not a human-operated Windows 10/11 device. No firewall changes, security exclusions, services or startup tasks are installed.
