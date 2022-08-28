# -*- coding: utf-8 -*-
# Module: users
# Author: Alex Bratchik
# Created on: 03.04.2021
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import json
import os
import pickle

import requests

import xbmc

from resources.lib.yandexzen import USER_AGENT

NEVER = 100 * 1000 * 60 * 60 * 24


class User:
    def __init__(self):
        self.yandex_login = ""
        self.domain = ""
        self._geo = {}

        self._site = None
        self.session = None

        self._headers = {}

        self._cookies_file = ""
        self.users_file = ""
        self.user_data = []
        self.usr = {}

        self.client_id = ""
        self.client_secret = ""

    def init_session(self, site):
        self._site = site

        self.yandex_login = site.addon.getSetting("yandex_login")
        self.client_id = site.addon.getSetting("client_id")
        self.client_secret = site.addon.getSetting("client_secret")
        self.users_file = os.path.join(self._site.data_path, "users.json")
        self.domain = site.domain

        self.session = requests.Session()

        self._headers = {
            'User-Agent': USER_AGENT,
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            'Accept-Encoding': "gzip",
            'Accept-Language': "en-US,en;q=0.5",
            'Connection': "keep-alive",
            'Sec-Fetch-Dest': "document",
            'Sec-Fetch-Mode': "navigate",
            'Sec-Fetch-Site': "cross-site",
            'Sec-GPC': "1",
            'Upgrade-Insecure-Requests': "1"}

        # Load saved cookies
        self._cookies_file = os.path.join(self._site.data_path, "cookies.dat")
        self._load_cookies()

        # If UID not in cookies, request it
        if not ('_yasc' in self.session.cookies):
            xbmc.log("Cookie file not found or missing UID, requesting from %s" % self.domain, xbmc.LOGDEBUG)
            self._register_client()
            self._save_cookies()

    def watch(self, site, context=""):
        """

        :param site: YandexZen
        :return:
        @param site: assumed YandexZen class
        @param context: context to load. If empty then site will use CLI arguments
        """
        self.init_session(site)

        if self._login():
            site.show_to(self, context)

        self._save_cookies()
        self.session.close()

    def _login(self):

        if not self.yandex_login:
            self._logout()
            return True
        else:
            if 'yandex_login' in self.session.cookies:
                if not (self.session.cookies['yandex_login'] == self.yandex_login):
                    # account has changed, logout
                    self._logout()
            else:
                self.session.cookies.set("yandex_login", self.yandex_login,
                                         expires=NEVER,
                                         domain=self._site.id,
                                         path="/")
                self._save_cookies()

        if self._is_login():
            return True

        # self.usr = self._get_user(yandex_login=self.yandex_login)

        return True

    def get_headers(self, type="dict"):
        if type == "dict":
            return self._headers
        elif type == "str":
            return "&".join(str(key) + "=" + str(value) for key, value in self._headers.items())
        else:
            return ""

    def get_http(self, url, headers=None, stream=False):
        self._set_host(url)
        if headers is None:
            headers = self._headers
        xbmc.log(str(headers), xbmc.LOGDEBUG)
        if stream:
            return self.session.get(url, headers=headers, stream=True)
        else:
            return self.session.get(url, headers=headers)

    def _set_host(self, url):
        host = url.split("://")[1].split("/")[0]
        self._headers.update({'Host': host})

    def _logout(self):
        if 'yandex_login' in self.session.cookies:
            self.session.cookies.clear(domain=self.yandex_login, path="/", name="yandex_login")

    def _is_login(self):
        return 'yandex_login' in self.session.cookies

    def _register_client(self):
        headers = dict(self._headers)
        headers.update({'Sec-Fetch-Site': "none",
                        'Sec-Fetch-User': "?1"})
        query_url = "https://%s/video" % self._site.api_host
        self.get_http(query_url, headers=headers)

    def _save_cookies(self):
        with open(self._cookies_file, "wb") as f:
            pickle.dump(self.session.cookies, f)

    def _load_cookies(self):
        if os.path.exists(self._cookies_file):
            with open(self._cookies_file, 'rb') as f:
                cj = pickle.load(f)
                for c in cj:
                    xbmc.log(str(c), xbmc.LOGDEBUG)
                    self.session.cookies.set_cookie(c)

    def _get_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, "r") as f:
                return json.load(f)
        else:
            return []

    def _get_user(self, yandex_login):
        if not self.user_data:
            self.user_data = self._get_users()
        query = [usr for usr in self.user_data if usr.get('yandex_login') == yandex_login]
        return query[0] if query else None
