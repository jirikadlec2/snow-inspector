console.log("Snow inspector! main_snow.js");

var chart;
var pixelBoundaries;
var styleCache = {};

function getUrlVars() {
	var vars = [], hash;
	var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
	for(var i = 0; i < hashes.length; i++)
	{
		hash = hashes[i].split('=');
		vars.push(hash[0]);
		vars[hash[0]] = hash[1];
	}
	return vars;
}


function get_date_for_chart(date) {
    var year = date.substring(0,4);
	var mon = parseInt(date.substring(5,7));
	var day = date.substring(8,10);
	return Date.UTC(year, mon-1, day);
}

var sequential_update = function(url){
	return function() {
		console.log('starting ' + url);
		//todo put ajax here
		$.getJSON(url).done(function () {
			console.log('received!');
		})
	}
}

function add_data_to_chart(beginDate, response_data, myChart) {
	var timeSeries = [];
	for (var i = 0; i < response_data.data.length; i++){
		if (response_data.data[i] !== null) {
			timeSeries.push([beginDate + (86400000 * i), response_data.data[i]]);
		}
	}  
	myChart.series[0].setData(timeSeries);
}

function add_data_to_chart2(response_data, myChart) {
	var n = myChart.series[0].data.length;
	var beginDate = Date.parse(response_data.query.startdate);
	for (var i = 0; i < response_data.data.length; i++){
		if (response_data.data[i] !== null) {		
			var newPoint = [beginDate + (86400000 * i), response_data.data[i]];
			myChart.series[0].addPoint(newPoint);
		}
	}  
}

function set_chart_tooltip(myChart, tile_url, xpixel, ypixel) {
	myChart.tooltip.options.formatter = function() {
		x_date = (new Date(this.x)).toISOString().substring(0, 10);
		var url = tile_url.replace("DATE_PLACEHOLDER", x_date);
		var html = '<p>original data: ' + x_date + ' snow: ' + this.y + '%</p><div class="img-container" style="position: relative"><img width="256px" height="256px" style="border:1px solid #000000" src="' + url + '" /><p style="position: absolute; left: ' +
xpixel +'px; top: ' + ypixel +'px; color: #000000; font-weight:bold">X</p></div>';
                //console.log(html);	
		return html;	
	}
}



function add_days(time_ms, days) {
	return (new Date(time_ms + 86400000 * days)).toISOString().substring(0, 10);
}

//gets the proper URL requests for the AJAX function call
function get_ajax_urls(lat, lon, begin_ms, end_ms, step) {
	var base_url = "/apps/snow-inspector/snow_data/?lat=" + lat + "&lon=" + lon;
	var urls = [];
	var nSteps = ((end_ms - begin_ms) / 86400000) / step;
	var begin_ms1 = begin_ms - 86400000;
	for (i=0; i < nSteps; i++) {
		var iBegin = add_days(begin_ms1, i*step + 1);
		var iEnd = add_days(begin_ms, i*step + step);
		var iUrl = base_url + "&start=" + iBegin + "&end=" + iEnd;
		urls.push(iUrl);
	}
	var iBeginLast = begin_ms + (nSteps * step * 86400000);
	if (iBeginLast < end_ms) {
		urls.push(base_url + "&start=" + iBeginLast + "&end=" + iEnd);
	}
	return(urls);
}


function update_chart(lat, lon, begin, end) { 
   //var hydro_year = get_hydrologic_year(date);
   //var beginDate = Date.UTC((hydro_year - 1), 9, 1);
   //var series_url = get_chart_url(station_id, hydro_year);
   var beginDate = Date.parse(begin);
   var endDate = Date.parse(end);
   console.log(beginDate);

   var urls = get_ajax_urls(lat, lon, beginDate, endDate, 15);
   for (var u=0; u< urls.length; u++) {
   	console.log(urls[u]);
   }

   //the number of the request currently executed
   var iRequest = 0;

	//adds data to chart with existing data
	function ajax2() {
		console.log("ajax2! " + urls[iRequest]);
		$.ajax({
			url: urls[iRequest], 
			type: "GET",
			dataType: "json",
			success: function(response_data){

				if (iRequest === 0) {
					set_chart_tooltip(chart, response_data.tile,
                                          response_data.xpixel,response_data.ypixel);
				}

				add_data_to_chart2(response_data, chart);
				
				iRequest++;
				if (iRequest < urls.length) {
					ajax2();
				}	
			},
			error: function() {
				//try to repeat data retrieval..
				console.log("error for URL: " + urls[iRequest]);
				ajax2();
			}
		});
	}

    ajax2();


   //chart.showLoading('Loading Snow Data...');
   //chart.hideLoading();
}


