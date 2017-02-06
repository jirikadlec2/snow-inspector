import math
import datetime
import png
import urllib2

from django.http import JsonResponse
from django.shortcuts import render_to_response


"""
Convert (lat, lon) to the proper tile number
Taken from http://wiki.openstreetmap.org/wiki/Tilenames#Lon..2Flat._to_tile_numbers_2
"""
def deg2num(lat_deg, lon_deg, zoom):
    tileSize = 256;
    lat_rad = math.radians(float(lat_deg))
    n = 2.0 ** zoom
    xtilef = (float(lon_deg) + 180.0) / 360.0 * n
    xtile = int(xtilef)
    xpixel = int((xtilef - float(xtile)) * tileSize)
    ytilef = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    ytile = int(ytilef)
    ypixel = int((ytilef -float(ytile)) * tileSize)
    return (xtile, ytile, xpixel, ypixel)
    

def getTileURL(xtile, ytile, zoom, date):
    baseURL = 'http://map1.vis.earthdata.nasa.gov/wmts-webmerc/' + \
    '{0}/default/{1}/{2}/{3}/{4}/{5}.png'
    layer = 'MODIS_Terra_Snow_Cover'
    tileMatrix = 'GoogleMapsCompatible_Level8'
    time = date.strftime("%Y-%m-%d")
    zoom = 8
    return baseURL.format(layer, time, tileMatrix, zoom, ytile, xtile)
    
        
def getTileURLTemplate(xtile, ytile, zoom):
    baseURL = 'http://map1.vis.earthdata.nasa.gov/wmts-webmerc/' + \
    '{0}/default/{1}/{2}/{3}/{4}/{5}.png'
    layer = 'MODIS_Terra_Snow_Cover'
    tileMatrix = 'GoogleMapsCompatible_Level8'
    time = 'DATE_PLACEHOLDER'
    return baseURL.format(layer, time, tileMatrix, zoom, ytile, xtile)

    
def getTimeSeries(lat, lon, beginDate, endDate):
    nDays = (endDate - beginDate).days
    datelist = [beginDate + datetime.timedelta(days=x) for x in range(0,nDays)]
    zoom = 8
    xtile, ytile, xpixel, ypixel = deg2num(lat, lon, zoom)
    ts = []
    for d in datelist:        
        url = getTileURL(xtile, ytile, zoom, d)
        snow_val = getImage(url, ypixel, xpixel)
        if snow_val > 100:
            snow_val = None
        ts.append(snow_val)
    return ts


def getTimeSeries2(lat, lon, beginDate, endDate, zoom):
    nDays = (endDate - beginDate).days
    datelist = [beginDate + datetime.timedelta(days=x) for x in range(0,nDays)]
    xtile, ytile, xpixel, ypixel = deg2num(lat, lon, zoom)
    ts = []
    for d in datelist:        
        url = getTileURL(xtile, ytile, zoom, d)
        snow_val = getImage(url, ypixel, xpixel)
        if snow_val > 100:
            snow_val = None
        ts.append(snow_val)
    return ts


def xCoordinateToLongitude(x, zoom):
    return float(x) / (2.0 ** zoom) * 360.0 - 180.0


def yCoordinateToLatitude(y, zoom):
    n = math.pi - (2 * math.pi * float(y)) / (2 ** zoom)
    lat_rad = math.atan(math.sinh(n))
    return lat_rad * (180.0 / math.pi)

def tileBoundsLonLat(x, y, zoom):
    xMin = xCoordinateToLongitude(x, zoom)
    yMin = yCoordinateToLatitude(y, zoom)
    xMax = xCoordinateToLongitude(x+1,zoom)
    yMax = yCoordinateToLatitude(y+1, zoom)
    return (xMin, yMin, xMax, yMax)
    
def getImage(url, rowpixel, colpixel):
    r = png.Reader(file=urllib2.urlopen(url))
    w, h, pixels, metadata = r.read()
    pxlist = list(pixels)
    return pxlist[rowpixel][colpixel]

