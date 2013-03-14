#coding: utf-8
"""
markdown から変換した HTML に属性を追加する
"""

from markdown.util import etree
from markdown import treeprocessors
import markdown

class AttributeTreeprocessor(treeprocessors.Treeprocessor):
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

    def run(self, root):
        self._iterate(root, self._add_color_code)
        self._iterate(root, self._add_border_table)


class AttributeExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        md.treeprocessors['html_attribute'] = AttributeTreeprocessor(md)

def makeExtension(configs):
    return AttributeExtension(configs)
