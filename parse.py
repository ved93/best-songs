#!/usr/bin/env python3
#
# Usage: parse.py 
# Generates 'index.html' and 'README.md' from songs listed in 'list_of_songs'
# and data stored in 'data/wiki_data.txt'. 
#
# To install Image library run:
#   pip3 install pillow


import calendar
import json
import math
import os
import re
import sys

# from PIL import Image
import matplotlib.pyplot as plt


JSONIZE_WIKI_DATA = True

MAP_IMAGE = "worldmap.jpg"
HTML_TOP = "html-top.html"
HTML_TEXT = "html-text.html"
HTML_BOTTOM = "html-bottom.html"
TEMPLATE = "web/template.html"

DRAW_YEARLY_DISTRIBUTION_PLOT = True
DRAW_HEATMAP = False
GENERATE_MD = False
GENERATE_HTML = True

HEAT_FACTOR = 0.5
HEAT_DISTANCE_THRESHOLD = 5
HEATMAP_ALPHA = 180
ALPHA_CUTOFF = 0.15

DISPLAY_KEYS = ['genre', 'writer', 'producer', 'length', 'label', 'origin']
MONTHS_RE = 'january|february|march|april|may|june|july|august|september|octo' \
            'ber|november|december'

SORT_BY_DATE = True

MONTHS = {'january': 1,
          'february': 2,
          'march': 3,
          'april': 4,
          'may' : 5,
          'june': 6,
          'july': 7,
          'august': 8,
          'september': 9,
          'october': 10,
          'november': 11,
          'december': 12}

IMG_HEIGHT = 146 # 123

###
##  MAIN
#

def main():
    if JSONIZE_WIKI_DATA:
        os.popen('cd data;./jsonize.py;cd ..').read()
    readme = get_file_contents("list_of_songs")
    albumData = read_json("data/wiki_data.json")
    listOfAlbums = get_list_of_songs(readme)
    if SORT_BY_DATE:
        listOfAlbums = sort_by_date(listOfAlbums, albumData)
    if DRAW_YEARLY_DISTRIBUTION_PLOT:
        os.popen('cd data;./plot.py;cd ..').read()
    out_html, out_md = generate_files(albumData, listOfAlbums)
    write_to_file('index.html', out_html)
    write_to_file('README.md', out_md)


def get_list_of_songs(readme):
    listOfSongs = []
    for line in readme:
        if line.startswith('###'):
            line = re.sub('^.*\* ', '', line)
            listOfSongs.append(line.strip())
    return listOfSongs


def sort_by_date(listOfAlbums, albumData):
    dates = [(get_numeric_date(get_song_name(a), albumData), a) for a in listOfAlbums]
    dates.sort()
    return [a[1] for a in dates]


def generate_files(albumData, listOfAlbums):
    table_html, table_md = generate_list(listOfAlbums, albumData)

    if DRAW_YEARLY_DISTRIBUTION_PLOT:
        table_html += '<h2><a href="#release-dates" name="release-dates">#</a>Release Dates</h2>\n'
        table_html += '<img src="data/img/years.png" alt="Release dates" width="920"/>\n'
        table_md += '\nRelease Dates\n------\n![yearly graph](data/img/years.png.png)'

    if DRAW_HEATMAP:
        out += '<h2><a href="#studio-locations" name="studio-locations">#</a>Studio Locations</h2>\n'
        out += '<img src="heatmap.png" alt="Studio Locations" width="920"/>\n'

    no_albums = len(listOfAlbums)
    title = f"{no_albums} Greatest Songs From '54 to '04"
    template = ''.join(get_file_contents(TEMPLATE))
    out_html = template.format(title=title, table=table_html)
    out_md = get_out_md(table_md, title, template)
    return out_html, out_md


def get_out_md(table_md, title, template):
    out = [title, '\n']
    out.append('=' * len(title))
    out.append('\n')
    match = re.search('\{title\}</h1>(.*)\{table\}', template, flags=re.DOTALL)
    out.append(match.group(1))
    out.append(table_md)
    return ''.join(out)


def generate_list(listOfAlbums, albumData):
    out_html, out_md = [], []
    for albumName in listOfAlbums:
        songName = get_song_name(albumName)
        if not songName:
            print(f'Cannot match song with albumName: {albumName}')
            continue
        if songName not in albumData:
            print(f"Song name not in wiki_data: {songName}")
            continue
        bandName = albumData[songName]['artist']
        title_html, title_md = get_title(albumName, songName, bandName, albumData)
        image_html, image_md = get_image(songName, bandName, albumData)
        div_html, div_md = get_div(songName, albumData)
        out_html.extend((title_html, image_html, div_html))
        out_md.extend((title_md, image_md, div_md))
    return ''.join(out_html), ''.join(out_md)


