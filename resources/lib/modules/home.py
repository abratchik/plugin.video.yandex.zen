# -*- coding: utf-8 -*-
# Module: home
# Author: Alex Bratchik
# Created on: 03.04.2021
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import xbmc

import resources.lib.modules.pages as pages
import resources.lib.modules.searches as searches
import resources.lib.modules.videos as videos
from resources.lib.kodiutils import get_url


class Home(pages.Page):

    def get_data_query(self):
        search = searches.Search(self.site)
        video = videos.Video(self.site)

        home_menu = [search.create_root_li(),
                     video.create_root_li(),
                     self.create_fav_li()]

        return {'data': home_menu}

    def set_context_title(self):
        self.site.context_title = self.site.language(30300)

    def create_fav_li(self):
        return self.create_menu_li("favorites", 30023, is_folder=False, is_playable=False,
                                   url=get_url(self.site.url, action="favorites", context="home", url=self.site.url),
                                   info={'plot': self.site.language(30023)})

    def favorites(self):
        xbmc.executebuiltin("ActivateWindow(Favourites)")
