#!/usr/bin/env python
#
#   Copyright (c) 2011-2012 Canonical Ltd.
#
#   This file is part of: SST (selenium-simple-test)
#   https://launchpad.net/selenium-simple-test
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

"""
Tests are comprised of Python scripts. Files whose names begin with an
underscore will *not* be executed as test scripts.

Test scripts drive the browser with Selenium WebDriver by importing and
using SST actions.

The standard set of actions are imported by starting the test scripts with::

    from sst.actions import *


Actions that work on page elements take either an element id or an
element object as their first argument. If the element you are working with
doesn't have a specific id you can get the element object with the
`get_element` action. `get_element` allows you to find an element by its
id, tag, text, class or other attributes. See the `get_element` documentation.
"""


import os
import re
import time

from datetime import datetime
from pdb import set_trace as debug

from unittest2 import SkipTest

from selenium import webdriver
from selenium.webdriver.common import keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException, NoSuchAttributeException,
    InvalidElementStateException, WebDriverException,
    NoSuchWindowException, NoSuchFrameException)
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from sst import config
from sst import bmobproxy


__all__ = [
    'accept_alert', 'assert_attribute', 'assert_button', 'assert_checkbox',
    'assert_checkbox_value', 'assert_css_property', 'assert_displayed',
    'assert_dropdown', 'assert_dropdown_value', 'assert_element',
    'assert_equal', 'assert_link', 'assert_not_equal', 'assert_radio',
    'assert_radio_value', 'assert_table_has_rows', 'assert_table_headers',
    'assert_table_row_contains_text', 'assert_text', 'assert_text_contains',
    'assert_textfield', 'assert_title', 'assert_title_contains', 'assert_url',
    'assert_url_contains', 'check_flags', 'click_button', 'click_element',
    'click_link', 'close_window', 'debug', 'dismiss_alert', 'end_test',
    'exists_element', 'fails', 'get_argument', 'get_base_url', 'get_cookies',
    'get_current_url', 'get_element', 'get_element_by_css',
    'get_element_by_xpath', 'get_elements', 'get_elements_by_css',
    'get_elements_by_xpath', 'get_link_url', 'get_page_source', 'go_back',
    'go_to', 'refresh', 'reset_base_url', 'run_test', 'set_base_url',
    'set_checkbox_value', 'set_dropdown_value', 'set_radio_value',
    'set_wait_timeout', 'simulate_keys', 'skip', 'sleep', 'start', 'stop',
    'switch_to_frame', 'switch_to_window', 'take_screenshot',
    'toggle_checkbox', 'wait_for', 'wait_for_and_refresh', 'write_textfield',
]


browser = None
browsermob_proxy = None
_check_flags = True
_test = None

BASE_URL = 'http://localhost:8000/'
__DEFAULT_BASE_URL__ = BASE_URL
VERBOSE = True


class EndTest(StandardError):
    pass


debug.__doc__ = """Start the debugger, a shortcut for `pdb.set_trace()`."""


class _Sentinel(object):
    def __repr__(self):
        return 'default'
_sentinel = _Sentinel()


def _raise(msg):
    _print(msg)
    raise AssertionError(msg)


def set_base_url(url):
    """Set the url used for relative arguments to the `go_to` action."""
    global BASE_URL
    if not url.endswith('/'):
        url += '/'
    if not url.startswith('http') and not url.startswith('file'):
        url = 'http://' + url
    _print('Setting base url to: %r' % url)
    BASE_URL = url


def get_base_url():
    """Return the base url used by `go_to`."""
    return BASE_URL


def reset_base_url():
    """
    Restore the base url to the default. This is called automatically for
    you when a test script completes."""
    global BASE_URL
    BASE_URL = __DEFAULT_BASE_URL__


def end_test():
    """
    If called it ends the test. Can be used conditionally to exit a
    test under certain conditions."""
    raise EndTest


def skip(reason=''):
    """
    Skip the test. Unlike `end_test` a skipped test will be reported
    as a skip rather than a pass."""
    raise SkipTest(reason)


def _print(text):
    if VERBOSE:
        print '    %s' % text


