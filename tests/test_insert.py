import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import insert_pdf, pymupdf

class InsertTests(unittest.TestCase):
    def test_insert_and_append(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, texts in [('หลัก', ['1','2','3','4']), ('เพิ่ม', ['A','B'])]:
                with pymupdf.open() as doc:
                    for text in texts:
                        doc.new_page().insert_text((50,50), text)
                    doc.save(root / (name + '.pdf'))
            main, extra = root/'หลัก.pdf', root/'เพิ่ม.pdf'
            original = main.read_bytes()
            for position, expected in [(4,['1','2','3','A','B','4']), (5,['1','2','3','4','A','B'])]:
                output = root/f'{position}.pdf'
                self.assertEqual(insert_pdf(main, extra, position, output),6)
                with pymupdf.open(output) as doc:
                    self.assertEqual([p.get_text().strip() for p in doc], expected)
            self.assertEqual(main.read_bytes(), original)
            for output in [main, extra, root/'4.pdf']:
                with self.assertRaises(ValueError): insert_pdf(main,extra,4,output)
            for position in [0,6]:
                with self.assertRaises(ValueError): insert_pdf(main,extra,position,root/'bad.pdf')

if __name__ == '__main__': unittest.main()
