#!/usr/bin/env pythmn

# The MIT License (MIT)
#
# Copyright (c) 2018 Sunaina Pai
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


"""Make static website/blog with Python."""


import os
import shutil
import re
import glob
import sys
import json
import datetime
import getopt
import html
import frontmatter
import commonmark
import urllib.parse

def fread(filename):
  """Read file and close the file."""
  with open(filename, 'r') as f:
    return f.read()


def fwrite(filename, text):
  """Write content to file and close the file."""
  basedir = os.path.dirname(filename)
  if not os.path.isdir(basedir):
    os.makedirs(basedir)

  with open(filename, 'w') as f:
    f.write(text)


def log(msg, *args):
  """Log message with specified arguments."""
  sys.stderr.write(msg.format(*args) + '\n')

def isArray(obj):
  return hasattr(obj, 'pop')

def isDate(obj):
    return hasattr(obj, "strftime")

def asArray(obj):
  """If obj is not an array, make it into an array with one item (obj)."""
  if obj == None:
    return []
  if not isArray(obj):
    obj = [obj]
  return obj

def truncate(text, words=25):
  """Remove tags and truncate text to the specified number of words."""
  text =  re.sub(r'{%\s+([^%]+)\s+%}','', text)
  return ' '.join(re.sub('(?s)<.*?>', ' ', text).split()[:words])


def rfc_2822_format(date_str):
  """Convert yyyy-mm-dd date string to RFC 2822 format date string."""
  d = datetime.datetime.strptime(date_str, '%Y-%m-%d')
  return d.strftime('%a, %d %b %Y %H:%M:%S +0000')

def location_with_link(loc):
  args = { 'place': loc }
  encoded_loc = urllib.parse.urlencode(args)
  output = '<a href="/locations/index.html?' + encoded_loc + '">' + loc + '</a>'
  return output

def locations_with_links(loc):
  if loc is None:
    return ''
  if loc == 'Unrecorded':
    return ''
  loc = asArray(loc)
  outputStrs = [location_with_link(lee) for lee in loc]
  return ', '.join(outputStrs)

def friend_with_link(friend):
  # turn spaces in the friend's name into dash.
  friend_url = re.sub(r' ','-',friend)
  output = '<a href="/friends/' + friend_url + '">' + friend + '</a>'
  return output

def friends_with_links(friend):
  if friend is None:
    return ''
  if friend == 'Only God!':
    return friend
  friend = asArray(friend)
  outputStrs = [friend_with_link(lee) for lee in friend]
  return ', '.join(outputStrs)

def format_elevation(el):
  el = asArray(el)
  # compute the total
  total = sum(el)
  string_output = ' + '.join([str(x) + 'm' for x in el])
  return str(total) + 'm = ' + string_output

def format_routes(routes):
  """Format route metadata as a compact, readable HTML list."""
  formatted_routes = []
  for route in asArray(routes):
    parts = [part.strip() for part in str(route).split('|', 2)]
    if len(parts) != 3:
      formatted_routes.append('<li>{}</li>'.format(html.escape(str(route))))
      continue

    name, rating_system, ratings = parts
    pitches = [rating.strip() for rating in ratings.split(',') if rating.strip()]
    pitch_count = len(pitches)
    pitch_label = 'pitch' if pitch_count == 1 else 'pitches'
    formatted_routes.append(
        '<li><strong>{}</strong> <span class="route-system">{}</span>'
        ' &mdash; {} {}: {}</li>'.format(
            html.escape(name),
            html.escape(rating_system),
            pitch_count,
            pitch_label,
            html.escape(', '.join(pitches))))

  if not formatted_routes:
    return ''
  return '<ul class="routes">{}</ul>'.format(''.join(formatted_routes))