def start(browser_type=None, browser_version='',
          browser_platform='ANY', session_name='',
          javascript_disabled=False, assume_trusted_cert_issuer=False,
          webdriver_remote=None,
          preferences = [],
          capabilities = {} ):
    """
    Starts Browser with a new session. Called for you at
    the start of each test script."""
    global browser
    global browsermob_proxy

    if browser_type is None:
        browser_type = config.browser_type

    if VERBOSE:
        _print('')

    _print('Starting %s' % browser_type)

    def update_preferences(profile, preferences):
        profile.set_preference('intl.accept_languages', 'en')

        for (preference,value) in preferences:
            profile.set_preference(preference, value)

        if assume_trusted_cert_issuer:
            profile.set_preference(
                'webdriver_assume_untrusted_issuer', False)
        if javascript_disabled:
            profile.set_preference('javascript.enabled', False)

        profile.update_preferences()

    if webdriver_remote is None:
        if browser_type == 'Firefox':
            # profile features are FF only
            profile = getattr(webdriver, '%sProfile' % browser_type)()
            update_preferences(profile, preferences)

            if config.browsermob_enabled:
                # proxy integration is currently FF only
                browsermob_proxy = bmobproxy.BrowserMobProxy(
                    'localhost', 8080)
                selenium_proxy = webdriver.Proxy(
                    {'httpProxy': browsermob_proxy.url})
                profile.set_proxy(selenium_proxy)

            browser = getattr(webdriver, browser_type)(profile)
        else:
            browser = getattr(webdriver, browser_type)()
    else:
        profile = webdriver.FirefoxProfile()
        update_preferences(profile, preferences)

        desired_capabilities = {"browserName": browser_type.lower(),
                                "platform": browser_platform.upper(),
                                "version": browser_version,
                                "javascriptEnabled": not javascript_disabled,
                                "name": session_name }

        for key in capabilities:
            desired_capabilities[key] = capabilities[key]

        browser = webdriver.Remote(desired_capabilities=desired_capabilities,
                                   command_executor=webdriver_remote, 
                                   browser_profile = profile)

def stop():
    """
    Stops Firefox and ends the browser session. Called automatically for you at
    the end of each test script."""
    global browser
    global browsermob_proxy

    _print('Stopping browser')
    # quit calls close() and does cleanup
    browser.quit()
    browser = None

    if browsermob_proxy is not None:
        _print('Closing http proxy')
        browsermob_proxy.close()
        browsermob_proxy = None


def refresh(wait=True):
    """
    Refresh the current page.

    By default this action will wait until a page with a body element is
    available after the click. You can switch off this behaviour by passing
    `wait=False`."""
    if browsermob_proxy is not None:
        _print('Capturing http traffic...')
        browsermob_proxy.new_har()

    _print('Refreshing current page')
    browser.refresh()

    if wait:
        _waitforbody()

    if browsermob_proxy is not None:
        _print('Saving HAR output')
        _make_results_dir()
        browsermob_proxy.save_har(_make_useable_har_name())


def take_screenshot(filename='screenshot.png'):
    """
    Takes a screenshot of the browser window. Called automatically on failures
    when running in `-s` mode."""
    _print('Capturing Screenshot')
    _make_results_dir()
    screenshot_file = os.path.join(config.results_directory, filename)
    browser.get_screenshot_as_file(screenshot_file)


def _make_results_dir():
    """
    Make results directory if it does not exist."""
    try:
        os.makedirs(config.results_directory)
    except OSError:
        pass  # already exists


def sleep(secs):
    """
    Delay execution for a given number of seconds. The argument may be a
    floating point number for subsecond precision."""
    _print('Sleeping %s secs' % secs)
    time.sleep(secs)


def _fix_url(url):
    if url.startswith('/'):
        url = url[1:]
    if not url.startswith('http') and not url.startswith('file'):
        url = BASE_URL + url
    return url


def get_argument(name, default=_sentinel):
    """
    Get an argument from the one the test was called with.

    A test is called with arguments when it is executed by
    the `run_test`. You can optionally provide a default value
    that will be used if the argument is not set. If you don't
    provide a default value and the argument is missing an
    exception will be raised."""
    args = config.__args__

    value = args.get(name, default)
    if value is _sentinel:
        raise LookupError(name)
    return value


def run_test(name, **kwargs):
    """
    Execute a named test, with the specified arguments.

    Arguments can be retrieved by the test with `get_argument`.

    The `name` is the test file name without the '.py'.

    You can specify tests in an alternative directory with
    relative path syntax. e.g.::

        run_test('subdir/foo', spam='eggs')

    Tests can return a result by setting the name `RESULT`
    in the test.

    Tests are executed with the same browser (and browser
    session) as the test calling `test_run`. This includes
    whether or not Javascript is enabled.

    Before the test is called the timeout and base url are
    reset, but will be restored to their orginal value
    when `run_test` returns."""
    # delayed import to workaround circular imports
    from sst import context
    _print('Executing test: %s' % name)
    return context.run_test(name, kwargs)


def _make_useable_har_name(stem=''):
    now = datetime.now()
    timestamped_base = 'har-%s' % now.strftime('%Y-%m-%d_%H-%M-%S-%f')
    if stem:
        slug_name = ''.join(x for x in stem if x.isalnum())
        out_name = '%s-%s.har' % (timestamped_base, slug_name)
    else:
        out_name = '%s.har' % timestamped_base
    file_name = os.path.join(config.results_directory, out_name)
    return file_name


def go_to(url='', wait=True):
    """
    Go to a specific URL. If the url provided is a relative url it will be added
    to the base url. You can change the base url for the test with
    `set_base_url`.

    By default this action will wait until a page with a body element is
    available after the click. You can switch off this behaviour by passing
    `wait=False`."""
    if browser is None:
        start()

    url = _fix_url(url)

    if browsermob_proxy is not None:
        _print('Capturing http traffic...')
        browsermob_proxy.new_har()

    _print('Going to... %s' % url)
    browser.get(url)

    if wait:
        _waitforbody()

    if browsermob_proxy is not None:
        _print('Saving HAR output')
        _make_results_dir()
        browsermob_proxy.save_har(_make_useable_har_name(url))


