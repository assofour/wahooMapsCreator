#!/usr/bin/python

# import official python packages
import glob
import os
import os.path
import subprocess
import sys
import platform

# import custom python packages
from os import sys, path

from common_resources import downloader
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from common_resources import file_directory_functions
from common_resources import constants
from common_resources import constants_functions

from common_resources.file_directory_functions import FileDir
from common_resources.downloader import Downloader


class OsmMaps:
    "This is a OSM data class"


    def __init__(self, Max_Days_Old, Force_Download,
     Force_Processing, workers, threads, Save_Cruiser):
        #self.max_days_old = Max_Days_Old
        self.force_processing = Force_Processing
        self.workers = workers
        self.threads = threads
        self.save_cruiser = Save_Cruiser
        self.tiles = []
        self.border_countries = {}

        self.country_name = ''

        self.o_downloader = Downloader(Max_Days_Old, Force_Download)


    def read_process_input(self, input_file):
        self.tiles = file_directory_functions.read_json_file(input_file,
         constants_functions.get_region_of_country(input_file))

        self.country_name = os.path.split(input_file)[1][:-5]

        force_processing = self.o_downloader.download_if_needed(self.tiles)
        if force_processing == 1:
            self.force_processing = force_processing

        self.border_countries = self.o_downloader.border_countries


    def filter_tags_from_country_osm_pbf_files(self):

        print('\n# Filter tags from country osm.pbf files')

        # Windows
        if platform.system() == "Windows":
            for key, val in self.border_countries.items():
            # print(key, val)
                out_file = os.path.join(file_directory_functions.OUTPUT_DIR,
                 f'filtered-{key}.osm.pbf')
                out_file_o5m = os.path.join(file_directory_functions.OUTPUT_DIR,
                 f'outFile-{key}.o5m')
                out_file_o5m_filtered = os.path.join(file_directory_functions.OUTPUT_DIR,
                 f'outFileFiltered-{key}.o5m')

                if not os.path.isfile(out_file) or self.force_processing == 1:
                    print(f'\n+ Converting map of {key} to o5m format')
                    cmd = ['osmconvert']
                    cmd.extend(['-v', '--hash-memory=2500', '--complete-ways', '--complete-multipolygons', '--complete-boundaries', '--drop-author', '--drop-version'])
                    cmd.append(val['map_file'])
                    cmd.append('-o='+out_file_o5m)
                    # print(cmd)
                    result = subprocess.run(cmd)
                    if result.returncode != 0:
                        print(f'Error in OSMConvert with country: {key}')
                        sys.exit()

                    print(f'\n# Filtering unwanted map objects out of map of {key}')
                    cmd = ['osmfilter']
                    cmd.append(out_file_o5m)
                    cmd.append('--keep="' + constants.FILTERED_TAGS_WIN + '"')
                    cmd.append('-o=' + out_file_o5m_filtered)
                    # print(cmd)
                    result = subprocess.run(cmd)
                    if result.returncode != 0:
                        print(f'Error in OSMFilter with country: {key}')
                        sys.exit()

                    print(f'\n# Converting map of {key} back to osm.pbf format')
                    cmd = ['osmconvert', '-v', '--hash-memory=2500', out_file_o5m_filtered]
                    cmd.append('-o='+out_file)
                    # print(cmd)
                    result = subprocess.run(cmd)
                    if result.returncode != 0:
                        print(f'Error in OSMConvert with country: {key}')
                        sys.exit()

                    os.remove(out_file_o5m)
                    os.remove(out_file_o5m_filtered)

                self.border_countries[key]['filtered_file'] = out_file

        # Non-Windows
        else:
            for key, val  in self.border_countries.items():
                ## print(key, val)
                out_file = os.path.join(file_directory_functions.OUTPUT_DIR,
                 f'filtered-{key}.osm.pbf')
                ## print(outFile)
                if not os.path.isfile(out_file):
                    print(f'+ Create filtered country file for {key}')

                    cmd = ['osmium', 'tags-filter']
                    cmd.append(val['map_file'])
                    cmd.extend(constants.filtered_tags)
                    cmd.extend(['-o', out_file])
                    # print(cmd)
                    subprocess.run(cmd)
                self.border_countries[key]['filtered_file'] = out_file

        # logging
        print('# Filter tags from country osm.pbf files: OK')


    def generate_land(self):
        print('\n# Generate land')

        tile_count = 1
        for tile in self.tiles:
            land_file = os.path.join(file_directory_functions.OUTPUT_DIR,
             f'{tile["x"]}', f'{tile["y"]}', 'land.shp')
            out_file = os.path.join(file_directory_functions.OUTPUT_DIR,
             f'{tile["x"]}', f'{tile["y"]}', 'land')

            if not os.path.isfile(land_file) or self.force_processing == 1:
                print(f'+ Generate land {tile_count} of {len(self.tiles)} for Coordinates: {tile["x"]} {tile["y"]}')
                cmd = ['ogr2ogr', '-overwrite', '-skipfailures']
                cmd.extend(['-spat', f'{tile["left"]-0.1:.6f}',
                            f'{tile["bottom"]-0.1:.6f}',
                            f'{tile["right"]+0.1:.6f}',
                            f'{tile["top"]+0.1:.6f}'])
                cmd.append(land_file)
                cmd.append(file_directory_functions.LAND_POLYGONS_PATH)
                #print(cmd)
                subprocess.run(cmd)

            if not os.path.isfile(out_file+'1.osm') or self.force_processing == 1:
                # Windows
                if platform.system() == "Windows":
                    cmd = ['python', os.path.join(file_directory_functions.COMMON_DIR,
                     'shape2osm.py'), '-l', out_file, land_file]
                # Non-Windows
                else:
                    cmd = ['python3', os.path.join(file_directory_functions.COMMON_DIR,
                     'shape2osm.py'), '-l', out_file, land_file]
                #print(cmd)
                subprocess.run(cmd)
            tile_count += 1

        # logging
        print('# Generate land: OK')


    def generate_sea(self):
        print('\n# Generate sea')

        tile_count = 1
        for tile in self.tiles:
            out_file = os.path.join(file_directory_functions.OUTPUT_DIR,
             f'{tile["x"]}', f'{tile["y"]}', 'sea.osm')
            if not os.path.isfile(out_file) or self.force_processing == 1:
                print(f'+ Generate sea {tile_count} of {len(self.tiles)} for Coordinates: {tile["x"]} {tile["y"]}')
                with open(os.path.join(file_directory_functions.COMMON_DIR, 'sea.osm')) as sea_file:
                    sea_data = sea_file.read()

                    sea_data = sea_data.replace('$LEFT', f'{tile["left"]-0.1:.6f}')
                    sea_data = sea_data.replace('$BOTTOM',f'{tile["bottom"]-0.1:.6f}')
                    sea_data = sea_data.replace('$RIGHT',f'{tile["right"]+0.1:.6f}')
                    sea_data = sea_data.replace('$TOP',f'{tile["top"]+0.1:.6f}')

                    with open(out_file, 'w') as output_file:
                        output_file.write(sea_data)
            tile_count += 1

        # logging
        print('# Generate sea: OK')


    def split_filtered_country_files_to_tiles(self):
        print('\n# Split filtered country files to tiles')
        tile_count = 1
        for tile in self.tiles:

            for country in tile['countries']:
                print(f'+ Split filtered country {country}')
                print(f'+ Splitting tile {tile_count} of {len(self.tiles)} for Coordinates: {tile["x"]},{tile["y"]} from map of {country}')
                out_file = os.path.join(file_directory_functions.OUTPUT_DIR,
                 f'{tile["x"]}', f'{tile["y"]}', f'split-{country}.osm.pbf')
                if not os.path.isfile(out_file) or self.force_processing == 1:
                    # Windows
                    if platform.system() == "Windows":
                        #cmd = ['.\\osmosis\\bin\\osmosis.bat', '--rbf',border_countries[c]['filtered_file'],'workers='+workers, '--buffer', 'bufferCapacity=12000', '--bounding-box', 'completeWays=yes', 'completeRelations=yes']
                        #cmd.extend(['left='+f'{tile["left"]}', 'bottom='+f'{tile["bottom"]}', 'right='+f'{tile["right"]}', 'top='+f'{tile["top"]}', '--buffer', 'bufferCapacity=12000', '--wb'])
                        #cmd.append('file='+outFile)
                        #cmd.append('omitmetadata=true')
                        cmd = ['osmconvert', '-v', '--hash-memory=2500']
                        cmd.append('-b='+f'{tile["left"]}' + ',' + f'{tile["bottom"]}' + ',' + f'{tile["right"]}' + ',' + f'{tile["top"]}')
                        cmd.extend(['--complete-ways', '--complete-multipolygons', '--complete-boundaries'])
                        cmd.append(self.border_countries[country]['filtered_file'])
                        cmd.append('-o='+out_file)

                        # print(cmd)
                        result = subprocess.run(cmd)
                        if result.returncode != 0:
                            print(f'Error in Osmosis with country: {country}')
                            sys.exit()
                        # print(border_countries[c]['filtered_file'])

                    # Non-Windows
                    else:
                        cmd = ['osmium', 'extract']
                        cmd.extend(['-b',f'{tile["left"]},{tile["bottom"]},{tile["right"]},{tile["top"]}'])
                        cmd.append(self.border_countries[country]['filtered_file'])
                        cmd.extend(['-s', 'smart'])
                        cmd.extend(['-o', out_file])
                        # print(cmd)
                        subprocess.run(cmd)
                        print(self.border_countries[country]['filtered_file'])

            tile_count += 1

            # logging
            print('# Split filtered country files to tiles: OK')


    def merge_splitted_tiles_with_land_and_sea(self):
        print('\n# Merge splitted tiles with land an sea')
        tile_count = 1
        for tile in self.tiles:
            print(f'+ Merging tiles for tile {tile_count} of {len(self.tiles)} for Coordinates: {tile["x"]},{tile["y"]}')
            out_file = os.path.join(file_directory_functions.OUTPUT_DIR,
             f'{tile["x"]}', f'{tile["y"]}', 'merged.osm.pbf')
            if not os.path.isfile(out_file) or self.force_processing == 1:
                # Windows
                if platform.system() == "Windows":
                    cmd = [os.path.join (file_directory_functions.COMMON_DIR,
                     'Osmosis', 'bin', 'osmosis.bat')]
                    loop=0
                    for country in tile['countries']:
                        cmd.append('--rbf')
                        cmd.append(os.path.join(file_directory_functions.OUTPUT_DIR,
                         f'{tile["x"]}', f'{tile["y"]}', f'split-{country}.osm.pbf'))
                        cmd.append('workers='+ self.workers)
                        if loop > 0:
                            cmd.append('--merge')
                        loop+=1
                    land_files = glob.glob(os.path.join(file_directory_functions.OUTPUT_DIR,
                     f'{tile["x"]}', f'{tile["y"]}', 'land*.osm'))
                    for land in land_files:
                        cmd.extend(['--rx', 'file='+os.path.join(file_directory_functions.OUTPUT_DIR,
                         f'{tile["x"]}', f'{tile["y"]}', f'{land}'), '--s', '--m'])
                    cmd.extend(['--rx', 'file='+os.path.join(file_directory_functions.OUTPUT_DIR,
                     f'{tile["x"]}', f'{tile["y"]}', 'sea.osm'), '--s', '--m'])
                    cmd.extend(['--tag-transform', 'file=' + os.path.join (file_directory_functions.COMMON_DIR, 'tunnel-transform.xml'), '--wb', out_file, 'omitmetadata=true'])

                    #print(cmd)
                    result = subprocess.run(cmd)
                    if result.returncode != 0:
                        print(f'Error in Osmosis with country: {country}')
                        sys.exit()
                # Non-Windows
                else:
                    cmd = ['osmium', 'merge', '--overwrite']
                    for country in tile['countries']:
                        cmd.append(os.path.join(file_directory_functions.OUTPUT_DIR,
                         f'{tile["x"]}', f'{tile["y"]}', f'split-{country}.osm.pbf'))

                    cmd.append(os.path.join(file_directory_functions.OUTPUT_DIR,
                     f'{tile["x"]}', f'{tile["y"]}', 'land1.osm'))
                    cmd.append(os.path.join(file_directory_functions.OUTPUT_DIR,
                     f'{tile["x"]}', f'{tile["y"]}', 'sea.osm'))
                    cmd.extend(['-o', out_file])

                    #print(cmd)
                    subprocess.run(cmd)
            tile_count += 1

        # logging
        print('# Merge splitted tiles with land an sea: OK')


    def create_map_files(self):
        print('\n# Creating .map files')
        tile_count = 1
        for tile in self.tiles:
            print(f'+ Creating map file for tile {tile_count} of {len(self.tiles)} for Coordinates: {tile["x"]}, {tile["y"]}')
            out_file = os.path.join(file_directory_functions.OUTPUT_DIR,
             f'{tile["x"]}', f'{tile["y"]}.map')
            if not os.path.isfile(out_file+'.lzma') or self.force_processing == 1:
                merged_file = os.path.join(file_directory_functions.OUTPUT_DIR,
                 f'{tile["x"]}', f'{tile["y"]}', 'merged.osm.pbf')

                # Windows
                if platform.system() == "Windows":
                    cmd = [os.path.join (file_directory_functions.COMMON_DIR, 'Osmosis', 'bin', 'osmosis.bat'), '--rbf', merged_file, 'workers=' + self.workers, '--mw', 'file='+out_file]
                # Non-Windows
                else:
                    cmd = ['osmosis', '--rb', merged_file, '--mw', 'file='+out_file]

                cmd.append(f'bbox={tile["bottom"]:.6f},{tile["left"]:.6f},{tile["top"]:.6f},{tile["right"]:.6f}')
                cmd.append('zoom-interval-conf=10,0,17')
                cmd.append('threads='+ self.threads)
                # should work on macOS and Windows
                cmd.append(f'tag-conf-file={os.path.join(file_directory_functions.COMMON_DIR, "tag-wahoo.xml")}')
                # print(cmd)
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    print(f'Error in Osmosis with country: c // tile: {tile["x"]}, {tile["y"]}')
                    sys.exit()

                # Windows
                if platform.system() == "Windows":
                    cmd = ['lzma', 'e', out_file, out_file+'.lzma', f'-mt{self.threads}', '-d27', '-fb273', '-eos']
                # Non-Windows
                else:
                    cmd = ['lzma', out_file]

                    # --keep: do not delete source file
                    if self.save_cruiser:
                        cmd.append('--keep')

                # print(cmd)
                subprocess.run(cmd)
            tile_count += 1

        # logging
        print('# Creating .map files: OK')


    def zip_map_files(self):
        print('\n# Zip .map.lzma files')
        print(f'+ Country: {self.country_name}')

        # Make Wahoo zip file
        # Windows
        if platform.system() == "Windows":
            cmd = ['7za', 'a', '-tzip', '-m0=lzma', '-mx9', '-mfb=273', '-md=1536m', self.country_name + '.zip']
            #cmd = ['7za', 'a', '-tzip', '-m0=lzma', countryName[1] + '.zip']
        # Non-Windows
        else:
            cmd = ['zip', '-r', self.country_name + '.zip']

        for tile in self.tiles:
            cmd.append(os.path.join(f'{tile["x"]}', f'{tile["y"]}.map.lzma'))
        #print(cmd)
        subprocess.run(cmd, cwd=file_directory_functions.OUTPUT_DIR)

        # logging
        print('# Zip .map.lzma files: OK \n')


    def make_cruiser_files(self):
        # Make Cruiser map files zip file
        if self.save_cruiser == 1:
            # Windows
            if platform.system() == "Windows":
                cmd = ['7za', 'a', '-tzip', '-m0=lzma', self.country_name + '-maps.zip']
            # Non-Windows
            else:
                cmd = ['zip', '-r', self.country_name + '-maps.zip']

            for tile in self.tiles:
                cmd.append(os.path.join(f'{tile["x"]}', f'{tile["y"]}.map'))
            #print(cmd)
            subprocess.run(cmd, cwd=file_directory_functions.OUTPUT_DIR)