function make_point_layer() {
	var source = new ol.source.Vector();
	var vector = new ol.layer.Vector({
	  source: source,
	  style: new ol.style.Style({
		fill: new ol.style.Fill({
		  color: 'rgba(255, 255, 255, 0.2)'
		}),
		stroke: new ol.style.Stroke({
		  color: '#ffcc33',
		  width: 2
		}),
		image: new ol.style.Circle({
		  radius: 7,
		  fill: new ol.style.Fill({
			color: '#ffcc33'
		  })
		})
	  })
	});
	return(vector);
}


function add_point_to_map(layer, coordinates){
	var coords = ol.proj.transform(coordinates, 'EPSG:4326','EPSG:3857');
	var geometry = new ol.geom.Point(coords);
	var feature = new ol.Feature({
		geometry: geometry,
		attr: '1'
	});
	layer.getSource().clear();
	layer.getSource().addFeature(feature);
}

function add_snow_pixels_to_map(map, map_date) {
	var extent = map.getView().calculateExtent(map.getSize());

	var extentLatLon = ol.proj.transformExtent(extent, 'EPSG:3857', 'EPSG:4326')
	var xmin = extentLatLon[0];
	var ymin = extentLatLon[1];
	var xmax = extentLatLon[2];
	var ymax = extentLatLon[3];

	var baseurl = '/apps/snow-inspector/pixel-borders/';

	var pixel_url = baseurl +'?lonmin=' + xmin + '&latmin=' + ymin + '&lonmax=' + xmax + '&latmax=' + ymax + '&date=' + map_date;
	console.log(pixel_url);

	var pixel_source = new ol.source.GeoJSON({
		projection : 'EPSG:3857',
		url : pixel_url
	});

	if (typeof pixelBoundaries === 'undefined') {
		pixelBoundaries = new ol.layer.Vector({
			source : pixel_source,
			style : function(feature, resolution) {
				var text = feature.get('val');
				if (!styleCache[text]) {
					styleCache[text] = [new ol.style.Style({
						fill : new ol.style.Fill({
							color : 'rgba(255, 255, 255, 0.1)'
						}),
						stroke : new ol.style.Stroke({
							color : '#319FD3',
							width : 1
						}),
						text : new ol.style.Text({
							font : '12px sans-serif',
							text : text,
							fill : new ol.style.Fill({
								color : '#000'
							}),
							stroke : new ol.style.Stroke({
								color : '#fff',
								width : 3
							})
						}),
						zIndex : 999
					})];
				}
				return styleCache[text];
			}
		});
		map.addLayer(pixelBoundaries);
	} else {
		pixelBoundaries.setSource(pixel_source);
	}
}


function make_base_layer() {

	var params = getUrlVars();
	var layerName = params.layer;
	console.log(layerName);

	// build the BING Map layer
	if (layerName === 'bing') {
		var bing_layer = new ol.layer.Tile({
			source: new ol.source.BingMaps({
				imagerySet: 'AerialWithLabels',
				key: 'AkCPywc954jTLm72zRDvk0JpSJarnJBYPWrNYZB1X8OajN_1DuXj1p5u1Hy2betj'
			})
		})
		return bing_layer;
	}

    //build OpenStreet map layer
	if (layerName == 'osm') {
		var openstreet_layer = new ol.layer.Tile({
			source: new ol.source.OSM()
		});
		return openstreet_layer;
	}

    //build MapQuest map layer
	if (layerName == 'mapQuest') {
		var mapQuest_layer = new ol.layer.Tile({
			source: new ol.source.MapQuest({layer: 'sat'})
		});
		return mapQuest_layer;
	}

    //default option: build Esri map layer
	layerName = 'esri';
	if (layerName == 'esri') {
		var esri_layer = new ol.layer.Tile({
			source: new ol.source.XYZ({
				attribution: [new ol.Attribution({
					html: 'Tiles &copy; <a href="http://services.arcgisonline.com/ArcGIS/' +
					'rest/services/World_Topo_Map/MapServer>ArcGIS</a>'
				})],
				url: 'http://server.arcgisonline.com/ArcGIS/rest/services/' +
				'World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
			})
		});
		return esri_layer;
	}
}


