from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Union, Callable

class BaseHandler(ABC):
    """Базовый класс для всех обработчиков."""
    
    # Словарь соответствия типов Python для конвертации
    TYPE_CONVERTERS: Dict[Type, Callable] = {
        int: int,
        float: float,
        bool: lambda x: str(x).lower() == 'true',
        str: str
    }
    
    def __init__(self, required_params: list = None, optional_params: Dict[str, Any] = None):
        """
        Инициализация обработчика.
        
        Args:
            required_params: Список обязательных параметров
            optional_params: Словарь опциональных параметров с их значениями по умолчанию
        """
        self.required_params = required_params or []
        self.optional_params = optional_params or {}
        self.params: Dict[str, Any] = {}
    
    def validate_params(self, **kwargs) -> None:
        """
        Проверяет наличие всех обязательных параметров.
        
        Raises:
            ValueError: Если отсутствуют обязательные параметры
        """
        if missing_params := set(self.required_params) - set(kwargs):
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
    
    def convert_param_type(self, param_name: str, param_value: Any) -> Any:
        """
        Конвертирует значение параметра в правильный тип на основе optional_params.
        
        Args:
            param_name: Имя параметра
            param_value: Значение параметра

        Returns:
            Сконвертированное значение параметра
        """
        if param_name not in self.optional_params:
            return param_value
            
        default_value = self.optional_params[param_name]
        converter = self.TYPE_CONVERTERS.get(type(default_value))
        
        if not converter:
            return param_value
            
        try:
            return converter(param_value)
        except (ValueError, TypeError):
            return default_value
    
    def prepare_params(self, **kwargs) -> None:
        """
        Подготавливает параметры, добавляя значения по умолчанию и конвертируя типы.
        
        Args:
            **kwargs: Входящие параметры
        """
        self.params = {
            key: self.convert_param_type(key, value)
            for key, value in {**self.optional_params, **kwargs}.items()
        }
    
    @abstractmethod
    def process(self) -> Dict[str, Any]:
        """
        Основная логика обработчика.
        
        Returns:
            Dict[str, Any]: Результат обработки
        """
        pass
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Точка входа в обработчик.
        
        Args:
            **kwargs: Входящие параметры

        Returns:
            Dict[str, Any]: Результат обработки
        """
        self.validate_params(**kwargs)
        self.prepare_params(**kwargs)
        return self.process() 