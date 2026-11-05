"""Create a clean source archive from Git-tracked files plus its verified bundle."""
import argparse,subprocess,zipfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='../RiskLab_Source_Package.zip');args=p.parse_args()
    root=Path(__file__).resolve().parents[1];output=Path(args.output).resolve()
    files=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    files=[x for x in files if x]
    if not (root/'RiskLab_History.bundle').is_file():raise SystemExit('Create and verify RiskLab_History.bundle first')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in files+['RiskLab_History.bundle']:
            file=root/name
            if not file.is_file():raise SystemExit('Tracked file missing: '+name)
            archive.write(file,Path('RiskLab')/name)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise SystemExit('Archive CRC failure')
    print(output)

if __name__=='__main__':main()