$(document).ready(function () {

	var base_layer = make_base_layer();
	var snow_point_layer = make_point_layer();
	var map = new ol.Map({
		layers: [base_layer, snow_point_layer],
		controls: ol.control.defaults(),
		target: 'detail-map',
		view: new ol.View({
			center: [0, 0],
			zoom: 14
		})
	});

	var snow_lat = parseFloat($("#lat").text());
	var snow_lon = parseFloat($("#lon").text());
	var snow_coords = [snow_lon, snow_lat];
	console.log(snow_coords);
	add_point_to_map(snow_point_layer, snow_coords);
	var coords_mercator = ol.proj.transform(snow_coords, 'EPSG:4326','EPSG:3857');
	map.getView().setCenter(coords_mercator);


	if (!($("#snow-chart").length)) {
        	console.log("no snow-chart element found!");
                return;
        } else {
		var lat = $("#lat").text();
		var lon = $("#lon").text();
		var begin_date = $("#startDate").text();
		var end_date = $("#endDate").text();
		var begin_ms = Date.parse(begin_date);
		var end_ms = Date.parse(end_date);
		console.log("lat: " + lat + " lon: " + lon + " begin_date: " + begin_date + " end_date: " + end_date);
	}

	var chart_options = {
		chart: {
			renderTo: 'snow-chart',
			zoomType: 'x'
		},
		loading: {
			labelStyle: {
				top: '45%',
				left: '50%',
				backgroundImage: 'url("/static/snow_inspector/images/ajax-loader.gif")',
				display: 'block',
				width: '134px',
				height: '100px',
				backgroundColor: '#000'
			}
		},
		title: {
			text: 'Snow Coverage at: ' + lat + 'N ' + lon + 'E'
		},
		xAxis: {
			type: 'datetime',
			min: begin_ms,
			max: end_ms
		},
		yAxis: {
			title: {
				text: 'Snow Coverage(%)'
			},
			min: 0.0,
			max: 100.0
		},
		legend: {
			enabled: false
		},
                tooltip: {
                    useHTML: true
                },
		plotOptions: {
			series: {
				cursor: 'pointer',
				allowPointSelect: true,
				point: {
					events: {
						click: function (e) {
							// mouse click event
							console.log('you clicked the chart!');
							var selected_date = Highcharts.dateFormat('%Y-%m-%d', this.x);
							add_snow_pixels_to_map(map, selected_date);
						},
						mouseOver: function() {
							// mouse hover event
							console.log('mouse over!');
							var selected_date = Highcharts.dateFormat('%Y-%m-%d', this.x);
							add_snow_pixels_to_map(map, selected_date);
						}
					}
				}
			},
			line: {
				color: Highcharts.getOptions().colors[0],
				marker: {
					radius: 2,
					states: {
                		select: {
                    		fillColor: 'red',
                    		lineWidth: 0,
							radius: 4
                		}
            		}
				},
				lineWidth: 1,
				states: {
					hover: {
						lineWidth: 1
					}
				},
				threshold: null
			}
		},
		series: [{}]
	};

	chart_options.series[0].type = 'line';
	chart_options.series[0].name = 'Snow Coverage';
	chart = new Highcharts.Chart(chart_options);

	//setup some default values
	var resTitle = 'MODIS Snow coverage at ' + lon + ', ' + lat;

	var resAbstr = 'This resource contains an automatically created WaterML representing a time series of fractional snow cover ' +
            'from the MODIS TERRA MOD10_L3 data set at lat: ' + lat + ', lon: ' + lon + ' in the time period: ' + begin_date +
			' - ' + end_date + '. It was retrieved from the NASA GIBS web service and ' +
			'processed using the MODIS Snow Inspector application.';


    var resKwds = 'snow, MODIS';

	$("#resource-title").val(resTitle);
	$("#resource-abstract").val(resAbstr);
	$("#resource-keywords").val(resKwds);

	update_chart(lat, lon, begin_date, end_date);


});
