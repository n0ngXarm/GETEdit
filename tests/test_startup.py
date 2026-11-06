import os
import tempfile
import unittest
from pathlib import Path
from app import startup_paths


class StartupTests(unittest.TestCase):
    def test_nautilus_absolute_selection_wins_over_basename(self):
        with tempfile.TemporaryDirectory() as folder:
            selected=Path(folder)/'ไฟล์ มีช่องว่าง.pdf'
            selected.touch()
            env={'NAUTILUS_SCRIPT_SELECTED_FILE_PATHS':str(selected)+'\n'}
            self.assertEqual(startup_paths([selected.name],env,Path(folder)/'GETEdit'),[str(selected)])

    def test_relative_selection_uses_original_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            env={'GETEDIT_LAUNCH_CWD':folder}
            self.assertEqual(startup_paths(['test.pdf'],env,Path(folder)/'GETEdit'),[str(Path(folder)/'test.pdf')])

    def test_file_uri_and_current_nautilus_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ไฟล์ + ทดสอบ.pdf'
            self.assertEqual(startup_paths([path.as_uri()],{},folder),[str(path)])
            env={'NAUTILUS_SCRIPT_CURRENT_URI':Path(folder).as_uri()}
            self.assertEqual(startup_paths([path.name],env,'/tmp/elsewhere'),[str(path)])

    @unittest.skipUnless(os.name=='posix','Nautilus launcher is a POSIX script')
    def test_installed_launcher_preserves_file_manager_directory(self):
        import importlib.util
        import json
        import subprocess
        from unittest.mock import patch
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('getedit_installer',root/'install-linux.py')
        installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder:
            caller=Path(folder)/'เอกสาร มีช่องว่าง';caller.mkdir()
            executable=Path(folder)/'fake-python'
            executable.write_text('#!/usr/bin/env python3\nimport json,os,sys\nprint(json.dumps({"cwd":os.getcwd(),"args":sys.argv[1:]}))\n')
            executable.chmod(0o755)
            with patch.object(installer.sys,'executable',str(executable)),patch('builtins.print'):
                launcher=installer.install(Path(folder)/'data')
            process=subprocess.run([str(launcher),'ไฟล์.pdf'],cwd=caller,capture_output=True,text=True,check=True)
            result=json.loads(process.stdout)
            self.assertEqual(result['cwd'],str(caller))
            self.assertEqual(result['args'][1],'ไฟล์.pdf')