def process_markdown(text):
  # some markdown files don't begin with '---'. Add this if they appear
  # to have yaml content.
  if (text.find('\n---') > 0) and (text.find('---') != 0):
    text = '---\n' + text
  content = {}
  t = frontmatter.loads(text, frontmatter.YAMLHandler)
  text = t.content
  for key in t.keys():
    # Turn Date objects into strings
    if isDate(t[key]):
      content[key] = t[key].strftime("%Y-%m-%d")
    else:
      content[key] = t[key]

  # This needs to become a method in its own right.
  content['formatted_guests'] = friends_with_links(content.get('guests', 'Only God!'))
  content['formatted_location'] = locations_with_links(content.get('location', 'Unrecorded'))
  content['formatted_elevation'] = format_elevation(content.get('elevation', 0))
  content['formatted_routes'] = format_routes(content.get('routes'))

  text = commonmark.commonmark(text)  # , extensions = ['meta'])
  return (content, text)

def format_category(cat):
  result = ""
  cata = asArray(cat)
  afterFirst = False
  for c in cata:
    if afterFirst:
      result += ", "
    # result += "<img width=30 src='/assets/icons/" + c + ".png'>"
    if c == 'hiking':
      result += 'hike'
    elif c == 'climbing':
      result += 'climb'
    elif c == 'skiing':
      result += 'ski'
    else:
      result += c
    afterFirst = True

  return result

def read_content(filename, basepath = None):
  """Read content and metadata from file into a dictionary."""
  # Read file content.
  text = fread(filename)

  # Read metadata and save it in a dictionary.
  date_slug = os.path.basename(filename).split('.')[0]
  match = re.search(r'^(?:(\d\d\d\d-\d\d-\d\d)-)?(.+)$', date_slug)
  content = {
    'date': match.group(1) or '1970-01-01',
    'slug': match.group(2),
  }

  if basepath != None:
    # We can improve on the slug. It is everything from the basepath
    # up to the filename, which was already taken care of in the slug.
    d = os.path.dirname(filename)
    slug_extended = d[len(basepath):]
    content['slug'] = os.path.join(slug_extended, content['slug'])

  # Convert Markdown content to HTML.
  if filename.endswith(('.md', '.mkd', '.mkdn', '.mdown', '.markdown')):
    try:
      if _test == 'ImportError':
        raise ImportError('Error forced by test')
      (t, text) = process_markdown(text)
      # consume metadata
      for i in t.keys():
        content[i] = t[i]
    except ImportError as e:
      log('WARNING: Cannot render Markdown in {}: {}', filename, str(e))

  # Update the dictionary with content and RFC 2822 date.
  content.update({
      'content': text,
      'rfc_2822_date': rfc_2822_format(content['date'])
  })

  if content.get('category') != None:
    content['category_formatted'] = format_category(content.get('category'))

  return content

def apply_plugin(plugins, params, data, default):
  args = data.split()
  plugin = plugins.get(args[0], None)
  if plugin:
    output = plugin(params, args[1:])
    return output
  return default

def render(plugins, template, **params):
  """Replace placeholders in template with values from params and plugins."""
  output =  re.sub(r'{{\s*([^}\s]+)\s*}}',
                lambda match: str(params.get(match.group(1), match.group(0))),
                template)
  output =  re.sub(r'{%\s+([^%]+)\s+%}',
                lambda match: str(apply_plugin(plugins, params, match.group(1), match.group(0))),
                output)
  return output


def get_base_path(src):
  index = src.find('*')
  if index > 0 and src.find('[') > 0 and src.find('[') < index:
    index = src.find('[')
  if index > 0:
    return src[0:index]
  return None

def make_pages(plugins, src, dst, layout, **params):
  """Generate pages from page content."""
  items = []

  # Compute a "base path" from the first wildcard in src.
  # This will be used to compose a slug that includes subdirectories.
  basepath = get_base_path(src)
  for src_path in glob.glob(src):
    content = read_content(src_path, basepath)

    page_params = dict(params, **content)

    if page_params.get('draft') != True:
      # Populate placeholders in content if content-rendering is enabled.
      if page_params.get('render') == True:
        rendered_content = render(plugins, page_params['content'], **page_params)
        page_params['content'] = rendered_content
        content['content'] = rendered_content

      items.append(content)

      dst_path = render(plugins, dst, **page_params)
      # Certain meta params need processing
      # if page_params.get('guests')
      output = render(plugins, layout, **page_params)

      log('Rendering {} => {} ...', src_path, dst_path)
      fwrite(dst_path, output)

  comparison_fun = lambda x: datetime.datetime.strptime(x['date'], '%Y-%m-%d')
  return sorted(items, key=comparison_fun, reverse=True)


