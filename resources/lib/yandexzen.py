# -*- coding: utf-8 -*-
# Module: users
# Author: Alex Bratchik
# Created on: 03.04.2021
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import inspect
import os
import sys

import xbmc
import xbmcaddon

from urllib.parse import parse_qsl
from urllib.parse import quote as encode4url

import xbmcvfs

from resources.lib import kodiutils
from importlib import import_module

ADDON_ID = "plugin.video.yandex.zen"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0"


class YandexZen:
    def __init__(self):
        self.id = ADDON_ID
        self.addon = xbmcaddon.Addon(self.id)
        self.path = self.addon.getAddonInfo('path')
        self.media_path = os.path.join(self.path, "resources", "media")
        self.data_path = get_data_path(self.addon)
        self.history_path = kodiutils.create_folder(os.path.join(self.data_path, 'history'))

        self.user = None

        self.url = sys.argv[0] if len(sys.argv) > 0 else ""
        self.handle = int(sys.argv[1]) if len(sys.argv) > 1 else 0

        self.params = {}

        self.domain = "dzen.ru"
        self.api_host = self.domain
        self.cdnapi_host = self.api_host
        self.api_url = "https://%s/api/v3" % self.api_host
        self.cdnapi_url = self.api_url
        self.liveapi_host = self.domain
        self.liveapi_url = "https://%s" % self.liveapi_host

        self.language = self.addon.getLocalizedString

        # to save current context
        self.context = "home"
        self.action = "load"
        self.context_title = self.language(30300)

    def show_to(self, user, context=""):

        self.user = user

        xbmc.log("Addon: %s" % self.id, xbmc.LOGDEBUG)
        xbmc.log("Handle: %d" % self.handle, xbmc.LOGDEBUG)
        xbmc.log("User: %s" % user.yandex_login, xbmc.LOGDEBUG)

        if context:
            self.params = {'context': context}
            xbmc.log("Params ignored")
        else:
            params_ = sys.argv[2]
            xbmc.log("Params: %s" % params_, xbmc.LOGDEBUG)
            self.params = dict(parse_qsl(params_[1:]))

        self.context = self.params['context'] if self.params and ('context' in self.params) else "home"
        self.action = self.params['action'] if self.params and ('action' in self.params) else "load"
        xbmc.log("Context: %s" % self.context, xbmc.LOGDEBUG)
        xbmc.log("Action: %s" % self.action, xbmc.LOGDEBUG)

        self.load_context_items()

        # load items from self.context

    def load_context_items(self):
        mod = import_module("resources.lib.modules.%s" % self.context)
        classes = [cls for _, cls in inspect.getmembers(mod, inspect.isclass(mod))]
        getattr(classes[0](self), self.action)()

    def request(self, url, output="text", headers=None):
        xbmc.log("Query site url: %s" % url, xbmc.LOGDEBUG)
        is_stream = (output == "stream")
        response = self.user.get_http(url, headers=headers, stream=is_stream)
        err = response.status_code != 200
        if err:
            xbmc.log("Query %s returned HTTP error %s" % (url, response.status_code))
        if output == "json":
            return {} if err else response.json()
        elif output == "text":
            return "" if err else response.text
        else:
            return response

        # *** Add-on helpers

    def get_media(self, file_name):
        return os.path.join(self.media_path, file_name)

    def get_user_input(self):
        kbd = xbmc.Keyboard()
        kbd.setDefault('')
        kbd.setHeading(self.language(30010))
        kbd.doModal()
        keyword = None

        if kbd.isConfirmed():
            keyword = kbd.getText()

        return keyword

    def prepare_url(self, url):
        return "|".join([url,
                         "&".join(
                             ["User-Agent=%s" % encode4url(USER_AGENT),
                              "Origin=%s" % encode4url(self.liveapi_url),
                              "Referer=%s" % encode4url(self.liveapi_url),
                              "!Sec-Fetch-Dest=empty",
                              "!Sec-Fetch-Mode=cors",
                              "!Sec-Fetch-Site=cross-site",
                              "!Sec-GPC=1",
                              "Connection=keep-alive"])
                         ])


def get_data_path(addon: object = None):
    if addon is None:
        addon = xbmcaddon.Addon(ADDON_ID)
    return kodiutils.create_folder(os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('profile')), 'data'))
