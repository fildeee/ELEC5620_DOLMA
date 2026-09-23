"""
The loopback exemption that lets OAuth complete over http://localhost.

oauthlib refuses to exchange an authorization code over plain HTTP, which would
otherwise make connecting Google impossible in local development: nobody serves
HTTPS on localhost. app.py relaxes that rule, but only for a callback that comes
back to this machine. These cover where the line is drawn, because a mistake here
would silently permit an unencrypted token exchange with a real remote host.
"""

import app as dolma_app

_is_loopback_http = dolma_app._is_loopback_http


def test_localhost_http_is_loopback():
    assert _is_loopback_http("http://localhost:5050/api/google/oauth2callback")


def test_ipv4_and_ipv6_loopback_literals_count():
    assert _is_loopback_http("http://127.0.0.1:5000/api/google/oauth2callback")
    assert _is_loopback_http("http://[::1]:5000/api/google/oauth2callback")


def test_remote_host_over_http_is_not_exempt():
    # The whole point: an unencrypted exchange with a real host stays refused.
    assert not _is_loopback_http("http://dolma.example.com/api/google/oauth2callback")


def test_hostname_merely_containing_localhost_is_not_exempt():
    assert not _is_loopback_http("http://localhost.example.com/api/google/oauth2callback")


def test_https_is_never_the_loopback_case():
    # Already secure, so it needs no exemption and must not be granted one.
    assert not _is_loopback_http("https://localhost:5050/api/google/oauth2callback")


def test_missing_or_malformed_urls_are_not_exempt():
    assert not _is_loopback_http(None)
    assert not _is_loopback_http("")
    assert not _is_loopback_http("not a url")


def test_the_exemption_is_applied_for_the_default_redirect_uri():
    # app.py ran the check at import; the default redirect URI is loopback, so
    # the exchange in google_oauth2callback will be permitted.
    import os
    assert _is_loopback_http(dolma_app.REDIRECT_URI)
    assert os.environ.get("OAUTHLIB_INSECURE_TRANSPORT") == "1"