def go_back(wait=True):
    """
    Go one step backward in the browser history.

    By default this action will wait until a page with a body element is
    available after the click. You can switch off this behaviour by passing
    `wait=False`."""
    if browsermob_proxy is not None:
        _print('Capturing http traffic...')
        browsermob_proxy.new_har()

    _print('Going back one step in browser history')
    browser.back()

    if wait:
        _waitforbody()

    if browsermob_proxy is not None:
        _print('Saving HAR output')
        _make_results_dir()
        browsermob_proxy.save_har(_make_useable_har_name())


def assert_checkbox(id_or_elem):
    """
    Assert that the element is a checkbox.

    Takes an id or an element object.
    Raises a failure exception if the element specified doesn't exist or isn't
    a checkbox."""
    elem = _get_elem(id_or_elem)
    _elem_is_type(elem, id_or_elem, 'checkbox')
    return elem


def assert_checkbox_value(id_or_elem, value):
    """
    Assert checkbox value. Takes an element id or object plus either True or
    False. Raises a failure exception if the element specified doesn't exist
    or isn't a checkbox."""
    checkbox = assert_checkbox(id_or_elem)
    real = checkbox.is_selected()
    msg = 'Checkbox: %r - Has Value: %r' % (id_or_elem, real)
    if real != value:
        _raise(msg)


def toggle_checkbox(id_or_elem):
    """
    Toggle the checkbox value. Takes an element id or object. Raises a failure
    exception if the element specified doesn't exist or isn't a checkbox."""
    _print('Toggling checkbox: %r' % id_or_elem)
    checkbox = assert_checkbox(id_or_elem)
    before = checkbox.is_selected()
    checkbox.click()
    after = checkbox.is_selected()
    msg = 'Checkbox: %r - was not toggled, value remains: %r' \
        % (id_or_elem, before)
    if before == after:
        _raise(msg)


def set_checkbox_value(id_or_elem, new_value):
    """
    Set a checkbox to a specific value, either True or False. Raises a failure
    exception if the element specified doesn't exist or isn't a checkbox."""
    _print('Setting checkbox %r to %r' % (id_or_elem, new_value))
    checkbox = assert_checkbox(id_or_elem)
    # There is no method to 'unset' a checkbox in the browser object
    current_value = checkbox.is_selected()
    if new_value != current_value:
        toggle_checkbox(id_or_elem)


def _make_keycode(key_to_make):
    """
    Take a key and return a keycode"""
    k = keys.Keys()
    keycode = k.__getattribute__(key_to_make.upper())
    return keycode


def simulate_keys(id_or_elem, key_to_press):
    """
    Simulate key sent to specified element.
    (available keys located in `selenium/webdriver/common/keys.py`)

    e.g.::

        simulate_keys('text_1', 'BACK_SPACE')

    """
    key_element = _get_elem(id_or_elem)
    _print('Simulating keypress on %r with %r key' \
        % (id_or_elem, key_to_press))
    key_code = _make_keycode(key_to_press)
    key_element.send_keys(key_code)


_textfields = (
    'text', 'password', 'textarea', 'email',
    'url', 'search', 'number', 'file')


def assert_textfield(id_or_elem):
    """
    Assert that the element is a textfield, textarea or password box.

    Takes an id or an element object.
    Raises a failure exception if the element specified doesn't exist
    or isn't a textfield."""
    elem = _get_elem(id_or_elem)
    _elem_is_type(elem, id_or_elem, *_textfields)  # see _textfields tuple
    return elem


def write_textfield(id_or_elem, new_text, check=True, clear=True):
    """
    Set the specified text into the textfield. If the text fails to write (the
    textfield contents after writing are different to the specified text) this
    function will fail. You can switch off the checking by passing
    `check=False`.  The field is cleared before written to. You can switch this
    off by passing `clear=False`."""
    _print('Writing to textfield %r with text %r' % (id_or_elem, new_text))
    textfield = assert_textfield(id_or_elem)

    # clear field like this, don't use clear()
    if clear:
        textfield.send_keys(keys.Keys().CONTROL, 'a')
        textfield.send_keys(keys.Keys().DELETE)

    if isinstance(new_text, unicode):
        textfield.send_keys(new_text)
    else:
        textfield.send_keys(str(new_text))
    if not check:
        return
    _print('Check text wrote correctly')
    current_text = textfield.get_attribute('value')
    if current_text != new_text:
        msg = 'Textfield: %r - did not write. Text was: %r' \
            % (id_or_elem, current_text)
        _raise(msg)


def assert_link(id_or_elem):
    """
    Assert that the element is a link.

    Raises a failure exception if the element specified doesn't exist or
    isn't a link"""
    link = _get_elem(id_or_elem)
    href = link.get_attribute('href')
    if href is None:
        msg = 'The text %r is not part of a Link or a Link ID' % id_or_elem
        _raise(msg)
    return link