def make_list(posts, dst, list_layout, item_layout, **params):
  """Generate list page for a blog."""
  items = []
  for post in posts:
    item_params = dict(params, **post)
    item_params['summary'] = post.get('excerpt', truncate(post['content']))
    item = render({}, item_layout, **item_params)
    items.append(item)

  params['content'] = ''.join(items)
  dst_path = render({}, dst, **params)
  output = render({}, list_layout, **params)

  log('Rendering list => {} ...', dst_path)
  fwrite(dst_path, output)

def plugin_image(params, args):
  arg = args[0]
  thumbs = arg.replace('cmaimages', 'cmaimages/thumbs')
  output = '<a href={image}><img src={thumb}></a><br/>'.format(image=arg, thumb=thumbs)
  return output

def plugin_image_right(params, args):
  arg = args[0]
  thumbs = arg.replace('cmaimages', 'cmaimages/thumbs')
  output = '<a href={image}><img align=\"right\" src={thumb}></a><br/>'.format(image=arg, thumb=thumbs)
  return output

def plugin_image_left(params, args):
  arg = args[0]
  thumbs = arg.replace('cmaimages', 'cmaimages/thumbs')
  output = '<a href={image}><img align=\"left\" src={thumb}></a><br/>'.format(image=arg, thumb=thumbs)
  return output

def plugin_friend_reports(params, args):
  name = ' '.join(args)
  friends_db = params['plugin_friendreports_friends_db']
  output = '<h2>Reports with ' + name + '</h2>\n'
  output += "<ul>\n"
  for trip in friends_db[name]:
    output += '<li><a href="'
    output += trip.url
    output += '">' + trip.title + '</a></li>\n'

  output += "</ul>\n"
  return output

def plugin_category_reports(params, args):
  name = ' '.join(args)
  print('called plugin_category_reports with ' + name)
  categories_db = params['plugin_categoryreports_categories_db']
  output = '<h2>Reports with ' + name + '</h2>\n'
  output += "<ul>\n"
  for trip in categories_db[name]:
    output += '<li><a href="'
    output += trip.url
    output += '">' + trip.title + '</a></li>\n'

  output += "</ul>\n"
  return output


def plugin_audioplayer(params, args):
  arg = args[0]
  print('called audioplayer with ' + arg)
  output = '<a href="' + arg + '">' + arg + '</a>\n'
  # output = '<audio controls src="' + arg + '">\n'
  # output += '  <a href="' + arg + '">Download audio</a>\n'
  # output += '</audio>\n'
  return output


def create_plugins():
  # Setup plugins
  plugins = {}
  plugins['image'] = plugin_image
  plugins['imageLeft'] = plugin_image_left
  plugins['imageRight'] = plugin_image_right
  plugins['friendreports'] = plugin_friend_reports
  plugins['categoryreports'] = plugin_category_reports
  plugins['audioplayer'] = plugin_audioplayer
  return plugins

def compose_url(post, **params):
  if params['blog'] == 'cma':
    url = params['base_path'] + '/' + params['blog'] + '/' + post['slug'] + '.html'
  else:
    url = params['base_path'] + '/' + params['blog'] + '/' + post['slug'] + '/index.html'
  return url

def full_url(post, **params):
  url = compose_url(post, **params)
  return params['site_url'] + url

def create_recents(posts, num_items, **params):
  items = []
  count = 0
  for post in posts:
    if count >= num_items:
      break
    count += 1
    url = compose_url(post, **params)
    s = '<li><a href=\"' + url + '\">' + post['title'] + '</a></li>\n'
    items.append(s)

  s = '<ul>\n' + ''.join(items) + '</ul>\n'
  return s

