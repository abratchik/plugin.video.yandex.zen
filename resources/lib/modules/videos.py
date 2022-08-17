# -*- coding: utf-8 -*-
# Module: videos
# Author: Alex Bratchik
# Created on: 03.04.2021
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import json
import gzip
import xbmc

import resources.lib.modules.pages as pages
from resources.lib.kodiutils import get_url, clean_html


class Video(pages.Page):
    def __init__(self, site):
        super(Video, self).__init__(site)

    def get_load_url(self):
        if self.params.get('load_url', ""):
            return self.params['load_url']
        return get_url(self.site.api_url + '/launcher/video-more', country_code="ru")

    def get_data_query(self):
        xbmc.log("Loading data from %s" % self.get_load_url(), xbmc.LOGDEBUG)
        data = self.site.request(self.get_load_url(), output="json")

        if data.get('items', []):
            return {'data': data['items'],
                    'pagination': {'next': data.get('more',{}).get('link'),
                                   'prev': data.get('prev',{}).get('link')
                                  }
                    }

        return {'data': []}

    def create_element_li(self, element):
        title = clean_html(element['title'])
        return {'id': element['id'],
                'label': title,
                'is_folder': False,
                'is_playable': True,
                'url': get_url(self.site.url,
                               action="play",
                               context=self.context,
                               spath=element.get('video', {}).get('id', ""),
                               url=self.site.url),
                'info': {'mediatype': "movie",
                         'plot': "[B]%s[/B]\n\n%s" % (element['domain'], title)},
                'art': {'thumb': element.get('image', ""),
                        'icon': element.get('image_squared', ""),
                        'fanart': element.get('big_card_image', ""),
                        'poster': element.get('big_card_image', "")}
                }

    def create_root_li(self):
        return self.create_menu_li("channels", 30120, is_folder=True, is_playable=False,
                                   url=get_url(self.site.url, action="load",
                                               context="videos",
                                               content="videos",
                                               url=self.site.url),
                                   info={'plot': self.site.language(30120)})

    def play(self):
        spath = self.params['spath']

        self.play_url(spath)