def get_link_url(id_or_elem):
    """Return the URL from a link."""
    _print('Getting url from link %r' % id_or_elem)
    link = assert_link(id_or_elem)
    link_url = link.get_attribute('href')
    return link_url


def get_current_url():
    """Gets the URL of the current page."""
    return browser.current_url


def click_link(id_or_elem, check=False, wait=True):
    """
    Click the specified link. As some links do redirects the location you end
    up at is not checked by default. If you pass in `check=True` then this
    action asserts that the resulting url is the link url.

    By default this action will wait until a page with a body element is
    available after the click. You can switch off this behaviour by passing
    `wait=False`."""
    link = assert_link(id_or_elem)
    link_url = link.get_attribute('href')

    if browsermob_proxy is not None:
        _print('Capturing http traffic...')
        browsermob_proxy.new_har()

    _print('Clicking link %r' % id_or_elem)
    link.click()

    if wait:
        _waitforbody()

    if browsermob_proxy is not None:
        _print('Saving HAR output')
        _make_results_dir()
        browsermob_proxy.save_har(_make_useable_har_name())

    # some links do redirects - so we
    # don't check by default
    if check:
        assert_url(link_url)


def assert_displayed(id_or_elem):
    """
    Assert that the element is displayed.

    Takes an id or an element object.
    Raises a failure exception if the element specified doesn't exist or isn't
    displayed. Returns the element if it is displayed."""
    element = _get_elem(id_or_elem)
    if not element.is_displayed():
        message = 'Element is not displayed'
        _raise(message)
    return element


def click_element(id_or_elem, wait=True):
    """
    Click on an element of any kind not specific to links or buttons.

    By default this action will wait until a page with a body element is
    available after the click. You can switch off this behaviour by passing
    `wait=False`."""
    elem = _get_elem(id_or_elem)

    if browsermob_proxy is not None:
        _print('Capturing http traffic...')
        browsermob_proxy.new_har()

    _print('Clicking element %r' % id_or_elem)
    elem.click()

    if wait:
        _waitforbody()

    if browsermob_proxy is not None:
        _print('Saving HAR output')
        _make_results_dir()
        browsermob_proxy.save_har(_make_useable_har_name())


def assert_title(title):
    """Assert the page title is as specified."""
    real_title = browser.title
    msg = 'Title is: %r. Should be: %r' % (real_title, title)
    if real_title != title:
        _raise(msg)


def assert_title_contains(text, regex=False):
    """
    Assert the page title contains the specified text.

    set `regex=True` to use a regex pattern."""
    real_title = browser.title
    msg = 'Title is: %r. Does not contain %r' % (real_title, text)
    if regex:
        if not re.search(text, real_title):
            _raise(msg)
    else:
        if not text in real_title:
            _raise(msg)


def assert_url(url):
    """
    Assert the current url is as specified. Can be an absolute url or
    relative to the base url."""
    url = _fix_url(url)
    real_url = browser.current_url
    msg = 'Url is: %r.  Should be: %r' % (real_url, url)
    if url != real_url:
        _raise(msg)


def assert_url_contains(text, regex=False):
    """
    Assert the current url contains the specified text.

    set `regex=True` to use a regex pattern."""
    real_url = browser.current_url
    msg = 'Url is %r.  Does not contain %r' % (real_url, text)
    if regex:
        if not re.search(text, real_url):
            _raise(msg)
    else:
        if text not in real_url:
            _raise(msg)


_TIMEOUT = 10
_POLL = 0.1


def set_wait_timeout(timeout, poll=None):
    """
    Set the timeout, in seconds, used by `wait_for`. The default at the start of
    a test is always 10 seconds.

    The optional second argument, is how long (in seconds) `wait_for` should
    wait in between checking its condition (the poll frequency). The default
    at the start of a test is always 0.1 seconds."""
    global _TIMEOUT
    global _POLL
    _TIMEOUT = timeout
    msg = 'Setting wait timeout to %rs' % timeout
    if poll is not None:
        msg += ('. Setting poll time to %rs' % poll)
        _POLL = poll
    _print(msg)


def _get_name(obj):
    try:
        return obj.__name__
    except:
        return repr(obj)


def _wait_for(condition, refresh, timeout, poll, *args, **kwargs):
    global VERBOSE
    _print('Waiting for %s' % _get_name(condition))
    original = VERBOSE
    VERBOSE = False
    try:
        max_time = time.time() + timeout
        msg = _get_name(condition)
        while True:
            #refresh the page if requested
            if refresh:
                refresh()
            e = None
            try:
                result = condition(*args, **kwargs)
            except AssertionError as e:
                pass
            else:
                if result != False:
                    break
            if time.time() > max_time:
                error = 'Timed out waiting for: %s' % msg
                if e:
                    error += '\nError during wait: %s' % e
                _raise(error)
            time.sleep(poll)
    finally:
        VERBOSE = original

