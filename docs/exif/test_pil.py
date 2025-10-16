import os
from PIL import Image, ExifTags, IptcImagePlugin
# image_path = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\exif\\DSC05742.JPG"
image_path = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\exif\\IMG_0207_4.tif"
with Image.open(image_path) as im:
    print("FileName =", im.filename)
    print("FileSize =", os.path.getsize(image_path))
    print("FileType =", im.format)
    print("FileTypeExtension =", os.path.splitext(im.filename)[1][1:].upper())
    print("MIMEType =", im.get_format_mimetype())

    description = im.getxmp()["xmpmeta"]["RDF"]["Description"]
    print("| City =", description["City"])
    print("| State =", description["State"])
    print("| Country =", description["Country"])
    print("| Headline =", description["Headline"])
    print("| CountryCode =", description["CountryCode"])
    print("| Location =", description["Location"])
    print("| DocumentID =", description["DocumentID"])
    print("| Creator =", description["creator"]["Seq"]["li"])
    print("| Description =", description["description"]["Alt"]["li"]["text"])
    print("| Subject =", description["subject"]["Bag"]["li"])
    print("|| ObjectName =", description["title"]["Alt"]["li"]["text"])
    print("|| Keywords =", IptcImagePlugin.getiptcinfo(im)[(2, 25)])