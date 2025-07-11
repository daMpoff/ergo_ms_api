import csv

def hextorgb(h: str):
    r = h[1:3]
    g = h[3:5]
    b = h[5:7]

    return tuple(map(lambda n: int(n, 16), [r,g,b]))

color_to_name: dict[tuple[int, int, int], str] = {}

path_to_csv = 'src/modules/cities_expansion/geoanalyzer/csv/color_codes.csv'

with open(path_to_csv) as file:
    next(file)
    reader = csv.reader(file, )
    for r in reader:
        color_to_name[hextorgb(r[1])] = r[0]

name_to_color: dict[str, tuple[int, int, int]] = {v: k for k, v in color_to_name.items()}