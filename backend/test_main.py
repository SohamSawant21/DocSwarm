import unittest
from main import build_file_tree

class TestBuildFileTree(unittest.TestCase):

    def test_basic_tree(self):
        paths = ["a/b/c.js", "a/d.js", "e.js"]
        tree = build_file_tree(paths)
        
        # Expected structure
        # a (folder)
        #   b (folder)
        #     c.js (file)
        #   d.js (file)
        # e.js (file)
        
        self.assertEqual(len(tree), 2)
        
        self.assertEqual(tree[0]["name"], "a")
        self.assertEqual(tree[0]["type"], "folder")
        
        self.assertEqual(tree[1]["name"], "e.js")
        self.assertEqual(tree[1]["type"], "file")
        self.assertEqual(tree[1]["path"], "e.js")
        
        # Check children of 'a'
        a_children = tree[0]["children"]
        self.assertEqual(len(a_children), 2)
        self.assertEqual(a_children[0]["name"], "b")
        self.assertEqual(a_children[0]["type"], "folder")
        
        self.assertEqual(a_children[1]["name"], "d.js")
        self.assertEqual(a_children[1]["type"], "file")
        self.assertEqual(a_children[1]["path"], "a/d.js")
        
        # Check children of 'b'
        b_children = a_children[0]["children"]
        self.assertEqual(len(b_children), 1)
        self.assertEqual(b_children[0]["name"], "c.js")
        self.assertEqual(b_children[0]["type"], "file")
        self.assertEqual(b_children[0]["path"], "a/b/c.js")

    def test_sorting(self):
        paths = ["folder_b/file.js", "folder_a/file.js", "root_file_b.js", "root_file_a.js"]
        tree = build_file_tree(paths)
        
        # Folders first, then alphabetically
        self.assertEqual(tree[0]["name"], "folder_a")
        self.assertEqual(tree[1]["name"], "folder_b")
        self.assertEqual(tree[2]["name"], "root_file_a.js")
        self.assertEqual(tree[3]["name"], "root_file_b.js")

    def test_special_characters_and_deep_nesting(self):
        paths = ["@org/package-name/src/index.ts", ".github/workflows/ci.yml"]
        tree = build_file_tree(paths)
        
        self.assertEqual(tree[0]["name"], ".github")
        self.assertEqual(tree[1]["name"], "@org")
        
        # .github/workflows/ci.yml
        self.assertEqual(tree[0]["children"][0]["name"], "workflows")
        self.assertEqual(tree[0]["children"][0]["children"][0]["name"], "ci.yml")
        self.assertEqual(tree[0]["children"][0]["children"][0]["path"], ".github/workflows/ci.yml")

    def test_duplicate_names_in_different_directories(self):
        paths = ["src/index.js", "tests/index.js", "index.js"]
        tree = build_file_tree(paths)
        
        self.assertEqual(len(tree), 3)
        self.assertEqual(tree[0]["name"], "src")
        self.assertEqual(tree[1]["name"], "tests")
        self.assertEqual(tree[2]["name"], "index.js")
        
        self.assertEqual(tree[0]["children"][0]["name"], "index.js")
        self.assertEqual(tree[0]["children"][0]["path"], "src/index.js")
        
        self.assertEqual(tree[1]["children"][0]["name"], "index.js")
        self.assertEqual(tree[1]["children"][0]["path"], "tests/index.js")

if __name__ == '__main__':
    unittest.main()
