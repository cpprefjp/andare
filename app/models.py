#coding: utf-8
import os
import json
import datetime
from collections import namedtuple
import re
import subprocess
from django.conf import settings
import requests
from pygithub3 import Github
from pygithub3.core.client import Client
import markdown

BASE_URL = 'https://sites.google.com/site/cpprefjp'
TARGET_GITHUB_USER = 'cpprefjp'
TARGET_GITHUB_REPO = 'site'

def _md_to_html(md_data, paths):
    qualified_fenced_code = 'markdown_to_html.qualified_fenced_code'
    html_attribute = 'markdown_to_html.html_attribute(base_url={base_url}, base_path={base_path}, full_path={full_path})'.format(
        base_url=BASE_URL,
        base_path='/'.join(paths[:-1]),
        full_path='/'.join(paths),
    )
    footer = 'markdown_to_html.footer(url={url})'.format(
        url='https://github.com/cpprefjp/site/edit/master/{paths}'.format(
            paths='/'.join(paths),
        )
    )

    md = markdown.Markdown([
        'tables',
        qualified_fenced_code,
        'codehilite(noclasses=True)',
        html_attribute,
        footer])
    return md.convert(unicode(md_data, encoding='utf-8'))

def _get_tree_by_path(trees, sha, path):
    result = trees.get(sha)
    for tree in result.tree:
        if tree['path'] == path:
            return tree

def _get_file_from_path(paths):
    access_token = open('.access_token').read()
    gh = Github(user=TARGET_GITHUB_USER, repo=TARGET_GITHUB_REPO, token=access_token)

    sha = 'HEAD'
    for path in paths:
        tree = _get_tree_by_path(gh.git_data.trees, sha, path)
        sha = tree['sha']
    assert tree['type'] == 'blob'

    blob = gh.git_data.blobs.get(sha)
    return blob.content.decode(encoding=blob.encoding)

def _get_file_from_path_local(paths):
    git_checkout(settings.GIT_LOCAL_FETCHED)
    path = os.path.join(settings.GIT_DIR, *paths)
    return open(path).read()

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

def _get_html_content(paths, get_file):
    md = get_file(paths)
    title, md = _split_title(md)
    if title is None:
        title = paths[-1].split('.')[0]
    return {
        'title': title,
        'html': _md_to_html(md, paths),
    }

def get_latest_html_content_by_path(paths):
    return _get_html_content(paths, _get_file_from_path)

def get_html_content_by_path(paths):
    return _get_html_content(paths, _get_file_from_path_local)


DiffType = namedtuple('DiffType', ['command', 'path'])

def _git_diff():
    output = subprocess.check_output(['git', 'diff', '--name-status', settings.GIT_LOCAL_BRANCH, settings.GIT_REMOTE_BRANCH], cwd=settings.GIT_DIR)
    output = output.strip()
    if len(output) == 0:
        return []

    lines = output.split('\n')
    return [DiffType(*t.split('\t')) for t in lines]

def _diff_all():
    git_checkout(settings.GIT_LOCAL_FETCHED)
    output = subprocess.check_output(['git', 'ls-files'], cwd=settings.GIT_DIR)
    output = output.strip()
    if len(output) == 0:
        return []

    paths = output.split('\n')
    return [DiffType(command='M', path=path) for path in paths]

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

def get_all_contents():
    return _diff_to_contents(_diff_all())

def git_fetch(branch):
    return subprocess.check_output(['git', 'fetch', branch], cwd=settings.GIT_DIR)

def git_checkout(branch):
    return subprocess.check_output(['git', 'checkout', '-q', branch], cwd=settings.GIT_DIR)

def git_merge(branch):
    return subprocess.check_output(['git', 'merge', branch], cwd=settings.GIT_DIR)

def get_commit_id(branch):
    git_checkout(branch)
    return subprocess.check_output(['git', 'log', '-1', 'HEAD', '--pretty=format:%H'], cwd=settings.GIT_DIR)

TITLE_FORMAT = 'Update Error: {commit_id}'

def resolve_errors():
    commit_id = get_commit_id(settings.GIT_LOCAL_BRANCH)
    title = TITLE_FORMAT.format(commit_id=commit_id)

    access_token = open('.access_token').read()
    gh = Github(user=TARGET_GITHUB_USER, repo=TARGET_GITHUB_REPO, token=access_token)
    issues = gh.issues.list_by_repo(milestone=None, assignee=None)
    for issue in issues.all():
        if title == issue.title:
            # 自動で閉じる
            body = (
                '\n\n'
                '---- Closed by andare ----\n'
                '修正が確認されたので Close します。'
            )
            gh.issues.update(issue.number, {
                'state': 'close',
                'body': issue.body.encode('utf-8') + body,
            })
            break

def register_errors(errors, next_trigger_at):
    commit_id = get_commit_id(settings.GIT_LOCAL_BRANCH)
    title = TITLE_FORMAT.format(commit_id=commit_id)

    urls = ['| [/{error}](/cpprefjp/site/blob/master/{error}) | [check_site](http://melpon.org/andare/view/{error}) |'.format(error=error) for error in errors]

    access_token = open('.access_token').read()
    gh = Github(user=TARGET_GITHUB_USER, repo=TARGET_GITHUB_REPO, token=access_token)
    issues = gh.issues.list_by_repo(milestone=None, assignee=None)
    for issue in issues.all():
        if title == issue.title:
            # 更新する
            body = issue.body.encode('utf-8')
            body += (
                '\n\n'
                '---- Updated At {date} ----\n'
                'まだ修正されていないファイルがあります。\n'
                '\n'
                '|ファイル|チェックサイト|\n'
                '|--------|--------------|\n'
            ).format(date=datetime.datetime.now())
            body += '\n'.join(urls)
            body += (
                '\n\n'
                '次の自動実行は [{datetime}] に行われます。\n'
            ).format(datetime=next_trigger_at)

            gh.issues.update(issue.number, {
                'title': issue.title,
                'body': body,
            })
            break
    else:
        body = (
            '自動更新に失敗しました。\n'
            '\n'
            '以下の『ファイル』を更新し、『チェックサイト』のページを開いてもエラーが出ないことを確認して下さい。\n'
            '\n'
            '|ファイル|チェックサイト|\n'
            '|--------|--------------|\n'
        )
        body += '\n'.join(urls)
        body += (
            '\n\n'
            '次の自動実行は [{datetime}] に行われます。\n'
        ).format(datetime=next_trigger_at)
        # 新規作成
        gh.issues.create({
            'title': title,
            'body': body,
        })

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