def wait_for(condition, *args, **kwargs):
    """
    Wait for an action to pass. Useful for checking the results of actions
    that may take some time to complete.

    This action takes a condition function and any arguments it should be
    called with. The condition function can either be an action or a function
    that returns True for success and False for failure. For example::

        wait_for(assert_title, 'Some page title')

    If the specified condition does not become true within 10 seconds then
    `wait_for` fails.

    You can set the timeout for `wait_for` by calling `set_wait_timeout`."""
    _wait_for(condition, False, _TIMEOUT, _POLL, *args, **kwargs)


def wait_for_and_refresh(condition, *args, **kwargs):
    """
    Wait for an action to pass. Useful for checking the results of actions
    that may take some time to complete. The difference to wait_for() is, that 
    wait_for_and_refresh() refresh the current page with refresh() after every
    condition check.

    This action takes a condition function and any arguments it should be
    called with. The condition function can either be an action or a function
    that returns True for success and False for failure. For example::

        wait_for_and_refresh(assert_title, 'Some page title')

    If the specified condition does not become true within 10 seconds then
    `wait_for_and_refresh` fails.

    You can set the timeout for `wait_for_and_refresh` by calling `set_wait_timeout`.
    """
    _wait_for(condition, True, _TIMEOUT, _POLL, *args, **kwargs)


def fails(action, *args, **kwargs):
    """
    This action is particularly useful for *testing* other actions, by
    checking that they fail when they should do. `fails` takes a function
    (usually an action) and any arguments and keyword arguments to call the
    function with. If calling the function raises an AssertionError then
    `fails` succeeds. If the function does *not* raise an AssertionError then
    this action raises the appropriate failure exception. Alll other
    exceptions will be propagated normally."""
    _print('Trying action: %s' % _get_name(action))
    try:
        action(*args, **kwargs)
    except AssertionError:
        return
    msg = 'Action %r did not fail' % action.__name__
    _raise(msg)


def _get_elem(id_or_elem):
    if isinstance(id_or_elem, WebElement):
        return id_or_elem
    try:
        return browser.find_element_by_id(id_or_elem)
    except (NoSuchElementException, WebDriverException):
        msg = 'Element with id: %r does not exist' % id_or_elem
        _raise(msg)


# Takes an optional 2nd input type for cases like textfield & password
#    where types are similar
def _elem_is_type(elem, name, *elem_types):
    try:
        result = elem.get_attribute('type')
    except NoSuchAttributeException:
        msg = 'Element has no type attribute'
        _raise(msg)
    if not result in elem_types:
        msg = 'Element %r is not one of %r' % (name, elem_types)
        _raise(msg)


def assert_dropdown(id_or_elem):
    """Assert the specified element is a select drop-list."""
    elem = _get_elem(id_or_elem)
    _elem_is_type(elem, id_or_elem, 'select-one')
    return elem


def set_dropdown_value(id_or_elem, text=None, value=None):
    """Set the select drop-list to a text or value specified."""
    _print('Setting %r option list to %r' % (id_or_elem, text or value))
    elem = assert_dropdown(id_or_elem)
    if text and not value:
        for element in elem.find_elements_by_tag_name('option'):
            if element.text == text:
                element.click()
                return
        msg = 'The following option could not be found in the list: %r' % text
    elif value and not text:
        for element in elem.find_elements_by_tag_name('option'):
            if element.get_attribute("value") == value:
                element.click()
                return
        msg = 'The following option could not be found in the list: %r' % value
    else:
        msg = 'Use set_dropdown_value() with either text or value!'
    _raise(msg)


def assert_dropdown_value(id_or_elem, text_in):
    """Assert the specified select drop-list is set to the specified value."""
    elem = assert_dropdown(id_or_elem)
    # Because there is no way to connect the current
    # text of a select element we have to use 'value'
    current = elem.get_attribute('value')
    for element in elem.find_elements_by_tag_name('option'):
        if text_in == element.text and \
            current == element.get_attribute('value'):
                return
    msg = 'The option is not currently set to: %r' % text_in
    _raise(msg)


def assert_radio(id_or_elem):
    """
    Assert the specified element is a radio button.

    Takes an id or an element object.
    Raises a failure exception if the element specified doesn't exist or isn't
    a radio button"""
    elem = _get_elem(id_or_elem)
    _elem_is_type(elem, id_or_elem, 'radio')
    return elem


def assert_radio_value(id_or_elem, value):
    """
    Assert the specified element is a radio button with the specified value;
    True for selected and False for unselected.

    Takes an id or an element object.
    Raises a failure exception if the element specified doesn't exist or isn't
    a radio button"""
    elem = assert_radio(id_or_elem)
    selected = elem.is_selected()
    msg = 'Radio %r should be set to: %s.' % (id_or_elem, value)
    if value != selected:
        _raise(msg)


def set_radio_value(id_or_elem):
    """Select the specified radio button."""
    _print('Selecting radio button item %r' % id_or_elem)
    elem = assert_radio(id_or_elem)
    elem.click()


