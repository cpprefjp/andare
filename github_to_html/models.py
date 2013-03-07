import json
import requests
from pygithub3 import Github
from pygithub3.core.client import Client

def md_to_html(md):
    data = { 'text': md, 'mode': 'markdown' }

    client = Client()
    url = "%s%s" % (client.config['base_url'], 'markdown')
    response = requests.post(url, data=json.dumps(data))
    return response.content

def get_tree_by_path(trees, sha, path):
    result = trees.get(sha)
    for tree in result.tree:
        if tree['path'] == path:
            return tree

def get_file_from_path(paths):
    gh = Github(user='cpprefjp', repo='html_to_markdown')

    sha = 'HEAD'
    for path in paths:
        tree = get_tree_by_path(gh.git_data.trees, sha, path)
        sha = tree['sha']
    assert tree['type'] == 'blob'

    blob = gh.git_data.blobs.get(sha)
    return blob.content.decode(encoding=blob.encoding)

def get_html_from_path(paths):
    return md_to_html(get_file_from_path(paths))
