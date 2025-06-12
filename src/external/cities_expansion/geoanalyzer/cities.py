import numpy as np
import pandas as pd

class CityObject:
    """
    Представляет собой объект в городе. Свойства:
        x_pos_center: Позиция x (пикселей) относительно левого края города  
        y_pos_center: Позиция y (пикселей) относительно верхнего края города
        square: Площадь объекта (количество точек)
        points - точки x,y (массив) где находится объект
        type: тип объекта (напр. зелёная зона или жилой дом)
    """
    x_pos_center: int = None
    y_pos_center: int = None
    square: int = None
    points: np.ndarray = None
    type: str = None

class City:
    """
    Представляет собой город. Свойства:
        objects: Список объектов CityObject
        upper_left: Координаты (ширина, долгота) левого верхнего угла города
        down_right: Координаты (ширина, долгота) правого нижнего угла города
        width: Ширина города (пиксели)
        scale_x: Масштабирование города по горизонтали (метры/пиксели)
        scale_y: Масштабирование города по вертикали (метры/пиксели)
    """
    objects: list[CityObject] = None
    upper_left: tuple[float, float] = None
    down_right: tuple[float, float] = None
    width: int = None
    height: int = None
    x_scale: float = None
    y_scale: float = None

    def as_dataframe(self):
        data = []
        for obj in self.objects:
            row = {
                'x_pos': obj.x_pos_center,
                'y_pos': obj.y_pos_center,
                'square': obj.square,
                'type': obj.type,
                'points': obj.points
            }

            if self.width is not None and self.height is not None:
                # Нормализуем позицию (0-1)
                x_norm = obj.x_pos_center / self.width
                y_norm = obj.y_pos_center / self.height

                # Вычисляем ширину и долготу объекта от его позиции
                row['latitude'] = self.upper_left[0] - y_norm * (self.upper_left[0] - self.down_right[0])
                row['longitude'] = self.upper_left[1] + x_norm * (self.down_right[1] - self.upper_left[1])
            
            if self.x_scale is not None and self.y_scale is not None:
                row['area_m2'] = obj.square * ((self.x_scale + self.y_scale) / 2)
            
            data.append(row)
        
        df = pd.DataFrame(data)
        return df
    
    def point_area(self):
        """
        Возвращает площадь одного пикселя в метрах квадратных
        """
        if self.x_scale is not None and self.y_scale is not None:
            return self.x_scale * self.y_scale
    
    def get_center_coordinates(self):
        latitude = (self.upper_left[0] + self.down_right[0]) / 2
        longitude = (self.upper_left[1] + self.down_right[1]) / 2
        return (latitude, longitude)
