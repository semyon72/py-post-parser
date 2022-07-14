# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: ssl_provider.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

from urllib.request import urlopen, Request
from urllib.parse import urlparse
from http.client import HTTPResponse
from urllib.error import URLError
import ssl

# By default it is suitable for client to server connection
# where /home/ox23/openssl-ca/blog-ca/blog.crt is certificate of requested URL (site)
# ssl_context = ssl.create_default_context(cafile='/home/ox23/openssl-ca/blog-ca/blog.crt')
# Or need to switch into ignore root certificate authority mode
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE


def context_reset():
    get_context.context = ssl.create_default_context()
    return get_context.context


def get_context(addr=None, *, cafile=None):
    """
        Common usages
        get_context((ip_or_host, port)) - will get a server certificate and add it to the current context CA
        get_context.reset() - will reset the current context to the default state
        get_context() - It just returns a current context
    """
    context = get_context.context
    if cafile:
        context.load_verify_locations(cafile=cafile)
    elif addr:
        chn, vm = (context.check_hostname, context.verify_mode)
        try:
            context.check_hostname, context.verify_mode = (False, ssl.CERT_NONE)
            context.load_verify_locations(cadata=ssl.get_server_certificate(addr))
        finally:
            context.check_hostname, context.verify_mode = (chn, vm)

    return context


get_context.context = ssl.create_default_context()
get_context.reset = context_reset
get_context.ca_certs = lambda binary_form=False: get_context.context.get_ca_certs(binary_form)


class GetResponse:
    """
        Main usage:
            host = 'blog.lan'
            url = 'https://{0}/entry/9/?text=1'.format(host)

            gresp = GetResponse(url, False)

            server_cert = '/home/ox23/openssl-ca/blog-ca/blog.crt'
            # this should good
            resp = gresp._get_response(url, context=ssl.create_default_context(cafile=server_cert))
            print(resp.read())

            try:
                # this should fail cause gresp._allow_self_signed_cert = False
                print(gresp.process().read())
            except Exception as err:
                print('##### Exception #####')
                print(err)

            # this one should also good
            gresp._allow_self_signed_cert = True
            print(gresp.process().read())

        If GetResponse(url, False) it will raise exception if certificate self-signed,
        have no trusted cert in system or context does not configured properly

    """
    _url = ''
    _allow_self_signed_cert = False

    def __init__(self, url, allow_self_signed_cert=True) -> None:
        self._url = url
        self._allow_self_signed_cert = bool(allow_self_signed_cert)

    @staticmethod
    def _get_ssl_addr(url):
        if isinstance(url, Request):
            url = url.full_url
        o = urlparse(url)
        if o.scheme == 'https':
            port = 443
            if o.port:
                port = o.port
        else:
            if o.port in (443, 4433):
                port = o.port
            else:
                return None
        return o.hostname, port

    def _self_signed_fallback(self, err, ssl_addr):
        if not self._allow_self_signed_cert:
            raise err

        reason = err
        if isinstance(err, URLError):
            reason = err.reason
        if isinstance(reason, ssl.SSLCertVerificationError) and reason.errno == 1 \
                and reason.verify_code == 18 and reason.verify_message == 'self signed certificate':
            print('Certificate is self-signed: so used as one time CA.')
        else:
            raise err

        return get_context(ssl_addr)

    def _get_response(self, url):
        context = get_context()

        ssl_addr = self._get_ssl_addr(url)
        if ssl_addr is None:
            # does not look like SSL connection
            context = None

        try:
            # if context exists then test self signed cert
            response = urlopen(url, context=context)
        except (URLError, ssl.SSLCertVerificationError) as err:
            self._self_signed_fallback(err, ssl_addr)
            response = urlopen(url, context=context)

        return response

    def process(self) -> HTTPResponse:
        return self._get_response(self._url)


if __name__ == '__main__':

    host = 'blog.lan'
    url = 'https://{0}:443/entry/9/?text=1'.format(host)

    gresp = GetResponse(url, False)

    try:
        # this should fail cause gresp._allow_self_signed_cert = False
        print(gresp.process().read())
    except Exception as err:
        print('##### Exception #####')
        print(err)

    # this should also good
    gresp._allow_self_signed_cert = True
    print(gresp.process().read())

    get_context(cafile='/home/ox23/openssl-ca/blog-ca/blog.crt')

    # this should good
    resp = gresp._get_response(url)
    print(resp.read())

    print(len(get_context().get_ca_certs()))
