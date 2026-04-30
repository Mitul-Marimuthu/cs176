import os


class FileReader:
    def __init__(self, root):
        self.root = os.path.realpath(root)

    def _resolve(self, filepath):
        full = os.path.realpath(os.path.join(self.root, filepath.lstrip('/')))
        if full != self.root and not full.startswith(self.root + os.sep):
            return None
        return full

    def get(self, filepath, cookies):
        """
        Returns a binary string of the file contents, or None.
        """
        full = self._resolve(filepath)
        if full is None:
            return None
        if os.path.isdir(full):
            return f'<html><body><h1>{filepath}</h1></body></html>'.encode('utf-8')
        if os.path.isfile(full):
            with open(full, 'rb') as f:
                return f.read()
        return None

    def head(self, filepath, cookies):
        """
        Returns the size to be returned, or None.
        """
        content = self.get(filepath, cookies)
        if content is None:
            return None
        return len(content)
