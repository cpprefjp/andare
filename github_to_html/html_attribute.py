#coding: utf-8
from __future__ import unicode_literals
"""
markdown から変換した HTML に属性を追加する
"""

from markdown.util import etree
from markdown import postprocessors
import markdown

class AttributePostprocessor(postprocessors.Postprocessor):
    def __init__(self, md):
        postprocessors.Postprocessor.__init__(self, md)
        self._markdown = md

    def _iterate(self, elements, f):
        f(elements)
        for child in elements.getchildren():
            self._iterate(child, f)

    def _add_color_code(self, element):
        if element.tag == 'code':
            text = element.text
            element.text = ''
            e = etree.SubElement(element, 'span', style='color: #000')
            e.text = text

    def _add_border_table(self, element):
        if element.tag == 'table':
            element.attrib['border'] = '1'
            element.attrib['bordercolor'] = '#888'
            element.attrib['style'] = 'border-collapse:collapse'

    def _to_absolute_url(self, element):
        if element.tag == 'a':
            base_url = self.config['base_url'].strip('/')
            base_paths = self.config['base_path'].strip('/').split('/')

            url = element.attrib['href']
            if url.startswith('http://') or url.startswith('https://'):
                # 絶対パス
                base_url_body = base_url.split('//', 2)[1]
                url_body = url.split('//', 2)[1]
                # 別ドメインの場合は別タブで開く
                if not url_body.startswith(base_url_body):
                    element.attrib['target'] = '_blank'
            elif url.startswith('/'):
                # サイト内絶対パス
                element.attrib['href'] = base_url + url
            else:
                # サイト内相対パス
                paths = base_paths
                for p in url.split('/'):
                    if p == '':
                        continue
                    elif p == '.':
                        continue
                    elif p == '..':
                        paths = paths[:-1]
                    else:
                        paths.append(p)
                element.attrib['href'] = base_url + '/' + '/'.join(paths)

    def run(self, text):
        text = '<{tag}>{text}</{tag}>'.format(tag=self._markdown.doc_tag, text=text)
        root = etree.fromstring(text.encode('utf-8'))
        self._iterate(root, self._add_color_code)
        self._iterate(root, self._add_border_table)
        self._iterate(root, self._to_absolute_url)

        output = self._markdown.serializer(root)
        if self._markdown.stripTopLevelTags:
            try:
                start = output.index('<%s>'%self._markdown.doc_tag)+len(self._markdown.doc_tag)+2
                end = output.rindex('</%s>'%self._markdown.doc_tag)
                output = output[start:end].strip()
            except ValueError:
                if output.strip().endswith('<%s />'%self._markdown.doc_tag):
                    # We have an empty document
                    output = ''
                else:
                    # We have a serious problem
                    raise ValueError('Markdown failed to strip top-level tags. Document=%r' % output.strip())
        return output

class AttributeExtension(markdown.Extension):
    def __init__(self, configs):
        # デフォルトの設定
        self.config = {
            'base_url' : [None, "Base URL used to link URL as absolute URL"],
            'base_path' : [None, "Base Path used to link URL as relative URL"],
        }

        # ユーザ設定で上書き
        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        attr = AttributePostprocessor(md)
        attr.config = self.getConfigs()
        md.postprocessors.add('html_attribute', attr, '_end')

def makeExtension(configs):
    return AttributeExtension(configs)