def _get_text(elem):
    text = None
    try:
        text = elem.text
    except InvalidElementStateException:
        pass
    if text:
        # Note that some elements (like textfields) return empty string
        # for text and we still need to call value
        return text
    try:
        text = elem.get_attribute('value')
    except InvalidElementStateException:
        pass
    return text


def assert_text(id_or_elem, text):
    """
    Assert the specified element text is as specified.

    Raises a failure exception if the element specified doesn't exist or isn't
    as specified"""
    elem = _get_elem(id_or_elem)
    real = _get_text(elem)
    if real is None:
        msg = 'Element %r has no text attribute' % id_or_elem
        _raise(msg)
    if real != text:
        msg = 'Element text should be %r.  It is %r.' % (text, real)
        _raise(msg)


def assert_text_contains(id_or_elem, text, regex=False):
    """
    Assert the specified element contains the specified text.

    set `regex=True` to use a regex pattern."""
    elem = _get_elem(id_or_elem)
    real = _get_text(elem)
    if real is None:
        msg = 'Element %r has no text attribute' % id_or_elem
        _raise(msg)
    msg = 'Element text is %r. Does not contain %r' % (real, text)
    if regex:
        if not re.search(text, real):
            _raise(msg)
    else:
        if text not in real:
            _raise(msg)


def _check_text(elem, text):
    return _get_text(elem) == text


def _match_text(elem, regex):
    text = _get_text(elem) or ''
    return bool(re.search(regex, text))


def get_elements(tag=None, css_class=None, id=None, text=None,
                 text_regex=None, **kwargs):
    """
    This function will find and return all matching elements by any of several
    attributes. If the elements cannot be found from the attributes you
    provide, the call will fail with an exception.

    You can specify as many or as few attributes as you like.

    `text_regex` finds elements by doing a regular expression search against
    the text of elements. It cannot be used in conjunction with the `text`
    argument and cannot be the *only* argument to find elements."""
    if text and text_regex:
        raise TypeError("You can't use text and text_regex arguments")

    selector_string = ''
    if tag:
        selector_string = tag
    if css_class:
        css_class_selector = css_class.strip().replace(' ', '.')
        selector_string += ('.%s' % css_class_selector)
    if id:
        selector_string += ('#%s' % id)

    selector_string += ''.join(['[%s=%r]' % (key, value) for
                                key, value in kwargs.items()])
    try:
        if text and not selector_string:
            elems = browser.find_elements_by_xpath('//*[text() = %r]' % text)
        else:
            if not selector_string:
                msg = 'Could not identify element: no arguments provided'
                _raise(msg)
            elems = browser.find_elements_by_css_selector(selector_string)
    except (WebDriverException, NoSuchElementException) as e:
        msg = 'Element not found: %s' % e
        _raise(msg)

    if text:
        # if text was specified, filter elements
        elems = [element for element in elems if _check_text(element, text)]
    elif text_regex:
        elems = [elem for elem in elems if _match_text(elem, text_regex)]

    if not elems:
        msg = 'Could not identify elements: 0 elements found'
        _raise(msg)

    return elems


def get_element(tag=None, css_class=None, id=None, text=None,
                text_regex=None, **kwargs):
    """
    This function will find and return an element by any of several
    attributes. If the element cannot be found from the attributes you
    provide, or the attributes match more than one element, the call will fail
    with an exception.

    Finding elements is useful for checking that the element exists, and also
    for passing to other actions that work with element objects.

    You can specify as many or as few attributes as you like, so long as they
    uniquely identify one element.

    `text_regex` finds elements by doing a regular expression search against
    the text of elements. It cannot be used in conjunction with the `text`
    argument and cannot be the *only* argument to find elements."""
    elems = get_elements(tag=tag, css_class=css_class,
                         id=id, text=text, text_regex=text_regex, **kwargs)

    if len(elems) != 1:
        msg = 'Could not identify element: %s elements found' % len(elems)
        _raise(msg)

    return elems[0]


def exists_element(tag=None, css_class=None, id=None, text=None,
                   text_regex=None, **kwargs):
    """
    This function will find if an element exists by any of several
    attributes. It returns True if the element is found or False
    if it can't be found.

    You can specify as many or as few attributes as you like."""
    try:
        get_elements(tag=tag, css_class=css_class, id=id, text=text,
                     text_regex=text_regex, **kwargs)
        return True
    except AssertionError:
        return False


def assert_element(tag=None, css_class=None, id=None, text=None,
                   text_regex=None, **kwargs):
    """
    Assert an element exists by any of several attributes.

    You can specify as many or as few attributes as you like."""
    try:
        elems = get_elements(tag=tag, css_class=css_class, id=id, text=text,
                             text_regex=text_regex, **kwargs)
        return elems
    except AssertionError:
        msg = 'Could not assert element exists'
        _raise(msg)


def assert_button(id_or_elem):
    """
    Assert that the specified element is a button.

    Takes an id or an element object.
    Raises a failure exception if the element specified doesn't exist or isn't
    a button"""
    elem = _get_elem(id_or_elem)
    if elem.tag_name == 'button':
        return elem
    if elem.get_attribute('type') == 'button':
        return elem
    _elem_is_type(elem, id_or_elem, 'submit')
    return elem


