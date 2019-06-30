
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from bs4.element import Tag
from urllib.parse import urlparse
from difflib import SequenceMatcher
from dateutil import parser as dateutil
from datetime import datetime
from json import dumps

important_tags = ['p', 'ul', 'ol', 'img'] + \
                 ['h' + str(i) for i in range(1, 7)] + \
                 ['a', 'blockquote']

"""
From the soup object, get the container with the content.
"""
def get_article_container(soup):
    text_size = len(soup.get_text().split())
    p_elems = soup('p')

    largest_p = soup
    largest_p_size = 0

    if not len(p_elems):
        p_elems = soup('div')

    for p_elem in p_elems:
        p_text_size = len(p_elem.get_text().split())
        if p_text_size > largest_p_size:
            largest_p_size = p_text_size
            largest_p = p_elem

    while largest_p.parent:
        largest_p = largest_p.parent
        captured_words = len(largest_p.get_text().split())
        if captured_words * 2 > text_size:
            break

    return largest_p

"""
Tells if higher is a descendant of lower. If higher == lower,
we return false.
"""
def tag_is_descendant(higher, lower):
    while lower.parent:
        lower = lower.parent
        if lower == higher:
            return True

    return False

"""
Matching <title> to <h1>
"""
def title_match_builder(title):
    def title_matcher(tag):
        if tag.name not in ['h1']:
            return False
        
        if not tag.string:
            return False

        matcher = SequenceMatcher(None, tag.string, title)
        match = matcher.find_longest_match(0, len(tag.string), 0, len(title))

        if match.size < 20:
            return False

        return True

    return title_matcher

"""
Given the soup object, find the article title tag.
"""
def get_title_tag(soup):
    title = soup('title')[0].string.strip()
    results = soup(title_match_builder(title))

    if len(results):
        return results[0]

    return None

"""
Extracts date from a tag.
"""
def get_date_from_tag(tag):
    if not tag.string:
        return None

    try:
        d = dateutil.parse(tag.string)
        result = d.strftime('%B %-d, %Y')
    except ValueError:
        result = None

    return result

"""
Given the title tag, find the date of the article.
"""
def get_date_string(title):
    search_space = title.parent

    while search_space is not None:
        possible_tags = search_space.find_all(
            lambda tag: get_date_from_tag(tag) is not None
        )

        if len(possible_tags):
            return get_date_from_tag(possible_tags[0])

        search_space = search_space.parent

    return None

"""
From the article content, get the sequence of important tags
"""
def get_tag_sequence(soup):
    seq = soup(important_tags)

    mark_delete = set()
    for tag in seq:
        for i in range(len(seq)):
            if tag_is_descendant(tag, seq[i]) and i not in mark_delete:
                mark_delete.add(i)

    for elem in mark_delete:
        seq[elem] = None

    seq = [item for item in seq if item]

    return seq

"""
Given a URL string, convert it so it contains the domain name.
"""
def convert_url_string(req_url, string):
    parsed = urlparse(req_url)

    if not len(string):
        return ''
    if string.startswith('https://') or string.startswith('http://'):
        # Is a regular url. We are good
        return string
    elif string.startswith('/'):
        # Should be resolved relative to the hostname
        return parsed.scheme + '://' + parsed.netloc + string
    else:
        # Should be resolved relative to the request url
        if req_url.endswith('/'):
            return req_url + string
        else:
            return req_url + '/' + string

"""
Given a tag, convert it to markdown.
"""
def convert_one_tag(req_url, tag):
    name = str(tag.name).lower()

    if isinstance(tag, NavigableString):
        return str(tag).strip()
    if name == 'p':
        return convert_tags(req_url, tag.children) + '\n\n'
    elif name == 'h1':
        return '# ' + convert_tags(req_url, tag.children) + '\n'
    elif name == 'h2':
        return '## ' + convert_tags(req_url, tag.children) + '\n'
    elif name == 'h3':
        return '## ' + convert_tags(req_url, tag.children) + '\n'
    elif name == 'h4':
        return '## ' + convert_tags(req_url, tag.children) + '\n'
    elif name == 'h5':
        return '### ' + convert_tags(req_url, tag.children) + '\n'
    elif name == 'h6':
        return '#### ' + convert_tags(req_url, tag.children) + '\n'
    elif name == 'img' or name == 'image':
        return '![image not found](' + convert_url_string(
                                            req_url, tag.get('src', '')) + ')'
    elif name == 'a':
        return '[' + convert_tags(req_url, tag.children) + '](' + \
               convert_url_string(req_url, tag.get('href', '')) + ')'
    elif name == 'blockquote':
        return '> ' + convert_tags(req_url, tag.children) + '\n\n'
    else:
        return ''

"""
Given a list of tags, convert them to markdown. Mutually recursive
with convert_one_tag.
"""
def convert_tags(req_url, tags):
    return ' '.join(convert_one_tag(req_url, tag) for tag in tags)

"""
Main method to turn the HTML into markdown.
Returns (title, date, content) tuple
"""
def churn(req_url, body):
    soup = BeautifulSoup(body, 'html.parser')

    for kill in soup(['script', 'style']):
        kill.decompose()

    t = get_article_container(soup)
    seq = get_tag_sequence(t)
    h = get_title_tag(soup)
    d = get_date_string(h)

    return h.string.strip(), d, convert_tags(req_url, seq)
