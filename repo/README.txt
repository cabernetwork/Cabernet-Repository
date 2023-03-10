Structure is based on the plugin.json file where:
folder name is the id from plugin.json
files in folder are zip files where the filename is
<id>-x.y.z.zip

The zip file contains at some level the folder name = <id>
which is where the plugin starts.  It can either be at the 
top level or be in a single folder structure.  Only one 
folder is checked at each level.  If a folder with the name
<id> is not found, the unzipping of the zip file is aborted.