def get_song_name(albumName):
    song = re.search('\'(.*)\'', albumName)
    if not song:
        print(f"No parenthesis around song name: {albumName}")
        sys.exit()
    return song.group(1)


def get_title(albumName, songName, bandName, albumData):
    album_name_abr = albumName.replace(' ', '')
    releaseDate = albumData[songName]['released']
    if type(releaseDate) == list:
        releaseDate = releaseDate[0]
    year = get_numeric_year(releaseDate)
    if not year:
        print(f'Cannot match release year with releaseDate: {releaseDate}')
        year = ''
    year = year[-2:]
    month = get_month(releaseDate)
    month = '' if not month else calendar.month_abbr[int(month)]
    link = f"<a href='#{album_name_abr}' name='{album_name_abr}'>#</a>" 
    text = f"'{year} {month} | \"{songName}\" — {bandName}"      
    title_html = f"<h2>{link}{text}</h2>\n"
    title_md = f"\n### {text}  \n"
    return title_html, title_md


def get_numeric_date(album, albumData):
    release = albumData[album]['released']
    if type(release) == list:
        release = release[0]
    year = get_numeric_year(release)
    if not year:
        return 0
    month = get_month(release)
    if not month:
        return int(year+'00')
    month = '{:0>2}'.format(month)
    return int(year+month)


def get_month(release):
    if re.search('[a-zA-Z]', release):
        month = re.search(MONTHS_RE, release, flags=re.IGNORECASE)
        if month:
            month = month.group()
            return MONTHS[month.lower()]
    return get_numeric_month(release)


def get_numeric_month(release):
    if re.search('\.', release):
        tokens = release.split('.')
        digit_month = re.match('\d+', tokens[1])
        if digit_month:
            return digit_month.group()


def get_numeric_year(release):
    year = re.search('\d{4}', release)
    if not year:
        return
    return year.group()


def get_image(songName, bandName, albumData):
    cover_html, cover_md = get_cover(songName, bandName, albumData)
    if not cover_html:
        cover_html = ''
    image_html = f'<div style="display:inline-block;vertical-align:top;border' \
                 f'-left:7px solid transparent">\n{cover_html}\n</div>'
    return image_html, cover_md


def get_div(songName, albumData):
    data_html, data_md = [], []
    for key in DISPLAY_KEYS:
        row_html, row_md = get_row(albumData[songName], key)
        data_html.append(row_html)
        if row_md:
            data_md.append(row_md)
    data_str = '\n'.join(data_html)
    div_html = f'<div style="display:inline-block;border-left:15px solid tran' \
               f'sparent"><table>{data_str}</table></div>'
    div_md = get_div_md(data_md)
    return div_html, div_md


def get_div_md(data):
    lines = [f"**{line}**  " for line in data]
    out = (lines + ['<br>  ']*6)[:6]
    out = '\n'.join(out)
    return f'\n{out}\n'


def get_row(songData, key):
    if key not in songData:
        return '', ''
    value = songData[key]
    if type(value) == list:
        value = ', '.join(value)
        key = f'{key}s'
    if type(value) != str:
        return '', ''
    key = key.title()
    value = value.title()
    row_html = f"<tr><td><b>{key}&ensp;</b></td><td><b>{value}</b></td></tr>"
    row_md = f"{key}:&ensp;{value}"
    return row_html, row_md


def get_cover(albumName, bandName, albumData):
    imageLink = get_img_link(albumName, albumData)
    if not imageLink or not os.path.isfile(imageLink):
        return None, None
    yt_link = get_yt_link(f'{bandName} {albumName}')
    cover_html = f'{yt_link}<img src="{imageLink}" alt="cover" height="' \
                 f'{IMG_HEIGHT}px"/></a>\n'
    cover_md = f'{yt_link}<img src="{imageLink}" align="left" alt="cover" hei' \
               f'ght="{IMG_HEIGHT}px"/></a>\n'
    return cover_html, cover_md


def get_img_link(albumName, albumData):
    album = albumData.get(albumName, None)
    if not album:
        return
    link = album.get('cover', None)
    if not link:
        return
    return f'data/img/cover/{link}'


def get_yt_link(albumName):
    out = '<a target="_blank" href="https://www.youtube.com/results?search_query=' \
          + albumName.replace('-', '').replace(' ', '+') + '+song"> '
    return out


###
##  UTIL
#

def get_file_contents(fileName):
    with open(fileName) as f:
        return f.readlines()


def read_json(fileName):
    with open(fileName) as f:    
        return json.load(f)


def write_to_file(fileName, contents):
    f = open(fileName,'w')
    f.write(contents) 
    f.close()


if __name__ == '__main__':
  main()
