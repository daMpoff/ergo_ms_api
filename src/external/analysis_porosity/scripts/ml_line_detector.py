import numpy as np
import cv2

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from skimage.measure import regionprops, label
from skimage.morphology import disk, dilation
from scipy.spatial.distance import pdist

import joblib
import os


class MLLineDetector:
    """
    Детектор линий на основе машинного обучения с использованием признаков формы
    для отличия пор от линейных дефектов
    """
    
    def __init__(self, model_path=None):
        """
        Инициализация детектора
        
        Args:
            model_path (str, optional): Путь к предобученной модели
        """
        self.model = None
        self.feature_names = [
            'area', 'perimeter', 'eccentricity', 'aspect_ratio', 
            'solidity', 'extent', 'orientation', 'major_axis_length',
            'minor_axis_length', 'equivalent_diameter', 'convex_area',
            'euler_number', 'filled_area', 'hu_moments_0', 'hu_moments_1',
            'hu_moments_2', 'bbox_area_ratio', 'compactness', 'elongation',
            'perimeter_area_ratio', 'width_height_ratio', 'convexity'
        ]
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def extract_shape_features(self, binary_image):
        """
        Извлекает признаки формы из бинарного изображения
        
        Args:
            binary_image (numpy.ndarray): Бинарное изображение
            
        Returns:
            list: Список словарей с признаками для каждого объекта
        """
        labeled_img = label(binary_image)
        regions = regionprops(labeled_img)
        
        features_list = []
        
        for region in regions:
            if region.area < 10:  # Игнорируем очень мелкие объекты
                continue
                
            # Основные геометрические признаки
            features = {
                'area': region.area,
                'perimeter': region.perimeter,
                'eccentricity': region.eccentricity,
                'solidity': region.solidity,
                'extent': region.extent,
                'orientation': abs(region.orientation),  # Абсолютное значение ориентации
                'major_axis_length': region.major_axis_length,
                'minor_axis_length': region.minor_axis_length,
                'equivalent_diameter': region.equivalent_diameter,
                'convex_area': region.convex_area,
                'euler_number': region.euler_number,
                'filled_area': region.filled_area,
                'bbox': region.bbox,
                'coords': region.coords
            }
            
            # Вычисляемые признаки
            features['aspect_ratio'] = (features['major_axis_length'] / 
                                      max(features['minor_axis_length'], 1e-6))
            
            # Соотношение площади к площади ограничивающего прямоугольника
            bbox = region.bbox
            bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            features['bbox_area_ratio'] = features['area'] / max(bbox_area, 1)
            
            # Новые признаки для лучшего определения линий
            # Компактность (круглость) - линии имеют низкую компактность
            features['compactness'] = (4 * np.pi * features['area']) / max(features['perimeter'] ** 2, 1e-6)
            
            # Удлинение (альтернативный расчет соотношения сторон)
            features['elongation'] = features['major_axis_length'] / max(features['minor_axis_length'], 1e-6)
            
            # Соотношение периметра к площади - у линий высокое
            features['perimeter_area_ratio'] = features['perimeter'] / max(features['area'], 1)
            
            # Соотношение ширины к высоте ограничивающего прямоугольника
            bbox_width = bbox[3] - bbox[1]
            bbox_height = bbox[2] - bbox[0]
            features['width_height_ratio'] = max(bbox_width, bbox_height) / max(min(bbox_width, bbox_height), 1)
            
            # Выпуклость (отношение площади к выпуклой площади)
            features['convexity'] = features['area'] / max(features['convex_area'], 1)
            
            # Моменты Ху (только первые 3 для ускорения)
            try:
                y1, x1, y2, x2 = bbox
                roi = binary_image[y1:y2, x1:x2]
                if roi.size > 0:
                    moments = cv2.moments(roi.astype(np.uint8))
                    hu_moments = cv2.HuMoments(moments)
                    features['hu_moments_0'] = abs(hu_moments[0][0])
                    features['hu_moments_1'] = abs(hu_moments[1][0])
                    features['hu_moments_2'] = abs(hu_moments[2][0])
                else:
                    features['hu_moments_0'] = 0
                    features['hu_moments_1'] = 0
                    features['hu_moments_2'] = 0
            except:
                features['hu_moments_0'] = 0
                features['hu_moments_1'] = 0
                features['hu_moments_2'] = 0
            
            features_list.append(features)
        
        return features_list
    
    def create_training_data(self, binary_image, interactive=True):
        """
        Создает обучающие данные путем интерактивной разметки
        
        Args:
            binary_image (numpy.ndarray): Бинарное изображение
            interactive (bool): Использовать интерактивную разметку
            
        Returns:
            tuple: (features, labels) - признаки и метки классов
        """
        features_list = self.extract_shape_features(binary_image)
        
        if not features_list:
            return np.array([]), np.array([])
        
        if not interactive:
            # Автоматическая разметка на основе эвристик
            labels = self._auto_label_features(features_list)
        else:
            # Интерактивная разметка (упрощенная версия)
            labels = self._interactive_labeling(binary_image, features_list)
        
        # Преобразуем в массивы numpy
        feature_matrix = self._features_to_matrix(features_list)
        
        return feature_matrix, np.array(labels)
    
    def _auto_label_features(self, features_list):
        """
        Автоматическая разметка на основе эвристических правил
        
        Args:
            features_list (list): Список признаков
            
        Returns:
            list: Метки классов (0 - пора, 1 - линия)
        """
        labels = []
        
        for features in features_list:
            # Улучшенные эвристические правила для определения линий
            aspect_ratio = features['aspect_ratio']
            eccentricity = features['eccentricity']
            solidity = features['solidity']
            area = features['area']
            perimeter = features['perimeter']
            
            # Вычисляем дополнительные метрики
            compactness = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
            elongation = features['major_axis_length'] / max(features['minor_axis_length'], 1e-6)
            
            # Условие 1: Классические длинные тонкие объекты
            condition1 = (
                aspect_ratio > 3.5 and  # Снижен порог для лучшего захвата
                eccentricity > 0.85 and  # Снижен порог
                area > 20  # Снижен минимальный размер
            )
            
            # Условие 2: Очень тонкие линии
            condition2 = (
                aspect_ratio > 5 and
                area > 15
            )
            
            # Условие 3: Линии средней длины с высокой вытянутостью
            condition3 = (
                elongation > 4 and
                eccentricity > 0.8 and
                solidity > 0.7 and
                area > 25
            )
            
            # Условие 4: Компактность (линии имеют низкую компактность)
            condition4 = (
                compactness < 0.3 and  # Низкая компактность
                aspect_ratio > 2.5 and
                area > 30
            )
            
            # Условие 5: Очень длинные объекты независимо от других параметров
            condition5 = (
                features['major_axis_length'] > 40 and
                aspect_ratio > 2.0
            )
            
            is_line = condition1 or condition2 or condition3 or condition4 or condition5
            
            labels.append(1 if is_line else 0)
        
        return labels
    
    def _interactive_labeling(self, binary_image, features_list):
        """
        Упрощенная интерактивная разметка (для демонстрации)
        
        Args:
            binary_image (numpy.ndarray): Бинарное изображение
            features_list (list): Список признаков
            
        Returns:
            list: Метки классов
        """
        # В реальном случае здесь была бы полноценная интерактивная разметка
        # Пока используем автоматическую разметку
        return self._auto_label_features(features_list)
    
    def _features_to_matrix(self, features_list):
        """
        Преобразует список признаков в матрицу
        
        Args:
            features_list (list): Список словарей с признаками
            
        Returns:
            numpy.ndarray: Матрица признаков
        """
        feature_matrix = []
        
        for features in features_list:
            row = []
            for feature_name in self.feature_names:
                value = features.get(feature_name, 0)
                # Обработка nan и inf значений
                if np.isnan(value) or np.isinf(value):
                    value = 0
                row.append(value)
            feature_matrix.append(row)
        
        return np.array(feature_matrix)
    
    def train_model(self, training_images, validation_split=0.2, save_path=None):
        """
        Обучает модель классификатора
        
        Args:
            training_images (list): Список бинарных изображений для обучения
            validation_split (float): Доля данных для валидации
            save_path (str, optional): Путь для сохранения модели
            
        Returns:
            dict: Метрики обучения
        """
        all_features = []
        all_labels = []
        
        print("Извлечение признаков из обучающих изображений...")
        
        for i, image in enumerate(training_images):
            print(f"Обработка изображения {i+1}/{len(training_images)}")
            features, labels = self.create_training_data(image, interactive=False)
            
            if len(features) > 0:
                all_features.append(features)
                all_labels.extend(labels)
        
        if not all_features:
            raise ValueError("Не удалось извлечь признаки из обучающих данных")
        
        # Объединяем все признаки
        X = np.vstack(all_features)
        y = np.array(all_labels)
        
        print(f"Всего образцов: {len(X)}")
        print(f"Пор: {np.sum(y == 0)}, Линий: {np.sum(y == 1)}")
        
        # Разделяем на обучающую и валидационную выборки
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        # Обучаем Random Forest
        self.model = RandomForestClassifier(
            n_estimators=200,  # Увеличено количество деревьев
            max_depth=15,  # Увеличена глубина
            min_samples_split=3,  # Уменьшено для лучшего обучения
            min_samples_leaf=1,  # Уменьшено
            class_weight='balanced',  # Автоматическая балансировка классов
            random_state=42,
            n_jobs=-1,
            max_features='sqrt'  # Улучшает обобщение
        )
        
        print("Обучение модели...")
        self.model.fit(X_train, y_train)
        
        # Оценка модели
        train_score = self.model.score(X_train, y_train)
        val_score = self.model.score(X_val, y_val)
        
        y_pred = self.model.predict(X_val)
        
        print(f"Точность на обучающей выборке: {train_score:.3f}")
        print(f"Точность на валидационной выборке: {val_score:.3f}")
        print("\nОтчет по классификации:")
        print(classification_report(y_val, y_pred, target_names=['Поры', 'Линии']))
        
        # Важность признаков
        feature_importance = self.model.feature_importances_
        importance_pairs = list(zip(self.feature_names, feature_importance))
        importance_pairs.sort(key=lambda x: x[1], reverse=True)
        
        print("\nВажность признаков:")
        for feature, importance in importance_pairs[:10]:
            print(f"{feature}: {importance:.3f}")
        
        # Сохранение модели
        if save_path:
            self.save_model(save_path)
            print(f"Модель сохранена в {save_path}")
        
        return {
            'train_score': train_score,
            'val_score': val_score,
            'classification_report': classification_report(y_val, y_pred, target_names=['Поры', 'Линии'])
        }
    
    def detect_and_exclude_lines(self, image, dilation_size=5, confidence_threshold=0.5):
        """
        Основная функция для детекции и исключения линий
        
        Args:
            image (numpy.ndarray): Входное изображение в оттенках серого
            dilation_size (int): Размер ядра для расширения найденных линий
            confidence_threshold (float): Порог уверенности для классификации
            
        Returns:
            numpy.ndarray: Маска для исключения линий (True там, где линии нет)
        """
        if self.model is None:
            raise ValueError("Модель не обучена. Используйте train_model() или load_model()")
        
        # Предобработка изображения
        binary_image = self._preprocess_image(image)
        
        # Извлечение признаков
        features_list = self.extract_shape_features(binary_image)
        
        if not features_list:
            return np.ones_like(image, dtype=bool)
        
        # Классификация с вероятностями
        features_matrix = self._features_to_matrix(features_list)
        probabilities = self.model.predict_proba(features_matrix)
        predictions = probabilities[:, 1] > confidence_threshold  # Вероятность быть линией
        
        # Дополнительная геометрическая фильтрация
        refined_predictions = self._refine_line_detection(features_list, predictions)
        
        # Создание маски линий
        lines_mask = np.zeros_like(image, dtype=bool)
        
        for i, (features, is_line) in enumerate(zip(features_list, refined_predictions)):
            if is_line:  # Если объект классифицирован как линия
                coords = features['coords']
                lines_mask[coords[:, 0], coords[:, 1]] = True
        
        # Расширение маски линий
        if np.any(lines_mask) and dilation_size > 0:
            dilation_kernel = disk(dilation_size)
            lines_mask = dilation(lines_mask, dilation_kernel)
        
        # Инвертируем маску (True там, где НЕТ линий)
        final_mask = ~lines_mask
        
        print(f"Обнаружено {np.sum(refined_predictions)} линейных объектов")
        print(f"Исключено {np.sum(lines_mask)} пикселей ({(np.sum(lines_mask)/image.size)*100:.2f}%)")
        
        return final_mask
    
    def _refine_line_detection(self, features_list, ml_predictions):
        """
        Дополнительная фильтрация результатов ML на основе геометрических правил
        
        Args:
            features_list (list): Список признаков объектов
            ml_predictions (numpy.ndarray): Предсказания ML модели
            
        Returns:
            numpy.ndarray: Уточненные предсказания
        """
        refined = []
        
        for i, (features, ml_pred) in enumerate(zip(features_list, ml_predictions)):
            # Базовое предсказание модели
            is_line = ml_pred
            
            # Дополнительные геометрические проверки
            aspect_ratio = features['aspect_ratio']
            area = features['area']
            compactness = features.get('compactness', 0)
            elongation = features.get('elongation', 1)
            
            # Усиливаем детекцию для явно линейных объектов
            if (aspect_ratio > 6 or elongation > 8 or 
                (compactness < 0.2 and aspect_ratio > 3)):
                is_line = True
            
            # Исключаем явно круглые объекты (поры)
            if (compactness > 0.6 and aspect_ratio < 2 and 
                features['eccentricity'] < 0.7):
                is_line = False
            
            # Исключаем слишком мелкие объекты
            if area < 10:
                is_line = False
                
            refined.append(is_line)
        
        return np.array(refined)
    
    def _preprocess_image(self, image):
        """
        Предобработка изображения для бинаризации
        
        Args:
            image (numpy.ndarray): Входное изображение
            
        Returns:
            numpy.ndarray: Бинарное изображение
        """
        # Гауссово размытие для уменьшения шума
        blurred = cv2.GaussianBlur(image.astype(np.uint8), (3, 3), 0)
        
        # Применяем морфологический градиент для выделения краев
        kernel_grad = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        gradient = cv2.morphologyEx(blurred, cv2.MORPH_GRADIENT, kernel_grad)
        
        # Комбинированная бинаризация
        # 1. Адаптивная бинаризация
        binary1 = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # 2. Бинаризация градиента (хорошо выделяет линии)
        _, binary2 = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Объединяем результаты
        binary = cv2.bitwise_or(binary1, binary2)
        
        # Морфологическое закрытие для соединения разорванных линий
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)
        
        # Морфологическое открытие для удаления мелкого шума
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)
        
        return binary.astype(bool)
    
    def save_model(self, filepath):
        """
        Сохраняет обученную модель
        
        Args:
            filepath (str): Путь для сохранения модели
        """
        if self.model is None:
            raise ValueError("Нет модели для сохранения")
        
        # Создаем папку для модели, если её нет
        model_dir = os.path.dirname(filepath)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names
        }
        
        joblib.dump(model_data, filepath)
    
    def load_model(self, filepath):
        """
        Загружает обученную модель
        
        Args:
            filepath (str): Путь к файлу модели
        """
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
    
    def analyze_detection_quality(self, image, confidence_thresholds=[0.3, 0.5, 0.7], 
                                 dilation_sizes=[3, 5, 7]):
        """
        Анализирует качество детекции с разными параметрами
        
        Args:
            image (numpy.ndarray): Входное изображение
            confidence_thresholds (list): Список порогов уверенности для тестирования
            dilation_sizes (list): Список размеров расширения для тестирования
            
        Returns:
            dict: Результаты анализа с рекомендуемыми параметрами
        """
        if self.model is None:
            raise ValueError("Модель не обучена. Используйте train_model() или load_model()")
        
        binary_image = self._preprocess_image(image)
        features_list = self.extract_shape_features(binary_image)
        
        if not features_list:
            return {"error": "Не найдено объектов для анализа"}
        
        features_matrix = self._features_to_matrix(features_list)
        probabilities = self.model.predict_proba(features_matrix)
        
        results = {}
        
        print("Анализ качества детекции линий:")
        print("=" * 50)
        
        for conf_thresh in confidence_thresholds:
            for dil_size in dilation_sizes:
                predictions = probabilities[:, 1] > conf_thresh
                refined_predictions = self._refine_line_detection(features_list, predictions)
                
                # Создаем маску
                lines_mask = np.zeros_like(image, dtype=bool)
                for features, is_line in zip(features_list, refined_predictions):
                    if is_line:
                        coords = features['coords']
                        lines_mask[coords[:, 0], coords[:, 1]] = True
                
                if np.any(lines_mask) and dil_size > 0:
                    dilation_kernel = disk(dil_size)
                    lines_mask = dilation(lines_mask, dilation_kernel)
                
                excluded_percentage = (np.sum(lines_mask) / image.size) * 100
                detected_lines = np.sum(refined_predictions)
                
                key = f"conf_{conf_thresh}_dil_{dil_size}"
                results[key] = {
                    'confidence_threshold': conf_thresh,
                    'dilation_size': dil_size,
                    'detected_lines': detected_lines,
                    'excluded_percentage': excluded_percentage,
                    'excluded_pixels': np.sum(lines_mask)
                }
                
                print(f"Порог: {conf_thresh}, Расширение: {dil_size} -> "
                      f"Линий: {detected_lines}, Исключено: {excluded_percentage:.2f}%")
        
        # Рекомендуемые параметры (баланс между чувствительностью и точностью)
        best_params = min(results.items(), 
                         key=lambda x: abs(x[1]['excluded_percentage'] - 5))  # Целевое исключение ~5%
        
        print("\nРекомендуемые параметры:")
        print(f"confidence_threshold: {best_params[1]['confidence_threshold']}")
        print(f"dilation_size: {best_params[1]['dilation_size']}")
        
        return results