def add_location_trip(locations, location, trip):
  if locations.get(location) == None:
    locations[location] = []
  locations[location].append(trip)

def add_elevation_year(elevations, year, elevation):
  if elevations.get(year) == None:
    elevations[year] = 0
  elevations[year] += elevation


def gather_elevation_data(cma_posts, **params):
  # Create an elevation data structure.
  elevations = {}
  for post in cma_posts:
    year = datetime.datetime.strptime(post.get('date'), '%Y-%m-%d').year
    es = post.get('elevation')
    if es != None:
      es = asArray(es)
      for elevation in es:
        add_elevation_year(elevations, year, elevation)
  out = "<script>\n"
  out += "const elevation_data = {\n"

  firstRow = True
  for y in elevations.keys():
    if firstRow != True:
      out += ',\n'
    out += '  "' + str(y) + '": ' + str(elevations[y])
    firstRow = False

  out += "\n};"
  out += "</script>"
  print(out)
  return out

def get_pitches(route):
  data = route.split("|")
  if len(data) > 2:
    return len(data[2].split(","))
  print("badly formed data string " + route)
  return 0

def gather_pitch_count(cma_posts, **params):
  # Return total number of pitches
  pitches = 0
  for post in cma_posts:
    routes = post.get('routes')
    # Name|Rating system|pitches separated by commas
    if routes != None:
      routes = asArray(routes)
      for route in routes:
        pitches += get_pitches(route)

  print("Pitches = " + str(pitches))

  out = "<script>\n"
  out += "const pitch_count = " + str(pitches) + ";\n"
  out += "</script>"
  print(out)
  return out

def format_locations(cma_posts, **params):
  # Create a location database.
  locations = {}
  for post in cma_posts:
    location = post.get('location')
    if location != None:
      tripdata = [compose_url(post, **params), post['title']]
      location = asArray(location)
      for l in location:
        add_location_trip(locations, l, tripdata)

  out = ""
  for l in locations.keys():
    out += '<h1>' + l + '</h1>\n'
    out += '<ul>\n'
    for t in locations[l]:
      out += '<li><a href=\"' + t[0] + '\">' + t[1] + '</a></li>\n'
    out += '</ul>\n'
  return out

from typing import NamedTuple

class Region(NamedTuple):
  region: str
  locations: list

class Location(NamedTuple):
  name: str
  location: list
  map_name: str
Location.__new__.__defaults__ = (None,) * len(Location._fields)

def remove_regions(location_db):
  locations = {}
  for region in location_db:
    r = Region(**region)
    for location in r.locations:
      flocation = Location(**location)
      locations[flocation.name] = flocation
  return locations

class OutputTrip(NamedTuple):
  title: str
  date: str
  blurb: str
  url: str
OutputTrip.__new__.__defaults__ = (None,) * len(OutputTrip._fields)

class OutputLocation(NamedTuple):
  name: str
  location: list
  region: str
  trips: list
OutputLocation.__new__.__defaults__ = (None,) * len(OutputLocation._fields)

def locations_code(location_db, cma_posts, **params):
  locations = {}
  for post in cma_posts:
    location = post.get('location')
    if location != None:
      tripdata = OutputTrip(post['title'], post['date'], '', compose_url(post, **params))
      location = asArray(location)
      for l in location:
        add_location_trip(locations, l, tripdata._asdict())

  mapdata = []
  for name in locations.keys():
    # Look up the coordinates of the location.
    if name in location_db:
      o = OutputLocation(name, location_db[name].location, '', locations[name])
      mapdata.append(o._asdict())

  mapdata_string = json.dumps(mapdata);
  mapdata_string = "const mapdata = " + mapdata_string + ";"
  return mapdata_string

def add_friend_trip(friends, friend, trip):
  if friends.get(friend) == None:
    friends[friend] = []
  friends[friend].append(trip)

