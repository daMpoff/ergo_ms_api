import json
import random
import string

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_random_email():
    return f"{generate_random_string(8)}@{generate_random_string(5)}.com"

def generate_random_grade():
    return random.choice(['A', 'B', 'C', 'D', 'F'])

def get_courses(num_courses, num_students, num_grades):
    # Генерация данных о курсах
    courses = [
        {"id": i + 1, "name": f"Course {i + 1}", "description": generate_random_string(50)}
        for i in range(num_courses)
    ]

    # Генерация данных о студентах
    students = [
        {"id": i + 1, "name": f"Student {i + 1}", "email": generate_random_email()}
        for i in range(num_students)
    ]

    # Генерация данных об оценках
    grades = [
        {"student_id": random.randint(1, num_students), "course_id": random.randint(1, num_courses), "grade": generate_random_grade()}
        for _ in range(num_grades)
    ]

    # Формирование структуры данных для JSON
    lms_data = {
        "courses": courses,
        "students": students,
        "grades": grades
    }

    return lms_data