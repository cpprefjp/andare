#coding: utf-8
import json
from collections import namedtuple
import subprocess
import requests
from pygithub3 import Github
from pygithub3.core.client import Client

def _md_to_html(md):
    data = { 'text': md, 'mode': 'markdown' }

    client = Client()
    url = "%s%s" % (client.config['base_url'], 'markdown')
    response = requests.post(url, data=json.dumps(data))
    return response.content

def _get_tree_by_path(trees, sha, path):
    result = trees.get(sha)
    for tree in result.tree:
        if tree['path'] == path:
            return tree

def _get_file_from_path(paths):
    gh = Github(user='cpprefjp', repo='html_to_markdown')

    sha = 'HEAD'
    for path in paths:
        tree = _get_tree_by_path(gh.git_data.trees, sha, path)
        sha = tree['sha']
    assert tree['type'] == 'blob'

    blob = gh.git_data.blobs.get(sha)
    return blob.content.decode(encoding=blob.encoding)

def get_html_content_by_path(paths):
    return {
        'title': paths[-1].split('.')[0],
        'html': _md_to_html(_get_file_from_path(paths)),
    }



DiffType = namedtuple('DiffType', ['command', 'path'])

def _git_diff():
    #こんな感じで差分が出せるはず。
    #subprocess.check_output(['git', 'diff', '--name-status', 'master', 'origin/master], cwd=...)

    # ひとまず毎回固定値で
    lines = ['M	fetch_add.md',
             'M	advance.md']
    #lines = ['M	file1',
    #         'A	file2',
    #         'M	dir1/file2',
    #         'D	dir1/file3']
    return [DiffType(*t.split('\t')) for t in lines]

def _diff_to_contents(diff_type_list):
    contents = { }
    def to_longname(command):
        lookup = {
            'A': 'append',
            'M': 'update',
            'D': 'delete',
        }
        return lookup[command]

    def to_name(path):
        return path.split('.')[0]

    for dt in diff_type_list:
        paths = dt.path.split('/')
        dic = contents
        for path in paths[:-1]:
            if path not in dic:
                dic[path] = {
                    "type": "directory",
                    "command": "nothing", #TODO
                    "name": to_name(path),
                    "children": { },
                }
            dic = dic[path]["children"]
        dic[paths[-1]] = {
            "type": "file",
            "command": to_longname(dt.command),
            "name": to_name(paths[-1]),
            "path": dt.path,
        }

    return contents

def get_update_contents():
    """
    origin/master との差分を調べて、どのファイルを更新すればいいのかを返す

    $ git diff --name-status master origin/master
    M	file1.md
    A	file2.md
    M	dir1/file2.md
    D	dir1/file3.md

    このデータから、こんな感じのデータを生成する。

    {
      "file1.md": {
        "type": "file",
        "command": "update",
        "name": "file1",
        "path": "file1.md"
      },
      "file2.md": {
        "type": "file",
        "command": "append",
        "name": "file2"
        "path": "file2.md"
      },
      "dir1": {
        "type": "directory",
        "command": "nothing",
        "name": "dir1",
        "children": {
          "file2.md": {
            "type": "file",
            "command": "update",
            "name": "file2"
            "path": "dir1/file2.md"
          },
          "file3.md": {
            "type": "file",
            "command": "delete",
            "name": "file3"
            "path": "dir1/file3.md"
          }
        }
      }
    }
    """
    return _diff_to_contents(_git_diff())