def create_sample_training_data(image_paths=None, save_path=None):
    """
    Создает и обучает модель на примерных данных
    
    Args:
        image_paths (list, optional): Пути к изображениям для обучения
        save_path (str): Путь для сохранения модели
        
    Returns:
        MLLineDetector: Обученный детектор
    """
    # Если путь не указан, используем глобальную папку trained_models
    if save_path is None:
        import os
        from django.conf import settings
        trained_models_dir = os.path.join(settings.BASE_DIR, "trained_models")
        os.makedirs(trained_models_dir, exist_ok=True)
        save_path = os.path.join(trained_models_dir, "ml_line_detector.pkl")
    detector = MLLineDetector()
    
    if image_paths is None:
        # Создаем синтетические данные для демонстрации
        training_images = []
        
        for i in range(5):
            # Создаем синтетическое изображение с порами и линиями
            img = np.zeros((200, 200), dtype=np.uint8)
            
            # Добавляем круглые поры
            for _ in range(10):
                center = (np.random.randint(20, 180), np.random.randint(20, 180))
                radius = np.random.randint(3, 8)
                cv2.circle(img, center, radius, 255, -1)
            
            # Добавляем линии
            for _ in range(3):
                start = (np.random.randint(0, 200), np.random.randint(0, 200))
                end = (np.random.randint(0, 200), np.random.randint(0, 200))
                cv2.line(img, start, end, 255, 2)
            
            # Преобразуем в булево для алгоритма
            training_images.append(img > 0)
    else:
        # Загружаем реальные изображения
        training_images = []
        for path in image_paths:
            print(f"Загрузка изображения: {path}")
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                print(f"  Размер изображения: {img.shape}")
                binary = detector._preprocess_image(img)
                training_images.append(binary)
            else:
                print(f"  Предупреждение: не удалось загрузить изображение {path}")
    
    # Обучаем модель
    if training_images:
        print(f"Обучение на {len(training_images)} изображениях...")
        detector.train_model(training_images, save_path=save_path)
    else:
        print("Ошибка: нет доступных изображений для обучения")
    
    return detector


if __name__ == "__main__":
    # Пример использования улучшенного детектора
    print("Создание и обучение улучшенной модели детектора линий...")
    
    # Создаем детектор с синтетическими данными
    detector = create_sample_training_data()
    
    print("\nДетектор готов к использованию!")
    print("\nДля использования с реальными изображениями:")
    print("1. Загрузите изображение: img = cv2.imread('path_to_image.jpg', cv2.IMREAD_GRAYSCALE)")
    print("2. Проанализируйте качество: detector.analyze_detection_quality(img)")
    print("3. Настройте параметры и детектируйте: mask = detector.detect_and_exclude_lines(img, confidence_threshold=0.4)")
    print("4. Примените маску для исключения линий в анализе пористости")
    
    print("\nНовые улучшения:")
    print("- Более точные эвристические правила для линий")
    print("- Дополнительные признаки (компактность, удлинение и др.)")
    print("- Улучшенная предобработка с морфологическим градиентом")
    print("- Балансировка классов в модели")
    print("- Дополнительная геометрическая фильтрация")
    print("- Анализ качества детекции с разными параметрами") 