def getImageVals(url):
    r = png.Reader(file=urllib2.urlopen(url))
    w, h, pixels, metadata = r.read()
    pxlist = list(pixels)
    return pxlist


def process_query(request):
    #default value for lat, lon
    lat = '50'
    lon = '15'
    start = datetime.datetime.today().strftime("%Y-%m-%d")
    end = (datetime.datetime.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

    if request.GET:
        lat = request.GET["lat"]
        lon = request.GET["lon"]
        start = request.GET["start"]
        end = request.GET["end"]

        if request.GET["start"]:
            startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        if request.GET["end"]:
            enddate = datetime.datetime.strptime(end, "%Y-%m-%d")
    
    context = {'lat':lat, 'lon':lon, 'startdate':start, 'enddate':end}
    return context


def get_site_name(lat, lon):
    lat_name = "%0.4fN" % lat
    if lat < 0:
        lat_name = "%0.4fS" % (-1 * lat)
    lon_name = "%0.4fE" % lon
    if lon < 0:
        lon_name = "%0.4fW" % (-1 * lon)

    return lat_name + lon_name

def format_time_series(startDate, ts, nodata_value):
    nDays = len(ts)
    datelist = [startDate + datetime.timedelta(days=x) for x in range(0,nDays)]
    formatted_ts = []
    for i in range(0, nDays):
        formatted_val = ts[i]
        if (formatted_val is None):
            formatted_val = nodata_value
        formatted_date = datelist[i].strftime('%Y-%m-%dT%H:%M:%S')
        formatted_ts.append({'date':formatted_date, 'val':formatted_val})

    return formatted_ts

def get_data_for_pixel(request):
    """
    Controller that will show the snow data for a specific pixel in WaterML format
    """  
    start = datetime.datetime.today().strftime("%Y-%m-%d")
    end = (datetime.datetime.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

    if request.GET:
        x = request.GET["x"]
        y = request.GET["y"]
        start = request.GET["start"]
        end = request.GET["end"]

        if request.GET["start"]:
            startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        if request.GET["end"]:
            enddate = datetime.datetime.strptime(end, "%Y-%m-%d")
    
    context = {'x':x, 'y':y, 'startdate':start, 'enddate':end}
    #pass url of tile to output
    zoom = 16
    lon = xCoordinateToLongitude(x, zoom)
    lat = yCoordinateToLatitude(y, zoom)
    ts = getTimeSeries(lat, lon, startdate, enddate)
    nodata_value = -9999
    time_series = format_time_series(startdate, ts, nodata_value)
    site_name = str(x) + '-' + str(y)
    context = {'lat':lat, 'lon':lon, 'startdate':start, 'enddate':end, 'site_name':site_name, 'time_series':time_series}

    xmlResponse = render_to_response('snow_inspector/waterml.xml', context)
    xmlResponse['Content-Type'] = 'application/xml;'
    return xmlResponse



def get_data_json(request):
    """
    Controller that will show the snow data in Json format
    """  
    lat = '50'
    lon = '15'
    start = datetime.datetime.today().strftime("%Y-%m-%d")
    end = (datetime.datetime.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

    if request.GET:
        lat = request.GET["lat"]
        lon = request.GET["lon"]
        start = request.GET["start"]
        end = request.GET["end"]

        if request.GET["start"]:
            startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        if request.GET["end"]:
            enddate = datetime.datetime.strptime(end, "%Y-%m-%d")
    
    context = {'lat':lat, 'lon':lon, 'startdate':start, 'enddate':end}
    #pass url of tile to output
    zoom = 8
    xtile, ytile, xpixel, ypixel = deg2num(lat, lon, zoom)
    tile = getTileURLTemplate(xtile, ytile, zoom)

    ts = getTimeSeries(lat, lon, startdate, enddate)
    return JsonResponse({"query":context, "tile":tile, "data":ts})


def get_data_waterml(request):
    """
    Controller that will show the data in WaterML 1.1 format
    """
    lat = '50'
    lon = '15'
    start = datetime.datetime.today().strftime("%Y-%m-%d")
    end = (datetime.datetime.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

    if request.GET:
        lat = request.GET["lat"]
        lon = request.GET["lon"]
        start = request.GET["start"]
        end = request.GET["end"]

        if request.GET["start"]:
            startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        if request.GET["end"]:
            enddate = datetime.datetime.strptime(end, "%Y-%m-%d")
    
    zoom = 8
    nodata_value = -9999
    ts = getTimeSeries(lat, lon, startdate, enddate)
    time_series = format_time_series(startdate, ts, nodata_value)
    site_name = get_site_name(float(lat), float(lon))
    context = {'lat':lat, 'lon':lon, 'startdate':start, 'enddate':end, 'site_name':site_name, 'time_series':time_series}

    xmlResponse = render_to_response('snow_inspector/waterml.xml', context)
    xmlResponse['Content-Type'] = 'application/xml'
    xmlResponse['content-disposition'] = "attachment; filename=output-time-series.xml"
    return xmlResponse


#gets all of the tiles that are inside or overlap the bounding box
def getTilesInView(lonmin, latmin, lonmax, latmax, tileDate):

    tiles = []
    tileInfos = []
    zoom = 8

    #upper left
    ulX, ulY, ulpixelXUL, ulpixelYUL = deg2num(latmax, lonmin, zoom)
    ulTile = getTileURL(ulX, ulY, zoom, tileDate)
    (xLeft, yTop, xRight, yBottom) = getPixelsInTile(ulX, ulY, lonmin, latmin, lonmax, latmax)
    tile_ul = ({"url":ulTile, "xTile": ulX, "yTile": ulY,
                      "xPixelLeft":xLeft, "yPixelTop":yTop, "xPixelRight":xRight, "yPixelBottom":yBottom})

    #upper right
    urX, urY, urpixelX, urpixelY = deg2num(latmax, lonmax, zoom)
    urTile = getTileURL(urX, urY, zoom, tileDate)
    (xLeft, yTop, xRight, yBottom) = getPixelsInTile(urX, urY, lonmin, latmin, lonmax, latmax)
    tile_ur = ({"url":urTile, "xTile": urX, "yTile": urY,
                        "xPixelLeft":xLeft, "yPixelTop":yTop, "xPixelRight":xRight, "yPixelBottom":yBottom})

    #lower left
    llX, llY, llpixelX, llpixelY = deg2num(latmin, lonmin, zoom)
    llTile = getTileURL(llX, llY, zoom, tileDate)
    (xLeft, yTop, xRight, yBottom) = getPixelsInTile(llX, llY, lonmin, latmin, lonmax, latmax)
    tile_ll = ({"url":llTile, "xTile": llX, "yTile": llY,
                        "xPixelLeft":xLeft, "yPixelTop":yTop, "xPixelRight":xRight, "yPixelBottom":yBottom})

    #lower right
    lrX, lrY, lrpixelX, lrpixelY = deg2num(latmin, lonmax, zoom)
    lrTile = getTileURL(lrX, lrY, zoom, tileDate)
    (xLeft, yTop, xRight, yBottom) = getPixelsInTile(lrX, lrY, lonmin, latmin, lonmax, latmax)
    tile_lr = ({"url":lrTile, "xTile": lrX, "yTile": lrY,
                        "xPixelLeft":xLeft, "yPixelTop":yTop, "xPixelRight":xRight, "yPixelBottom":yBottom})

    #in between
    tileMinRow = tile_ul['yTile']
    tileMaxRow = tile_ll['yTile']
    tileMinCol = tile_ul['xTile']
    tileMaxCol = tile_ur['xTile']

    print tileMinRow
    print tileMaxRow
    print tileMinCol
    print tileMaxCol

    nTileCols = tileMaxCol - tileMinCol + 1
    nTileRows = tileMaxRow - tileMinRow + 1
    print nTileRows
    print nTileCols

    for tileRow in range(tileMinRow, tileMaxRow + 1):
        for tileCol in range(tileMinCol, tileMaxCol + 1):
            tileURL = getTileURL(tileCol, tileRow, zoom, tileDate)
            (xLeft, yTop, xRight, yBottom) = getPixelsInTile(tileCol, tileRow, lonmin, latmin, lonmax, latmax)
            tileInfo = ({"url":tileURL, "xTile": tileCol, "yTile": tileRow,
                          "xPixelLeft": xLeft, "yPixelTop": yTop, "xPixelRight": xRight, "yPixelBottom": yBottom})
            tiles.append(tileURL)
            tileInfos.append(tileInfo)

    return tileInfos


def getPixelsInTile(tileX, tileY, lonmin, latmin, lonmax, latmax):

    tileXmin, tileYmin, xPixelLeft, yPixelTop = deg2num(latmax, lonmin, 8)
    if (tileXmin == tileX):
        xPixelMin = xPixelLeft
    else:
        xPixelMin = 0

    #xPixelRight
    tileXmax, tileYmax, xPixelRight, yPixelBottom = deg2num(latmin, lonmax, 8)
    if (tileXmax == tileX):
        xPixelMax = xPixelRight
    else:
        xPixelMax = 255

    #yPixelTop
    if (tileYmin == tileY):
        yPixelMin = yPixelTop
    else:
        yPixelMin = 0

    #yPixelBottom
    if (tileYmax == tileY):
        yPixelMax = yPixelBottom
    else:
        yPixelMax = 255

    return (xPixelMin, yPixelMin, xPixelMax, yPixelMax)



#gets the pixel borders for the web Mercator mapX, mapY
def get_pixel_borders2(request):

    if request.GET:
        lonmin = float(request.GET["lonmin"])
        latmin = float(request.GET["latmin"])
        lonmax = float(request.GET["lonmax"])
        latmax = float(request.GET["latmax"])
        tileDate = datetime.datetime.strptime(request.GET["date"], "%Y-%m-%d")

        #to get the bottom-right
        lon = lonmax
        lat = latmin

        boundaryList = []
        tileId = 0

        #check tiles in view
        tiles = getTilesInView(lonmin, latmin, lonmax, latmax, tileDate)

        #json feature list
        featureList = {"type":"FeatureCollection", "features":[]}


        #for each tile...
        for tile in tiles:
            bigTileLon = xCoordinateToLongitude(tile["xTile"], 8)
            bigTileLat = yCoordinateToLatitude(tile["yTile"], 8)

            startTileX, startTileY, xPixel, yPixel = deg2num(bigTileLat, bigTileLon, 16)
            vals = getImageVals(tile["url"])
            for i in range(tile["yPixelTop"], tile["yPixelBottom"] + 1):
                for j in range(tile["xPixelLeft"], tile["xPixelRight"] + 1):
                    tileY = startTileY + i
                    tileX = startTileX + j
                    tileId = tileId + 1
                    pixelVal = vals[i][j]

                    # special value for cloud..

                    if pixelVal > 100:
                        pixelVal = "C"

                    minX, minY, maxX, maxY = tileBoundsLonLat(tileX, tileY, 16)
                    pixel = {"id": tileId, "pixelval": pixelVal, "minX": minX, "minY": minY, "maxX": maxX, "maxY": maxY}
                    boundaryList.append(pixel)

                    newF = {
                        "type": "Feature",
                        "properties": {
                            "id": tileId,
                            "val": pixelVal
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [minX, minY], [maxX, minY], [maxX, maxY], [minX, maxY], [minX, minY]
                            ]]
                        }
                    }
                    featureList["features"].append(newF)

        return JsonResponse(featureList)

        #context = {'boundaries':boundaryList}
        #geojsonResponse = render_to_response('snow_inspector/geojson.json', context)
        #geojsonResponse['Content-Type'] = 'application/json;'
        #return geojsonResponse