def make_friends_db(cma_posts, **params):
  friend_db = {}
  for post in cma_posts:
    friends = post.get('guests')
    if friends != None:
      tripdata = OutputTrip(post['title'], post['date'], '', compose_url(post, **params))
      friends = asArray(friends)
      for f in friends:
        add_friend_trip(friend_db, f, tripdata)
  return friend_db

def add_category_trip(categories, category, trip):
  if categories.get(category) == None:
    categories[category] = []
  categories[category].append(trip)

def make_category_db(cma_posts, **params):
  category_db = {}
  for post in cma_posts:
    categories = post.get('category')
    if categories != None:
      tripdata = OutputTrip(post['title'], post['date'], '', compose_url(post, **params))
      categories = asArray(categories)
      for c in categories:
        add_category_trip(category_db, c, tripdata)
  return category_db

def getOrDefault(item, key, default):
  value = item.get(key)
  if value != None:
    return value
  return default

def process_routes(routesArray):
  route_number = 0
  db = []
  for route in routesArray:
    r = {}
    parts = route.split('|')
    if (len(parts) > 2):
      r['Name'] = parts[0]
      r['RatingSystem'] = parts[1]
      pitches = parts[2].split(',')
      pitches_db = []
      for p in pitches:
        pitches_db.append(p)
      r['pitches'] = pitches_db
      r['number'] = route_number
      db.append(r)
      route_number += 1
  return db

def create_database(cma_posts, outputFile, **params):
  comparison_fun = lambda x: datetime.datetime.strptime(x['date'], '%Y-%m-%d')
  cma_posts = sorted(cma_posts, key=comparison_fun, reverse=False)

  current_key = 0
  db = []
  for post in cma_posts:
    ep = {}
    ep['key'] = current_key
    ep['url'] = full_url(post, **params)
    ep['title'] = post.get('title')
    ep['date'] = post.get('date')
    ep['category'] = asArray(getOrDefault(post, 'category', None))
    ep['elevation'] = asArray(getOrDefault(post, 'elevation', None))
    ep['location'] = asArray(getOrDefault(post, 'location', None))
    ep['guests'] = asArray(getOrDefault(post, 'guests', None))

    # routes needs to be turned into objects.
    route_db = process_routes(asArray(getOrDefault(post, 'routes', None)))
    ep['routes'] = route_db
    db.append(ep)

    current_key += 1

  json_result = json.dumps(db)
  with open(outputFile, "w") as outfile:
    outfile.write(json_result);

  log('Database rendered to ' + outputFile)