def click_button(id_or_elem, wait=True):
    """
    Click the specified button.

    By default this action will wait until a page with a body element is
    available after the click. You can switch off this behaviour by passing
    `wait=False`."""
    button = assert_button(id_or_elem)

    if browsermob_proxy is not None:
        _print('Capturing http traffic...')
        browsermob_proxy.new_har()

    _print('Clicking button %r' % id_or_elem)
    button.click()

    if wait:
        _waitforbody()

    if browsermob_proxy is not None:
        _print('Saving HAR output')
        _make_results_dir()
        browsermob_proxy.save_har(_make_useable_har_name())


def get_elements_by_css(selector):
    """Find all elements that match a css selector."""
    try:
        return browser.find_elements_by_css_selector(selector)
    except (WebDriverException, NoSuchElementException) as e:
        msg = 'Element not found: %s' % e
        _raise(msg)


def get_element_by_css(selector):
    """Find an element by css selector."""
    elements = get_elements_by_css(selector)
    if len(elements) != 1:
        msg = 'Could not identify element: %s elements found' % len(elements)
        _raise(msg)
    return elements[0]


def get_elements_by_xpath(selector):
    """Find all elements that match an xpath."""
    try:
        return browser.find_elements_by_xpath(selector)
    except (WebDriverException, NoSuchElementException) as e:
        msg = 'Element not found: %s' % e
        _raise(msg)


def get_element_by_xpath(selector):
    """Find an element by xpath."""
    elements = get_elements_by_xpath(selector)
    if len(elements) != 1:
        msg = 'Could not identify element: %s elements found' % len(elements)
        _raise(msg)
    return elements[0]


def _waitforbody():
    wait_for(get_element, tag='body')


def get_page_source():
    """Gets the source of the current page."""
    return browser.page_source


def close_window():
    """ Closes the current window """
    _print('Closing the current window')
    browser.close()


def switch_to_window(index_or_name=None):
    """
    Switch focus to the specified window (by index or name).

    if no window is given, switch focus to the default window."""
    if index_or_name is None:
        _print('Switching to default window')
        browser.switch_to_window('')
    elif isinstance(index_or_name, int):
        index = index_or_name
        window_handles = browser.window_handles
        if index >= len(window_handles):
            msg = 'Index %r is greater than available windows.' % index
            _raise(msg)
        window = window_handles[index]
        try:
            _print('Switching to window: %r' % window)
            browser.switch_to_window(window)
        except NoSuchWindowException:
            msg = 'Could not find window: %r' % window
            _raise(msg)
    else:
        name = index_or_name
        try:
            _print('Switching to window: %r' % name)
            browser.switch_to_window(name)
        except NoSuchWindowException:
            msg = 'Could not find window: %r' % name
            _raise(msg)


def switch_to_frame(index_or_name=None):
    """
    Switch focus to the specified frame (by index or name).

    if no frame is given, switch focus to the default content frame."""
    if index_or_name is None:
        _print('Switching to default content frame')
        browser.switch_to_default_content()
    else:
        _print('Switching to frame: %r' % index_or_name)
        try:
            browser.switch_to_frame(index_or_name)
        except NoSuchFrameException:
            msg = 'Could not find frame: %r' % index_or_name
            _raise(msg)


def _alert_action(action, expected_text=None, text_to_write=None):
    """
    Accept or dismiss a JavaScript alert, confirmation or prompt.

    Optionally, it takes the expected text of the Popup box to check it,
    and the text to write in the prompt."""
    wait_for(browser.switch_to_alert)
    alert = browser.switch_to_alert()
    alert_text = alert.text
    # XXX workaround because Selenium sometimes returns the value in a
    # dictionary. See http://code.google.com/p/selenium/issues/detail?id=2955
    if isinstance(alert_text, dict):
        alert_text = alert_text['text']
    if expected_text and expected_text != alert_text:
        error_message = 'Element text should be %r.  It is %r.' \
            % (expected_text, alert_text)
        _raise(error_message)
    if text_to_write:
        alert.send_keys(text_to_write)
    if action == 'accept':
        alert.accept()
    elif action == 'dismiss':
        alert.dismiss()
    else:
        _raise('%r is an unknown action for an alert' % action)


def accept_alert(expected_text=None, text_to_write=None):
    """
    Accept a JavaScript alert, confirmation or prompt.

    Optionally, it takes the expected text of the Popup box to check it,
    and the text to write in the prompt.

    Note that the action that opens the alert should not wait for a page with
    a body element. This means that you should call functions like
    click_element with the argument wait=Fase."""
    _print('Accepting Alert')
    _alert_action('accept', expected_text, text_to_write)


def dismiss_alert(expected_text=None, text_to_write=None):
    """
    Dismiss a JavaScript alert.

    Optionally, it takes the expected text of the Popup box to check it.,
    and the text to write in the prompt.

    Note that the action that opens the alert should not wait for a page with
    a body element. This means that you should call functions like
    click_element with the argument wait=Fase."""
    _print('Dismissing Alert')
    _alert_action('dismiss', expected_text, text_to_write)


