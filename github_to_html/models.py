#coding: utf-8
import json
from collections import namedtuple
import re
import subprocess
from django.conf import settings
import requests
from pygithub3 import Github
from pygithub3.core.client import Client
import markdown

BASE_URL = 'https://sites.google.com/site/cpprefjpdummy'

def _md_to_html(md_data, paths):
    qualified_fenced_code = 'github_to_html.qualified_fenced_code'
    html_attribute = 'github_to_html.html_attribute(base_url={base_url}, base_path={base_path})'.format(
        base_url=BASE_URL,
        base_path='/'.join(paths[:-1]),
    )

    md = markdown.Markdown([
        'tables',
        qualified_fenced_code,
        'codehilite(noclasses=True)',
        html_attribute])
    md.safeMode = 'escape'
    return md.convert(unicode(md_data, encoding='utf-8'))

def _get_tree_by_path(trees, sha, path):
    result = trees.get(sha)
    for tree in result.tree:
        if tree['path'] == path:
            return tree

def _get_file_from_path(paths):
    access_token = open('.access_token').read()
    gh = Github(user='cpprefjp', repo='site', token=access_token)

    sha = 'HEAD'
    for path in paths:
        tree = _get_tree_by_path(gh.git_data.trees, sha, path)
        sha = tree['sha']
    assert tree['type'] == 'blob'

    blob = gh.git_data.blobs.get(sha)
    return blob.content.decode(encoding=blob.encoding)

_HASH_HEADER_RE = re.compile(r'^( *?\n)*#(?P<header>.*?)#*(\n|$)(?P<remain>(.|\n)*)', re.MULTILINE)
_SETEXT_HEADER_RE = re.compile(r'^( *?\n)*(?P<header>.*?)\n=+[ ]*(\n|$)(?P<remain>(.|\n)*)', re.MULTILINE)

def _split_title(md):
    r"""先頭の見出し部分を（あるなら）取り出す

    >>> md = '''
    ... # header
    ... 
    ... contents
    ... '''
    >>> _split_title(md)
    ('header', '\ncontents\n')

    >>> md = '''
    ... header
    ... ======
    ... 
    ... contents
    ... '''
    >>> _split_title(md)
    ('header', '\ncontents\n')

    >>> md = '''
    ... contents
    ... '''
    >>> _split_title(md)
    (None, '\ncontents\n')
    """
    m = _HASH_HEADER_RE.match(md)
    if m is None:
        m = _SETEXT_HEADER_RE.match(md)
    if m is None:
        return None, md
    return m.group('header').strip(), m.group('remain')

def get_html_content_by_path(paths):
    md = _get_file_from_path(paths)
    title, md = _split_title(md)
    if title is None:
        title = paths[-1].split('.')[0]
    return {
        'title': title,
        'html': _md_to_html(md, paths),
    }


DiffType = namedtuple('DiffType', ['command', 'path'])

def _git_diff():
    output = subprocess.check_output(['git', 'diff', '--name-status', settings.GIT_LOCAL_BRANCH, settings.GIT_REMOTE_BRANCH], cwd=settings.GIT_DIR)
    output = output.strip()
    if len(output) == 0:
        return []

    lines = output.split('\n')
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
        # 更新対象でないファイルは無視する
        if re.match('^([A-Z].*)|(.*!(\.md))$', paths[-1]):
            continue

        dic = contents
        for path in paths[:-1]:
            if path not in dic:
                dic[path] = {
                    "type": "directory",
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
    M	dir1.md
    M	dir1/file2.md
    D	dir1/file3.md
    M	UpperCaseFileIsIgnored.md
    D	ignored.if_extension_is_not_md

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
      "dir1.md": {
        "type": "file",
        "command": "update",
        "name": "dir1",
        "path": "dir1.md",
      },
      "dir1": {
        "type": "directory",
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

    >>> files = [
    ...     DiffType('M', 'file1.md'),
    ...     DiffType('A', 'file2.md'),
    ...     DiffType('M', 'dir1.md'),
    ...     DiffType('M', 'dir1/file2.md'),
    ...     DiffType('D', 'dir1/file3.md'),
    ...     DiffType('M', 'UpperCaseFileIsIgnored.md'),
    ...     DiffType('D', 'ignored.if_extension_is_not_md')]
    >>> _diff_to_contents(files)
    {'file1.md': {'command': 'update', 'type': 'file', 'name': 'file1', 'path': 'file1.md'}, 'dir1.md': {'command': 'update', 'type': 'file', 'name': 'dir1', 'path': 'dir1.md'}, 'dir1': {'type': 'directory', 'name': 'dir1', 'children': {'file2.md': {'command': 'update', 'type': 'file', 'name': 'file2', 'path': 'dir1/file2.md'}, 'file3.md': {'command': 'delete', 'type': 'file', 'name': 'file3', 'path': 'dir1/file3.md'}}}, 'file2.md': {'command': 'append', 'type': 'file', 'name': 'file2', 'path': 'file2.md'}, 'ignored.if_extension_is_not_md': {'command': 'delete', 'type': 'file', 'name': 'ignored', 'path': 'ignored.if_extension_is_not_md'}}
    """
    return _diff_to_contents(_git_diff())

def git_fetch():
    return subprocess.check_output(['git', 'fetch', settings.GIT_REMOTE], cwd=settings.GIT_DIR)

def git_merge():
    return subprocess.check_output(['git', 'merge', settings.GIT_REMOTE_BRANCH], cwd=settings.GIT_DIR)

def set_access_token(code):
    headers = {'Accept': 'application/json'}
    data = {
        'code': code,
        'client_id': '5163f9957aabe66d2ce4',
        'client_secret': open('.client_secret').read()[:-1],
    }
    r = requests.post('https://github.com/login/oauth/access_token', data=data, headers=headers)
    access_token = json.loads(r.text.encode('utf-8'))['access_token']
    open('.access_token', 'w').write(access_token)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
