#!/usr/bin/env python

# Egami: a very simple image gallery built using Flask, which
# serves image files found in the directory where it is executed.
# Copyright (C) 2011-2015 Francois Lebel <francoislebel@gmail.com>
# http://github.com/flebel/egami
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import glob
import itertools
import json
import os

from collections import OrderedDict, defaultdict

from flask import Flask, send_from_directory
from flask.ext.cache import Cache
from jinja2 import Template

# Look for files with an image extension (case insensitive.)
# Note that glob does not support regular expressions, hence the duplications.
IMAGE_EXTENSIONS = ('[gG][iI][fF]', '[jJ][pP][gG]', '[jJ][pP][eE][gG]', '[pP][nN][gG]')

# Path from where images are served. Must end with a forward slash.
IMAGES_URL = '/images/'

HTML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
    <head>
        <title>{{cwd}}</title>
        <script src="http://www.google.com/jsapi" type="text/javascript"></script>
        <script type="text/javascript" charset="utf-8">
            google.load("jquery", "1.7.0");
        </script>
        <script type="text/javascript">
        //<![CDATA[
            $(document).ready(function() {
                var groups = {{images}};
                var groups_keys = Object.keys(groups);
                var images = groups[groups_keys[0]];
                var number_images = images.length;
                var currentIndex = number_images - 1;

                function changeImage(index) {
                    var validIndex = getValidIndex(index);
                    $('img.current').attr('alt', images[validIndex]);
                    $('img.current').attr('src', '{{images_url}}' + images[validIndex]);
                    $('span.status').text("Now serving image " + (validIndex + 1) + " of " + number_images + " image(s) from '{{cwd}}':");
                    $('span.filename').text(images[validIndex]);
                    currentIndex = validIndex;
                }

                function getValidIndex(index) {
                    if (index < 0) {
                        index = 0;
                    }
                    if (index > images.length - 1) {
                        index = images.length - 1;
                    }
                    return index;
                }

                function preloadImage(index) {
                    var validIndex = getValidIndex(index);
                    $('<img />').attr('src', '{{images_url}}' + images[validIndex]).appendTo('body').hide();
                }

                function showPrevious() {
                    var offset = parseInt($('#offset').val());
                    changeImage(currentIndex - offset);
                    // Preload the previous image according to the (new) current position
                    preloadImage(currentIndex - offset);
                }

                function showNext() {
                    var offset = parseInt($('#offset').val());
                    changeImage(currentIndex + offset);
                    // Preload the next image according to the (new) current position
                    preloadImage(currentIndex + offset);
                }

                $('select#group').change(function (e) {
                    var group_name = $('#group').val();
                    images = groups[group_name];
                    number_images = images.length;
                    changeImage(number_images - 1);
                });

                $('button#first').click(function (e) {
                    e.preventDefault();
                    changeImage(0);
                });

                $('button#previous').click(function (e) {
                    e.preventDefault();
                    showPrevious();
                });

                $('button#next').click(function (e) {
                    e.preventDefault();
                    showNext();
                });

                $('button#last').click(function (e) {
                    e.preventDefault();
                    changeImage(images.length - 1);
                });

                $('button#preload').click(function (e) {
                    e.preventDefault();
                    var offset = parseInt($('#offset').val());
                    for (var i = currentIndex, n = images.length; i < n; i += offset) {
                        preloadImage(i);
                    }
                });

                $('a.current').click(function (e) {
                    e.preventDefault();
                    var action = $('#action').val();
                    switch (action) {
                        case 'previous':
                            showPrevious();
                            break;
                        case 'next':
                            showNext();
                            break;
                        case 'open':
                            window.location = '{{images_url}}' + images[validIndex];
                            break;
                    }
                });

                if (groups_keys.length <= 1) {
                    $('select#group').remove();
                } else {
                    for (var i = 0; i < groups_keys.length; i++) {
                        $('<option/>').val(groups_keys[i]).html(groups_keys[i]).appendTo('select#group');
                    }
                }

                // Initially set the current image to the last one
                if (images.length > 0) {
                    changeImage(currentIndex);
                } else {
                    $('img.current').hide();
                }
            });
        //]]>
        </script>
        <style type="text/css">
            button, select {
                height: 50px;
                margin-right: 20px;
            }
            select#offset {
                width: 50px;
            }
            img.current {
                max-height: 640px;
                max-width: 640px;
            }

            img.thumb {
                max-height: 150px;
                max-width: 150px;
            }
        </style>
    </head>
    <body>
        <div id="nav">
            <button id="first">First</button>
            <button id="previous">Previous</button>
            <select id="group">
            </select>
            <select id="offset">
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="5">5</option>
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
            </select>
            <button id="next">Next</button>
            <button id="last">Last</button>
            <hr/>
        </div>
        <div id="content">
            <p><span class="status"></span> <span class="filename"></span></p>
            <a class="current" href=""><img alt="" class="current" src=""/></a>
        </div>
        <div id="footer">
            <hr/>
            <button id="preload">Preload next images</button>
            <select id="action">
                <option value="previous" disabled selected>Action on click</option>
                <option value="previous">Previous image</option>
                <option value="next">Next image</option>
                <option value="open">Open image</option>
            </select>
        </div>
    </body>
</html>"""

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
cache_timeout = 15 # 15 seconds

parser = argparse.ArgumentParser(description='Exposes on the web the images found in current directory.')
parser.add_argument('port', metavar='port', default=1235, type=int, help='port on which to expose the web server.')
parser.add_argument('prefixes', metavar='prefix', type=str, nargs='*', help='list of file prefixes to be used to group images together.')

def _find_common_prefix(strings):
    """Given a list of `strings`, returns the longest common leading component.
    http://stackoverflow.com/a/6718435
    """
    if not strings:
        return ''
    s1 = min(strings)
    s2 = max(strings)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1

def get_images():
    files = []
    for extension in IMAGE_EXTENSIONS:
        files.extend(glob.glob('*.%s' % extension))
    files.sort()
    if not PREFIXES:
        prefix = _find_common_prefix(files)
        return {prefix: files}
    groups = defaultdict(list)
    for f, p in itertools.product(files, PREFIXES):
        if f.startswith(p):
            groups[p].append(f)
    return groups

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/')
@cache.cached(timeout=cache_timeout)
def album():
    images = get_images()
    template = Template(HTML)
    return template.render(cwd=os.getcwdu(),
                           images=json.dumps(images),
                           images_url=IMAGES_URL)

@app.route('/latest')
def latest():
    latest_images = reversed(sorted(glob.glob('*.*'), key=os.path.getctime))
    humanized_extensions = [''.join(OrderedDict.fromkeys(ext.translate(None, '[]').lower())) for ext in IMAGE_EXTENSIONS]
    for image, extension in itertools.product(latest_images, humanized_extensions):
        if image.lower().endswith(extension):
            break
    return send_from_directory(os.getcwdu(), image)

@app.route(IMAGES_URL + '<filename>')
def images(filename):
    return send_from_directory(os.getcwdu(), filename)

if __name__ == '__main__':
    #app.debug = True
    args = parser.parse_args()
    PREFIXES = sorted(args.prefixes)
    app.run(port=args.port)