def main():
  outdir = '_site'

  options, arguments = getopt.getopt(
    sys.argv[1:],
    'h',
    ['help', 'destination='])


  for o, a in options:
    if o in ('-h', '--help'):
      print("Use --destination to specify the output directory")
      sys.exit()
    if o in ('--destination'):
      outdir = a

  # Create a new {outdir} directory from scratch.
  if os.path.isdir(outdir):
    shutil.rmtree(outdir)
  shutil.copytree('static', outdir, symlinks=True)

  # Default parameters.
  params = {
    'base_path': '',
    'author': 'Michael Stanton',
    'site_url': 'https://www.mountainwerks.org',
    'current_year': datetime.datetime.now().year
  }

  # If params.json exists, load it.
  if os.path.isfile('params.json'):
    params.update(json.loads(fread('params.json')))

  # Setup plugins
  plugins = create_plugins()
 
  # Load layouts.
  page_layout = fread('layout/page.html')
  post_layout = fread('layout/post.html')
  cma_post_layout = fread('layout/cma_post.html')
  list_layout = fread('layout/list.html')
  item_layout = fread('layout/item.html')
  friend_item_layout = fread('layout/friend_item.html')
  category_item_layout = fread('layout/category_item.html')
  html_item_layout = fread('layout/html_item.html')
  feed_xml = fread('layout/feed.xml')
  item_xml = fread('layout/item.xml')
  html_item_xml = fread('layout/html_item.xml')

  # Combine layouts to form final layouts.
  post_layout = render(plugins, page_layout, content=post_layout)
  cma_post_layout = render(plugins, page_layout, content=cma_post_layout)
  list_layout = render(plugins, page_layout, content=list_layout)

  # Create blogs.
  blog_posts = make_pages(plugins, 'content/blog/*.md',
                          outdir + '/blog/{{ slug }}/index.html',
                          post_layout, blog='blog', **params)
  cma_posts = make_pages(plugins, 'content/cma/**/*.md',
                          outdir + '/cma/{{ slug }}.html',
                          cma_post_layout, blog='cma', **params)

  # Create tags {{recent_mountaintrips}} and {{recent_blogposts}}
  params['recent_mountaintrips'] = create_recents(cma_posts, 3, blog='cma', **params)
  params['recent_blogposts'] = create_recents(blog_posts, 3, blog='blog', **params)

  # Create generated content, now that the cma_posts are finished, we can
  # mine that for location data. The goal is to create 'locations_formatted'
  params['locations_formatted'] = format_locations(cma_posts, blog='cma', **params)

  # elevation_data is available for charting, used by reporting.md.
  params['elevation_data'] = gather_elevation_data(cma_posts, **params)

  # pitch_count is available for reporting.
  params['pitch_count'] = gather_pitch_count(cma_posts, **params)


  # locations_code is JSON formatted data for display of locations on a map.
  location_database = json.loads(fread('data/locations.json'))
  # Remove unnecessary region organization in the location database.
  location_database = remove_regions(location_database)
  params['locations_code'] = locations_code(location_database, cma_posts, blog='cma', **params)
  friends_db = make_friends_db(cma_posts, blog='cma', **params)
  friend_posts = make_pages(plugins, 'content/friends/*.md',
                          outdir + '/friends/{{ slug }}/index.html',
                          post_layout,
                          plugin_friendreports_friends_db=friends_db,
                          blog='friends',
                          **params)
  # TODO: friend_posts should be sorted alphabetically instead of by date,
  # which make_pages does by default.

  categories_db = make_category_db(cma_posts, blog='cma', **params)
  category_posts = make_pages(plugins, 'content/categories/*.md',
                          outdir + '/categories/{{ slug }}/index.html',
                          post_layout,
                          plugin_categoryreports_categories_db=categories_db,
                          blog='categories',
                          **params)

  # Create site pages.
  # These pages need "render=yes" because they rely on inserting precreated lists
  # like 'recent_mountaintrips' and 'recent_blogposts' into their content.
  make_pages(plugins, 'content/_index.html', outdir + '/index.html',
             page_layout, **params, render=True, title='Mountainwerks')
  make_pages(plugins, 'content/[!_]*.html', outdir + '/{{ slug }}/index.html',
             page_layout, **params, render=True)
  make_pages(plugins, 'content/*.md', outdir + '/{{ slug }}/index.html',
             page_layout, **params, render=True)

  # Create blog list pages.
  make_list(blog_posts, outdir + '/blog/index.html',
            list_layout, item_layout, blog='blog', title='Blog', **params)
  make_list(cma_posts, outdir + '/cma/index.html',
            list_layout, html_item_layout, blog='cma', title='Mountains', **params)
  make_list(friend_posts, outdir + '/friends/index.html',
            list_layout, friend_item_layout, blog='friends', title='My Mountain Friends', **params)
  make_list(category_posts, outdir + '/categories/index.html',
            list_layout, category_item_layout, blog='categories', title='Categories', **params)



  # Create RSS feeds.
  make_list(blog_posts, outdir + '/blog/rss.xml',
            feed_xml, item_xml, blog='blog', title='Blog',
            description='Mountainwerks Blog', **params)
  make_list(cma_posts, outdir + '/cma/rss.xml',
            feed_xml, html_item_xml, blog='cma', title='Mountains',
            description='Mountainwerks Mountain Reports', **params)

  # Create json database
  create_database(cma_posts, outdir + '/database.json', blog='cma', **params)

# Test parameter to be set temporarily by unit tests.
_test = None



if __name__ == '__main__':
  main()
