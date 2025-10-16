# image_path = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\exif\\DSC05742.JPG"
# image_path = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\exif\\IMG_0207_4.tif"
# import os
import exiftool
exiftool_file_path = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\external_tools\\exiftool-13.36_64\\exiftool.exe"
# os.environ['exiftoolpath'] = '"E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\external_tools\\exiftool-13.36_64'
files = ["E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\exif\\DSC05742.JPG",
         "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\exif\\IMG_0207_4.tif"]
# exiftoolpath_value = os.getenv("exiftoolpath")
# with exiftool.ExifToolHelper() as et:
metadata_by_file_path = {}
try:
    # with exiftool.ExifTool(executable=exiftool_file_path) as et:
    # with exiftool.ExifToolHelper(executable=os.environ.get('exiftoolpath')) as et:
    with exiftool.ExifToolHelper(executable=exiftool_file_path) as et:
        for file in files:
            metadata = et.get_metadata(file)
            metadata_by_file_path[file] = metadata
        # metadata = et.get_metadata_batch(files)
        # for d in metadata:
        #     print("{:20.20} {:20.20}".format(d["SourceFile"],
        #                                      d["EXIF:DateTimeOriginal"]))
except Exception as e:
    str_error = 'EXIFTOOL Error: ' + e.args[0]
    print(str_error)
yo = 1