def reconstruct_class_code(dynamic_class):
    # Имя класса
    class_name = dynamic_class.__name__
    # Базовый класс
    base_classes = "APIView"

    # Собираем атрибуты
    attributes = []
    for attr_name, attr_value in dynamic_class.__dict__.items():
        if not callable(attr_value) and not attr_name.startswith("__"):
            if attr_name in ["permission_classes", "throttle_classes", "renderer_classes"]:
                # Преобразуем список классов в имена классов
                formatted_permissions = [cls.__name__ for cls in attr_value]
                attributes.append(f"    {attr_name} = [{', '.join(formatted_permissions)}]")
            else:
                attributes.append(f"    {attr_name} = {repr(attr_value)}")

    for attr_name, attr_value in dynamic_class.__base__.__dict__.items():
        if not callable(attr_value) and not attr_name.startswith("__"):
            if attr_name in ["permission_classes", "throttle_classes", "renderer_classes"]:
                # Преобразуем список классов в имена классов
                formatted_permissions = [cls.__name__ for cls in attr_value]
                attributes.append(f"    {attr_name} = [{', '.join(formatted_permissions)}]")
            else:
                attributes.append(f"    {attr_name} = {repr(attr_value)}")

    # Собираем методы
    methods = []
    for attr_name, attr_value in dynamic_class.__dict__.items():
        if callable(attr_value) and not attr_name.startswith("__"):
            try:
                import inspect
                method_code = inspect.getsource(attr_value)  # Попробуем получить код метода
                methods.append(method_code.replace("def ", "    def "))
            except Exception:
                # Если код недоступен, оставляем заглушку
                methods.append(f"    def {attr_name}(self):\n        pass  # Original code unavailable")

    for attr_name, attr_value in dynamic_class.__base__.__dict__.items():
        if callable(attr_value) and not attr_name.startswith("__"):
            try:
                import inspect
                method_code = inspect.getsource(attr_value)  # Попробуем получить код метода
                methods.append(method_code.replace("def ", "    def "))
            except Exception:
                # Если код недоступен, оставляем заглушку
                methods.append(f"    def {attr_name}(self):\n        pass  # Original code unavailable")

    # Формируем код класса
    class_code = f"class {class_name}({base_classes}):\n"
    if attributes:
        class_code += "\n".join(attributes) + "\n"
    if methods:
        class_code += "\n".join(methods)
    else:
        class_code += "    pass  # No methods or attributes found\n"

    if (class_name == "Tasks1GraphView"):
        print(class_code)

    return class_code