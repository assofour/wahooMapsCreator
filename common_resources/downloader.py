#!/usr/bin/python

# import official python packages
import glob
import os
import os.path
import sys
import time

# import custom python packages
import requests
from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from common_resources import file_directory_functions
from common_resources import constants_functions

class Downloader:
    "This is the class to check and download maps / artifacts"

    def __init__(self, Max_Days_Old, Force_Download):
        self.max_days_old = Max_Days_Old
        self.force_download = Force_Download
        self.force_processing = False
        self.tiles_from_json = []
        self.border_countries = {}


    def download_if_needed(self, tiles_from_json):
        self.tiles_from_json = tiles_from_json

        if self.check_poligons_file() is True or self.force_download is True:
            self.download_land_poligons_file()
            self.force_processing = True

         # logging
        print('# check land_polygons.shp file: OK')


        if self.check_osm_pbf_file() is True or self.force_download is True:
            self.download_osm_pbf_file()
            self.force_processing = True

        # logging
        print('# Check countries .osm.pbf files: OK')

        if self.force_processing is True:
            return 1


    def check_poligons_file(self):
        need_to_download = False
        print('\n# check land_polygons.shp file')
        # Check for expired land polygons file and delete it
        now = time.time()
        to_old_timestamp = now - 60 * 60 * 24 * self.max_days_old
        try:
            file_creation_timestamp = os.path.getctime(file_directory_functions.LAND_POLYGONS_PATH)
            if file_creation_timestamp < to_old_timestamp:
                print ('# Deleting old land polygons file')
                os.remove(file_directory_functions.LAND_POLYGONS_PATH)
                need_to_download = True

        except:
            need_to_download = True

        # if landpoligony file does not exists --> download
        if not os.path.exists(file_directory_functions.LAND_POLYGONS_PATH) or not os.path.isfile(file_directory_functions.LAND_POLYGONS_PATH):
            need_to_download = True
            # logging
            print('# land_polygons.shp file needs to be downloaded')

            return need_to_download


    def download_land_poligons_file(self):
        print('# Downloading land polygons file')
        url = 'https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip'
        request_land_polygons = requests.get(url, allow_redirects=True, stream = True)
        if request_land_polygons.status_code != 200:
            print('failed to find or download land polygons file')
            sys.exit()
        land_poligons_dl=open(os.path.join (file_directory_functions.COMMON_DIR,
            'land-polygons-split-4326.zip'), 'wb')
        for chunk in request_land_polygons.iter_content(chunk_size=1024*100):
            land_poligons_dl.write(chunk)
        land_poligons_dl.close()

        # unpack it - should work on macOS and Windows
        file_directory_functions.unzip(os.path.join (file_directory_functions.COMMON_DIR,
            'land-polygons-split-4326.zip'), file_directory_functions.COMMON_DIR)
        os.remove(os.path.join (file_directory_functions.COMMON_DIR,
            'land-polygons-split-4326.zip'))

        # Check if land polygons file exists
        if not os.path.isfile(file_directory_functions.LAND_POLYGONS_PATH):
            print(f'! failed to find {file_directory_functions.LAND_POLYGONS_PATH}')
            sys.exit()


    def check_osm_pbf_file(self):
        need_to_download = False
        print('\n# check countries .osm.pbf files')
        # Build list of countries needed
        border_countries = {}
        for tile in self.tiles_from_json:
            for country in tile['countries']:
                if country not in border_countries:
                    border_countries[country] = {'map_file':country}

        # logging
        print(f'+ Border countries of json file: {len(border_countries)}')
        for country in border_countries:
            print(f'+ Border country: {country}')

        # Check for expired maps and delete them
        print(f'+ Checking for old maps and remove them and for mapfile for  {country}')

        now = time.time()
        to_old_timestamp = now - 60 * 60 * 24 * self.max_days_old
        for country in border_countries:
            # print(f'+ mapfile for {c}')

            # check for already existing .osm.pbf file
            # ToDo: comment
            map_files = glob.glob(f'{file_directory_functions.MAPS_DIR}/{country}*.osm.pbf')
            if len(map_files) != 1:
                map_files = glob.glob(f'{file_directory_functions.MAPS_DIR}/**/{country}*.osm.pbf')

            # ToDo: comment
            if len(map_files) == 1 and os.path.isfile(map_files[0]):
                file_creation_timestamp = os.path.getctime(map_files[0])
                if file_creation_timestamp < to_old_timestamp or self.force_download == 1:
                    print(f'+ mapfile for {country}: deleted')
                    os.remove(map_files[0])
                    need_to_download = True
                else:
                    border_countries[country] = {'map_file':map_files[0]}
                    print(f'+ mapfile for {country}: up-to-date')

            if len(border_countries[country]) != 1 or not os.path.isfile(border_countries[country]['map_file']):
                # if there exists no file or it is no file --> download
                need_to_download = True

        self.border_countries = border_countries

        return need_to_download


    def download_osm_pbf_file(self):

        file_directory_functions.create_empty_directories(self.tiles_from_json)

        for country in self.border_countries:
            map_files = self.download_map(country)
            self.border_countries[country] = {'map_file':map_files[0]}


    def download_map(self, country):
        print(f'+ Trying to download missing map of {country}.')

        # get Geofabrik region of country
        translated_country = constants_functions.translate_country_input_to_geofabrik(country)
        region = constants_functions.get_geofabrik_region_of_country(f'{country}')

        if region != 'no':
            url = 'https://download.geofabrik.de/'+ region + '/' + translated_country + '-latest.osm.pbf'
        else:
            url = 'https://download.geofabrik.de/' + translated_country + '-latest.osm.pbf'

        request_geofabrik = requests.get(url, allow_redirects=True, stream = True)
        if request_geofabrik.status_code != 200:
            print(f'! failed to find or download country: {country}')
            sys.exit()
        download=open(os.path.join (file_directory_functions.MAPS_DIR, f'{country}' + '-latest.osm.pbf'), 'wb')
        for chunk in request_geofabrik.iter_content(chunk_size=1024*100):
            download.write(chunk)
        download.close()
        map_files = [os.path.join (file_directory_functions.MAPS_DIR, f'{country}' + '-latest.osm.pbf')]
        print(f'+ Map of {country} downloaded.')

        return map_files
