from django.db import models

from src.modules.cities_expansion.models import Group

class GroupCoords(models.Model):
    group = models.OneToOneField(Group, models.CASCADE)
    upper_left_latitude = models.FloatField()
    upper_left_longitude = models.FloatField()
    down_right_latitude = models.FloatField()
    down_right_longitude = models.FloatField()

    def __str__(self):
        def decimal_to_dms(coord, is_latitude):
            degrees = int(coord)
            remaining = abs(coord - degrees) * 60
            minutes = int(remaining)
            seconds = round((remaining - minutes) * 60)
            
            direction = ''
            if is_latitude:
                direction = 'N' if coord >= 0 else 'S'
            else:
                direction = 'E' if coord >= 0 else 'W'
            
            return f"{abs(degrees)}°{minutes}'{seconds}\"{direction}"

        upper_left_lat = decimal_to_dms(self.upper_left_latitude, True)
        upper_left_lon = decimal_to_dms(self.upper_left_longitude, False)
        down_right_lat = decimal_to_dms(self.down_right_latitude, True)
        down_right_lon = decimal_to_dms(self.down_right_longitude, False)

        return f"{upper_left_lat}, {upper_left_lon} → {down_right_lat}, {down_right_lon}"