def assert_table_headers(id_or_elem, headers):
    """
    Assert table `id_or_elem` has headers (<th> tags) where the text matches
    the sequence `headers`.
    """
    _print('Checking headers for %r' % (id_or_elem,))
    elem = _get_elem(id_or_elem)
    if not elem.tag_name == 'table':
        _raise('Element %r is not a table.' % (id_or_elem,))
    header_elems = elem.find_elements_by_tag_name('th')
    header_text = [_get_text(elem) for elem in header_elems]
    if not header_text == headers:
        msg = ('Expected headers:%r\n    Actual headers%r\n' %
               (headers, header_text))
        _raise(msg)


def assert_table_has_rows(id_or_elem, num_rows):
    """
    Assert the specified table has the specified number of rows (<tr> tags
    inside the <tbody>).
    """
    _print('Checking table %r has %s rows' % (id_or_elem, num_rows))
    elem = _get_elem(id_or_elem)
    if not elem.tag_name == 'table':
        _raise('Element %r is not a table.' % (id_or_elem,))
    body = elem.find_elements_by_tag_name('tbody')
    if not body:
        _raise('Table %r has no tbody.' % (id_or_elem,))
    rows = body[0].find_elements_by_tag_name('tr')
    if not len(rows) == num_rows:
        msg = 'Expected %s rows. Found %s.' % (num_rows, len(rows))
        _raise(msg)


def assert_table_row_contains_text(id_or_elem, row, contents, regex=False):
    """
    Assert the specified row (starting from 0) in the specified table
    contains the specified contents.

    contents should be a sequence of strings, where each string is the same
    as the text of the corresponding column.

    If `regex` is True (the default is False) then each cell is checked
    with a regular expression search.

    The row will be looked for inside the <tbody>, to check headers use
    `assert_table_headers`.
    """
    _print('Checking the contents of table %r, row %s.' % (id_or_elem, row))
    elem = _get_elem(id_or_elem)
    if not elem.tag_name == 'table':
        _raise('Element %r is not a table.' % (id_or_elem,))
    body = elem.find_elements_by_tag_name('tbody')
    if not body:
        _raise('Table %r has no tbody.' % (id_or_elem,))
    rows = body[0].find_elements_by_tag_name('tr')
    if len(rows) <= row:
        msg = 'Asked to fetch row %s. Highest row is %s' % (row, len(rows) - 1)
        _raise(msg)
    columns = rows[row].find_elements_by_tag_name('td')
    cells = [_get_text(elem) for elem in columns]
    if not regex:
        success = cells == contents
    elif len(contents) != len(cells):
        success = False
    else:
        success = all(re.search(expected, actual) for expected, actual in
                      zip(contents, cells))
    if not success:
        msg = ('Expected row contents: %r\n    Actual contents: %r' %
               (contents, cells))
        _raise(msg)


def assert_attribute(id_or_elem, attribute, value, regex=False):
    """
    assert that the specified `attribute` on the element is equal to the
    `value`.

    If `regex` is True (default is False) then the value will be compared to
    the attribute using a regular expression search.
    """
    _print('Checking attribute %s of %s' % (attribute, id_or_elem))
    elem = _get_elem(id_or_elem)
    actual = elem.get_attribute(attribute)
    if not regex:
        success = value == actual
    else:
        success = actual is not None and re.search(value, actual)
    if not success:
        msg = 'Expected attribute: %r\n    Actual attribute: %r' % (value, actual)
        _raise(msg)


def assert_css_property(id_or_elem, property, value, regex=False):
    """
    assert that the specified `css property` on the element is equal to the
    `value`.

    If `regex` is True (default is False) then the value will be compared to
    the property using a regular expression search.
    """
    _print('Checking css property %s: %s of %r' % (property, value, id_or_elem))
    elem = _get_elem(id_or_elem)
    actual = elem.value_of_css_property(property)
    if not regex:
        success = value == actual
    else:
        success = actual is not None and re.search(value, actual)
    if not success:
        msg = 'Expected property: %r\n    Actual property: %r' % (value, actual)
        _raise(msg)


def check_flags(*args):
    """
    A test will only run if all the flags passed to this action were supplied
    at the command line. If a required flag is missing the test is skipped.

    Flags are case-insensitive.
    """
    if not _check_flags:
        # Flag checking disabled
        return
    missing = set(arg.lower() for arg in args) - set(config.flags)
    if missing:
        _msg = 'Flags required but not used: %s' % ', '.join(missing)
        skip(_msg)


def assert_equal(first, second):
    """Assert two objects are equal."""
    if _test is None:
        assert first == second
    else:
        _test.assertEqual(first, second)

def assert_not_equal(first, second):
    """Assert two objects are not equal."""
    if _test is None:
        assert first != second
    else:
        _test.assertNotEqual(first, second)


def get_cookies():
    """Gets the cookies of current session (set of dicts)."""
    return browser.get_cookies()
