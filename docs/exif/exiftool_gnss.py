import os
import glob
import exiftool


# Start subprocess with exiftool
et = exiftool.ExifTool()
et.start()


# Returns dictionary with relevant EXIF tags
def get_metadata(fn, et=et):
    tags = ['EXIF:GPSLatitude', 'EXIF:GPSLongitude', 'EXIF:GPSLatitudeRef', 'EXIF:GPSLongitudeRef', \
            'EXIF:GPSAltitude', 'EXIF:GPSAltitudeRef', 'XMP:AbsoluteAltitude', 'XMP:RelativeAltitude']
    metadata = et.get_tags(tags, fn)
    # Convert to positive east longitude
    if metadata['EXIF:GPSLongitudeRef'] == "W":
        metadata['EXIF:GPSLongitude'] *= -1
    if metadata['EXIF:GPSLatitudeRef'] == "S":
        metadata['EXIF:GPSLatitude'] *= -1
    print(metadata)
    return metadata


def update_gps_altitude(fn, home_elev):

    metadata = get_metadata(fn)
    relAlt = float(metadata['XMP:RelativeAltitude'])
    home_elev = float(home_elev)
    print(relAlt)
    adjAlt = home_elev + relAlt

    # Update metadata
    etArg = ["-GPSAltitude=" + str(adjAlt), ]
    etArg.append("-AbsoluteAltitude=" + str(adjAlt))

    # Set altitude reference
    # 1 is 'Below Sea Level'; 0 is 'Above Sea Level'
    if adjAlt >= 0.0:
        etArg.append("-GPSAltitudeRef=0")
    else:
        etArg.append("-GPSAltitudeRef=1")

    # Since we're modifying our own copy of originl, we don't need the default exiftool _original copy
    etArg.append("-overwrite_original")
    print(etArg)

    # pyexiftool execution requires binary string
    etArg_b = [str.encode(a) for a in etArg]
    f_b = str.encode(fn)
    etArg_b.append(f_b)
    et.execute(*etArg_b)

    # Check updated
    metadata = get_metadata(fn)


def main(img_dir, home_elev):
    image_dir = img_dir
    home_elev = str(home_elev)

    fn_list_orig = sorted(glob.glob(os.path.join(image_dir, '*.JPG')))

    for fn in fn_list_orig:
        update_gps_altitude(fn, home_elev)

    et.terminate()

#####################
###### Altitude Adjust
####################

#Required input is the directory of the images to be adjusted
#NOTE: The images are updated and saved in the image, not in a copy

img_dir = '/Volumes/MasterLiang/Testing script/'
home_elev = 0

if __name__ == "__main__":
    main(img_dir, home_elev)