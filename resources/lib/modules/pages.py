# -*- coding: utf-8 -*-
# Module: pages
# Author: Alex Bratchik
# Created on: 03.04.2021
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import json
import os
import time
import re

import xbmc
import xbmcgui
import xbmcplugin
import hashlib

from urllib.parse import quote as encode4url
from ..kodiutils import remove_files_by_pattern, upnext_signal, kodi_version_major, get_url
import resources.lib.kodiplayer as kodiplayer
from ..yandexzen import USER_AGENT
from ..kodiutils import clean_html


class Page(object):

    def __init__(self, site):
        self.site = site
        self.data = {}
        self.params = site.params
        self.action = site.action
        self.context = site.context
        self.list_items = []
        self.context_menu_items = []
        self.offset = 0
        self.limit = 0

        self.next_page = ""
        self.prev_page = ""

        self.cache_enabled = False
        self.cache_file = ""
        self.cache_expire = int(self.params.get('cache_expire', 0))

    def load(self):

        self.preload()

        self.cache_file = self.get_cache_filename()

        xbmc.log("Cache file name: %s" % self.cache_file)

        self.data = self.get_data_query()

        xbmc.log("Items per page: %s" % len(self.data['data']), xbmc.LOGDEBUG)

        self.set_context_title()

        self.set_navigation_pages()

        if self.prev_page and self.offset > 0:
            self.list_items.append(self.create_menu_li("previous",
                                                       label=30032, is_folder=True, is_playable=False,
                                                       url=self.get_nav_url(load_url=self.prev_page,
                                                                            offset=self.offset - 1),
                                                       info={'plot': self.site.language(30031) %
                                                                     (self.offset + 1)}))

        if self.data.get('pagination', ""):
            self.list_items.append(self.create_menu_li("home", label=30020, is_folder=True, is_playable=False,
                                                       url=self.site.url,
                                                       info={'plot': self.site.language(30021)}))

        if 'data' in self.data:
            for element in self.data['data']:
                self.append_li_for_element(element)

            self.cache_data()

        if self.next_page:
            self.list_items.append(self.create_menu_li("first", label=30030, is_folder=True, is_playable=False,
                                                       url=self.get_nav_url(load_url=self.next_page,
                                                                            offset=self.offset + 1),
                                                       info={'plot': self.site.language(30031) %
                                                                     (self.offset + 1)}))

        self.postload()

        self.show_list_items()

    def preload(self):
        """
        Override this function if it is necessary to perform some actions before preparing the list items
        @return:
        """
        pass

    def postload(self):
        """
        Override this function if it is necessary to perform some actions after preparing the list items
        @return:
        """
        pass

    def play(self):
        pass

    def play_url(self, url):

        xbmc.log("Play url: %s" % url, xbmc.LOGDEBUG)

        play_item = xbmcgui.ListItem(path=self.site.prepare_url(url))

        play_item.setMimeType('application/x-mpegURL')
        if '.m3u8' in url:
            if kodi_version_major() >= 19:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
            else:
                play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')

        xbmcplugin.setResolvedUrl(self.site.handle, True, listitem=play_item)

    def create_element_li(self, element):
        return element

    def create_root_li(self):
        """
        This method can be optionally overridden if the the module class wants to expose a root-level menu.
        Usage is mainly from the lib.modules.home module.

        @return: the structure defining the list item
        """
        return {}

    def get_load_url(self):
        """
        This method is to be overridden in the child class to provide the url for querying the site. It is used in the
        get_data_query method and can be ignored if get_data_query is overriden in the child class.
        @return:
        """
        return ""

    def set_context_title(self):
        """
        This method is setting the title of the context by setting self.site.context_title attribute. Override if
        you want to create custom title, otherwise the context name will be used by default.
        """
        self.site.context_title = self.context.title()

    def get_data_query(self):

        if self.is_cache_available():
            return self.get_data_from_cache()
        else:
            return self.site.request(self.get_load_url(), output="json")

    def is_cache_available(self):
        is_refresh = 'refresh' in self.params and self.params['refresh'] == "true"
        if is_refresh:
            remove_files_by_pattern(os.path.join(self.site.data_path, "%s*.json" % self.get_cache_filename_prefix()))
        return (not is_refresh) and self.cache_enabled and \
               os.path.exists(self.cache_file) and not (self.is_cache_expired())

    def get_data_from_cache(self):
        with open(self.cache_file, 'r+') as f:
            xbmc.log("Loading from cache file: %s" % self.cache_file, xbmc.LOGDEBUG)
            return json.load(f)

    def is_cache_expired(self):

        if self.cache_expire == 0:
            # cache never expires
            return False

        mod_time = os.path.getmtime(self.cache_file)
        now = time.time()

        return int(now - mod_time) > self.cache_expire

    def get_nav_url(self, load_url, offset=0):
        return get_url(self.site.url,
                       action=self.site.action,
                       context=self.site.context,
                       load_url=load_url, offset=offset, url=self.site.url)

    def append_li_for_element(self, element):
        self.list_items.append(self.create_element_li(element))

    def set_navigation_pages(self):
        self.offset = int(self.params.get('offset', "0"))
        if 'pagination' in self.data:
            self.prev_page = self.data['pagination']['prev']
            self.next_page = self.data['pagination']['next']

    def create_menu_li(self, label_id, label, is_folder, is_playable, url,
                       info=None, art=None,
                       lbl_format="[COLOR=FF00FF00][B]%s[/B][/COLOR]"):
        label_text = label if type(label) == str else self.site.language(label)
        return {'id': label_id, 'label': lbl_format % label_text, 'is_folder': is_folder, 'is_playable': is_playable,
                'url': url,
                'info': {'plot': label_text} if info is None else info,
                'art': {'icon': self.site.get_media("%s.png" % label_id),
                        'fanart': self.site.get_media("background.jpg")} if art is None else art}

    @staticmethod
    def format_date(s):
        if s:
            return "%s-%s-%s %s:%s:%s" % (s[6:10], s[3:5], s[0:2], s[11:13], s[14:16], s[17:19])
        else:
            return ""

    @staticmethod
    def get_country(countries):
        if type(countries) is list and len(countries) > 0:
            return countries[0]['title']
        else:
            return ""

    def show_list_items(self):

        xbmcplugin.setPluginCategory(self.site.handle, self.site.context_title)

        if self.context == "home":
            xbmcplugin.setContent(self.site.handle, "files")
        else:
            xbmcplugin.setContent(self.site.handle, self.params['content'] if "content" in self.params else "videos")

        # Iterate through categories
        for category in self.list_items:
            # Create a list item with a text label and a thumbnail image.
            list_item = xbmcgui.ListItem(label=category['label'])

            url = category['url']

            is_folder = category['is_folder']
            list_item.setProperty('IsPlayable', str(category['is_playable']).lower())

            if self.cache_enabled:
                self.context_menu_items = [(self.site.language(30001),
                                            "ActivateWindow(Videos, %s&refresh=true)" %
                                            self.get_nav_url(offset=0)), ]
            else:
                self.context_menu_items.clear()

            self.add_context_menu(category)

            if self.context_menu_items:
                list_item.addContextMenuItems(self.context_menu_items)

            if 'info' in category:
                list_item.setInfo(category['type'] if 'type' in category else "video", category['info'])

            if 'art' in category:
                list_item.setArt(category['art'])

            if 'cast' in category:
                list_item.setCast(category['cast'])

            xbmcplugin.addDirectoryItem(self.site.handle, url, list_item, is_folder)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.site.handle, cacheToDisc=False)

    def enrich_info_tag(self, list_item, episode, brand):
        """
        This function can be overridden to enrich the information available on the list item before passing to the
        player
        @param list_item: ListItem to be enriched
        @param episode: the element, which will be played
        @param brand: the element brand used for enrichment
        """
        pass

    def add_context_menu(self, category):
        """
        This function can be overriden to add context menu items
        @param category:
        @return:
        """
        pass

    def save_brand_to_history(self, brand):
        with open(os.path.join(self.site.history_path, "brand_%s.json" % brand['id']), 'w+') as f:
            json.dump(brand, f)

    def cache_data(self):
        if self.cache_enabled and len(self.data.get('data', [])) > 0 and \
                not (os.path.exists(self.cache_file) and not self.is_cache_expired()):
            with open(self.cache_file, 'w+') as f:
                json.dump(self.data, f)

    def get_cache_filename(self):
        return os.path.join(self.site.data_path,
                            "%s_%s_%s.json" % (self.get_cache_filename_prefix(),
                                               self.limit,
                                               self.offset))

    def get_cache_filename_prefix(self):
        return self.context
