#!/usr/bin/python3
"""
MIT License

Copyright (C) 2023 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
"""

"""
This file generates the plugin.json file containing all plugins in this repo
then generates the sha2 file for the plugin.json
<file.py>    -generates the plugin.json and sha2 files
<file.py> -u or <file.py> --update_repo   -updates the repo area with zip files from GitHub
"""

import argparse
import datetime
import glob
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib
import urllib.error
import urllib.request
import zipfile
from collections import OrderedDict


BUILDPATH  = os.path.abspath(os.path.dirname(sys.argv[0]))
TMPPATH    = os.path.join(BUILDPATH,'tmp','')
ROOTPATH   = os.path.join(BUILDPATH,'..','')
ZIPPATH    = os.path.join(BUILDPATH,'../repo','')
GIT_JSON_API     = 'https://api.github.com/repos/cabernetwork/{}/releases'

class Generator:
    """
    Generates a new plugin.json with its sha2 file for all
    plugins in this repository.  The latest version for
    each plugin is included. Assumes zip file format is
    <folder name>-x.y.z.zip
    """
    def __init__(self):
        self.search_version = re.compile('(([^, -]+)-(\d+)\.(\d+)\.(\d+)\.zip)')

    def generate(self):
        """
        Generates the plugin.json and plugin.json.sha2 files in the
        top folder based on the zip files in the repo folder
        """
        self.generate_plugin_file()
        Generator.generate_sha2_file()
        print('Finished updating main plugin: json and sha2 files')

    def generate_plugin_file(self):
        plugins = os.listdir(ZIPPATH)
        # final addons text
        json_file = b'{"plugins": ['
        filler = b''

        for plugin in plugins:
            _path = os.path.join(plugin, 'plugin.json')
            plugin_path = os.path.join(ZIPPATH, plugin)
            if not os.path.isdir(plugin_path):
                print('Ignoring {}'.format(plugin))
                continue

            filelist = [os.path.basename(x) for x in
                        glob.glob(os.path.join(plugin_path, plugin+'*.zip'))]
            if not filelist:
                print('No zip files found in plugin folder, moving on {}'.format(plugin))
                continue
            m = re.findall(self.search_version, ' '.join(filelist))
            versions = OrderedDict()
            for filename, plugin_name, d1, d2, d3 in m:
                v_int = (((int(d1)*100)+int(d2))*100)+int(d3)
                versions[v_int] = filename
            versions = sorted(versions.items(), reverse=True)
            if not versions:
                print('No properly formatted zip filenames found {}'.format(plugin))
                continue
            print('###### Processing {}'.format(plugin))
            ver_to_extract = next(iter(versions))
            file_to_extract = None
            try:
                file_to_extract = pathlib.Path(plugin_path).joinpath(ver_to_extract[1])
                with zipfile.ZipFile(file_to_extract, 'r') as z:
                    file_list = z.namelist()
                    res = [i for i in file_list if "plugin.json" in i]
                    if len(res) == 1:
                        file_path = res[0]
                        source = z.open(file_path)
                        json_file += filler+source.read()
                        filler = b','
                    else:
                        print('WARNING: Zip file contains more than one plugin.json file {}'.format(file_to_extract))
            except (zipfile.BadZipFile, FileNotFoundError, KeyError) as ex:
                print('Unable to unzip file to obtain plugin.json file {}\n{}'.format(file_to_extract, ex))
                raise
        json_file = json_file.strip() + b']}'
        Generator.save_file( json_file, file=os.path.join(ROOTPATH, 'plugin.json'))

    @staticmethod
    def parse_date_str(time_str):
        """
        format: YYYY-MM-DDTHH:mm:ssZ
        """
        d = datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
        return d

    @staticmethod
    def check_plugin_repo(plugin):
        """
        Uses GitHUB APi to obtain metadata for the plugin
        """
        githubapi = Generator.get_json_data(GIT_JSON_API.format(plugin))
        if not githubapi:
            print('GitHub says this is not a repository, ignoring {}'.format(plugin))
            return
        sorted_list = sorted(githubapi, key = lambda x: Generator.parse_date_str(x['created_at']), reverse=True)
        if not sorted_list:
            print('2 GitHub says this is not a repository, ignoring {}'.format(plugin))
            return

        latest = sorted_list[0]
        # check to see if file exists in the plugin folder
        zip_file = os.path.join(ZIPPATH, plugin, plugin + '-' + latest['tag_name'] + '.zip')
        if os.path.isfile(zip_file):
            return
        Generator.get_file(latest['zipball_url'], zip_file)

    def update_repo(self):
        """
        goes through the plugins in the repo area and determines if the
        latest GitHub released zip source is in the repo folder
        """
        plugins = os.listdir(ZIPPATH)

        for plugin in plugins:
            plugin_path = os.path.join(ZIPPATH, plugin)
            # filter out things that are not repos
            if not os.path.isdir(plugin_path):
                continue
            filelist = [os.path.basename(x) for x in
                        glob.glob(os.path.join(plugin_path, plugin+'*.zip'))]
            if not filelist:
                continue
            # found a folder with zip files in it, will process it
            print('Checking github for plugin {}'.format(plugin))
            self.check_plugin_repo(plugin)

    @staticmethod
    def get_file(_uri, filepath):
        req = urllib.request.Request(_uri)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            with open(filepath, mode="wb") as f:
                f.write(resp.read())
        print('New File downloaded:', filepath)
        return True

    @staticmethod
    def get_json_data(_uri):
        header = {'Content-Type': 'application/json'}
        try:
            req = urllib.request.Request(_uri, headers=header)
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                x = json.load(resp)
            return x
        except urllib.error.HTTPError:
            return

    @staticmethod
    def generate_sha2_file():
        m = hashlib.sha512( open( os.path.join(ROOTPATH, 'plugin.json'), 'rb').read()).hexdigest()
        try:
            Generator.save_file( m.encode('UTF-8'), file='plugin.json.sha2')
        except Exception as ex:
            print('An error occurred creating plugin.json.sha2 file\n{}'.format(ex))
            raise

    @staticmethod
    def save_file(data, file):
        try:
            open(os.path.join(ROOTPATH,file), 'wb').write(data)
        except Exception as e:
            print("An error occurred saving %s file\n%s" % (file, e))
            raise


def get_args():
    parser = argparse.ArgumentParser(description='Fetch online streams', epilog='')
    parser.add_argument('-u', '--update_repo', dest='update_repo',
                        action='store_true',
                        help='updates repo folder with zip files')
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    g = Generator()
    if args.update_repo:
        print('Request to update zip files in repo area')
        g.update_repo()
    else:
        print('Request to update plugin.json main file')
        g.generate()
