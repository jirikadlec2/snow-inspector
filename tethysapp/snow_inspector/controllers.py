
import json
import datetime
import sys
import tempfile
import shutil
import os
import traceback
import urllib

from django.shortcuts import render
from django.http import JsonResponse
from django.core.urlresolvers import reverse
from tethys_gizmos.gizmo_options import MapView, MVLayer, MVView

# Migrating app to Tethys 1.4; tethys_apps.sdk deprecated.
# from tethys_apps.sdk.gizmos import Button, TextInput, SelectInput
from tethys_sdk.gizmos import Button, TextInput, SelectInput
# End of changes

from hs_restclient import HydroShare, HydroShareAuthBasic
from oauthlib.oauth2 import TokenExpiredError
from hs_restclient import HydroShare, HydroShareAuthOAuth2, HydroShareNotAuthorized, HydroShareNotFound
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings


hs_hostname = "www.hydroshare.org"


def home(request):
    """
    Controller for the app home page.
    """
    context = {}

    return render(request, 'snow_inspector/home.html', context)

def map(request):
    """
    Controller for map page.
    """

    # If we received the input from the graph page:
    if request.GET:
        print 'request.GET!'
        lat = request.GET['lat']
        lon = request.GET['lon']
        endDate = request.GET['end']
        today = endDate.strptime('%Y-%m-%d')
    else:
        # Create a session
        session = SessionMaker()

        # Query DB for gage object
        id = 1
        site = session.query(SnowSite).filter(SnowSite. id ==id).one()
        lat = site.latitude
        lon = site.longitude
        today = datetime.date.today()

    # Transform into GeoJSON format
    geometries = []

    site_geometry = dict(type="Point",
                         coordinates=[lat, lon],
                         properties={"value" :site.value})
    geometries.append(site_geometry)

    geojson_sites = {"type": "GeometryCollection",
                     "geometries": geometries}

    # configure the map
    map_options = {'height': '500px',
                   'width': '100%',
                   'input_overlays': geojson_sites}

    # configure the date picker

    date_picker = {'display_text': 'Date',
                   'name': 'endDate',
                   'autoclose': True,
                   'format': 'MM d, yyyy',
                   'start_date': '1/1/2013',
                   'today_button': True,
                   'initial': today.strftime('%m/%d/%Y')
                   }

    days_picker = {'display_text': 'Number of days:',
                   'name': 'inputDays'
                   }

    # Pre-populate lat-picker and lon_picker from model
    lat_picker = {'display_text': 'Latitude:',
                  'name': 'inputLat',
                  'placeholder': lat}

    lon_picker = {'display_text': 'Longitude:',
                  'name': 'inputLon',
                  'placeholder': lon}


    # Pass variables to the template via the context dictionary
    context = {'map_options': map_options,
               'date_picker' :date_picker,
               'days_picker' :days_picker,
               'lon_picker' :lon_picker,
               'lat_picker' :lat_picker,
               'basemap_picker' :map_picker}

    return render(request, 'snow_inspector/map.html', context)


def snow_graph(request):
    """
    Controller that will show the snow graph for user-defined lat / lon.
    """
    # default value for lat, lon
    lat = '50'
    lon = '15'

    # Check form data
    # if request.POST and 'geometry' in request.POST:
    #    geom = request.POST['geometry']
    #    data = json.loads(geom)
    #    coords = data['geometries'][0]['coordinates']
    #    lat = coords[0]
    #    lon = coords[1]

    if request.GET:
        lat = request.GET['inputLat']
        lon = request.GET['inputLon']
        numdays = int(request.GET['inputDays'])
        endDate = request.GET['endDate']
        endDate2 = datetime.datetime.strptime(endDate, '%Y-%m-%d')
        startDate2 = (endDate2 - datetime.timedelta(days=numdays)).strftime("%Y-%m-%d")
        zoom = request.GET['zoom']

        # Make the waterml url query string
        waterml_url = '?start=%s&end=%s&lat=%s&lon=%s' % (startDate2, endDate, lat, lon)

        # Make the map url query string
        map_url = '?days=%s&end=%s&lat=%s&lon=%s&zoom=%s' % (numdays, endDate, lat, lon, zoom)

    # Create template context dictionary
    context = {'lat' :lat, 'lon' :lon, 'startDate' :startDate2, 'endDate': endDate, 'waterml_url': waterml_url, 'map_url': map_url}

    return render(request, 'snow_inspector/snow_graph.html', context)


def getOAuthHS(request):

    client_id = getattr(settings, "SOCIAL_AUTH_HYDROSHARE_KEY", "None")
    client_secret = getattr(settings, "SOCIAL_AUTH_HYDROSHARE_SECRET", "None")

    # this line will throw out from django.core.exceptions.ObjectDoesNotExist if current user is not signed in via HydroShare OAuth
    token = request.user.social_auth.get(provider='hydroshare').extra_data['token_dict']
    auth = HydroShareAuthOAuth2(client_id, client_secret, token=token)
    hs = HydroShare(auth=auth, hostname=hs_hostname)

    return hs


def upload_to_hydroshare(request):

    print "running upload_to_hydroshare!"
    temp_dir = None
    try:
        return_json = {}
        if request.method == 'GET':
            get_data = request.GET

            base_url = request.build_absolute_uri()
            waterml_url = base_url.replace('upload-to-hydroshare', 'waterml')
            print waterml_url

            r_title = request.GET['title']
            r_abstract = request.GET['abstract']
            r_keywords_raw = request.GET['keywords']
            r_type = 'GenericResource'
            r_keywords = r_keywords_raw.split(',')

            hs = getOAuthHS(request)

            # download the kml file to a temp directory
            temp_dir = tempfile.mkdtemp()

            waterml_file_path = os.path.join(temp_dir, "snow.wml")
            print waterml_file_path

            urllib.urlretrieve(waterml_url, waterml_file_path)

            # upload the temp file to HydroShare
            if os.path.exists(waterml_file_path):
                resource_id = hs.createResource(r_type, r_title, resource_file=waterml_file_path,
                                                keywords=r_keywords, abstract=r_abstract)
                return_json['success'] = 'File uploaded successfully!'
                return_json['newResource'] = resource_id
            else:
                raise

    except ObjectDoesNotExist as e:
        print ("1231")
        print str(e)
        return_json['error'] = 'Login timed out! Please re-sign in with your HydroShare account.'
    except TokenExpiredError as e:
        print str(e)
        return_json['error'] = 'Login timed out! Please re-sign in with your HydroShare account.'
    except Exception, err:
        if "401 Unauthorized" in str(err):
            return_json['error'] = 'Username or password invalid.'
        elif "400 Bad Request" in str(err):
            return_json['error'] = 'File uploaded successfully despite 400 Bad Request Error.'
        else:
            traceback.print_exc()
            return_json['error'] = 'HydroShare rejected the upload for some reason.'
    finally:
        if temp_dir != None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        print return_json
        return JsonResponse(return_json)
