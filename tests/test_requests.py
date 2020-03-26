import os
import tempfile

from covicdbtools import requests, workbooks


class UploadedFile:
    def __init__(self, path):
        self.path = path

    def _get_name(self):
        return os.path.basename(self.path)

    name = property(_get_name)

    def chunks(self, chunk_size=None):
        yield open(self.path, "rb").read()


def test_validate_request():
    result = requests.read_file({})
    assert result["status"] == 400

    result = requests.read_file({"file1": "foo", "file2": "bar"})
    assert result["status"] == 400

    upload = UploadedFile("examples/antibodies-submission.xlsx")
    result = requests.read_file({"file": upload})
    assert result["status"] == 200
    table = workbooks.read_xlsx(result["content"], "Antibodies")
    assert table == []

    tf = tempfile.NamedTemporaryFile(suffix=".xlsx")
    tf.write(result["content"].getvalue())
    table = workbooks.read_xlsx(tf.name, "Antibodies")
    assert table == []
