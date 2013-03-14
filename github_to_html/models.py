#coding: utf-8
import json
from collections import namedtuple
import re
import subprocess
import requests
from pygithub3 import Github
from pygithub3.core.client import Client
import markdown

BASE_URL = 'https://sites.google.com/site/cpprefjpdummy'

def _md_to_html(md, paths):
    ext = 'github_to_html.qualified_fenced_code(base_url={base_url}, base_path={base_path}'.format(
        base_url=BASE_URL,
        base_path='/'.join(paths),
    )
    return markdown.markdown(unicode(md, encoding='utf-8'), [
        'tables',
        ext,
        'codehilite(noclasses=True)',
        'github_to_html.html_attribute'])

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

def get_html_content_by_path(paths):
    return {
        'title': paths[-1].split('.')[0],
        'html': _md_to_html(_get_file_from_path(paths), paths),
    }



DiffType = namedtuple('DiffType', ['command', 'path'])

def _git_diff():
    #こんな感じで差分が出せるはず。
    #subprocess.check_output(['git', 'diff', '--name-status', 'master', 'origin/master], cwd=...)

    # ひとまず毎回固定値で
    lines = ['M	README.md',
             'M	reference/atomic.md',
             'M	reference/atomic/atomic_flag_test_and_set_explicit.md',
             'M	reference/atomic/atomic_var_init.md',
             'M	reference/atomic/atomic_fetch_add_explicit.md',
             'M	reference/atomic/atomic.md',
             'M	reference/atomic/atomic_fetch_and_explicit.md',
             'M	reference/atomic/atomic_is_lock_free.md',
             'M	reference/atomic/atomic_load.md',
             'M	reference/atomic/atomic_thread_fence.md',
             'M	reference/atomic/atomic_fetch_sub.md',
             'M	reference/atomic/atomic_flag.md',
             'M	reference/atomic/atomic_flag/atomic_flag.md',
             'M	reference/atomic/atomic_flag/clear.md',
             'M	reference/atomic/atomic_flag/test_and_set.md',
             'M	reference/atomic/atomic_flag_clear_explicit.md',
             'M	reference/atomic/kill_dependency.md',
             'M	reference/atomic/atomic_store_explicit.md',
             'M	reference/atomic/atomic_fetch_xor_explicit.md',
             'M	reference/atomic/memory_order.md',
             'M	reference/atomic/lock_free_property.md',
             'M	reference/atomic/atomic_compare_exchange_strong.md',
             'M	reference/atomic/atomic_exchange.md',
             'M	reference/atomic/atomic_init.md',
             'M	reference/atomic/atomic_fetch_or.md',
             'M	reference/atomic/atomic_store.md',
             'M	reference/atomic/atomic_exchange_explicit.md',
             'M	reference/atomic/atomic_fetch_and.md',
             'M	reference/atomic/atomic_signal_fence.md',
             'M	reference/atomic/atomic/atomic.md',
             'M	reference/atomic/atomic/fetch_add.md',
             'M	reference/atomic/atomic/op_xor_assign.md',
             'M	reference/atomic/atomic/op_minus_assign.md',
             'M	reference/atomic/atomic/fetch_xor.md',
             'M	reference/atomic/atomic/compare_exchange_weak.md',
             'M	reference/atomic/atomic/fetch_sub.md',
             'M	reference/atomic/atomic/exchange.md',
             'M	reference/atomic/atomic/op_decrement.md',
             'M	reference/atomic/atomic/fetch_and.md',
             'M	reference/atomic/atomic/op_t.md',
             'M	reference/atomic/atomic/op_or_assign.md',
             'M	reference/atomic/atomic/is_lock_free.md',
             'M	reference/atomic/atomic/compare_exchange_strong.md',
             'M	reference/atomic/atomic/op_plus_assign.md',
             'M	reference/atomic/atomic/op_increment.md',
             'M	reference/atomic/atomic/op_assign.md',
             'M	reference/atomic/atomic/op_and_assign.md',
             'M	reference/atomic/atomic/load.md',
             'M	reference/atomic/atomic/store.md',
             'M	reference/atomic/atomic/fetch_or.md',
             'M	reference/atomic/atomic_fetch_xor.md',
             'M	reference/atomic/atomic_fetch_or_explicit.md',
             'M	reference/atomic/atomic_compare_exchange_weak.md',
             'M	reference/atomic/atomic_fetch_add.md',
             'M	reference/atomic/atomic_flag_test_and_set.md',
             'M	reference/atomic/atomic_flag_clear.md',
             'M	reference/atomic/atomic_compare_exchange_strong_explicit.md',
             'M	reference/atomic/atomic_load_explicit.md',
             'M	reference/atomic/atomic_flag_init.md',
             'M	reference/atomic/atomic_fetch_sub_explicit.md',
             'M	reference/atomic/atomic_compare_exchange_weak_explicit.md']
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
    """
    return _diff_to_contents(_git_diff())

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
