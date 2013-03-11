#coding: utf-8
from __future__ import unicode_literals
"""
Fenced Code Extension の改造版
=========================================

github でのコードブロック記法が使える。

    >>> text = '''
    ... `````
    ... # コードをここに書く
    ... x = 10
    ... `````'''
    >>> print markdown.markdown(text, extensions=['qualified_fenced_code'])
    <pre><code># コードをここに書く
    x = 10
    </code></pre>

かつ、これらのコードに修飾ができる。

    >>> text = '''
    ... ```
    ... x = [3, 2, 1]
    ... y = sorted(x)
    ... x.sort()
    ... ```
    ... sorted[color: ff0000]
    ... sort[link: http://example.com/]
    ... '''
    >>> print markdown.markdown(text, extensions=['qualified_fenced_code'])
"""

from __future__ import absolute_import
import re
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.util import Processor
from markdown.extensions.codehilite import CodeHilite, CodeHiliteExtension

CODE_WRAP = '<pre><code%s>%s</code></pre>'
LANG_TAG = ' class="%s"'

FENCED_BLOCK_RE = re.compile( \
    r'(?P<fence>^(?:~{3,}|`{3,}))[ ]*(\{?\.?(?P<lang>[a-zA-Z0-9_+-]*)\}?)?[ ]*\n(?P<code>.*?)(?<=\n)(?P=fence)[ ]*$',
        re.MULTILINE|re.DOTALL
            )

QUALIFIED_FENCED_BLOCK_RE = re.compile(r'(?P<fence>`{3,})[ ]*(?P<lang>[a-zA-Z0-9_+-]*)[ ]*\n(?P<code>.*?)(?<=\n)(?P=fence)[ ]*\n(\n|(?P<qualifies>.*?\n\n))', re.MULTILINE|re.DOTALL)

class QualifiedFencedCodeExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)

        md.preprocessors.add('qualified_fenced_code',
                                 QualifiedFencedBlockPreprocessor(md),
                                 "_begin")

def multiple_replace(text,adict):
    if len(adict) == 0:
        return text
    import re
    rx = re.compile('|'.join(map(re.escape, adict)))
    def one_xlat(match):
        return adict[match.group(0)]
    return rx.sub(one_xlat, text)

QUALIFY_RE = re.compile(r'^(?P<target>.*?)(?P<commands>(\<.*?\>)*)$')
QUALIFY_COMMAND_RE = re.compile(r'\<(.*?)\>')

def _make_random_string():
    import string
    from random import randrange
    alphabets = string.ascii_letters
    return ''.join(alphabets[randrange(len(alphabets))] for i in xrange(32))

class Qualifier(object):
    def __init__(self, line):
        # parsing
        m = QUALIFY_RE.search(line)
        if m:
            self._target_re = re.compile('(?<=[^a-zA-Z_]){target}(?=[^a-zA-Z_])'.format(
                target=m.group('target')
            ))
            self._commands = { }
            def f(match):
                self._commands[_make_random_string()] = match.group(1)
            QUALIFY_COMMAND_RE.sub(f, m.group('commands'))

    def mark(self, code):
        def mark_command(match):
            text = match.group(0)
            for name,command in self._commands.iteritems():
                text = '%(unique_id)s %(command)s %(original)s %(unique_id)s' % {
                    'unique_id': name,
                    'command': command.encode('base64').replace('=', '_'),
                    'original': text,
                }
            return text
        x = self._target_re.sub(mark_command, code)
        return x

    def qualify(self, html):
        def _qualify_italic(*xs):
            return '<i>{0}</i>'.format(*xs)
        def _qualify_color(*xs):
            return '<span style="color:#{1}">{0}</span>'.format(*xs)
        def _qualify_link(*xs):
            return '<a href="{1}">{0}</a>'.format(*xs)
        qualify_dic = {
            'italic': _qualify_italic,
            'color': _qualify_color,
            'link': _qualify_link,
        }

        for name,command in self._commands.iteritems():
            marked_re = re.compile('%(unique_id)s %(command)s (?P<original>.*?)( %(unique_id)s)' % {
                'unique_id': re.escape(name),
                'command': re.escape(command.encode('base64').replace('=', '_')),
            })
            def replace(match):
                xs = command.split(' ')
                c = xs[0]
                remain = xs[1:]
                return qualify_dic[c](match.group('original'), *remain)
            html = marked_re.sub(replace, html)
        return html

class QualifiedFencedBlockPreprocessor(Preprocessor):

    def __init__(self, md):
        Preprocessor.__init__(self, md)

        self.checked_for_codehilite = False
        self.codehilite_conf = {}

    def run(self, lines):
        # Check for code hilite extension
        if not self.checked_for_codehilite:
            for ext in self.markdown.registeredExtensions:
                if isinstance(ext, CodeHiliteExtension):
                    self.codehilite_conf = ext.config
                    break

            self.checked_for_codehilite = True

        text = "\n".join(lines)
        while 1:
            m = QUALIFIED_FENCED_BLOCK_RE.search(text)
            if m:
                qualifies = m.group('qualifies') or ''
                qualifies = filter(None, qualifies.split('\n'))
                qualifies = set(qualifies)
                code = m.group('code')
                qualifiers = [Qualifier(qualify) for qualify in qualifies]
                for q in qualifiers:
                    code = q.mark(code)

                # If config is not empty, then the codehighlite extension
                # is enabled, so we call it to highlite the code
                if self.codehilite_conf:
                    highliter = CodeHilite(code,
                            linenos=self.codehilite_conf['force_linenos'][0],
                            guess_lang=self.codehilite_conf['guess_lang'][0],
                            css_class=self.codehilite_conf['css_class'][0],
                            style=self.codehilite_conf['pygments_style'][0],
                            lang=(m.group('lang') or None),
                            noclasses=self.codehilite_conf['noclasses'][0])

                    code = highliter.hilite()
                else:
                    lang = ''
                    if m.group('lang'):
                        lang = LANG_TAG % m.group('lang')

                    code = CODE_WRAP % (lang, self._escape(code))

                for q in qualifiers:
                    code = q.qualify(code)

                placeholder = self.markdown.htmlStash.store(code, safe=True)
                text = '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])
            else:
                break
        return text.split("\n")

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(configs=None):
    return QualifiedFencedCodeExtension(configs=configs)
