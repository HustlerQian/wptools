# -*- coding:utf-8 -*-

"""
WPTools RESTBase module
~~~~~~~~~~~~~~~~~~~~~~~

Support for getting RESTBase page info.
"""

try:  # python2
    from urlparse import urlparse
except ImportError:  # python3
    from urllib.parse import urlparse

from . import core
from . import utils


class WPToolsRESTBase(core.WPTools):
    """
    WPtoolsRESTBase class
    """

    def __init__(self, *args, **kwargs):
        """
        Returns a WPToolsRESTBase object

        Optional positional {params}:
        - [title]: <str> Mediawiki page title, file, category, etc.

        Optional keyword {params}:
        - [endpoint]: the RESTBase entry point (default=/page/)
        - [lang]: <str> Mediawiki language code (default=en)

        Optional keyword {flags}:
        - [silent]: <bool> do not echo page data if True
        - [skip]: <list> skip actions in this list
        - [verbose]: <bool> verbose output to stderr if True
        """
        super(WPToolsRESTBase, self).__init__(*args, **kwargs)

        endpoint = self._parse_endpoint(kwargs.get('endpoint'),
                                        self.params.get('title'))

        self.params.update({'endpoint': endpoint})

    def _handle_response(self):
        """
        returns RESTBase response if appropriate
        """
        content = self.cache['restbase']['info']['content']
        if content.startswith('text/html'):
            html = self.cache['restbase']['response']
            if isinstance(html, bytes):
                html = html.decode('utf-8')
            self.data['html'] = html
            return

        response = self._load_response('restbase')

        http_status = self.cache['restbase']['info']['status']
        if http_status == 404:
            raise LookupError(self.cache['restbase']['query'])

        if self.params.get('endpoint') == '/page/':
            msg = "RESTBase /page/ entry points: %s" % response.get('items')
            utils.stderr(msg)
            del self.cache['restbase']
            return

        return response

    def _parse_endpoint(self, endpoint, title):
        """
        parse input endpoint
        """
        if not endpoint:
            return '/page/'

        parts = endpoint.split('/')
        parts = [x for x in parts if x]

        if not parts[0] == 'page':
            parts.insert(0, 'page')

        if len(parts) == 2:
            if title:
                parts.append(title)
            else:
                raise ValueError("need a title.")

        if len(parts) == 3:
            if title:  # check title
                if title != parts[2]:
                    raise ValueError("titles conflict.")
            else:
                self.params['title'] = parts[-1]

        return '/' + '/'.join(parts)

    def _query(self, action, qobj):
        """
        returns WPToolsQuery string from action
        """
        return qobj.restbase(self.params['endpoint'])

    def _set_data(self, action):
        """
        Sets RESTBase response data
        """
        self._set_restbase_data()

    def _set_restbase_data(self):
        res = self._handle_response()
        if res is None:
            return

        self.data['description'] = res.get('description')
        self.data['pageid'] = (res.get('id') or res.get('pageid'))
        self.data['exrest'] = res.get('extract')
        self.data['exhtml'] = res.get('extract_html')

        lastmodified = res.get('lastmodified')
        if lastmodified:
            pagemod = {'page': lastmodified}
            if 'modified' in self.data:
                self.data['modified'].update(pagemod)
            else:
                self.data['modified'] = pagemod

        if res.get('sections'):
            lead = res.get('sections')[0]
            self.data['lead'] = lead.get('text')

        title = res.get('title') or res.get('normalizedtitle')
        if title:
            self.data['title'] = title.replace(' ', '_')

        wikibase = res.get('wikibase_item')
        if wikibase:
            self.data['wikibase'] = wikibase
            self.data['wikidata_url'] = utils.wikidata_url(wikibase)

        url = urlparse(self.cache['restbase']['query'])
        durl = "%s://%s/wiki/%s" % (url.scheme,
                                    url.netloc,
                                    self.params['title'])
        self.data['url'] = durl
        self.data['url_raw'] = durl + '?action=raw'

        self._unpack_images(res)

    def _unpack_images(self, rdata):
        """
        Set image data from RESTBase response
        """
        image = rdata.get('image')  # /page/mobile-sections-lead
        originalimage = rdata.get('originalimage')  # /page/summary
        thumbnail = rdata.get('thumbnail')  # /page/summary

        if image or originalimage or thumbnail:
            if 'image' not in self.data:
                self.data['image'] = []

        if image:
            img = {'kind': 'restbase-image'}
            img.update(image)
            self.data['image'].append(img)

        if originalimage:
            img = {'kind': 'restbase-original'}
            img.update(originalimage)
            if originalimage.get('source'):
                img.update({'url': originalimage.get('source')})
            self.data['image'].append(img)

        if thumbnail:
            img = {'kind': 'restbase-thumb'}
            img.update(thumbnail)
            if thumbnail.get('source'):
                img.update({'url': thumbnail.get('source')})
            self.data['image'].append(img)

    def get_restbase(self, endpoint=None, show=True, proxy=None, timeout=0):
        """
        GET RESTBase /page/ endpoints needing only {title}
        https://en.wikipedia.org/api/rest_v1/

        for example:
            /page/html/{title}
            /page/summary/{title}
            /page/mobile-sections-lead/{title}

        Required {params}: None
        Without arguments, lists RESTBase /page/ entry points

        Optional {params}:
        - [title]: <str> Mediawiki page title, file, category, etc.
        - [endpoint]: the RESTBase entry point (default=/page/)
        - [lang]: <str> Mediawiki language code (default=en)

        Optional arguments:
        - [endpoint]: the RESTBase entry point (default=/page/)
        - [show]: <bool> echo page data if true
        - [proxy]: <str> use this HTTP proxy
        - [timeout]: <int> timeout in seconds (0=wait forever)

        Data captured:
        - exhtml: <str> "extract_html" from /page/summary
        - exrest: <str> "extract" from /page/summary
        - html: <str> from /page/html
        - image: <dict> {rest-image, rest-thumb}
        - lead: <str> section[0] from /page/mobile-sections-lead
        - modified (page): <str> ISO8601 date and time
        - title: <str> the article title
        - url: <str> the canonical wiki URL
        - url_raw: <str> probable raw wikitext URL
        - wikibase: <str> Wikidata item ID
        - wikidata_url: <str> Wikidata URL
        """
        if endpoint:
            endpoint = self._parse_endpoint(endpoint, self.params.get('title'))
            self.params.update({'endpoint': endpoint})

        self._get('restbase', show, proxy, timeout)

        return self
