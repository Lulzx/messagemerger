from bs4 import BeautifulSoup, NavigableString
import re
import six

convert_heading_re = re.compile(r'convert_h(\d+)')
line_beginning_re = re.compile(r'^', re.MULTILINE)
# whitespace_re = re.compile(r'[\r\n\s\t ]+')

# Heading styles
ATX = 'atx'
ATX_CLOSED = 'atx_closed'
UNDERLINED = 'underlined'
SETEXT = UNDERLINED


def chomp(text):
    prefix = ' ' if text and text[0] == ' ' else ''
    suffix = ' ' if text and text[-1] == ' ' else ''
    text = text.strip()
    return prefix, suffix, text


def _todict(obj):
    return dict((k, getattr(obj, k)) for k in dir(obj) if not k.startswith('_'))


class MarkdownConverter(object):
    class DefaultOptions:
        strip = None
        convert = None
        autolinks = True
        heading_style = UNDERLINED
        bullets = '*+-'  # An iterable of bullet types.

    class Options(DefaultOptions):
        pass

    def __init__(self, **options):
        self.options = _todict(self.DefaultOptions)
        self.options.update(_todict(self.Options))
        self.options.update(options)
        if self.options['strip'] is not None and self.options['convert'] is not None:
            raise ValueError('You may specify either tags to strip or tags to'
                             ' convert, but not both.')

    def convert(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        return self.process_tag(soup, children_only=True)

    def process_tag(self, node, children_only=False):
        text = ''

        # Convert the children first
        for el in node.children:
            if isinstance(el, NavigableString):
                text += self.process_text(six.text_type(el))
            else:
                text += self.process_tag(el)

        if not children_only:
            convert_fn = getattr(self, 'convert_%s' % node.name, None)
            if convert_fn and self.should_convert_tag(node.name):
                text = convert_fn(node, text)

        return text

    def process_text(self, text):
        return text

    def __getattr__(self, attr):
        # Handle headings
        m = convert_heading_re.match(attr)
        if m:
            n = int(m.group(1))

            def convert_tag(el, text):
                return self.convert_hn(n, el, text)

            convert_tag.__name__ = 'convert_h%s' % n
            setattr(self, convert_tag.__name__, convert_tag)
            return convert_tag

        raise AttributeError(attr)

    def should_convert_tag(self, tag):
        tag = tag.lower()
        strip = self.options['strip']
        convert = self.options['convert']
        if strip is not None:
            return tag not in strip
        elif convert is not None:
            return tag in convert
        else:
            return True

    def underline(self, text, pad_char):
        text = (text or '').rstrip()
        return '%s\n%s\n\n' % (text, pad_char * len(text)) if text else ''

    def convert_a(self, el, text):
        prefix, suffix, text = chomp(text)
        if not text:
            return ''
        href = el.get('href')
        title = el.get('title')
        if self.options['autolinks'] and text == href and not title:
            # Shortcut syntax
            return '<%s>' % href
        title_part = ' "%s"' % title.replace('"', r'\"') if title else ''
        return '%s[%s](%s%s)%s' % (prefix, text, href, title_part, suffix) if href else text

    def convert_b(self, el, text):
        return self.convert_strong(el, text)

    def convert_em(self, el, text):
        prefix, suffix, text = chomp(text)
        if not text:
            return ''
        return '%s__%s__%s' % (prefix, text, suffix)

    def convert_i(self, el, text):
        return self.convert_em(el, text)

    def convert_strong(self, el, text):
        prefix, suffix, text = chomp(text)
        if not text:
            return ''
        return '%s**%s**%s' % (prefix, text, suffix)

    def convert_code(self, el, text):
        prefix, suffix, text = chomp(text)
        if not text:
            return ''
        return '%s`%s`%s' % (prefix, text, suffix)
